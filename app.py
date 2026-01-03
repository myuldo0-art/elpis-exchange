import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import time
import random
import json
import os
import gspread
from google.oauth2.service_account import Credentials

# --- [0. 구글 시트 DB 연결 설정] ---
# Streamlit Secrets에서 키 가져오기 & 캐싱
@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

# --- [데이터 영구 저장 시스템 : 구글 시트 버전] ---
# 복잡한 객체 구조를 유지하기 위해 JSON String 형태로 시트 A1 셀에 통째로 저장/로드합니다.

def load_db():
    """구글 시트에서 전체 데이터를 JSON으로 불러옴"""
    try:
        client = init_connection()
        sh = client.open("ELPIS_DB") # 구글 시트 파일명
        worksheet = sh.worksheet("JSON_DATA") # 탭 이름
        
        # A1 셀의 데이터를 가져옴 (매우 긴 텍스트)
        raw_data = worksheet.acell('A1').value
        
        if raw_data:
            return json.loads(raw_data)
        return None
    except Exception as e:
        # DB가 비어있거나 연결 실패 시 None 반환 -> 초기화 로직으로 이동
        print(f"DB Load Error: {e}")
        return None

def save_db():
    """현재 session_state의 핵심 데이터를 구글 시트에 백업"""
    # 저장할 데이터 추출
    data = {
        'user_db': st.session_state['user_db'],
        'user_names': st.session_state['user_names'],
        'market_data': st.session_state['market_data'],
        'trade_history': st.session_state['trade_history'],
        'board_messages': st.session_state['board_messages'],
        'user_states': st.session_state.get('user_states', {}),
        'pending_orders': st.session_state.get('pending_orders', []),
        'interested_codes': list(st.session_state.get('interested_codes', []))
    }
    
    try:
        client = init_connection()
        sh = client.open("ELPIS_DB")
        worksheet = sh.worksheet("JSON_DATA")
        
        # 데이터를 JSON 문자열로 변환
        json_str = json.dumps(data, ensure_ascii=False)
        
        # A1 셀에 덮어쓰기
        worksheet.update_acell('A1', json_str)
        
    except Exception as e:
        st.error(f"데이터 저장 실패 (네트워크 문제일 수 있음): {e}")

# --- [페이지 설정] ---
st.set_page_config(layout="wide", page_title="ELPIS EXCHANGE", page_icon="📈")

# --- [CSS 스타일 : 프리미엄 금융 앱 디자인 (원본 유지)] ---
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    /* [Pull-to-Refresh 차단] */
    html, body, .stApp {
        overscroll-behavior-y: none !important;
        overscroll-behavior: none !important;
    }
    div[data-testid="stAppViewContainer"] {
        overscroll-behavior-y: none !important;
        overscroll-behavior: none !important;
    }

    /* [전체 레이아웃] */
    html, body, .stApp {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
        background-color: #F2F4F6;
        color: #191F28;
    }
    .main { background-color: #F2F4F6; }
    
    /* [카드 디자인] */
    div[data-testid="stVerticalBlock"] > div { background-color: transparent; }
    .stMetric {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E8EB !important;
        border-radius: 16px !important;
        padding: 15px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }
    
    /* [버튼 스타일] */
    .stButton>button {
        width: 100%;
        border-radius: 12px !important;
        font-weight: 600 !important;
        height: 52px !important;
        font-size: 16px !important;
        border: none !important;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    button[kind="primary"] { background-color: #3182F6 !important; color: white !important; }
    button[kind="primary"]:hover { background-color: #1B64DA !important; }
    button[kind="secondary"] { background-color: #FFFFFF !important; color: #4E5968 !important; border: 1px solid #D1D6DB !important; }
    
    /* [입력 필드] */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D6DB !important;
        border-radius: 10px !important;
        height: 48px !important;
        font-size: 16px !important;
        color: #191F28 !important;
    }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
        border-color: #3182F6 !important;
        box-shadow: 0 0 0 2px rgba(49, 130, 246, 0.2) !important;
    }

    /* [텍스트 컬러] */
    .up-text { color: #E22A2A !important; font-weight: 700; }
    .down-text { color: #2A6BE2 !important; font-weight: 700; }
    .flat-text { color: #333333 !important; font-weight: 700; }
    .small-gray { font-size: 13px; color: #8B95A1; margin-top: 2px; }
    
    /* [프로필 카드] */
    .profile-card {
        background: white;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #F2F4F6;
    }
    .profile-card h2 { margin: 0; font-size: 22px; color: #191F28; }
    .profile-card p { color: #4E5968; font-size: 14px; margin: 8px 0; }
    
    /* [호가창] */
    .hoga-container {
        font-family: 'Pretendard', sans-serif;
        font-size: 14px;
        width: 100%;
        background: white;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #E5E8EB;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .hoga-row { display: flex; height: 38px; align-items: center; border-bottom: 1px solid #F9FAFB; }
    .sell-bg { background-color: rgba(66, 133, 244, 0.04); }
    .buy-bg { background-color: rgba(234, 67, 53, 0.04); }
    .cell-vol { flex: 1; text-align: right; padding-right: 12px; color: #4E5968; font-size: 12px; letter-spacing: -0.5px; }
    .cell-price { 
        flex: 1.2; text-align: center; font-weight: 700; font-size: 15px; 
        background-color: #ffffff; 
        border-left: 1px solid #F2F4F6; border-right: 1px solid #F2F4F6;
        cursor: pointer;
    }
    .cell-vol-buy { flex: 1; text-align: left; padding-left: 12px; color: #4E5968; font-size: 12px; letter-spacing: -0.5px; }
    .cell-empty { flex: 1; }
    .price-up { color: #E22A2A; }
    .price-down { color: #2A6BE2; }
    .current-price-box { border: 2px solid #191F28 !important; background-color: #FFF !important; color: #191F28 !important; font-size: 16px !important; }
    
    /* [채팅] */
    .chat-box {
        background-color: #FFFFFF;
        padding: 14px;
        border-radius: 16px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #F2F4F6;
    }
    .chat-user { font-weight: 700; font-size: 14px; color: #191F28; margin-bottom: 4px; }
    .chat-msg { font-size: 15px; color: #333D4B; line-height: 1.4; }
    .chat-time { font-size: 11px; color: #8B95A1; text-align: right; margin-top: 4px; }
    
    /* [탭] */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: white; padding: 10px; border-radius: 12px; border: 1px solid #E5E8EB; }
    .stTabs [data-baseweb="tab"] { height: 40px; border-radius: 8px; font-weight: 600; font-size: 14px; color: #4E5968; }
    .stTabs [aria-selected="true"] { background-color: #F2F4F6 !important; color: #191F28 !important; }
    .big-font { font-size: 32px; font-weight: 800; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)


# --- [데이터 초기화 및 로드] ---
if 'initialized' not in st.session_state:
    st.session_state['initialized'] = True
    st.session_state['logged_in'] = False 
    st.session_state['user_info'] = {}
    st.session_state['view_profile_id'] = None
    
    with st.spinner('클라우드 서버(Google Sheets)에서 데이터 불러오는 중...'):
        saved_data = load_db()
    
    if saved_data:
        st.session_state['user_db'] = saved_data['user_db']
        st.session_state['user_names'] = saved_data['user_names']
        st.session_state['market_data'] = saved_data['market_data']
        st.session_state['trade_history'] = saved_data['trade_history']
        st.session_state['board_messages'] = saved_data['board_messages']
        st.session_state['user_states'] = saved_data['user_states']
        st.session_state['pending_orders'] = saved_data.get('pending_orders', [])
        st.session_state['interested_codes'] = set(saved_data.get('interested_codes', ['IU', 'G_DRAGON', 'ELON', 'DEV_MASTER']))
    else:
        # [초기 데이터 생성 - DB가 비어있을 때 최초 1회 실행]
        st.session_state['user_db'] = {'test': '1234'} 
        st.session_state['user_names'] = {'test': '테스터'}
        st.session_state['user_states'] = {
            'test': {
                'balance_id': 10000000.0,
                'my_elpis_locked': 1000000,
                'portfolio': {},
                'my_profile': {'vision': '', 'sns': '', 'photo': None},
                'last_mining_time': None
            }
        }
        
        st.session_state['market_data'] = {
            'IU': {'name': '아이유', 'price': 50000, 'change': 2.5, 'desc': '국내 원탑 솔로 가수', 'history': [48000, 49000, 50000]},
            'G_DRAGON': {'name': '지드래곤', 'price': 45000, 'change': -1.2, 'desc': 'K-POP의 아이콘', 'history': [46000, 45500, 45000]},
            'ELON': {'name': '일론 머스크', 'price': 120000, 'change': 5.8, 'desc': '화성으로 가는 남자', 'history': [110000, 115000, 120000]},
            'DEV_MASTER': {'name': '50년코딩장인', 'price': 10000, 'change': 0.0, 'desc': '이 앱을 만든 개발자', 'history': [10000]}
        }
        
        # 봇 생성 로직
        bot_profiles = [
            ("김철수", "경제적 자유", "instagram.com/chulsoo"),
            ("이영희", "건물주 목표", "youtube.com/younghee"),
            ("박민수", "100억 자산가", "blog.naver.com/minsu"),
            # ... (나머지 봇들 생략 가능하나 원본 유지를 위해 3개만 예시, 원하면 추가하세요)
        ]
        
        for i in range(5): # 예시로 5명만 생성 (속도 최적화)
            bot_id = f"pppp{i+1}" 
            name = f"Bot_{i+1}"
            
            st.session_state['user_db'][bot_id] = '1234'
            st.session_state['user_names'][bot_id] = name
            st.session_state['user_states'][bot_id] = {
                'balance_id': 10000000.0,
                'my_elpis_locked': 1000000, 
                'portfolio': {},
                'my_profile': {'vision': 'AI Trader', 'sns': '', 'photo': None},
                'last_mining_time': None
            }
            st.session_state['market_data'][bot_id] = {
                'name': name,
                'price': 10000, 
                'change': 0.0,
                'desc': 'AI Bot',
                'history': [10000]
            }

        st.session_state['trade_history'] = []
        st.session_state['board_messages'] = [
            {'code': 'IU', 'user': 'Fan_001', 'msg': '아이유 10만 전자 가즈아!!', 'time': '12:00'},
            {'code': 'ELON', 'user': 'Mars_Lover', 'msg': '화성 갈끄니까~', 'time': '12:05'}
        ]
        st.session_state['pending_orders'] = []
        st.session_state['interested_codes'] = {'IU', 'G_DRAGON', 'ELON', 'DEV_MASTER'}
        save_db()

    st.session_state['selected_code'] = 'IU'


# --- [헬퍼 함수] ---

def sync_user_state(user_id):
    if user_id not in st.session_state['user_states']:
        st.session_state['user_states'][user_id] = {
            'balance_id': 10000000.0,
            'my_elpis_locked': 1000000,
            'portfolio': {},
            'my_profile': {'vision': '', 'sns': '', 'photo': None},
            'last_mining_time': None
        }
    state = st.session_state['user_states'][user_id]
    st.session_state['balance_id'] = state['balance_id']
    st.session_state['my_elpis_locked'] = state['my_elpis_locked']
    st.session_state['portfolio'] = state['portfolio']
    st.session_state['my_profile'] = state['my_profile']
    st.session_state['last_mining_time'] = state.get('last_mining_time', None)

def save_current_user_state(user_id):
    st.session_state['user_states'][user_id] = {
        'balance_id': st.session_state['balance_id'],
        'my_elpis_locked': st.session_state['my_elpis_locked'],
        'portfolio': st.session_state['portfolio'],
        'my_profile': st.session_state['my_profile'],
        'last_mining_time': st.session_state['last_mining_time']
    }
    # 사진 데이터는 JSON 저장이 어려우므로 제외 (실제 배포시엔 S3 등 필요)
    temp_profile = st.session_state['my_profile'].copy()
    temp_profile['photo'] = None 
    st.session_state['user_states'][user_id]['my_profile'] = temp_profile
    
    # [중요] 상태 변경 시 구글 시트에 저장
    save_db()

def update_price_match(market_code, price):
    market = st.session_state['market_data'][market_code]
    market['price'] = price
    market['change'] = round(((price - market['history'][0]) / market['history'][0]) * 100, 2)
    market['history'].append(price)

# --- [리얼 매칭 엔진] ---

def place_order(type, code, price, qty):
    market = st.session_state['market_data'][code]
    user_id = st.session_state['user_info']['id']
    
    if type == 'BUY':
        total_cost = price * qty
        if st.session_state['balance_id'] < total_cost:
            return False, "이드(잔고)가 부족합니다."
            
        st.session_state['balance_id'] -= total_cost
        
        sells = [o for o in st.session_state['pending_orders'] if o['code'] == code and o['type'] == 'SELL' and o['price'] <= price]
        sells.sort(key=lambda x: x['price']) 
        
        remaining_qty = qty
        
        for sell_order in sells:
            if remaining_qty <= 0: break
            if sell_order['user'] == user_id: continue 
            
            match_qty = min(remaining_qty, sell_order['qty'])
            match_price = sell_order['price'] 
            seller_id = sell_order['user']
            
            if code in st.session_state['portfolio']:
                old_qty = st.session_state['portfolio'][code]['qty']
                old_avg = st.session_state['portfolio'][code]['avg_price']
                new_avg = ((old_qty * old_avg) + (match_qty * match_price)) / (old_qty + match_qty)
                st.session_state['portfolio'][code]['qty'] += match_qty
                st.session_state['portfolio'][code]['avg_price'] = int(new_avg)
            else:
                st.session_state['portfolio'][code] = {'qty': match_qty, 'avg_price': match_price}
            
            refund = (price - match_price) * match_qty
            if refund > 0: st.session_state['balance_id'] += refund
            
            if seller_id in st.session_state['user_states']:
                s_state = st.session_state['user_states'][seller_id]
                s_state['balance_id'] += (match_price * match_qty)
            
            sell_order['qty'] -= match_qty
            remaining_qty -= match_qty
            
            update_price_match(code, match_price)
            
            st.session_state['trade_history'].insert(0, {
                'time': datetime.datetime.now().strftime("%H:%M:%S"), 
                'type': '체결(매수)', 
                'name': market['name'], 
                'price': match_price, 
                'qty': match_qty,
                'buyer': user_id,      
                'seller': seller_id    
            })

        st.session_state['pending_orders'] = [o for o in st.session_state['pending_orders'] if o['qty'] > 0]
        
        if remaining_qty > 0:
            st.session_state['pending_orders'].append({'code': code, 'type': 'BUY', 'price': price, 'qty': remaining_qty, 'user': user_id})
            save_current_user_state(user_id) 
            return True, f"{qty-remaining_qty}주 체결, {remaining_qty}주 대기 중"
        else:
            save_current_user_state(user_id)
            return True, "전량 체결 완료!"

    elif type == 'SELL':
        my_qty = st.session_state['portfolio'].get(code, {}).get('qty', 0)
        if my_qty < qty:
            return False, "보유 수량이 부족합니다."
            
        st.session_state['portfolio'][code]['qty'] -= qty
        if st.session_state['portfolio'][code]['qty'] == 0:
            del st.session_state['portfolio'][code]
            
        buys = [o for o in st.session_state['pending_orders'] if o['code'] == code and o['type'] == 'BUY' and o['price'] >= price]
        buys.sort(key=lambda x: x['price'], reverse=True) 
        
        remaining_qty = qty
        
        for buy_order in buys:
            if remaining_qty <= 0: break
            if buy_order['user'] == user_id: continue 
            
            match_qty = min(remaining_qty, buy_order['qty'])
            match_price = buy_order['price'] 
            buyer_id = buy_order['user']
            
            st.session_state['balance_id'] += (match_price * match_qty)
            
            if buyer_id in st.session_state['user_states']:
                b_state = st.session_state['user_states'][buyer_id]
                if 'portfolio' not in b_state: b_state['portfolio'] = {}
                
                if code in b_state['portfolio']:
                    b_old_qty = b_state['portfolio'][code]['qty']
                    b_old_avg = b_state['portfolio'][code]['avg_price']
                    b_new_avg = ((b_old_qty * b_old_avg) + (match_qty * match_price)) / (b_old_qty + match_qty)
                    b_state['portfolio'][code]['qty'] += match_qty
                    b_state['portfolio'][code]['avg_price'] = int(b_new_avg)
                else:
                    b_state['portfolio'][code] = {'qty': match_qty, 'avg_price': match_price}
            
            buy_order['qty'] -= match_qty
            remaining_qty -= match_qty
            
            update_price_match(code, match_price)
            
            st.session_state['trade_history'].insert(0, {
                'time': datetime.datetime.now().strftime("%H:%M:%S"), 
                'type': '체결(매도)', 
                'name': market['name'], 
                'price': match_price, 
                'qty': match_qty,
                'buyer': buyer_id,    
                'seller': user_id     
            })
            
        st.session_state['pending_orders'] = [o for o in st.session_state['pending_orders'] if o['qty'] > 0]
        
        if remaining_qty > 0:
            st.session_state['pending_orders'].append({'code': code, 'type': 'SELL', 'price': price, 'qty': remaining_qty, 'user': user_id})
            save_current_user_state(user_id)
            return True, f"{qty-remaining_qty}주 체결, {remaining_qty}주 대기 중"
        else:
            save_current_user_state(user_id)
            return True, "전량 체결 완료!"

def mining():
    now = datetime.datetime.now()
    last = st.session_state.get('last_mining_time')
    if last and isinstance(last, str):
        last_dt = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S.%f")
    else:
        last_dt = None
    if last_dt is None or (now - last_dt).total_seconds() > 86400:
        reward = 100000 
        st.session_state['balance_id'] += reward
        st.session_state['last_mining_time'] = str(now)
        save_current_user_state(st.session_state['user_info']['id'])
        return True, reward
    else:
        return False, 0

# ==========================================
# [앱 UI 시작]
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #191F28; font-family: Pretendard;'>ELPIS EXCHANGE</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8B95A1;'>욕망을 태워 희망을 거래하라</p>", unsafe_allow_html=True)
    st.divider()

    auth_tabs = st.tabs(["🔒 로그인", "📝 회원가입"])
    with auth_tabs[0]: 
        l_id = st.text_input("아이디", key="login_id")
        l_pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("접속하기", type="primary"):
            # DB 로드 재확인
            if not st.session_state['user_db']:
                 st.session_state['user_db'] = load_db()['user_db']
            
            if l_id in st.session_state['user_db'] and st.session_state['user_db'][l_id] == l_pw:
                st.session_state['logged_in'] = True
                st.session_state['user_info']['id'] = l_id
                sync_user_state(l_id)
                st.rerun()
            else:
                st.error("정보가 일치하지 않습니다.")
    with auth_tabs[1]:
        r_name = st.text_input("실명")
        r_rrn = st.text_input("주민등록번호 (앞 6자리)", max_chars=6)
        r_phone = st.text_input("휴대폰 번호")
        r_id = st.text_input("아이디", key="reg_id")
        r_pw = st.text_input("비밀번호", type="password", key="reg_pw")
        if st.button("가입하고 1,000만 이드 받기"):
            if r_name and r_rrn and r_phone and r_id and r_pw:
                if r_id in st.session_state['user_db']:
                    st.warning("이미 존재하는 아이디입니다.")
                else:
                    st.session_state['user_db'][r_id] = r_pw
                    st.session_state['user_names'][r_id] = r_name
                    sync_user_state(r_id) 
                    save_current_user_state(r_id)
                    st.success("가입 완료!")
            else:
                st.warning("정보를 입력하세요.")

else:
    user_id = st.session_state['user_info'].get('id', 'Guest')
    user_name = st.session_state['user_names'].get(user_id, '사용자')
    
    # [프로필 모달]
    if st.session_state.get('view_profile_id'):
        target_id = st.session_state['view_profile_id']
        target_name = st.session_state['user_names'].get(target_id, target_id)
        
        p_vision = "정보 없음"
        p_sns = "정보 없음"
        if target_id in st.session_state['user_states']:
            p_vision = st.session_state['user_states'][target_id]['my_profile']['vision']
            p_sns = st.session_state['user_states'][target_id]['my_profile']['sns']
        elif target_id in st.session_state['market_data']:
             p_vision = st.session_state['market_data'][target_id].get('desc', '정보 없음')
        
        st.markdown(f"<div class='profile-card'><h2>👤 {target_name} <small>({target_id})</small></h2><hr style='border: 0; border-top: 1px solid #F2F4F6;'><p><b>Vision:</b> {p_vision}</p><p><b>SNS:</b> {p_sns}</p></div>", unsafe_allow_html=True)
        if st.button("닫기 (Close)", type="secondary"):
            st.session_state['view_profile_id'] = None
            st.rerun()
    
    tabs = st.tabs(["메인화면(프로필)", "관심", "현재가", "주문", "잔고", "내역", "거래소"])

    # [② 탭: 메인화면]
    with tabs[0]:
        with st.container():
            st.markdown(f"<div style='text-align:center;'>", unsafe_allow_html=True)
            col_img1, col_img2, col_img3 = st.columns([1,1,1])
            with col_img2: 
                # 사진 업로드 기능은 로컬 파일 시스템 의존이므로 시각적으로만 표시 (DB저장 X)
                uploaded_file = st.file_uploader("사진", type=['jpg', 'png'], key="profile_upload", label_visibility="collapsed")
                if uploaded_file is not None:
                     st.image(uploaded_file, width=120) 
            
            with col_img3:
                if st.button("로그아웃", key="logout_btn", type="secondary"):
                    st.session_state['logged_in'] = False
                    st.session_state['user_info'] = {}
                    st.rerun()

            st.markdown(f"<h2>{user_name} <span style='font-size:16px; color:#8B95A1'>({user_id})</span></h2>", unsafe_allow_html=True)
            st.caption(st.session_state['my_profile']['vision'] if st.session_state['my_profile']['vision'] else "나의 비전이 없습니다.")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

        total_asset = st.session_state['balance_id']
        for c, d in st.session_state['portfolio'].items():
            total_asset += (d['qty'] * st.session_state['market_data'][c]['price'])

        with st.container():
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"### 💰 총 자산<br><span style='color:#333D4B; font-size:24px; font-weight:bold'>{total_asset:,.0f} ID</span>", unsafe_allow_html=True)
            c2.metric("보유 이드", f"{st.session_state['balance_id']:,.0f}")
            c3.metric("내 엘피스", f"{st.session_state['my_elpis_locked']:,}")
        st.markdown("---")
        
        st.subheader("📝 프로필 수정")
        vision = st.text_area("비전", value=st.session_state['my_profile']['vision'])
        sns = st.text_input("SNS", value=st.session_state['my_profile']['sns'])
        if st.button("저장", type="primary"):
            st.session_state['my_profile']['vision'] = vision
            st.session_state['my_profile']['sns'] = sns
            save_current_user_state(user_id) 
            st.rerun()
        st.divider()
        if st.button("⛏️ 채굴 (Daily Mining)", type="primary"):
            ok, reward = mining()
            if ok: st.balloons(); st.success(f"+{reward:,} ID"); time.sleep(1); st.rerun()
            else: st.warning("이미 채굴했습니다.")
        
        st.divider()
        st.subheader(f"📨 {user_name}님에게 남겨진 메시지")
        my_messages = [m for m in st.session_state['board_messages'] if m['code'] == user_id]
        
        if my_messages:
            for m in my_messages:
                st.markdown(f"<div class='chat-box'><div class='chat-user'>{m['user']} <span style='font-weight:normal; color:#888;'>님이 작성</span></div><div class='chat-msg'>{m['msg']}</div><div class='chat-time'>{m['time']}</div></div>", unsafe_allow_html=True)
        else:
            st.info("아직 도착한 메시지가 없습니다.")

    # [③ 탭: 관심]
    with tabs[1]:
        st.subheader("❤️ 관심 종목")
        h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
        h1.caption("종목명(Click)")
        h2.caption("현재가")
        h3.caption("등락률")
        h4.caption("관리")
        st.divider()

        targets = list(st.session_state['interested_codes'])
        targets = [t for t in targets if t != user_id]

        if not targets:
            st.info("관심 종목이 없습니다. '현재가' 탭에서 검색해보세요.")
        
        for code in targets:
            if code in st.session_state['market_data']:
                info = st.session_state['market_data'][code]
                c_price = info['price']
                c_change = info['change']
                
                if c_change > 0: color_class, arrow = "up-text", "▲"
                elif c_change < 0: color_class, arrow = "down-text", "▼"
                else: color_class, arrow = "flat-text", "-"
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        if st.button(info['name'], key=f"fav_n_{code}", type="secondary"):
                            st.session_state['view_profile_id'] = code
                            st.rerun()
                        st.markdown(f"<div class='small-gray'>{code}</div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"<div class='{color_class}' style='font-size:16px;'>{c_price:,}</div>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<div class='{color_class}' style='font-size:14px;'>{arrow} {c_change}%</div>", unsafe_allow_html=True)
                    with col4:
                        if st.button("✖️", key=f"del_{code}"):
                            st.session_state['interested_codes'].remove(code)
                            save_db()
                            st.rerun()
                st.divider()

    # [④ 탭: 현재가]
    with tabs[2]:
        col_s1, col_s2 = st.columns([3, 1])
        search_q = col_s1.text_input("검색 (ID/이름)", placeholder="종목 검색...", label_visibility="collapsed")
        if col_s2.button("🔍"):
            found = False
            for k, v in st.session_state['market_data'].items():
                if search_q in k or search_q in v['name']:
                    st.session_state['selected_code'] = k
                    st.session_state['interested_codes'].add(k) 
                    save_db()
                    found = True
                    break
            if not found: st.toast("검색 결과가 없습니다.")
            else: st.rerun()

        target = st.session_state['selected_code']
        market = st.session_state['market_data'][target]
        curr_price = market['price']
        change_pct = market['change']
        
        st.markdown(f"### {market['name']} <span style='font-size:14px; color:gray'>$ELP-{target}</span>", unsafe_allow_html=True)
        pc1, pc2 = st.columns(2)
        color_cls = "price-up" if change_pct >= 0 else "price-down"
        pc1.markdown(f"<div class='big-font {color_cls}'>{curr_price:,} ID</div>", unsafe_allow_html=True)
        pc2.markdown(f"<div class='{color_cls}' style='text-align:right; font-size:18px'>{change_pct}%</div>", unsafe_allow_html=True)
        
        pending_orders = [o for o in st.session_state['pending_orders'] if o['code'] == target]
        
        buy_book = {} 
        sell_book = {} 
        
        for o in pending_orders:
            if o['type'] == 'BUY':
                buy_book[o['price']] = buy_book.get(o['price'], 0) + o['qty']
            elif o['type'] == 'SELL':
                sell_book[o['price']] = sell_book.get(o['price'], 0) + o['qty']
        
        best_asks = sorted(sell_book.items(), key=lambda x: x[0])[:5] 
        best_asks.sort(key=lambda x: x[0], reverse=True)
        best_bids = sorted(buy_book.items(), key=lambda x: x[0], reverse=True)[:5]

        hoga_html = "<div class='hoga-container'>"
        
        sell_rows = []
        for p, q in best_asks:
            sell_rows.append((p, q))
        while len(sell_rows) < 5:
            sell_rows.insert(0, (None, None)) 
            
        for p, q in sell_rows:
            if p:
                hoga_html += f"<div class='hoga-row sell-bg'><div class='cell-vol'>{q:,}</div><div class='cell-price price-down'>{p:,}</div><div class='cell-empty'></div></div>"
            else:
                hoga_html += f"<div class='hoga-row sell-bg'><div class='cell-vol'></div><div class='cell-price'></div><div class='cell-empty'></div></div>"
            
        hoga_html += f"<div class='hoga-row'><div class='cell-vol'></div><div class='cell-price {color_cls} current-price-box'>{curr_price:,}</div><div class='cell-empty'></div></div>"
        
        buy_rows = []
        for p, q in best_bids:
            buy_rows.append((p, q))
        while len(buy_rows) < 5:
            buy_rows.append((None, None))
            
        for p, q in buy_rows:
            if p:
                hoga_html += f"<div class='hoga-row buy-bg'><div class='cell-empty'></div><div class='cell-price price-up'>{p:,}</div><div class='cell-vol-buy'>{q:,}</div></div>"
            else:
                 hoga_html += f"<div class='hoga-row buy-bg'><div class='cell-empty'></div><div class='cell-price'></div><div class='cell-vol-buy'></div></div>"
            
        hoga_html += "</div>"
        st.markdown(hoga_html, unsafe_allow_html=True)

        with st.expander("📊 차트", expanded=True):
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=market['history'], mode='lines+markers', line=dict(color='#E22A2A', width=2)))
            fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), dragmode=False, paper_bgcolor='white', plot_bgcolor='#F2F4F6')
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': False, 'displayModeBar': False})

        st.divider()
        st.subheader(f"💬 {market['name']} 토론방 (방명록)")
        with st.form(key='msg_form', clear_on_submit=True):
            user_msg = st.text_input("메시지", placeholder="응원/방명록 남기기")
            if st.form_submit_button("등록", type="primary") and user_msg:
                st.session_state['board_messages'].insert(0, {'code': target, 'user': user_id, 'msg': user_msg, 'time': datetime.datetime.now().strftime("%H:%M")})
                save_db()
                st.rerun()
        st.markdown("<div style='max-height: 300px; overflow-y: auto;'>", unsafe_allow_html=True)
        for m in st.session_state['board_messages']:
            if m['code'] == target:
                st.markdown(f"<div class='chat-box'><div class='chat-user'>{m['user']}</div><div class='chat-msg'>{m['msg']}</div><div class='chat-time'>{m['time']}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # [⑤ 탭: 주문]
    with tabs[3]:
        target = st.session_state['selected_code']
        market = st.session_state['market_data'][target]
        st.subheader("🛒 매수 주문")
        
        if st.button(f"선택 종목: {market['name']} ({target})", type="secondary", use_container_width=True):
            st.session_state['view_profile_id'] = target
            st.rerun()
        
        with st.container():
            st.markdown(f"#### 가용: <span style='color:#3182F6'>{st.session_state['balance_id']:,.0f} ID</span>", unsafe_allow_html=True)
            buy_price = st.number_input("매수 희망가 (ID)", value=market['price'], step=100, key="buy_price_main")
            buy_qty = st.number_input("매수 수량 (주)", value=10, step=1, key="buy_qty_main")
            
            if st.button("🔴 매수 주문 전송", type="primary"):
                ok, msg = place_order('BUY', target, buy_price, buy_qty)
                if ok: st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)

    # [⑥ 탭: 잔고]
    with tabs[4]:
        st.subheader("💼 잔고 및 매도")
        
        with st.expander("📢 내 엘피스 상장 (IPO)", expanded=True):
            locked = st.session_state['my_elpis_locked']
            st.markdown(f"**보유(Lock): {locked:,} 주**")
            c1, c2 = st.columns(2)
            ipo_qty = c1.number_input("상장 수량", 1, locked, 1000, key="ipo_qty")
            ipo_price = c2.number_input("상장 가격", 100, value=10000, key="ipo_price")
            if st.button("내 엘피스 시장에 팔기 (상장)", type="primary"):
                if locked >= ipo_qty:
                    st.session_state['my_elpis_locked'] -= ipo_qty
                    if user_id in st.session_state['market_data']:
                        st.session_state['market_data'][user_id]['price'] = ipo_price
                    else:
                        st.session_state['market_data'][user_id] = {'name': user_id, 'price': ipo_price, 'change': 0.0, 'desc': '신규 상장', 'history': [ipo_price]}
                    
                    st.session_state['pending_orders'].append({'code': user_id, 'type': 'SELL', 'price': ipo_price, 'qty': ipo_qty, 'user': user_id})
                    
                    st.session_state['interested_codes'].add(user_id)
                    save_current_user_state(user_id) 
                    st.success("상장 주문 등록 완료! (매수자가 나타나면 체결됩니다)"); time.sleep(1.5); st.rerun()
                else:
                    st.error("보유 수량이 부족합니다.")
        
        st.divider()

        if not st.session_state['portfolio']: 
            st.info("보유 중인 주식이 없습니다.")
        else:
            for code, info in st.session_state['portfolio'].items():
                curr_p = st.session_state['market_data'][code]['price']
                profit = (info['qty'] * curr_p) - (info['qty'] * info['avg_price'])
                rate = (profit / (info['qty'] * info['avg_price'])) * 100
                color = "#E22A2A" if profit >= 0 else "#2A6BE2"
                
                with st.container():
                    if st.button(f"{st.session_state['market_data'][code]['name']} ({code})", key=f"pf_n_{code}", type="secondary"):
                        st.session_state['view_profile_id'] = code
                        st.rerun()
                        
                    col_info1, col_info2, col_info3 = st.columns(3)
                    col_info1.metric("보유 수량", f"{info['qty']:,}주")
                    col_info2.metric("평가액", f"{info['qty'] * curr_p:,}")
                    col_info3.markdown(f"수익률 <br> <span style='color:{color}; font-weight:bold; font-size:20px'>{rate:.1f}%</span>", unsafe_allow_html=True)
                    
                    with st.expander("🔵 매도 하기"):
                        c_sell1, c_sell2, c_sell3 = st.columns([1, 1, 1])
                        s_price = c_sell1.number_input("매도가", value=curr_p, step=100, key=f"sell_p_{code}")
                        s_qty = c_sell2.number_input("수량", 1, info['qty'], info['qty'], key=f"sell_q_{code}")
                        if c_sell3.button("매도 주문", key=f"btn_sell_{code}", type="primary"):
                            ok, msg = place_order('SELL', code, s_price, s_qty)
                            if ok: st.success(msg); time.sleep(1); st.rerun()
                            else: st.error(msg)
                st.divider()

    # [⑦ 탭: 내역]
    with tabs[5]:
        st.subheader("📜 거래 및 주문 내역")

        st.markdown("#### ⏳ 미체결 주문 (Pending)")
        my_pending = [o for o in st.session_state['pending_orders'] if o['user'] == user_id]
        if my_pending:
            df_pending = pd.DataFrame(my_pending)
            st.dataframe(df_pending[['code', 'type', 'price', 'qty']], use_container_width=True)
        else:
            st.info("대기 중인 주문이 없습니다.")

        st.divider()

        st.markdown("#### ✅ 체결 내역 (Executed - My Trades)")
        if 'trade_history' in st.session_state:
            my_trades = [t for t in st.session_state['trade_history'] 
                         if t.get('buyer') == user_id or t.get('seller') == user_id]
            
            if my_trades:
                st.dataframe(pd.DataFrame(my_trades), use_container_width=True)
            else:
                st.caption("체결된 나의 거래 내역이 없습니다.")
        else:
            st.caption("아직 거래 내역이 생성되지 않았습니다.")
    
    with tabs[6]:
        st.subheader("💱 거래소")
        st.info("Coming Soon")



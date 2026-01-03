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
@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    # secrets가 없는 로컬 환경 등을 대비한 예외처리는 생략
    credentials_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

# --- [데이터 영구 저장 시스템] ---
def load_db():
    try:
        client = init_connection()
        sh = client.open("ELPIS_DB")
        worksheet = sh.worksheet("JSON_DATA")
        raw_data = worksheet.acell('A1').value
        if raw_data:
            return json.loads(raw_data)
        return None
    except Exception as e:
        print(f"DB Load Error: {e}")
        return None

def save_db():
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
        json_str = json.dumps(data, ensure_ascii=False)
        worksheet.update_acell('A1', json_str)
    except Exception as e:
        st.error(f"데이터 저장 실패: {e}")

# --- [페이지 설정] ---
st.set_page_config(layout="wide", page_title="ELPIS EXCHANGE", page_icon="📈")

# --- [CSS 스타일 : 모바일 최적화 보존] ---
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    /* [기본 레이아웃] */
    .block-container {
        padding-top: 1rem !important; 
        padding-bottom: 0rem !important;
        max-width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    html, body, .stApp {
        font-family: 'Pretendard', sans-serif !important;
        background-color: #F2F4F6;
        color: #191F28;
        overscroll-behavior: none !important;
        overflow-x: hidden !important;
    }
    header[data-testid="stHeader"] { display: none !important; }

    /* [모바일 반응형 패치 보존] */
    @media (max-width: 640px) {
        div[data-testid="stHorizontalBlock"] { gap: 2px !important; }
        div[data-testid="column"] { min-width: 0px !important; flex: 1 !important; padding: 0 !important; }
        .stButton > button { padding-left: 2px !important; padding-right: 2px !important; font-size: 12px !important; height: 42px !important; min-width: 0px !important; }
    }

    .main { background-color: #F2F4F6; }
    div[data-testid="stVerticalBlock"] > div { background-color: transparent; }
    .stMetric {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E8EB !important;
        border-radius: 16px !important;
        padding: 15px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }
    .auth-card {
        background-color: #FFFFFF;
        padding: 30px 20px;
        border-radius: 24px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        border: 1px solid #E5E8EB;
        margin-top: 10px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px !important;
        font-weight: 600 !important;
        height: 52px;
        font-size: 16px;
        border: none !important;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    button[kind="primary"] { background-color: #3182F6 !important; color: white !important; }
    button[kind="primary"]:hover { background-color: #1B64DA !important; }
    button[kind="secondary"] { background-color: #FFFFFF !important; color: #4E5968 !important; border: 1px solid #D1D6DB !important; }
    
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

    .up-text { color: #E22A2A !important; font-weight: 700; }
    .down-text { color: #2A6BE2 !important; font-weight: 700; }
    .profile-card {
        background: white;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #F2F4F6;
    }
    
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
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: transparent !important;
        padding: 10px 0 !important;
        border: none !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 55px !important;
        border-radius: 16px !important;
        font-weight: 800 !important;
        font-size: 18px !important;
        color: #8B95A1 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
        border: 1px solid #F2F4F6 !important;
        flex-grow: 1 !important;
        transition: all 0.2s ease !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3182F6 !important; 
        color: #FFFFFF !important;
        box-shadow: 0 6px 16px rgba(49, 130, 246, 0.4) !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] p { color: #FFFFFF !important; }
    .big-font { font-size: 32px; font-weight: 800; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

# --- [데이터 초기화] ---
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
        # 초기화 데이터
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
        # Bot 생성
        for i in range(5):
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
        st.session_state['board_messages'] = [{'code': 'IU', 'user': 'Fan_001', 'msg': '아이유 10만 전자 가즈아!!', 'time': '12:00'}]
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
    temp_profile = st.session_state['my_profile'].copy()
    temp_profile['photo'] = None 
    st.session_state['user_states'][user_id]['my_profile'] = temp_profile
    save_db()

# [수정된 로직: 가격 및 차트 DB 즉시 반영]
def update_price_match(market_code, price):
    market = st.session_state['market_data'][market_code]
    market['price'] = price
    base_price = market['history'][0]
    market['change'] = round(((price - base_price) / base_price) * 100, 2)
    market['history'].append(price)
    save_db()

# [수정된 로직: 매칭 엔진 고도화 - 상대방 잔고 반영, 내역 기록]
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
            
            # 판매자에게 돈 입금
            if seller_id in st.session_state['user_states']:
                st.session_state['user_states'][seller_id]['balance_id'] += (match_price * match_qty)
            
            sell_order['qty'] -= match_qty
            remaining_qty -= match_qty
            update_price_match(code, match_price)
            
            # 거래 기록 저장
            trade_record = {
                'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'type': '체결(매수)', 
                'name': market['name'], 
                'price': match_price, 
                'qty': match_qty,
                'buyer': user_id,      
                'seller': seller_id    
            }
            st.session_state['trade_history'].insert(0, trade_record)

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
            
            # 구매자에게 주식 입고
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
            
            trade_record = {
                'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'type': '체결(매도)', 
                'name': market['name'], 
                'price': match_price, 
                'qty': match_qty,
                'buyer': buyer_id,    
                'seller': user_id     
            }
            st.session_state['trade_history'].insert(0, trade_record)
            
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
    last_dt = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S.%f") if last else None
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
    col_spacer1, col_center, col_spacer2 = st.columns([1, 6, 1])
    with col_center:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 15px; margin-top: 20px;'>
                <h1 style='color: #3182F6; font-size: 52px; font-weight: 900; letter-spacing: -2px; margin-bottom: 0;'>ELPIS</h1>
                <h3 style='color: #191F28; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; margin-top: 0;'>EXCHANGE</h3>
            </div>
        """, unsafe_allow_html=True)

        quotes_db = [("가장 큰 위험은 아무런 위험도 감수하지 않는 것이다.", "마크 저커버그")]
        time_slot = int(time.time() / (4 * 3600)) 
        random.seed(time_slot) 
        today_quote, author = random.choice(quotes_db)
        
        st.markdown(f"<div style='background-color: #FFFFFF; padding: 8px 16px; border-radius: 12px; margin-bottom: 20px; text-align: center; border: 1px solid #E5E8EB; box-shadow: 0 2px 6px rgba(0,0,0,0.03);'><p style='color: #4E5968; font-size: 12px; font-weight: 500; margin: 0;'>{today_quote} - {author}</p></div>", unsafe_allow_html=True)
        
        st.markdown("<div class='auth-card'>", unsafe_allow_html=True)
        auth_tabs = st.tabs(["🔒 로그인", "📝 회원가입"])
        
        with auth_tabs[0]: 
            st.markdown("<br>", unsafe_allow_html=True)
            l_id = st.text_input("아이디", key="login_id")
            l_pw = st.text_input("비밀번호", type="password", key="login_pw")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("ELPIS 시작하기", type="primary"):
                if not st.session_state['user_db']: st.session_state['user_db'] = load_db()['user_db']
                if l_id in st.session_state['user_db'] and st.session_state['user_db'][l_id] == l_pw:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info']['id'] = l_id
                    sync_user_state(l_id)
                    st.rerun()
                else: st.error("로그인 실패")
                    
        with auth_tabs[1]:
            st.markdown("<br>", unsafe_allow_html=True)
            r_name = st.text_input("실명")
            r_rrn = st.text_input("주민번호 앞자리")
            r_phone = st.text_input("폰번호")
            r_id = st.text_input("아이디", key="reg_id")
            r_pw = st.text_input("비밀번호", type="password", key="reg_pw")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("가입하기", type="primary"):
                if r_id and r_pw:
                    if r_id in st.session_state['user_db']: st.warning("ID 중복")
                    else:
                        st.session_state['user_db'][r_id] = r_pw
                        st.session_state['user_names'][r_id] = r_name
                        sync_user_state(r_id) 
                        save_current_user_state(r_id)
                        st.success("가입 완료")
                else: st.warning("입력 확인")
        st.markdown("</div>", unsafe_allow_html=True) 

else:
    user_id = st.session_state['user_info'].get('id', 'Guest')
    user_name = st.session_state['user_names'].get(user_id, '사용자')
    
    if st.session_state.get('view_profile_id'):
        target_id = st.session_state['view_profile_id']
        target_name = st.session_state['user_names'].get(target_id, target_id)
        p_vision = st.session_state['user_states'].get(target_id, {}).get('my_profile', {}).get('vision', '정보 없음')
        st.markdown(f"<div class='profile-card'><h2>👤 {target_name}</h2><p>{p_vision}</p></div>", unsafe_allow_html=True)
        if st.button("닫기", type="secondary"):
            st.session_state['view_profile_id'] = None
            st.rerun()
    
    tabs = st.tabs(["메인화면", "관심", "현재가", "주문", "잔고", "내역", "거래소"])

    with tabs[0]:
        st.markdown(f"### {user_name}님 환영합니다.")
        total_asset = st.session_state['balance_id']
        for c, d in st.session_state['portfolio'].items():
            total_asset += (d['qty'] * st.session_state['market_data'][c]['price'])
        c1, c2 = st.columns(2)
        c1.metric("총 자산", f"{total_asset:,.0f} ID")
        c2.metric("보유 이드", f"{st.session_state['balance_id']:,.0f}")
        
        if st.button("채굴", type="primary"):
            ok, r = mining()
            if ok: st.success(f"+{r}")
            else: st.warning("이미 채굴함")
        st.divider()
        st.subheader("메시지")
        for m in st.session_state['board_messages']:
            if m['code'] == user_id:
                st.write(f"[{m['user']}] {m['msg']}")

    # [관심 탭: 모바일 패치 보존]
    with tabs[1]:
        st.markdown("#### 관심 종목")
        h1, h2, h3, h4 = st.columns([4, 3, 2, 1], gap="small")
        h1.caption("종목명")
        h2.caption("현재가")
        h3.caption("등락")
        st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
        
        targets = [t for t in st.session_state['interested_codes'] if t != user_id]
        for code in targets:
            if code in st.session_state['market_data']:
                info = st.session_state['market_data'][code]
                c_change = info['change']
                color = "#E22A2A" if c_change > 0 else "#2A6BE2"
                
                with st.container():
                    r1, r2, r3, r4 = st.columns([4, 3, 2, 1], gap="small")
                    with r1:
                        if st.button(info['name'], key=f"fav_{code}", type="secondary", use_container_width=True):
                            st.session_state['view_profile_id'] = code
                            st.rerun()
                    with r2: st.markdown(f"<div style='text-align:right; font-weight:bold; color:{color}; font-size:13px; padding-top:10px;'>{info['price']:,}</div>", unsafe_allow_html=True)
                    with r3: st.markdown(f"<div style='color:{color}; font-size:11px; padding-top:10px;'>{c_change}%</div>", unsafe_allow_html=True)
                    with r4:
                        if st.button("✕", key=f"del_{code}"):
                            st.session_state['interested_codes'].remove(code)
                            save_db()
                            st.rerun()
                    st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

    with tabs[2]:
        col_s1, col_s2 = st.columns([3, 1])
        q = col_s1.text_input("검색", label_visibility="collapsed")
        if col_s2.button("🔍"):
            for k, v in st.session_state['market_data'].items():
                if q in k or q in v['name']:
                    st.session_state['selected_code'] = k
                    st.session_state['interested_codes'].add(k)
                    save_db()
                    st.rerun()
        
        target = st.session_state['selected_code']
        market = st.session_state['market_data'][target]
        st.metric(market['name'], f"{market['price']:,} ID", f"{market['change']}%")
        
        # 호가창 로직
        pending = [o for o in st.session_state['pending_orders'] if o['code'] == target]
        sells = sorted([o for o in pending if o['type'] == 'SELL'], key=lambda x: x['price'])[:5]
        buys = sorted([o for o in pending if o['type'] == 'BUY'], key=lambda x: x['price'], reverse=True)[:5]
        
        html = "<div class='hoga-container'>"
        for s in reversed(sells): html += f"<div class='hoga-row sell-bg'><div class='cell-vol'>{s['qty']:,}</div><div class='cell-price price-down'>{s['price']:,}</div><div class='cell-empty'></div></div>"
        html += f"<div class='hoga-row'><div class='cell-vol'></div><div class='cell-price current-price-box'>{market['price']:,}</div><div class='cell-empty'></div></div>"
        for b in buys: html += f"<div class='hoga-row buy-bg'><div class='cell-empty'></div><div class='cell-price price-up'>{b['price']:,}</div><div class='cell-vol-buy'>{b['qty']:,}</div></div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        
        st.divider()
        with st.form("msg"):
            msg = st.text_input("메시지")
            if st.form_submit_button("등록") and msg:
                st.session_state['board_messages'].insert(0, {'code': target, 'user': user_id, 'msg': msg, 'time': datetime.datetime.now().strftime("%H:%M")})
                save_db()
                st.rerun()
        for m in st.session_state['board_messages']:
            if m['code'] == target: st.markdown(f"<div class='chat-box'><div class='chat-user'>{m['user']}</div><div class='chat-msg'>{m['msg']}</div></div>", unsafe_allow_html=True)

    with tabs[3]:
        target = st.session_state['selected_code']
        st.subheader("매수 주문")
        price = st.number_input("가격", value=st.session_state['market_data'][target]['price'], step=100)
        qty = st.number_input("수량", value=10)
        if st.button("매수 주문"):
            ok, msg = place_order('BUY', target, price, qty)
            if ok: st.success(msg); time.sleep(1); st.rerun()
            else: st.error(msg)

    with tabs[4]:
        st.subheader("잔고")
        with st.expander("IPO"):
            l = st.session_state['my_elpis_locked']
            st.write(f"Locked: {l}")
            iq = st.number_input("수량", 1, l, 1000)
            ip = st.number_input("가격", 100, value=10000)
            if st.button("상장"):
                st.session_state['my_elpis_locked'] -= iq
                if user_id not in st.session_state['market_data']:
                     st.session_state['market_data'][user_id] = {'name': user_id, 'price': ip, 'change': 0, 'history': [ip]}
                st.session_state['pending_orders'].append({'code': user_id, 'type': 'SELL', 'price': ip, 'qty': iq, 'user': user_id})
                st.session_state['interested_codes'].add(user_id)
                save_current_user_state(user_id)
                st.rerun()
        
        for c, v in st.session_state['portfolio'].items():
            curr = st.session_state['market_data'][c]['price']
            st.markdown(f"**{st.session_state['market_data'][c]['name']}**: {v['qty']}주 (평단 {v['avg_price']})")
            sq = st.number_input("매도 수량", 1, v['qty'], key=f"sq_{c}")
            sp = st.number_input("매도 가격", value=curr, key=f"sp_{c}")
            if st.button("매도", key=f"sb_{c}"):
                ok, msg = place_order('SELL', c, sp, sq)
                if ok: st.success(msg); time.sleep(1); st.rerun()

    # [수정된 내역 탭: 필터링 로직 적용]
    with tabs[5]:
        st.subheader("나의 거래 내역")
        st.markdown("#### 미체결")
        my_pending = [o for o in st.session_state['pending_orders'] if o['user'] == user_id]
        if my_pending: st.dataframe(pd.DataFrame(my_pending)[['code', 'type', 'price', 'qty']], use_container_width=True)
        else: st.info("없음")
        
        st.divider()
        st.markdown("#### 체결 완료")
        if st.session_state['trade_history']:
            # 본인 관련 거래만 필터링
            my_trades = [t for t in st.session_state['trade_history'] if t.get('buyer') == user_id or t.get('seller') == user_id]
            if my_trades: st.dataframe(pd.DataFrame(my_trades)[['time', 'name', 'type', 'price', 'qty']], use_container_width=True)
            else: st.caption("내역 없음")
        else: st.caption("기록 없음")

    with tabs[6]:
        st.info("Coming Soon")

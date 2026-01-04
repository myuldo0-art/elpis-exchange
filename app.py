import streamlit as st
import time
import random
from database import load_db, save_db
from logic import sync_user_state, save_current_user_state

# [핵심] 방금 만든 ui.py를 여기서 불러옵니다.
from ui import render_ui

# --- [페이지 설정] ---
st.set_page_config(layout="wide", page_title="ELPIS EXCHANGE", page_icon="📈")

# --- [CSS 스타일] ---
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 100% !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    html, body { overscroll-behavior: none !important; overscroll-behavior-y: none !important; overflow-x: hidden !important; }
    div[data-testid="stAppViewContainer"] { overscroll-behavior: none !important; overscroll-behavior-y: none !important; position: fixed !important; left: 0; top: 0; width: 100%; height: 100%; overflow-y: auto !important; background-color: #F2F4F6; }
    header[data-testid="stHeader"] { display: none !important; }
    @media (max-width: 640px) { div[data-testid="stHorizontalBlock"] { gap: 2px !important; } div[data-testid="column"] { min-width: 0px !important; flex: 1 !important; padding: 0 !important; } .stButton > button { padding-left: 2px !important; padding-right: 2px !important; font-size: 12px !important; height: 42px !important; min-width: 0px !important; } }
    html, body, .stApp { font-family: 'Pretendard', sans-serif !important; background-color: #F2F4F6; color: #191F28; }
    .main { background-color: #F2F4F6; }
    div[data-testid="stVerticalBlock"] > div { background-color: transparent; }
    .stMetric { background-color: #FFFFFF !important; border: 1px solid #E5E8EB !important; border-radius: 16px !important; padding: 15px !important; box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important; }
    
    /* [수정] padding-top을 40px -> 15px로 줄여 빈공간 삭제 */
    .auth-card { background-color: #FFFFFF; padding: 15px 40px 40px 40px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.08); border: 1px solid #E5E8EB; margin-top: 10px; }
    
    .stButton>button { width: 100%; border-radius: 12px !important; font-weight: 600 !important; height: 52px; font-size: 16px; border: none !important; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    button[kind="primary"] { background-color: #3182F6 !important; color: white !important; }
    button[kind="primary"]:hover { background-color: #1B64DA !important; }
    button[kind="secondary"] { background-color: #FFFFFF !important; color: #4E5968 !important; border: 1px solid #D1D6DB !important; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #FFFFFF !important; border: 1px solid #D1D6DB !important; border-radius: 10px !important; height: 48px !important; font-size: 16px !important; color: #191F28 !important; }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus { border-color: #3182F6 !important; box-shadow: 0 0 0 2px rgba(49, 130, 246, 0.2) !important; }
    .up-text { color: #E22A2A !important; font-weight: 700; }
    .down-text { color: #2A6BE2 !important; font-weight: 700; }
    .flat-text { color: #333333 !important; font-weight: 700; }
    .small-gray { font-size: 13px; color: #8B95A1; margin-top: 2px; }
    .profile-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; margin-bottom: 20px; border: 1px solid #F2F4F6; }
    .profile-card h2 { margin: 0; font-size: 22px; color: #191F28; }
    .profile-card p { color: #4E5968; font-size: 14px; margin: 8px 0; }
    .hoga-container { font-family: 'Pretendard', sans-serif; font-size: 14px; width: 100%; background: white; border-radius: 12px; overflow: hidden; border: 1px solid #E5E8EB; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .hoga-row { display: flex; height: 38px; align-items: center; border-bottom: 1px solid #F9FAFB; }
    .sell-bg { background-color: rgba(66, 133, 244, 0.04); }
    .buy-bg { background-color: rgba(234, 67, 53, 0.04); }
    .cell-vol { flex: 1; text-align: right; padding-right: 12px; color: #4E5968; font-size: 12px; letter-spacing: -0.5px; }
    .cell-price { flex: 1.2; text-align: center; font-weight: 700; font-size: 15px; background-color: #ffffff; border-left: 1px solid #F2F4F6; border-right: 1px solid #F2F4F6; cursor: pointer; }
    .cell-vol-buy { flex: 1; text-align: left; padding-left: 12px; color: #4E5968; font-size: 12px; letter-spacing: -0.5px; }
    .cell-empty { flex: 1; }
    .price-up { color: #E22A2A; }
    .price-down { color: #2A6BE2; }
    .current-price-box { border: 2px solid #191F28 !important; background-color: #FFF !important; color: #191F28 !important; font-size: 16px !important; }
    .chat-box { background-color: #FFFFFF; padding: 14px; border-radius: 16px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #F2F4F6; }
    .chat-user { font-weight: 700; font-size: 14px; color: #191F28; margin-bottom: 4px; }
    .chat-msg { font-size: 15px; color: #333D4B; line-height: 1.4; }
    .chat-time { font-size: 11px; color: #8B95A1; text-align: right; margin-top: 4px; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px !important; background-color: transparent !important; padding: 10px 0 !important; border: none !important; }
    .stTabs [data-baseweb="tab"] { height: 65px !important; border-radius: 16px !important; font-weight: 800 !important; font-size: 20px !important; color: #8B95A1 !important; background-color: #FFFFFF !important; box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important; border: 1px solid #F2F4F6 !important; flex-grow: 1 !important; transition: all 0.2s ease !important; }
    .stTabs [data-baseweb="tab"]:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.1) !important; color: #3182F6 !important; }
    .stTabs [aria-selected="true"] { background-color: #3182F6 !important; color: #FFFFFF !important; box-shadow: 0 6px 16px rgba(49, 130, 246, 0.4) !important; border: none !important; }
    .stTabs [aria-selected="true"] p { color: #FFFFFF !important; }
    .big-font { font-size: 32px; font-weight: 800; letter-spacing: -1px; }
    div[data-testid="column"][style*="1.21"] button { background-color: transparent !important; border: none !important; padding: 0 !important; box-shadow: none !important; }
    div[data-testid="column"][style*="1.21"] button * { color: #2A6BE2 !important; font-weight: 800 !important; font-size: 15px !important; }
    div[data-testid="column"][style*="1.21"] button:hover { background-color: rgba(66, 133, 244, 0.1) !important; }
    div[data-testid="column"][style*="1.22"] button { background-color: transparent !important; border: none !important; padding: 0 !important; box-shadow: none !important; }
    div[data-testid="column"][style*="1.22"] button * { color: #E22A2A !important; font-weight: 800 !important; font-size: 15px !important; }
    div[data-testid="column"][style*="1.22"] button:hover { background-color: rgba(234, 67, 53, 0.1) !important; }
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
        st.session_state['board_messages'] = [
            {'code': 'IU', 'user': 'Fan_001', 'msg': '아이유 10만 전자 가즈아!!', 'time': '12:00'},
            {'code': 'ELON', 'user': 'Mars_Lover', 'msg': '화성 갈끄니까~', 'time': '12:05'}
        ]
        st.session_state['pending_orders'] = []
        st.session_state['interested_codes'] = {'IU', 'G_DRAGON', 'ELON', 'DEV_MASTER'}
        save_db()

    st.session_state['selected_code'] = 'IU'

# ==========================================
# [앱 UI 시작]
# ==========================================
if not st.session_state['logged_in']:
    col_spacer1, col_center, col_spacer2 = st.columns([1, 6, 1])
    
    with col_center:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 15px; margin-top: 20px;'>
                <h1 style='color: #3182F6; font-size: 52px; font-weight: 900; letter-spacing: -2px; margin-bottom: 0;'>ELPIS</h1>
                <h3 style='color: #191F28; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; margin-top: 0;'>거래소</h3>
            </div>
        """, unsafe_allow_html=True)

        quotes_db = [
            ("가장 큰 위험은 아무런 위험도 감수하지 않는 것이다.", "마크 저커버그"),
            ("가격은 당신이 지불하는 것이고, 가치는 당신이 얻는 것이다.", "워렌 버핏"),
            ("너의 가치를 세상에 증명하라. 그러면 세상은 너에게 값을 지불할 것이다.", "ELPIS Master"),
            ("시간은 인간이 쓸 수 있는 가장 값진 것이다.", "테오프라스토스"),
            ("오늘 누군가가 그늘에 앉아 쉴 수 있는 이유는, 오래 전에 누군가가 나무를 심었기 때문이다.", "워렌 버핏"),
            ("욕망은 인간을 움직이는 엔진이고, 희망은 그 엔진의 연료다.", "ELPIS Philosophy"),
            ("기회는 일어나는 것이 아니라, 만들어내는 것이다.", "크리스 그로서"),
            ("성공한 사람보다는 가치 있는 사람이 되려 노력하라.", "알베르트 아인슈타인"),
            ("잠을 자면 꿈을 꾸지만, 꿈을 꾸면 잠이 온다? 아니, 꿈을 이루게 된다.", "ELPIS Motivation"),
            ("인내할 수 있는 사람은 그가 바라는 것은 무엇이든 손에 넣을 수 있다.", "벤저민 프랭클린")
        ]
        
        time_slot = int(time.time() / (4 * 3600)) 
        random.seed(time_slot) 
        today_quote, author = random.choice(quotes_db)
        
        st.markdown(f"""
            <div style='background-color: #FFFFFF; padding: 8px 16px; border-radius: 12px; margin-bottom: 20px; text-align: center; border: 1px solid #E5E8EB; box-shadow: 0 2px 6px rgba(0,0,0,0.03);'>
                <p style='color: #4E5968; font-size: 12px; font-weight: 500; margin: 0; letter-spacing: -0.3px; line-height: 1.4;'>
                    <span style='color: #FFC700; font-size: 14px; margin-right: 3px; vertical-align: -1px;'>❝</span>
                    {today_quote}
                    <span style='color: #8B95A1; font-size: 11px; margin-left: 8px; font-weight: 400;'>— {author}</span>
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # [수정] 이 auth-card의 CSS에서 padding-top을 줄여서 위쪽 빈공간을 제거함
        st.markdown("<div class='auth-card'>", unsafe_allow_html=True)
        
        auth_tabs = st.tabs(["🔒 로그인", "📝 회원가입"])
        
        with auth_tabs[0]: 
            st.markdown("<br>", unsafe_allow_html=True)
            l_id = st.text_input("아이디", key="login_id", placeholder="ID를 입력하세요")
            l_pw = st.text_input("비밀번호", type="password", key="login_pw", placeholder="비밀번호를 입력하세요")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("ELPIS 시작하기", type="primary"):
                if not st.session_state['user_db']:
                     st.session_state['user_db'] = load_db()['user_db']
                
                if l_id in st.session_state['user_db'] and st.session_state['user_db'][l_id] == l_pw:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info']['id'] = l_id
                    sync_user_state(l_id)
                    st.rerun()
                else:
                    st.error("계정 정보가 일치하지 않습니다.")
                    
        with auth_tabs[1]:
            st.markdown("<br>", unsafe_allow_html=True)
            r_name = st.text_input("실명", placeholder="본명을 입력하세요")
            r_rrn = st.text_input("주민등록번호 (앞 6자리)", max_chars=6, placeholder="YYMMDD")
            r_phone = st.text_input("휴대폰 번호", placeholder="010-0000-0000")
            r_id = st.text_input("아이디", key="reg_id", placeholder="사용할 ID")
            r_pw = st.text_input("비밀번호", type="password", key="reg_pw", placeholder="비밀번호")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            
            if st.button("가입하고 1,000만 이드(ID) 받기", type="primary"):
                if r_name and r_rrn and r_phone and r_id and r_pw:
                    if r_id in st.session_state['user_db']:
                        st.warning("이미 사용 중인 아이디입니다.")
                    else:
                        st.session_state['user_db'][r_id] = r_pw
                        st.session_state['user_names'][r_id] = r_name
                        sync_user_state(r_id) 
                        save_current_user_state(r_id)
                        st.success("환영합니다! 가입이 완료되었습니다.")
                else:
                    st.warning("모든 정보를 정확히 입력해주세요.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; margin-top: 30px; color: #B0B8C1; font-size: 12px;'>© 2026 ELPIS EXCHANGE. All rights reserved.</div>", unsafe_allow_html=True)

else:
    # 로그인 후 화면은 ui.py의 render_ui 함수가 전담합니다.
    render_ui()

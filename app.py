import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import time
import json
import gspread
from google.oauth2.service_account import Credentials

# --- [0. 구글 시트 DB 연결 설정] ---
@st.cache_resource
def init_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    return gspread.authorize(creds)

def load_db():
    try:
        client = init_connection()
        sh = client.open("ELPIS_DB")
        worksheet = sh.worksheet("JSON_DATA")
        raw_data = worksheet.acell('A1').value
        return json.loads(raw_data) if raw_data else None
    except:
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
        worksheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
    except:
        pass

# --- [페이지 설정 및 강력 CSS] ---
st.set_page_config(layout="wide", page_title="ELPIS EXCHANGE")

st.markdown("""
    <style>
    /* 1. 관리 버튼 및 메뉴 완전 숨김 */
    header, footer, #MainMenu, .stDeployButton {visibility: hidden !important; display: none !important;}
    [data-testid="stStatusWidget"], [data-testid="stDecoration"] {display: none !important;}
    iframe[title="Manage app"], div[class^="viewerBadge"] {display: none !important;}
    
    /* 2. 글자색 검은색으로 고정 (하얗게 보이는 문제 해결) */
    html, body, p, div, label, span, input {
        color: #191F28 !important;
        font-family: 'Pretendard', sans-serif !important;
    }
    .stTabs [data-baseweb="tab"] { color: #4E5968 !important; }
    
    /* 3. 모바일 새로고침 방지 */
    html, body { overscroll-behavior-y: none !important; background-color: #F2F4F6; }
    div[data-testid="stAppViewContainer"] {
        overscroll-behavior-y: none !important;
        position: fixed !important;
        width: 100%; height: 100%;
        overflow-y: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- [데이터 초기화] ---
if 'initialized' not in st.session_state:
    st.session_state.update({'initialized': True, 'logged_in': False, 'user_info': {}, 'view_profile_id': None})
    db = load_db()
    if db:
        st.session_state.update(db)
        st.session_state['interested_codes'] = set(db.get('interested_codes', ['IU', 'G_DRAGON']))
    else:
        st.session_state.update({
            'user_db': {'test': '1234'}, 'user_names': {'test': '테스터'},
            'user_states': {'test': {'balance_id': 10000000.0, 'my_elpis_locked': 1000000, 'portfolio': {}, 'my_profile': {'vision': '', 'sns': ''}}},
            'market_data': {'IU': {'name': '아이유', 'price': 50000, 'change': 0.0, 'history': [50000]}},
            'trade_history': [], 'board_messages': [], 'pending_orders': [], 'interested_codes': {'IU'}
        })
    st.session_state['selected_code'] = 'IU'

# --- [핵심 로직] ---
def save_current_state(user_id):
    st.session_state['user_states'][user_id].update({
        'balance_id': st.session_state.get('balance_id', 10000000.0),
        'portfolio': st.session_state.get('portfolio', {})
    })
    save_db()

# --- [화면 구현] ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>ELPIS EXCHANGE</h1>", unsafe_allow_html=True)
    l_id = st.text_input("아이디")
    l_pw = st.text_input("비밀번호", type="password")
    if st.button("접속하기", type="primary"):
        if l_id in st.session_state['user_db'] and st.session_state['user_db'][l_id] == l_pw:
            st.session_state['logged_in'] = True
            st.session_state['user_info']['id'] = l_id
            state = st.session_state['user_states'].get(l_id, {'balance_id': 10000000.0, 'portfolio': {}})
            st.session_state['balance_id'] = state['balance_id']
            st.session_state['portfolio'] = state['portfolio']
            st.rerun()
else:
    user_id = st.session_state['user_info']['id']
    st.write(f"### {user_id}님 환영합니다")
    st.metric("가용 자산", f"{st.session_state['balance_id']:,} ID")
    if st.button("로그아웃"):
        st.session_state['logged_in'] = False
        st.rerun()

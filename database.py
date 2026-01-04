import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials

# --- [구글 시트 DB 연결 설정] ---
@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    # secrets.toml에 gcp_service_account가 설정되어 있어야 합니다.
    credentials_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

# --- [데이터 로드] ---
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

# --- [데이터 저장] ---
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
        st.error(f"데이터 저장 실패 (네트워크 문제일 수 있음): {e}")

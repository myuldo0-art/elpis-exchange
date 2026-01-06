import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import time
import random 

from database import save_db
from logic import place_order, mining, save_current_user_state

# --- [황금 동전 이펙트 함수] ---
def falling_coins():
    st.markdown("""
        <style>
        .coin-emitter {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
        }
        .coin-particle {
            position: absolute;
            top: -50px;
            font-size: 30px;
            animation: fall linear forwards;
        }
        @keyframes fall {
            to {
                transform: translateY(110vh) rotate(360deg);
            }
        }
        </style>
    """, unsafe_allow_html=True)
    
    placeholder = st.empty()
    coin_html = '<div class="coin-emitter">'
    # 동전 30개 생성
    for _ in range(30):
        left = random.randint(0, 95)
        duration = random.uniform(1.5, 3.0)
        delay = random.uniform(0, 1.5)
        coin_html += f'<div class="coin-particle" style="left:{left}%; animation: fall {duration}s {delay}s linear forwards;">🪙</div>'
    coin_html += '</div>'
    
    placeholder.markdown(coin_html, unsafe_allow_html=True)
    time.sleep(0.1) # 렌더링 시간 확보

# --- [간편 매수 팝업] ---
@st.dialog("⚡ 간편 매수 (Quick Buy)")
def quick_buy_popup(code, price, name):
    st.markdown(f"<h3 style='text-align:center;'>{name}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#8B95A1; font-size:14px;'>{code}</p>", unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns(2)
    col_info1.metric("매수 단가", f"{price:,}")
    
    current_balance = st.session_state.get('balance_id', 0)
    if price > 0:
        max_buyable = int(current_balance / price)
    else:
        max_buyable = 0
        
    col_info2.metric("매수 가능", f"{max_buyable:,}주")
    st.divider()
    
    q_buy = st.number_input("매수 수량 (주)", min_value=1, value=10, step=1)
    
    total_cost = price * q_buy
    if total_cost > current_balance:
        st.warning(f"잔고 부족! (필요: {total_cost:,.0f} ID)")
    else:
        st.caption(f"총 주문금액: {total_cost:,.0f} ID")
    
    if st.button("매수 체결하기", type="primary", use_container_width=True):
        ok, msg = place_order('BUY', code, price, q_buy)
        if ok:
            st.success("체결 완료!")
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

# --- [간편 매도 팝업] ---
@st.dialog("⚡ 간편 매도 (Quick Sell)")
def quick_sell_popup(code, price, name):
    user_id = st.session_state['user_info'].get('id')
    current_portfolio = st.session_state.get('portfolio', {})
    
    my_qty = current_portfolio.get(code, {}).get('qty', 0)
    
    if code == user_id:
        my_qty += st.session_state.get('my_elpis_locked', 0)

    st.markdown(f"<h3 style='text-align:center;'>{name}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#8B95A1; font-size:14px;'>{code}</p>", unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns(2)
    col_info1.metric("매도 단가", f"{price:,}")
    col_info2.metric("매도 가능", f"{my_qty:,}주")
    st.divider()
    
    max_val = my_qty if my_qty > 0 else 1
    q_sell = st.number_input("매도 수량 (주)", min_value=1, max_value=max_val, value=10 if my_qty >= 10 else 1, step=1)
    
    total_gain = price * q_sell
    st.caption(f"총 정산금액: {total_gain:,.0f} ID")
    
    if st.button("매도 체결하기", type="primary", use_container_width=True):
        refresh_qty = st.session_state['portfolio'].get(code, {}).get('qty', 0)
        if code == user_id:
            refresh_qty += st.session_state.get('my_elpis_locked', 0)
            
        if refresh_qty < q_sell:
            st.error(f"보유 수량이 부족합니다. (현재: {refresh_qty}주)")
        else:
            ok, msg = place_order('SELL', code, price, q_sell)
            if ok:
                st.success("매도 체결 완료!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

# --- [UI 렌더링 메인 함수] ---
def render_ui():
    user_id = st.session_state['user_info'].get('id', 'Guest')
    user_name = st.session_state['user_names'].get(user_id, '사용자')

    # 사진 캐시용 세션 초기화
    if 'uploaded_photo_cache' not in st.session_state:
        st.session_state['uploaded_photo_cache'] = None

    # 다른 사용자 프로필 보기 (모달)
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
            
    tabs = st.tabs(["메인화면", "관심", "현재가", "주문", "잔고", "내역", "거래소"])

    # [수정] 메인 화면 (Tab 0) 전면 디자인 리뉴얼
    with tabs[0]:
        # 메인 대시보드 전용 CSS (카드 UI, 그림자, 타이포그래피)
        st.markdown("""
        <style>
            /* 메인 카드 컨테이너 디자인 */
            .main-card {
                background-color: #FFFFFF;
                border-radius: 20px;
                padding: 24px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
                margin-bottom: 16px;
                border: 1px solid #F2F4F6;
            }
            /* 자산 표시 텍스트 */
            .asset-label {
                color: #8B95A1;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 4px;
            }
            .asset-value-main {
                color: #191F28;
                font-size: 32px;
                font-weight: 800;
                letter-spacing: -1px;
            }
            .asset-value-sub {
                color: #333D4B;
                font-size: 18px;
                font-weight: 700;
            }
            /* 프로필 섹션 스타일 */
            .profile-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .user-welcome {
                font-size: 22px;
                font-weight: 700;
                color: #191F28;
            }
            .user-id-badge {
                background-color: #F2F4F6;
                color: #4E5968;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            /* 메시지 카드 스타일 */
            .msg-card {
                background-color: #F9FAFB;
                border-radius: 12px;
                padding: 12px 16px;
                margin-bottom: 8px;
                border-left: 4px solid #3182F6;
            }
        </style>
        """, unsafe_allow_html=True)

        # 1. [상단 헤더 영역] 프로필 요약 + 로그아웃
        col_header_l, col_header_r = st.columns([4, 1])
        with col_header_l:
            st.markdown(f"""
            <div class='profile-header'>
                <div>
                    <span class='user-welcome'>안녕하세요, {user_name}님</span>
                    <span class='user-id-badge'>{user_id}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state['my_profile']['vision']:
                st.caption(f"🚀 {st.session_state['my_profile']['vision']}")
            else:
                st.caption("✨ 당신의 금융 비전을 설정해보세요.")
        
        with col_header_r:
            if st.button("로그아웃", key="logout_btn_main", type="secondary"):
                st.session_state['logged_in'] = False
                st.session_state['user_info'] = {}
                st.session_state['uploaded_photo_cache'] = None
                st.rerun()

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # 2. [자산 대시보드 카드]
        total_asset = st.session_state['balance_id']
        for c, d in st.session_state['portfolio'].items():
            total_asset += (d['qty'] * st.session_state['market_data'][c]['price'])

        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.markdown("<div class='asset-label'>총 보유 자산</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='asset-value-main'>{total_asset:,.0f} ID</div>", unsafe_allow_html=True)
        
        st.markdown("<hr style='border: 0; border-top: 1px dashed #E5E8EB; margin: 16px 0;'>", unsafe_allow_html=True)
        
        c_asset1, c_asset2 = st.columns(2)
        with c_asset1:
            st.markdown("<div class='asset-label'>보유 현금</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='asset-value-sub' style='color:#3182F6'>{st.session_state['balance_id']:,.0f}</div>", unsafe_allow_html=True)
        with c_asset2:
            st.markdown("<div class='asset-label'>잠긴 자산 (Locked)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='asset-value-sub' style='color:#8B95A1'>{st.session_state['my_elpis_locked']:,} ELP</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 3. [액션 & 정보 카드] 채굴 및 알림
        col_main_L, col_main_R = st.columns([1.2, 1])

        with col_main_L:
            # 채굴 섹션
            st.markdown("<div class='main-card' style='height: 100%;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='margin-top:0;'>⛏️ Daily Mining</h4>", unsafe_allow_html=True)
            st.caption("매일 접속하여 100,000 ID를 채굴하세요.")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            
            if st.button("채굴 시작하기", type="primary", use_container_width=True):
                ok, reward = mining()
                if ok: 
                    falling_coins()
                    st.success(f"+{reward:,} ID 채굴 성공!")
                    time.sleep(2) 
                    st.rerun()
                else: 
                    st.warning("오늘은 이미 채굴했습니다. 내일 다시 오세요!")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_main_R:
            # 프로필 사진 및 수정
            with st.container(border=True):
                st.markdown("<div style='text-align:center; margin-bottom:10px;'><b>내 프로필</b></div>", unsafe_allow_html=True)
                
                # 사진 배치
                col_img_center = st.columns([1, 2, 1])
                with col_img_center[1]:
                    profile_img_placeholder = st.empty()
                    photo_to_show = None
                    if st.session_state['uploaded_photo_cache'] is not None:
                        photo_to_show = st.session_state['uploaded_photo_cache']
                    
                    if photo_to_show:
                        profile_img_placeholder.image(photo_to_show, width=100)
                    else:
                        st.markdown("<div style='text-align:center; color:#B0B8C1; font-size:40px;'>👤</div>", unsafe_allow_html=True)

                # 수정 기능은 Expander로 숨김
                with st.expander("프로필 수정 / 사진 업로드"):
                    new_vision = st.text_area("나의 비전", value=st.session_state['my_profile']['vision'])
                    new_sns = st.text_input("SNS 링크", value=st.session_state['my_profile']['sns'])
                    
                    uploaded_file = st.file_uploader("사진 변경", type=['jpg', 'png'], key="profile_upload_main", label_visibility="collapsed")
                    if uploaded_file:
                        st.session_state['uploaded_photo_cache'] = uploaded_file
                        st.rerun()

                    if st.button("정보 저장", key="save_profile_main"):
                        st.session_state['my_profile']['vision'] = new_vision
                        st.session_state['my_profile']['sns'] = new_sns
                        save_current_user_state(user_id)
                        st.success("저장되었습니다.")
                        time.sleep(1)
                        st.rerun()

        # 4. [메시지 센터]
        st.markdown("<div class='main-card'>", unsafe_allow_html=True)
        st.subheader(f"📨 알림 센터 ({len([m for m in st.session_state['board_messages'] if m['code'] == user_id])})")
        
        my_messages = [m for m in st.session_state['board_messages'] if m['code'] == user_id]
        if my_messages:
            for m in my_messages:
                st.markdown(f"""
                <div class='msg-card'>
                    <div style='display:flex; justify-content:space-between; margin-bottom:4px;'>
                        <span style='font-weight:700; color:#191F28;'>{m['user']}</span>
                        <span style='font-size:11px; color:#8B95A1;'>{m['time']}</span>
                    </div>
                    <div style='color:#4E5968; font-size:14px;'>{m['msg']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center; padding:20px; color:#B0B8C1;'>새로운 알림이 없습니다.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("<h4 style='margin-bottom: 15px; font-weight: 800;'>관심 종목</h4>", unsafe_allow_html=True)

        h1, h2, h3, h4 = st.columns([4, 3, 2, 1], gap="small")
        h1.markdown("<span style='color:#8B95A1; font-size:12px; padding-left:4px;'>종목명</span>", unsafe_allow_html=True)
        h2.markdown("<span style='color:#8B95A1; font-size:12px; display:block; text-align:right;'>현재가</span>", unsafe_allow_html=True)
        h3.markdown("<span style='color:#8B95A1; font-size:12px; display:block; text-align:right;'>등락</span>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 5px 0 0 0; border: 0; border-top: 1px solid #E5E8EB;'>", unsafe_allow_html=True)

        targets = list(st.session_state['interested_codes'])
        targets = [t for t in targets if t != user_id]

        if not targets:
            st.markdown("<div style='text-align:center; padding: 40px 0; color:#8B95A1; font-size:13px;'>관심 종목이 없습니다.</div>", unsafe_allow_html=True)

        for code in targets:
            if code in st.session_state['market_data']:
                info = st.session_state['market_data'][code]
                c_price = info['price']
                c_change = info['change']

                if c_change > 0:
                    color = "#E22A2A"; bg_color = "rgba(226, 42, 42, 0.1)"; arrow = "▲"
                elif c_change < 0:
                    color = "#2A6BE2"; bg_color = "rgba(42, 107, 226, 0.1)"; arrow = "▼"
                else:
                    color = "#333333"; bg_color = "rgba(51, 51, 51, 0.1)"; arrow = "-"

                with st.container():
                    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                    
                    r1, r2, r3, r4 = st.columns([4, 3, 2, 1], gap="small")

                    with r1:
                        if st.button(f"{info['name']}", key=f"fav_btn_{code}", type="secondary", use_container_width=True):
                            st.session_state['view_profile_id'] = code
                            st.session_state['selected_code'] = code 
                            st.rerun()
                    with r2:
                        st.markdown(f"""
                            <div style='text-align:right; padding-top: 10px; font-weight:700; font-size:13px; color:{color}; letter-spacing:-0.5px;'>
                                {c_price:,}
                            </div>
                        """, unsafe_allow_html=True)
                    with r3:
                        st.markdown(f"""
                            <div style='margin-top: 8px; float:right; background-color: {bg_color}; color: {color}; padding: 2px 4px; border-radius: 4px; font-size: 11px; font-weight: 600; white-space: nowrap;'>
                                {abs(c_change)}%
                            </div>
                        """, unsafe_allow_html=True)
                    with r4:
                        if st.button("✕", key=f"del_{code}"): 
                            st.session_state['interested_codes'].remove(code)
                            save_db()
                            st.rerun()

                    st.markdown("<hr style='margin: 6px 0 0 0; border: 0; border-top: 1px solid #F2F4F6;'>", unsafe_allow_html=True)

    with tabs[2]:
        # 호가창 텍스트 색상 강제 적용
        st.markdown("""
            <style>
            div[data-testid="column"] { padding: 0px !important; }
            
            button[kind="secondary"] { 
                height: 30px !important; 
                min-height: 30px !important; 
                padding: 0px !important; 
                margin: 0px !important;
                border: none !important;
                background: transparent !important;
                line-height: 1 !important;
            }
            .hoga-row-height { height: 28px !important; line-height: 28px !important; }
            
            /* 빨간색 강제 */
            div[data-testid="column"][style*="1.5"] button,
            div[data-testid="column"][style*="1.5"] button p,
            div[data-testid="column"][style*="1.5"] button div,
            div[data-testid="column"][style*="1.5"] button span { 
                color: #E22A2A !important; 
                font-weight: 800 !important; 
            }

            /* 파란색 강제 */
            div[data-testid="column"][style*="1.6"] button,
            div[data-testid="column"][style*="1.6"] button p,
            div[data-testid="column"][style*="1.6"] button div,
            div[data-testid="column"][style*="1.6"] button span { 
                color: #2A6BE2 !important; 
                font-weight: 800 !important; 
            }
            </style>
        """, unsafe_allow_html=True)

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
        
        is_me = (target == user_id)
        
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

        st.markdown("<div class='hoga-container'>", unsafe_allow_html=True)
        
        # [매도 호가 (Top) - 빨간색]
        sell_rows_data = []
        for p, q in best_asks:
            sell_rows_data.append((p, q))
        while len(sell_rows_data) < 5:
            sell_rows_data.insert(0, (None, None))
            
        for p, q in sell_rows_data:
            c1, c2, c3 = st.columns([1, 1.5, 1], gap="small")
            with c1: 
                if q: st.markdown(f"<div class='hoga-row-height' style='text-align:right; padding-right:12px; font-size:12px; color:#4E5968;'>{q:,}</div>", unsafe_allow_html=True)
                else: st.markdown("", unsafe_allow_html=True)
            with c2: 
                if p:
                    if not is_me: 
                        if st.button(f"{p:,}", key=f"ask_btn_{target}_{p}", type="secondary"):
                            quick_buy_popup(target, p, market['name'])
                    else: 
                         st.markdown(f"<div class='cell-price price-up hoga-row-height'>{p:,}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='hoga-row-height'></div>", unsafe_allow_html=True)
            with c3: 
                st.markdown("", unsafe_allow_html=True)
            st.markdown("<hr style='margin:0; border:0; border-bottom:1px solid #F9FAFB;'>", unsafe_allow_html=True)

        # [현재가 표시 줄]
        st.markdown(f"""
            <div style='display:flex; height:30px; align-items:center; border-top:1px solid #E5E8EB; border-bottom:1px solid #E5E8EB;'>
                <div style='flex:1;'></div>
                <div style='flex:1.2; text-align:center; font-weight:800; font-size:16px; color:#191F28; background-color:#FFF;'>{curr_price:,}</div>
                <div style='flex:1;'></div>
            </div>
        """, unsafe_allow_html=True)

        # [매수 호가 (Bottom) - 파란색]
        buy_rows_data = []
        for p, q in best_bids:
            buy_rows_data.append((p, q))
        while len(buy_rows_data) < 5:
            buy_rows_data.append((None, None))
            
        for p, q in buy_rows_data:
            c1, c2, c3 = st.columns([1, 1.6, 1], gap="small")
            with c1: 
                 st.markdown("", unsafe_allow_html=True)
            with c2: 
                if p:
                    if is_me: 
                        if st.button(f"{p:,}", key=f"bid_btn_{target}_{p}", type="secondary"):
                            quick_sell_popup(target, p, market['name'])
                    else:
                        st.markdown(f"<div class='cell-price price-down hoga-row-height'>{p:,}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='hoga-row-height'></div>", unsafe_allow_html=True)
            with c3: 
                if q: st.markdown(f"<div class='hoga-row-height' style='text-align:left; padding-left:12px; font-size:12px; color:#4E5968;'>{q:,}</div>", unsafe_allow_html=True)
                else: st.markdown("", unsafe_allow_html=True)
            st.markdown("<hr style='margin:0; border:0; border-bottom:1px solid #F9FAFB;'>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

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
                        st.session_state['selected_code'] = code
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

    with tabs[5]:
        st.subheader("📜 나의 거래 내역")

        st.markdown("#### ⏳ 미체결 주문 (Pending)")
        my_pending = [o for o in st.session_state['pending_orders'] if o['user'] == user_id]
        
        if my_pending:
            df_pending = pd.DataFrame(my_pending)
            st.dataframe(df_pending[['code', 'type', 'price', 'qty']], use_container_width=True)
        else:
            st.info("대기 중인 주문이 없습니다.")

        st.divider()

        st.markdown("#### ✅ 체결 완료 (Executed)")
        if 'trade_history' in st.session_state and st.session_state['trade_history']:
            my_trades = [t for t in st.session_state['trade_history'] 
                         if t.get('buyer') == user_id or t.get('seller') == user_id]
            
            if my_trades:
                st.dataframe(pd.DataFrame(my_trades)[['time', 'name', 'type', 'price', 'qty']], use_container_width=True)
            else:
                st.caption("아직 체결된 나의 거래 내역이 없습니다.")
        else:
            st.caption("거래 내역이 생성되지 않았습니다.")
    
    with tabs[6]:
        st.subheader("💱 거래소")
        st.info("Coming Soon")

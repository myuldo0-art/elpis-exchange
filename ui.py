import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import time
import random

from database import save_db
from logic import place_order, mining, save_current_user_state

# --- [황금 동전 이펙트] ---
def falling_coins():
    st.markdown("""
        <style>
        .coin-emitter {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none; z-index: 9999;
        }
        .coin-particle {
            position: absolute; top: -50px; font-size: 30px;
            animation: fall linear forwards;
        }
        @keyframes fall { to { transform: translateY(110vh) rotate(360deg); } }
        </style>
    """, unsafe_allow_html=True)
    
    placeholder = st.empty()
    coin_html = '<div class="coin-emitter">'
    for _ in range(30):
        left = random.randint(0, 95)
        duration = random.uniform(1.5, 3.0)
        delay = random.uniform(0, 1.5)
        coin_html += f'<div class="coin-particle" style="left:{left}%; animation: fall {duration}s {delay}s linear forwards;">🪙</div>'
    coin_html += '</div>'
    
    placeholder.markdown(coin_html, unsafe_allow_html=True)
    time.sleep(0.1)

# --- [팝업: 간편 매수] ---
@st.dialog("⚡ 간편 매수 (Quick Buy)")
def quick_buy_popup(code, price, name):
    st.markdown(f"<h3 style='text-align:center;'>{name}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#8B95A1; font-size:14px;'>{code}</p>", unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns(2)
    col_info1.metric("매수 단가", f"{price:,}")
    
    current_balance = st.session_state.get('balance_id', 0)
    max_buyable = int(current_balance / price) if price > 0 else 0
        
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

# --- [팝업: 간편 매도] ---
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

    if 'uploaded_photo_cache' not in st.session_state:
        st.session_state['uploaded_photo_cache'] = None

    # [수정] 개인 관심 종목 리스트 초기화 (없으면 생성)
    if 'likes' not in st.session_state['my_profile']:
        st.session_state['my_profile']['likes'] = []

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
        
        # [디자인 유지: 컨테이너 사용]
        with st.container(border=True):
            st.markdown(f"<h2>👤 {target_name} <small>({target_id})</small></h2><hr style='border: 0; border-top: 1px solid #F2F4F6;'><p><b>Vision:</b> {p_vision}</p><p><b>SNS:</b> {p_sns}</p>", unsafe_allow_html=True)
            if st.button("닫기 (Close)", type="secondary", use_container_width=True):
                st.session_state['view_profile_id'] = None
                st.rerun()
            
    tabs = st.tabs(["메인화면", "관심", "현재가", "주문", "잔고", "내역", "거래소"])

    with tabs[0]:
        col_top_spacer, col_top_logout = st.columns([4, 1])
        with col_top_logout:
            if st.button("로그아웃", key="logout_btn", type="secondary", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['user_info'] = {}
                st.session_state['uploaded_photo_cache'] = None
                st.rerun()

        with st.container(border=True):
            col_profile_info, col_profile_img = st.columns([3, 1]) 
            with col_profile_info:
                st.markdown(f"<h2>{user_name} <span style='font-size:16px; color:#8B95A1'>({user_id})</span></h2>", unsafe_allow_html=True)
                st.caption(st.session_state['my_profile']['vision'] if st.session_state['my_profile']['vision'] else "나의 비전이 없습니다.")
            
            with col_profile_img:
                photo_to_show = st.session_state.get('uploaded_photo_cache')
                if photo_to_show:
                    st.image(photo_to_show, use_container_width=True)
                else:
                    st.markdown("<div style='text-align:center; font-size:40px;'>👤</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        total_asset = st.session_state['balance_id']
        for c, d in st.session_state['portfolio'].items():
            total_asset += (d['qty'] * st.session_state['market_data'][c]['price'])

        with st.container(border=True):
            st.markdown(f"### 💰 총 자산<br><span style='color:#333D4B; font-size:28px; font-weight:bold'>{total_asset:,.0f} ID</span>", unsafe_allow_html=True)
            st.markdown("---")
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.metric("보유 이드", f"{st.session_state['balance_id']:,.0f}")
            c2.metric("내 엘피스", f"{st.session_state['my_elpis_locked']:,}")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        
        col_main_L, col_main_R = st.columns(2)
        
        with col_main_L:
             with st.container(border=True):
                st.subheader("⛏️ 채굴 (Daily Mining)")
                if st.button("채굴 시작", type="primary", use_container_width=True):
                    ok, reward = mining()
                    if ok: 
                        falling_coins()
                        st.success(f"+{reward:,} ID")
                        time.sleep(2) 
                        st.rerun()
                    else: st.warning("이미 채굴했습니다.")

        with col_main_R:
            with st.container(border=True):
                st.subheader("📝 프로필 수정")
                with st.expander("수정 열기"):
                    vision = st.text_area("비전", value=st.session_state['my_profile']['vision'])
                    sns = st.text_input("SNS", value=st.session_state['my_profile']['sns'])
                    
                    if st.button("저장", type="primary", use_container_width=True):
                        st.session_state['my_profile']['vision'] = vision
                        st.session_state['my_profile']['sns'] = sns
                        save_current_user_state(user_id) 
                        st.rerun()
                    
                    uploaded_file = st.file_uploader("사진", type=['jpg', 'png'], key="profile_upload", label_visibility="collapsed")
                    if uploaded_file is not None:
                        st.session_state['uploaded_photo_cache'] = uploaded_file
                        st.rerun()

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader(f"📨 {user_name}님에게 남겨진 메시지")
            my_messages = [m for m in st.session_state['board_messages'] if m['code'] == user_id]
            
            if my_messages:
                for m in my_messages:
                    st.info(f"[{m['user']}] {m['msg']} ({m['time']})")
            else:
                st.info("아직 도착한 메시지가 없습니다.")

    with tabs[1]:
        st.markdown("<h4 style='margin-bottom: 15px; font-weight: 800;'>관심 종목</h4>", unsafe_allow_html=True)
        
        # [수정] 공용 'interested_codes'가 아닌 개인 'likes' 리스트 사용
        targets = st.session_state['my_profile']['likes']
        targets = [t for t in targets if t != user_id]

        if not targets:
            st.markdown("<div style='text-align:center; padding: 40px 0; color:#8B95A1; font-size:13px;'>관심 종목이 없습니다.</div>", unsafe_allow_html=True)

        for code in targets:
            if code in st.session_state['market_data']:
                info = st.session_state['market_data'][code]
                c_price = info['price']
                c_change = info['change']

                with st.container(border=True):
                    r1, r2, r3 = st.columns([3, 2, 1], gap="small")

                    with r1:
                        st.markdown(f"**{info['name']}**")
                        if st.button(f"이동 >", key=f"fav_btn_{code}", type="secondary", use_container_width=True):
                            st.session_state['view_profile_id'] = code
                            st.session_state['selected_code'] = code 
                            st.rerun()
                    with r2:
                        color = "#E22A2A" if c_change > 0 else "#2A6BE2"
                        st.markdown(f"<div style='text-align:right; font-weight:bold; color:{color}'>{c_price:,}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align:right; font-size:12px; color:{color}'>{c_change}%</div>", unsafe_allow_html=True)
                    with r3:
                        if st.button("✕", key=f"del_{code}"): 
                            # [수정] 개인 리스트에서 삭제 후 저장
                            st.session_state['my_profile']['likes'].remove(code)
                            save_current_user_state(user_id)
                            st.rerun()

    with tabs[2]:
        st.markdown("""
            <style>
            .stButton > button {
                padding-left: 4px !important;
                padding-right: 4px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        col_s1, col_s2 = st.columns([3, 1])
        search_q = col_s1.text_input("검색 (ID/이름)", placeholder="종목 검색...", label_visibility="collapsed")
        if col_s2.button("🔍", use_container_width=True):
            found = False
            for k, v in st.session_state['market_data'].items():
                if search_q in k or search_q in v['name']:
                    st.session_state['selected_code'] = k
                    
                    # [수정] 검색 시 개인 'likes' 리스트에 추가 (공용 리스트 X)
                    if k not in st.session_state['my_profile']['likes']:
                        st.session_state['my_profile']['likes'].append(k)
                        save_current_user_state(user_id)
                    
                    found = True
                    break
            if not found: st.toast("검색 결과가 없습니다.")
            else: st.rerun()

        target = st.session_state['selected_code']
        market = st.session_state['market_data'][target]
        curr_price = market['price']
        change_pct = market['change']
        
        is_me = (target == user_id)
        
        with st.container(border=True):
            st.markdown(f"### {market['name']} <span style='font-size:14px; color:gray'>$ELP-{target}</span>", unsafe_allow_html=True)
            pc1, pc2 = st.columns(2)
            color_cls = "red" if change_pct >= 0 else "blue"
            pc1.markdown(f"**{curr_price:,} ID**")
            pc2.markdown(f":{color_cls}[{change_pct}%]")
        
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

        st.markdown("---")
        
        sell_rows_data = []
        for p, q in best_asks:
            sell_rows_data.append((p, q))
        while len(sell_rows_data) < 5:
            sell_rows_data.insert(0, (None, None))
            
        for p, q in sell_rows_data:
            c1, c2, c3 = st.columns([1.2, 1.5, 1.2])
            with c1: 
                if q: st.caption(f"{q:,}")
            with c2: 
                if p:
                    if st.button(f"{p:,}", key=f"ask_btn_{target}_{p}", type="secondary", use_container_width=True):
                         if not is_me: quick_buy_popup(target, p, market['name'])
            with c3: pass

        st.info(f"현재가: {curr_price:,}")

        buy_rows_data = []
        for p, q in best_bids:
            buy_rows_data.append((p, q))
        while len(buy_rows_data) < 5:
            buy_rows_data.append((None, None))
            
        for p, q in buy_rows_data:
            c1, c2, c3 = st.columns([1.2, 1.5, 1.2])
            with c1: pass
            with c2: 
                if p:
                    if st.button(f"{p:,}", key=f"bid_btn_{target}_{p}", type="secondary", use_container_width=True):
                        if is_me: quick_sell_popup(target, p, market['name'])
            with c3: 
                if q: st.caption(f"{q:,}")
        
        with st.expander("📊 차트", expanded=True):
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=market['history'], mode='lines+markers', line=dict(color='#E22A2A', width=2)))
            fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), dragmode=False, paper_bgcolor='white', plot_bgcolor='#F2F4F6')
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': False, 'displayModeBar': False})

        st.divider()
        st.subheader(f"💬 {market['name']} 토론방 (방명록)")
        with st.form(key='msg_form', clear_on_submit=True):
            user_msg = st.text_input("메시지", placeholder="응원/방명록 남기기")
            if st.form_submit_button("등록", type="primary", use_container_width=True) and user_msg:
                st.session_state['board_messages'].insert(0, {'code': target, 'user': user_id, 'msg': user_msg, 'time': datetime.datetime.now().strftime("%H:%M")})
                save_db()
                st.rerun()
        
        for m in st.session_state['board_messages'][:5]:
            if m['code'] == target:
                st.info(f"[{m['user']}] {m['msg']} ({m['time']})")

    with tabs[3]:
        target = st.session_state['selected_code']
        market = st.session_state['market_data'][target]
        st.subheader("🛒 매수 주문")
        
        if st.button(f"선택 종목: {market['name']} ({target})", type="secondary", use_container_width=True):
            st.session_state['view_profile_id'] = target
            st.rerun()
        
        with st.container(border=True):
            st.markdown(f"#### 가용: <span style='color:#3182F6'>{st.session_state['balance_id']:,.0f} ID</span>", unsafe_allow_html=True)
            buy_price = st.number_input("매수 희망가 (ID)", value=market['price'], step=100, key="buy_price_main")
            buy_qty = st.number_input("매수 수량 (주)", value=10, step=1, key="buy_qty_main")
            
            if st.button("🔴 매수 주문 전송", type="primary", use_container_width=True):
                ok, msg = place_order('BUY', target, buy_price, buy_qty)
                if ok: st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)

    with tabs[4]:
        st.subheader("💼 잔고 및 매도")
        
        with st.expander("📢 내 엘피스 상장 (IPO)", expanded=True):
            locked = st.session_state['my_elpis_locked']
            st.markdown(f"**보유(Lock): {locked:,} 주**")
            ipo_qty = st.number_input("상장 수량", 1, locked, 1000, key="ipo_qty")
            ipo_price = st.number_input("상장 가격", 100, value=10000, key="ipo_price")
            if st.button("내 엘피스 시장에 팔기 (상장)", type="primary", use_container_width=True):
                if locked >= ipo_qty:
                    st.session_state['my_elpis_locked'] -= ipo_qty
                    if user_id in st.session_state['market_data']:
                        st.session_state['market_data'][user_id]['price'] = ipo_price
                    else:
                        st.session_state['market_data'][user_id] = {'name': user_id, 'price': ipo_price, 'change': 0.0, 'desc': '신규 상장', 'history': [ipo_price]}
                    
                    st.session_state['pending_orders'].append({'code': user_id, 'type': 'SELL', 'price': ipo_price, 'qty': ipo_qty, 'user': user_id})
                    
                    # [수정] 상장 시 개인 'likes'에 추가
                    if user_id not in st.session_state['my_profile']['likes']:
                         st.session_state['my_profile']['likes'].append(user_id)
                    
                    save_current_user_state(user_id) 
                    st.success("상장 주문 등록 완료!"); time.sleep(1.5); st.rerun()
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
                color = "red" if profit >= 0 else "blue"
                
                with st.container(border=True):
                    st.markdown(f"**{st.session_state['market_data'][code]['name']} ({code})**")
                    if st.button(f"프로필 보기", key=f"pf_n_{code}", type="secondary", use_container_width=True):
                        st.session_state['view_profile_id'] = code
                        st.session_state['selected_code'] = code
                        st.rerun()
                        
                    col_info1, col_info2 = st.columns(2)
                    col_info1.metric("보유 수량", f"{info['qty']:,}주")
                    col_info2.markdown(f"수익률 <br> :{color}[{rate:.1f}%]", unsafe_allow_html=True)
                    
                    with st.expander("🔵 매도 하기"):
                        s_price = st.number_input("매도가", value=curr_p, step=100, key=f"sell_p_{code}")
                        s_qty = st.number_input("수량", 1, info['qty'], info['qty'], key=f"sell_q_{code}")
                        if st.button("매도 주문", key=f"btn_sell_{code}", type="primary", use_container_width=True):
                            ok, msg = place_order('SELL', code, s_price, s_qty)
                            if ok: st.success(msg); time.sleep(1); st.rerun()
                            else: st.error(msg)

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

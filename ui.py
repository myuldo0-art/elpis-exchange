import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import time
import random 

from database import save_db
from logic import place_order, mining, save_current_user_state

# --- [1. 이펙트: 터치 방해 금지 및 모바일 성능 최적화] ---
def falling_coins():
    # pointer-events: none; 설정으로 동전이 떨어져도 버튼 클릭 가능
    st.markdown("""
        <style>
        .coin-emitter {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none; z-index: 9990;
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
    # 모바일 성능 고려하여 파티클 개수 최적화 (30 -> 25)
    for _ in range(25): 
        left = random.randint(0, 95)
        duration = random.uniform(1.5, 3.0)
        delay = random.uniform(0, 1.5)
        coin_html += f'<div class="coin-particle" style="left:{left}%; animation: fall {duration}s {delay}s linear forwards;">🪙</div>'
    coin_html += '</div>'
    
    placeholder.markdown(coin_html, unsafe_allow_html=True)
    time.sleep(0.1)

# --- [2. 팝업: 모바일 화면 꽉 차게 최적화] ---
@st.dialog("⚡ 간편 매수")
def quick_buy_popup(code, price, name):
    st.markdown(f"**{name}**")
    c1, c2 = st.columns(2)
    c1.metric("가격", f"{price:,}")
    
    bal = st.session_state.get('balance_id', 0)
    max_q = int(bal / price) if price > 0 else 0
    c2.metric("가능", f"{max_q:,}")
    
    st.divider()
    # 모바일 키패드 입력 편의성 고려
    q = st.number_input("매수 수량", 1, value=10, step=1)
    
    cost = price * q
    if cost > bal: st.error(f"부족: {cost-bal:,.0f} ID")
    else: st.caption(f"총액: {cost:,.0f} ID")
    
    # 버튼을 꽉 채워 터치 오류 방지
    if st.button("체결하기", type="primary", use_container_width=True):
        ok, msg = place_order('BUY', code, price, q)
        if ok:
            st.success("매수 성공!")
            time.sleep(0.5); st.rerun()
        else: st.error(msg)

@st.dialog("⚡ 간편 매도")
def quick_sell_popup(code, price, name):
    uid = st.session_state['user_info'].get('id')
    pf = st.session_state.get('portfolio', {})
    qty = pf.get(code, {}).get('qty', 0)
    if code == uid: qty += st.session_state.get('my_elpis_locked', 0)

    st.markdown(f"**{name}**")
    c1, c2 = st.columns(2)
    c1.metric("가격", f"{price:,}")
    c2.metric("보유", f"{qty:,}")
    
    st.divider()
    max_v = qty if qty > 0 else 1
    q = st.number_input("매도 수량", 1, max_v, value=10 if qty>=10 else 1)
    st.caption(f"정산: {price * q:,.0f} ID")
    
    if st.button("체결하기", type="primary", use_container_width=True):
        rq = st.session_state['portfolio'].get(code, {}).get('qty', 0)
        if code == uid: rq += st.session_state.get('my_elpis_locked', 0)
            
        if rq < q: st.error("수량 부족")
        else:
            ok, msg = place_order('SELL', code, price, q)
            if ok:
                st.success("매도 성공!")
                time.sleep(0.5); st.rerun()
            else: st.error(msg)

# --- [3. 메인 UI 렌더링] ---
def render_ui():
    uid = st.session_state['user_info'].get('id', 'Guest')
    uname = st.session_state['user_names'].get(uid, '사용자')

    if 'uploaded_photo_cache' not in st.session_state:
        st.session_state['uploaded_photo_cache'] = None

    # 프로필 조회 모달 (안전한 컨테이너 사용)
    if st.session_state.get('view_profile_id'):
        tid = st.session_state['view_profile_id']
        tname = st.session_state['user_names'].get(tid, tid)
        
        v, s = "정보 없음", "정보 없음"
        if tid in st.session_state['user_states']:
            p = st.session_state['user_states'][tid]['my_profile']
            v, s = p['vision'], p['sns']
        elif tid in st.session_state['market_data']:
             v = st.session_state['market_data'][tid].get('desc', '')
        
        with st.container(border=True):
            st.subheader(tname)
            st.caption(f"@{tid}")
            st.info(f"Vision: {v}")
            st.text(f"SNS: {s}")
            if st.button("닫기", use_container_width=True):
                st.session_state['view_profile_id'] = None
                st.rerun()

    # [CSS: Universal Responsive Design]
    # 모든 기종에서 깨지지 않는 반응형 카드 및 탭 스타일 정의
    st.markdown("""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        * { font-family: 'Pretendard', sans-serif; }
        
        /* 탭 버튼 높이 및 패딩 최적화 (터치 영역 확보) */
        .stTabs [data-baseweb="tab"] {
            height: 50px; padding: 0 10px; flex: 1; border-radius: 8px;
        }
        /* 메트릭 값 폰트 크기 반응형 조절 */
        div[data-testid="stMetricValue"] > div { font-size: 20px !important; }
        
        /* 버튼 패딩 최소화로 모바일 공간 확보 */
        .stButton > button {
            padding-left: 5px !important;
            padding-right: 5px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 탭 이름 간소화 (모바일 가로폭 고려)
    tabs = st.tabs(["홈", "관심", "호가", "주문", "자산", "내역", "준비"])

    # === Tab 0: 홈 (대시보드) ===
    with tabs[0]:
        # 상단바
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**👋 {uname}**")
            vis = st.session_state['my_profile']['vision']
            st.caption(vis if vis else "비전을 입력하세요")
        with c2:
            if st.button("OUT", key="logout_btn", type="secondary"):
                st.session_state['logged_in'] = False
                st.session_state['uploaded_photo_cache'] = None
                st.rerun()

        # 자산 카드 (Native Container -> 모바일 깨짐 방지 핵심)
        total = st.session_state['balance_id']
        for c, d in st.session_state['portfolio'].items():
            total += (d['qty'] * st.session_state['market_data'][c]['price'])
            
        with st.container(border=True):
            st.caption("총 자산 가치")
            st.markdown(f"### {total:,.0f} ID")
            
            c_a, c_b = st.columns(2)
            c_a.metric("현금", f"{st.session_state['balance_id']:,.0f}")
            c_b.metric("Lock", f"{st.session_state['my_elpis_locked']:,}")

        # 액션 버튼 (2열 배치, 꽉 차게)
        ac1, ac2 = st.columns(2)
        with ac1:
            with st.container(border=True):
                st.markdown("**⛏️ 채굴**")
                if st.button("GET", use_container_width=True):
                    ok, r = mining()
                    if ok:
                        falling_coins()
                        st.toast(f"+{r:,} ID 획득!", icon="💰")
                        time.sleep(1.5); st.rerun()
                    else: st.toast("이미 완료", icon="✅")
        with ac2:
            with st.container(border=True):
                st.markdown("**👤 프로필**")
                # 이미지 반응형 처리
                img = st.session_state.get('uploaded_photo_cache')
                if img: st.image(img, use_container_width=True)
                else: st.caption("사진 없음")

                with st.expander("수정"):
                    nv = st.text_area("비전", value=st.session_state['my_profile']['vision'])
                    ns = st.text_input("SNS", value=st.session_state['my_profile']['sns'])
                    up = st.file_uploader("사진", type=['jpg','png'], key="pu", label_visibility="collapsed")
                    if up: 
                        st.session_state['uploaded_photo_cache'] = up
                        st.rerun()
                    if st.button("저장", use_container_width=True):
                        st.session_state['my_profile']['vision'] = nv
                        st.session_state['my_profile']['sns'] = ns
                        save_current_user_state(uid)
                        st.success("저장됨"); time.sleep(0.5); st.rerun()

        # 알림
        with st.container(border=True):
            msgs = [m for m in st.session_state['board_messages'] if m['code'] == uid]
            st.caption(f"알림 ({len(msgs)})")
            if msgs:
                for m in msgs[:3]:
                    st.info(f"{m['msg']}")
            else: st.text("새 알림 없음")

    # === Tab 1: 관심 종목 ===
    with tabs[1]:
        favs = [t for t in st.session_state['interested_codes'] if t != uid]
        if not favs: st.info("관심 종목을 추가하세요")
        
        for code in favs:
            if code in st.session_state['market_data']:
                d = st.session_state['market_data'][code]
                with st.container(border=True):
                    # 모바일에서 한 줄에 깔끔하게 나오도록 비율 조정
                    fc1, fc2, fc3 = st.columns([3, 2, 1])
                    with fc1:
                        st.markdown(f"**{d['name']}**")
                    with fc2:
                        clr = "red" if d['change'] > 0 else "blue"
                        st.markdown(f":{clr}[{d['price']:,}]")
                    with fc3:
                        if st.button(">", key=f"go_{code}"):
                            st.session_state['selected_code'] = code
                            st.session_state['view_profile_id'] = code
                            st.rerun()

    # === Tab 2: 호가 (Universal Responsive) ===
    with tabs[2]:
        # 검색
        sc1, sc2 = st.columns([3, 1])
        keyword = sc1.text_input("검색", placeholder="종목/ID", label_visibility="collapsed")
        if sc2.button("🔍", use_container_width=True):
            for k,v in st.session_state['market_data'].items():
                if keyword in k or keyword in v['name']:
                    st.session_state['selected_code'] = k
                    st.session_state['interested_codes'].add(k)
                    save_db(); st.rerun()
                    break

        target = st.session_state['selected_code']
        mdata = st.session_state['market_data'][target]

        with st.container(border=True):
            st.markdown(f"### {mdata['name']}")
            mc1, mc2 = st.columns(2)
            mc1.metric("현재가", f"{mdata['price']:,}")
            clr = "red" if mdata['change'] > 0 else "blue"
            mc2.markdown(f"**:{clr}[{mdata['change']}%]**")

        # 호가 데이터 처리
        p_ords = [o for o in st.session_state['pending_orders'] if o['code'] == target]
        b_dic, s_dic = {}, {}
        for o in p_ords:
            if o['type']=='BUY': b_dic[o['price']] = b_dic.get(o['price'],0)+o['qty']
            else: s_dic[o['price']] = s_dic.get(o['price'],0)+o['qty']
        
        asks = sorted(s_dic.items(), key=lambda x:x[0], reverse=True)[-5:] 
        asks.sort(key=lambda x:x[0], reverse=True)
        bids = sorted(b_dic.items(), key=lambda x:x[0], reverse=True)[:5]

        st.markdown("---")
        # [모바일 호가창 레이아웃: 잔량 | 버튼(가격) | 잔량]
        # 컬럼 비율 [1.2, 1.6, 1.2]가 좁은 화면에서도 숫자 줄바꿈 방지에 가장 효과적
        
        # 매도 (Red)
        for _ in range(5-len(asks)): asks.insert(0, (None,None))
        for p, q in asks:
            hc1, hc2, hc3 = st.columns([1.2, 1.6, 1.2])
            with hc1: 
                if q: st.caption(f"{q:,}")
            with hc2:
                if p:
                    # use_container_width=True로 버튼이 꽉 차게
                    if st.button(f"{p:,}", key=f"a_{p}", use_container_width=True):
                         if target != uid: quick_buy_popup(target, p, mdata['name'])
            with hc3: pass

        st.info(f"현재가: {mdata['price']:,}")

        # 매수 (Blue)
        for _ in range(5-len(bids)): bids.append((None,None))
        for p, q in bids:
            hc1, hc2, hc3 = st.columns([1.2, 1.6, 1.2])
            with hc1: pass
            with hc2:
                if p:
                    if st.button(f"{p:,}", key=f"b_{p}", use_container_width=True):
                        if target == uid: quick_sell_popup(target, p, mdata['name'])
            with hc3:
                if q: st.caption(f"{q:,}")

        # 차트 & 토론
        with st.expander("차트"):
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=mdata['history'], mode='lines', line=dict(color='#E22A2A')))
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=200)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### 토론")
        with st.form("chat_form", clear_on_submit=True):
            cm = st.text_input("메시지")
            if st.form_submit_button("전송", use_container_width=True) and cm:
                st.session_state['board_messages'].insert(0, {'code':target, 'user':uid, 'msg':cm, 'time':datetime.datetime.now().strftime("%H:%M")})
                save_db(); st.rerun()
        
        for m in st.session_state['board_messages'][:5]:
            if m['code'] == target:
                st.caption(f"**{m['user']}**: {m['msg']}")

    # === Tab 3: 주문 ===
    with tabs[3]:
        t = st.session_state['selected_code']
        info = st.session_state['market_data'][t]
        
        with st.container(border=True):
            st.subheader("매수하기")
            st.caption(f"종목: {info['name']}")
            st.metric("내 잔고", f"{st.session_state['balance_id']:,.0f}")
            
            bp = st.number_input("가격", value=info['price'], step=100)
            bq = st.number_input("수량", value=10, step=1)
            
            if st.button("매수 주문", type="primary", use_container_width=True):
                ok, msg = place_order('BUY', t, bp, bq)
                if ok: st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)

    # === Tab 4: 자산 ===
    with tabs[4]:
        with st.expander("📢 내 주식 상장 (IPO)"):
            lk = st.session_state['my_elpis_locked']
            st.write(f"Lock: {lk:,}")
            iq = st.number_input("수량", 1, lk, 1000)
            ip = st.number_input("가격", 100, value=10000)
            if st.button("상장 (매도 주문)", type="primary", use_container_width=True):
                if lk >= iq:
                    st.session_state['my_elpis_locked'] -= iq
                    if user_id not in st.session_state['market_data']:
                        st.session_state['market_data'][user_id] = {'name':user_id, 'price':ip, 'change':0.0, 'desc':'', 'history':[ip]}
                    st.session_state['pending_orders'].append({'code':user_id, 'type':'SELL', 'price':ip, 'qty':iq, 'user':user_id})
                    st.session_state['interested_codes'].add(user_id)
                    save_current_user_state(user_id)
                    st.success("상장 완료"); st.rerun()
                else: st.error("수량 부족")

        st.markdown("#### 보유 주식")
        pf = st.session_state['portfolio']
        if not pf: st.info("보유 주식이 없습니다.")
        
        for c, v in pf.items():
            cur = st.session_state['market_data'][c]['price']
            profit = (v['qty']*cur) - (v['qty']*v['avg_price'])
            pct = (profit / (v['qty']*v['avg_price'])) * 100 if v['avg_price'] else 0
            clr = "red" if pct >= 0 else "blue"
            
            with st.container(border=True):
                st.markdown(f"**{st.session_state['market_data'][c]['name']}**")
                c1, c2 = st.columns(2)
                c1.caption(f"{v['qty']:,}주")
                c2.markdown(f":{clr}[{pct:.1f}%]")
                
                with st.expander("매도"):
                    sp = st.number_input("가격", value=cur, key=f"sp_{c}")
                    sq = st.number_input("수량", 1, v['qty'], v['qty'], key=f"sq_{c}")
                    if st.button("매도", key=f"sb_{c}", use_container_width=True):
                         ok, msg = place_order('SELL', c, sp, sq)
                         if ok: st.success(msg); time.sleep(1); st.rerun()
                         else: st.error(msg)

    # === Tab 5: 내역 ===
    with tabs[5]:
        st.markdown("##### 미체결")
        mp = [o for o in st.session_state['pending_orders'] if o['user']==user_id]
        if mp: st.dataframe(pd.DataFrame(mp)[['code','type','price','qty']], use_container_width=True)
        else: st.caption("없음")
        
        st.divider()
        st.markdown("##### 체결 내역")
        th = st.session_state.get('trade_history', [])
        mt = [t for t in th if t.get('buyer')==user_id or t.get('seller')==user_id]
        if mt: st.dataframe(pd.DataFrame(mt)[['time','name','type','price','qty']], use_container_width=True)
        else: st.caption("없음")

    # === Tab 6: 거래소 ===
    with tabs[6]:
        st.info("Coming Soon - Global Market")

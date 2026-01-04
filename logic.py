import streamlit as st
import datetime
from database import save_db

# --- [유저 상태 동기화] ---
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

# --- [현재 상태 저장] ---
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

# --- [가격 업데이트] ---
def update_price_match(market_code, price):
    market = st.session_state['market_data'][market_code]
    market['price'] = price
    market['change'] = round(((price - market['history'][0]) / market['history'][0]) * 100, 2)
    market['history'].append(price)
    save_db()

# --- [주문 처리 핵심 로직] ---
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
                st.session_state['user_states'][seller_id]['balance_id'] += (match_price * match_qty)
            
            sell_order['qty'] -= match_qty
            remaining_qty -= match_qty
            
            update_price_match(code, match_price)
            
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
        # [CRITICAL FIX] 본인 종목일 경우 Locked 물량과 Portfolio 물량을 합산하여 검증 및 차감
        pf_qty = st.session_state['portfolio'].get(code, {}).get('qty', 0)
        locked_qty = 0
        if code == user_id:
            locked_qty = st.session_state.get('my_elpis_locked', 0)
            
        total_avail = pf_qty + locked_qty
        
        if total_avail < qty:
            return False, "보유 수량이 부족합니다."
            
        # 수량 차감 로직: Portfolio에서 먼저 빼고, 부족하면 Locked에서 뺌
        remaining_deduct = qty
        
        if pf_qty > 0:
            deduct_p = min(pf_qty, remaining_deduct)
            st.session_state['portfolio'][code]['qty'] -= deduct_p
            if st.session_state['portfolio'][code]['qty'] == 0:
                del st.session_state['portfolio'][code]
            remaining_deduct -= deduct_p
            
        if remaining_deduct > 0 and code == user_id:
            st.session_state['my_elpis_locked'] -= remaining_deduct

        # 이하 매칭 로직은 기존과 동일
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

# --- [채굴 함수] ---
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

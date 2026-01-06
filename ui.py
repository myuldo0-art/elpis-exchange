import streamlit as st
import time
import logic  # logic.py의 함수들을 사용하기 위해 임포트

# 1. [유지/변경] 황금 동전 이펙트 함수
def falling_coins_effect():
    st.markdown(
        """
        <style>
        @keyframes fall {
            0% { transform: translateY(-100vh); opacity: 1; }
            100% { transform: translateY(100vh); opacity: 0; }
        }
        .coin {
            position: fixed;
            top: -10vh;
            font-size: 2rem;
            animation: fall linear forwards;
            z-index: 9999;
        }
        </style>
        <script>
        function createCoin() {
            const coin = document.createElement('div');
            coin.innerText = '🪙';
            coin.className = 'coin';
            coin.style.left = Math.random() * 100 + 'vw';
            coin.style.animationDuration = Math.random() * 2 + 3 + 's';
            coin.style.fontSize = Math.random() * 20 + 20 + 'px';
            document.body.appendChild(coin);
            
            setTimeout(() => {
                coin.remove();
            }, 5000);
        }
        for(let i=0; i<50; i++) {
            setTimeout(createCoin, i * 100);
        }
        </script>
        """,
        unsafe_allow_html=True
    )
    st.toast("🪙 황금 동전이 쏟아집니다! 채굴 성공! 🪙", icon="💰")

# 2. [유지/변경] 프로필 표시 함수 (사진 소실 방지 및 세로 보기 적용)
def display_profile(user_data, update_callback):
    st.markdown("### 👤 내 프로필")
    
    current_image = user_data.get('profile_image')
    
    with st.form("profile_form"):
        new_vision = st.text_area("나의 비전 (Vision)", value=user_data.get('vision', ''), height=100)
        
        st.markdown("#### 프로필 사진")
        uploaded_file = st.file_uploader("사진 변경 (선택사항)", type=['png', 'jpg', 'jpeg'])
        
        # 이미지 미리보기 (세로 비율 유지)
        if uploaded_file is not None:
            st.image(uploaded_file, caption="새로 업로드된 사진", width=300)
        elif current_image is not None:
            st.image(current_image, caption="현재 프로필 사진", width=300)
        else:
            st.info("등록된 사진이 없습니다.")

        submitted = st.form_submit_button("프로필 수정 저장")
        
        if submitted:
            # 사진 소실 방지 로직
            final_image_data = current_image 
            if uploaded_file is not None:
                final_image_data = uploaded_file.getvalue()
            
            # logic.py의 업데이트 함수 호출
            success = update_callback(user_data['username'], new_vision, final_image_data)
            
            if success:
                st.success("프로필이 성공적으로 업데이트되었습니다!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("업데이트 중 오류가 발생했습니다.")

# 3. [유지/변경] 채굴 화면 함수 (황금 동전 이펙트 적용)
def display_mining(user_data, mining_callback):
    st.markdown("### ⛏️ 엘피스 채굴하기")
    st.write(f"현재 보유 자산: **{user_data.get('assets', 0):,} KRW**")
    
    if st.button("채굴 시작 (Click)", use_container_width=True):
        with st.spinner("블록체인 네트워크 연결 중..."):
            time.sleep(1.5)
            
            # logic.py의 채굴 함수 호출
            earned = mining_callback(user_data['username'])
            
            if earned > 0:
                falling_coins_effect() # 황금 동전 효과
                
                st.markdown(f"""
                <div style="padding:20px; border-radius:10px; background-color:#f0f2f6; text-align:center; border: 2px solid #FFD700;">
                    <h2 style="color:#d4af37;">🎉 채굴 성공! 🎉</h2>
                    <h3>+{earned:,} KRW</h3>
                    <p>자산이 지갑으로 전송되었습니다.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("채굴 쿨타임 중이거나 오류가 발생했습니다.")

# 4. [복구됨] 메인 UI 렌더링 함수 (이 부분이 빠져서 에러가 났습니다)
def render_ui(current_user):
    # 사이드바 메뉴
    menu = st.sidebar.radio("메뉴", ["채굴(Mining)", "프로필(Profile)"])
    
    if menu == "채굴(Mining)":
        # logic.process_mining 함수가 있다고 가정 (없으면 logic.py 확인 필요)
        display_mining(current_user, logic.process_mining)
        
    elif menu == "프로필(Profile)":
        # logic.update_profile 함수가 있다고 가정
        display_profile(current_user, logic.update_profile)

import streamlit as st
import time
import base64

# [주의] 맨 위에서 import logic을 하지 않습니다. (에러 원인 제거)

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


def display_profile(user_data, update_callback):
    st.markdown("### 👤 내 프로필")
    
    current_image = user_data.get('profile_image')
    
    with st.form("profile_form"):
        new_vision = st.text_area("나의 비전 (Vision)", value=user_data.get('vision', ''), height=100)
        
        st.markdown("#### 프로필 사진")
        uploaded_file = st.file_uploader("사진 변경 (선택사항)", type=['png', 'jpg', 'jpeg'])
        
        # 이미지 미리보기
        if uploaded_file is not None:
            st.image(uploaded_file, caption="새로 업로드된 사진", width=300)
        elif current_image is not None:
            st.image(current_image, caption="현재 프로필 사진", width=300)
        else:
            st.info("등록된 사진이 없습니다.")

        submitted = st.form_submit_button("프로필 수정 저장")
        
        if submitted:
            final_image_data = current_image 
            if uploaded_file is not None:
                final_image_data = uploaded_file.getvalue()
            
            success = update_callback(user_data['username'], new_vision, final_image_data)
            
            if success:
                st.success("프로필이 성공적으로 업데이트되었습니다!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("업데이트 중 오류가 발생했습니다.")


def display_mining(user_data, mining_callback):
    st.markdown("### ⛏️ 엘피스 채굴하기")
    st.write(f"현재 보유 자산: **{user_data.get('assets', 0):,} KRW**")
    
    if st.button("채굴 시작 (Click)", use_container_width=True):
        with st.spinner("블록체인 네트워크 연결 중..."):
            time.sleep(1.5)
            
            earned = mining_callback(user_data['username'])
            
            if earned > 0:
                falling_coins_effect()
                
                st.markdown(f"""
                <div style="padding:20px; border-radius:10px; background-color:#f0f2f6; text-align:center; border: 2px solid #FFD700;">
                    <h2 style="color:#d4af37;">🎉 채굴 성공! 🎉</h2>
                    <h3>+{earned:,} KRW</h3>
                    <p>자산이 지갑으로 전송되었습니다.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("채굴 쿨타임 중이거나 오류가 발생했습니다.")


def render_ui(current_user):
    # [핵심 수정] logic 모듈을 함수 안에서 import 합니다.
    # 이렇게 하면 파일이 로딩될 때 충돌(순환 참조)이 발생하지 않습니다.
    import logic
    
    menu = st.sidebar.radio("메뉴", ["채굴(Mining)", "프로필(Profile)"])
    
    if menu == "채굴(Mining)":
        display_mining(current_user, logic.process_mining)
        
    elif menu == "프로필(Profile)":
        display_profile(current_user, logic.update_profile)

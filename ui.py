import streamlit as st
import time
import base64

# [변경됨] 황금 동전 이펙트 함수 추가
def falling_coins_effect():
    # CSS와 JS를 이용해 황금 동전이 떨어지는 효과 구현
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
            coin.style.animationDuration = Math.random() * 2 + 3 + 's'; // 3~5초
            coin.style.fontSize = Math.random() * 20 + 20 + 'px';
            document.body.appendChild(coin);
            
            setTimeout(() => {
                coin.remove();
            }, 5000);
        }
        // 50개의 동전 생성
        for(let i=0; i<50; i++) {
            setTimeout(createCoin, i * 100);
        }
        </script>
        """,
        unsafe_allow_html=True
    )
    # 스크립트가 실행되지 않을 경우를 대비한 토스트 메시지
    st.toast("🪙 황금 동전이 쏟아집니다! 채굴 성공! 🪙", icon="💰")


def display_profile(user_data, update_callback):
    st.markdown("### 👤 내 프로필")
    
    # [변경됨] 현재 저장된 이미지 불러오기
    current_image = user_data.get('profile_image')
    
    with st.form("profile_form"):
        # 비전 텍스트 수정
        new_vision = st.text_area("나의 비전 (Vision)", value=user_data.get('vision', ''), height=100)
        
        # [변경됨] 사진 업로드 및 미리보기
        # 세로 사진이 잘리지 않도록 width 파라미터 대신 use_container_width=False 사용 혹은 캡션 조정
        st.markdown("#### 프로필 사진")
        uploaded_file = st.file_uploader("사진 변경 (선택사항)", type=['png', 'jpg', 'jpeg'])
        
        # 미리보기 로직
        if uploaded_file is not None:
            st.image(uploaded_file, caption="새로 업로드된 사진", width=300) # width 지정으로 세로 비율 유지 유도
        elif current_image is not None:
            # [변경됨] 기존 사진이 있으면 보여주기 (세로 보기 최적화)
            st.image(current_image, caption="현재 프로필 사진", width=300) 
        else:
            st.info("등록된 사진이 없습니다.")

        submitted = st.form_submit_button("프로필 수정 저장")
        
        if submitted:
            # [변경됨] 사진 저장 로직: 업로드가 없으면 기존 데이터 유지
            final_image_data = current_image # 기본값은 기존 사진
            
            if uploaded_file is not None:
                final_image_data = uploaded_file.getvalue() # 새 사진이 있으면 덮어쓰기
            
            # 콜백으로 데이터 업데이트 요청
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
            time.sleep(1.5) # 채굴 느낌을 위한 딜레이
            
            # 채굴 로직 실행
            earned = mining_callback(user_data['username'])
            
            if earned > 0:
                # [변경됨] 풍선 효과 대신 황금 동전 효과 적용
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

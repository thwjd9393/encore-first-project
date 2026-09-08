import streamlit as st
from pathlib import Path


def load_signup_css():
    css_path = (
        Path(__file__).parent.parent
        / "styles"
        / "signup.css"
    )

    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True,
        )


def render_signup():
    """회원가입 화면"""

    load_signup_css()

    # ==========================================
    # 1. 상단 로고
    # ==========================================

    st.markdown(
        """
        <div class="signup-navbar">
            <div class="brand-logo">
                <span class="brand-icon">🍴</span>
                <span>맛집친구</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ==========================================
    # 2. 회원가입 안내 문구
    # ==========================================

    st.markdown(
        """
        <div class="signup-label">
            맛있는
        </div>

        <div class="signup-title">
            새로운 맛집 생활을 시작해보세요
        </div>

        <div class="signup-description">
            AI가 추천하는 나만의 맛집을 만나보세요.
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ==========================================
    # 3. 회원 정보 입력
    # ==========================================

    login_id = st.text_input(
        "아이디",
        placeholder="아이디를 입력하세요",
        label_visibility="collapsed",
        key="signup_login_id",
    )

    email = st.text_input(
        "이메일",
        placeholder="이메일을 입력하세요",
        label_visibility="collapsed",
        key="signup_email",
    )

    password = st.text_input(
        "비밀번호",
        type="password",
        placeholder="비밀번호를 입력하세요",
        label_visibility="collapsed",
        key="signup_password",
    )

    password_confirm = st.text_input(
        "비밀번호 확인",
        type="password",
        placeholder="비밀번호를 다시 입력하세요",
        label_visibility="collapsed",
        key="signup_password_confirm",
    )

    username = st.text_input(
        "닉네임",
        placeholder="닉네임을 입력하세요",
        label_visibility="collapsed",
        key="signup_username",
    )


    # ==========================================
    # 4. 약관 동의
    # ==========================================

    terms_agreed = st.checkbox(
        "이용약관에 동의합니다.",
        key="signup_terms",
    )

    privacy_agreed = st.checkbox(
        "개인정보 수집 및 이용에 동의합니다.",
        key="signup_privacy",
    )


    # ==========================================
    # 5. 사용자 구분
    # ==========================================

    user_type = 2


    # ==========================================
    # 6. 회원가입 버튼
    # ==========================================

    if st.button(
        "회원가입",
        use_container_width=True,
        key="signup_button",
    ):

        login_id = login_id.strip()

        if not login_id:
            st.error("아이디를 입력해주세요.")
            return

        if len(login_id) < 4 or len(login_id) > 20:
            st.error("아이디는 4~20자로 입력해주세요.")
            return


        email = email.strip()

        if not email:
            st.error("이메일을 입력해주세요.")
            return

        if "@" not in email:
            st.error("올바른 이메일 형식으로 입력해주세요.")
            return


        if not password:
            st.error("비밀번호를 입력해주세요.")
            return

        if len(password) < 8:
            st.error("비밀번호는 8자 이상 입력해주세요.")
            return


        if not password_confirm:
            st.error("비밀번호 확인을 입력해주세요.")
            return

        if password != password_confirm:
            st.error("비밀번호가 서로 다릅니다.")
            return


        username = username.strip()

        if not username:
            st.error("닉네임을 입력해주세요.")
            return

        if len(username) < 2 or len(username) > 30:
            st.error("닉네임은 2~30자로 입력해주세요.")
            return


        if not terms_agreed:
            st.error("이용약관에 동의해주세요.")
            return

        if not privacy_agreed:
            st.error(
                "개인정보 수집 및 이용에 동의해주세요."
            )
            return


        # ======================================
        # FastAPI 연결 예정
        # ======================================

        # result = api(
        #     "POST",
        #     "/auth/signup",
        #     json={
        #         "login_id": login_id,
        #         "email": email,
        #         "password": password,
        #         "username": username,
        #         "user_type": user_type,
        #     },
        # )

        st.success(
            "회원가입 입력값 확인이 완료되었습니다."
        )


    # ==========================================
    # 7. 로그인 화면 이동
    # ==========================================

    st.markdown(
        """
        <div class="signup-footer">
            이미 계정이 있으신가요?
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "로그인하기",
        use_container_width=True,
        key="go_login_button",
    ):
        st.session_state.page = "login"
        st.rerun()
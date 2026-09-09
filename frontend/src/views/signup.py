from pathlib import Path

import streamlit as st

from src.common.api_client import post_json


def load_signup_terms():
    terms_path = Path(__file__).resolve().parents[3] / "약관.md"
    terms_text = "이용약관 파일을 찾을 수 없습니다."
    privacy_text = "개인정보 수집 및 이용 동의 파일을 찾을 수 없습니다."
    if not terms_path.is_file():
        return terms_text, privacy_text

    current = None
    terms_lines = []
    privacy_lines = []
    for line in terms_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## 이용약관"):
            current = "terms"
            continue
        if line.startswith("## 개인정보"):
            current = "privacy"
            continue
        if line.startswith("## "):
            current = None
            continue
        if current == "terms":
            terms_lines.append(line)
        elif current == "privacy":
            privacy_lines.append(line)

    if terms_lines:
        terms_text = "\n".join(terms_lines).strip()
    if privacy_lines:
        privacy_text = "\n".join(privacy_lines).strip()
    return terms_text, privacy_text


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

    # MVP 인증은 이메일 + 비밀번호다. 문자열 로그인 아이디는 받지 않는다.
    # 약관 체크 때 화면이 다시 그려지면 비밀번호 값이 비워지므로 form으로 한 번에 제출한다.
    terms_text, privacy_text = load_signup_terms()

    with st.form("signup_form", clear_on_submit=False):
        email = st.text_input(
            "이메일",
            placeholder="이메일을 입력하세요",
            key="signup_email",
        )

        password = st.text_input(
            "비밀번호",
            type="password",
            placeholder="비밀번호를 입력하세요",
            key="signup_password",
        )

        password_confirm = st.text_input(
            "비밀번호 확인",
            type="password",
            placeholder="비밀번호를 다시 입력하세요",
            key="signup_password_confirm",
        )

        username = st.text_input(
            "닉네임",
            placeholder="닉네임을 입력하세요",
            key="signup_username",
        )

        with st.expander("이용약관 보기"):
            st.markdown(terms_text)

        terms_agreed = st.checkbox(
            "이용약관에 동의합니다.",
            key="signup_terms",
        )

        with st.expander("개인정보 수집 및 이용 동의 보기"):
            st.markdown(privacy_text)

        privacy_agreed = st.checkbox(
            "개인정보 수집 및 이용에 동의합니다.",
            key="signup_privacy",
        )

        submitted = st.form_submit_button(
            "회원가입",
            use_container_width=True,
        )

    if submitted:
        email = (email or "").strip()

        if not email:
            st.error("이메일을 입력해주세요.")
            return

        if "@" not in email:
            st.error("올바른 이메일 형식으로 입력해주세요.")
            return

        # --------------------------------------
        # 비밀번호 검증
        # --------------------------------------

        if not (password or "").strip():
            st.error("비밀번호를 입력해주세요.")
            return

        if len(password) < 8:
            st.error("비밀번호는 8자 이상 입력해주세요.")
            return

        if len(password) > 128:
            st.error("비밀번호는 128자 이하로 입력해주세요.")
            return

        if not password_confirm:
            st.error("비밀번호 확인을 입력해주세요.")
            return

        if password != password_confirm:
            st.error("비밀번호가 서로 다릅니다.")
            return

        # --------------------------------------
        # 닉네임 검증
        # 백엔드 SignUpRequest 기준: 1~45자
        # --------------------------------------

        username = (username or "").strip()

        if not username:
            st.error("닉네임을 입력해주세요.")
            return

        if len(username) > 45:
            st.error("닉네임은 45자 이하로 입력해주세요.")
            return

        # --------------------------------------
        # 약관 동의 검증
        # --------------------------------------

        if not terms_agreed:
            st.error("이용약관에 동의해주세요.")
            return

        if not privacy_agreed:
            st.error(
                "개인정보 수집 및 이용에 동의해주세요."
            )
            return

        # ======================================
        # 6. FastAPI 회원가입 요청
        # ======================================

        with st.spinner("가입을 처리하는 중..."):
            result = post_json(
                "/auth/signups",
                json_body={
                    "email": email,
                    "password": password,
                    "nickname": username,
                    "terms_agreed": terms_agreed,
                    "privacy_agreed": privacy_agreed,
                },
            )

        if result["ok"]:
            st.session_state.page = "login"
            st.session_state.login_notice = (
                "회원가입이 완료되었습니다. 로그인해주세요."
            )
            st.rerun()

        error = result.get("error") or {}
        status_code = result.get("status_code")
        message = error.get("message") or "회원가입 처리 중 오류가 발생했습니다."

        if status_code == 409:
            st.error(message)
            return

        if status_code == 422:
            st.error("입력값을 다시 확인해주세요.")
            return

        if status_code == 429:
            st.error(message)
            return

        if status_code == 0:
            st.error(message)
            return

        st.error(
            "회원가입 처리 중 오류가 발생했습니다. "
            "잠시 후 다시 시도해주세요."
        )

    # ==========================================
    # 8. 로그인 화면 이동
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
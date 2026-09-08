from pathlib import Path
from textwrap import dedent

import streamlit as st


def load_login_css():
    css_path = (
        Path(__file__).parent.parent
        / "styles"
        / "login.css"
    )

    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


def render_navbar():

    st.markdown(
        dedent(
            """
            <div class="navbar">

                <div class="navbar-brand-group">

                    <div class="navbar-logo">
                        🍽 PlayEAT
                    </div>

                    <div class="navbar-slogan">
                        오늘의 한 끼가,
                        <span class="navbar-slogan-highlight">
                            좋은 기억이 되도록
                        </span>
                    </div>

                </div>

                <div class="navbar-text">
                    AI 맛집 추천 서비스
                </div>

            </div>
            """
        ),
        unsafe_allow_html=True,
    )

def render_login():
    """로그인 화면"""

    load_login_css()

    # -----------------------------------------
    # 로그인 화면
    # -----------------------------------------

    login_col, image_col = st.columns(
        [0.94, 1.06],
        gap="large",
    )


    with login_col:

        st.markdown(
            dedent(
                """
                <div class="login-main-title">
                    오늘,
                    <span class="orange-text">어디서</span>
                    먹을까요?
                </div>

                <div class="login-description">
                    AI가 내 취향과 상황에 맞는 맛집을 찾아드려요.
                </div>
                """
            ),
            unsafe_allow_html=True,
        )


        email = st.text_input(
            "이메일",
            placeholder="✉  이메일을 입력하세요",
            label_visibility="collapsed",
            key="login_email",
        )


        password = st.text_input(
            "비밀번호",
            placeholder="🔒  비밀번호를 입력하세요",
            type="password",
            label_visibility="collapsed",
            key="login_password",
        )


        remember_col, find_col = st.columns(
            [0.95, 1.05]
        )


        with remember_col:

            st.checkbox(
                "로그인 상태 유지",
                key="login_remember",
            )


        with find_col:

            if st.button(
                "ID / 비밀번호 찾기",
                use_container_width=True,
                key="find_account_button",
            ):

                st.session_state.page = "find_account"
                st.rerun()


        # -----------------------------------------
        # 로그인
        # -----------------------------------------

        if st.button(
            "로그인",
            type="primary",
            use_container_width=True,
            key="login_button",
        ):

            if not email or not password:

                st.warning(
                    "이메일과 비밀번호를 입력해주세요."
                )

            else:

                # =====================================
                # Supabase 연결 후 다시 사용
                # =====================================

                # try:
                #
                #     login_result = (
                #         supabase.auth.sign_in_with_password(
                #             {
                #                 "email": email,
                #                 "password": password,
                #             }
                #         )
                #     )
                #
                #     st.session_state.user = (
                #         login_result.user
                #     )
                #
                #     st.session_state.page = "home"
                #     st.rerun()
                #
                # except Exception:
                #
                #     st.error(
                #         "이메일 또는 비밀번호를 확인해주세요."
                #     )


                # =====================================
                # 현재 임시 로그인
                # =====================================

                st.session_state["is_logged_in"] = True
                st.session_state["nickname"] = "맛집러버"

                st.session_state.page = "home"

                st.rerun()


        # -----------------------------------------
        # 또는
        # -----------------------------------------

        st.markdown(
            dedent(
                """
                <div class="divider">
                    <span>또는</span>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )


        # -----------------------------------------
        # 카카오 로그인
        # -----------------------------------------

        # 나중에 OAuth 연결할 부분
        #
        # if "kakao_url" not in st.session_state:
        #     ...

        if st.button(
            "💬 카카오로 로그인",
            use_container_width=True,
            key="kakao_login_button",
        ):

            st.info(
                "카카오 로그인은 추후 연결 예정입니다."
            )


        # -----------------------------------------
        # 회원가입
        # -----------------------------------------

        st.markdown(
            dedent(
                """
                <div class="signup-guide">
                    계정이 없으신가요?
                </div>
                """
            ),
            unsafe_allow_html=True,
        )


        if st.button(
            "회원가입하기",
            use_container_width=True,
            key="go_signup",
        ):

            st.session_state.page = "signup"
            st.rerun()


    # -----------------------------------------
    # 오른쪽 이미지
    # -----------------------------------------

    with image_col:

        image_path = (
            Path(__file__).parent.parent.parent
            / "assets"
            / "login_food.jpg"
        )

        if image_path.exists():

            st.image(
                str(image_path),
                width="stretch",
            )

        else:

            st.warning(
                "assets/login_food.jpg 파일을 찾을 수 없습니다."
            )
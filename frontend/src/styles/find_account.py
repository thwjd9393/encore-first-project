import streamlit as st


def render_find_account():
    """ID / 비밀번호 찾기"""

    st.title("ID / 비밀번호 찾기")


    tab_id, tab_password = st.tabs(
        [
            "ID 찾기",
            "비밀번호 찾기",
        ]
    )


    with tab_id:

        name = st.text_input(
            "이름",
            key="find_name",
        )

        email = st.text_input(
            "이메일",
            key="find_email",
        )


        if st.button(
            "ID 찾기",
            use_container_width=True,
        ):

            if not name or not email:

                st.warning(
                    "이름과 이메일을 모두 입력해주세요."
                )

            else:

                st.info(
                    "회원 DB 연결 후 구현할 예정입니다."
                )


    with tab_password:

        reset_email = st.text_input(
            "이메일",
            key="reset_email",
        )


        if st.button(
            "비밀번호 재설정 이메일 보내기",
            use_container_width=True,
        ):

            if not reset_email:

                st.warning(
                    "이메일을 입력해주세요."
                )

            else:

                # ======================================
                # Supabase 연결 후 사용
                # ======================================

                # supabase.auth.reset_password_email(
                #     reset_email,
                #     {
                #         "redirect_to":
                #         "http://localhost:8501"
                #     }
                # )

                st.info(
                    "비밀번호 재설정 기능은 추후 연결 예정입니다."
                )


    if st.button(
        "← 로그인 화면으로 돌아가기",
    ):

        st.session_state.page = "login"

        st.rerun()
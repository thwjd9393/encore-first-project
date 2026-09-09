from pathlib import Path

import streamlit as st


def load_find_account_css():
    css_path = (
        Path(__file__).resolve().parents[0]
        / "login.css"
    )
    if css_path.is_file():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def render_find_account():
    """ID / 비밀번호 찾기"""

    load_find_account_css()

    st.title("ID / 비밀번호 찾기")

    tab_id, tab_password = st.tabs(
        [
            "ID 찾기",
            "비밀번호 찾기",
        ]
    )

    with tab_id:
        st.info("맛집친구 로그인 ID는 가입할 때 사용한 이메일입니다.")
        email = st.text_input(
            "이메일",
            placeholder="가입한 이메일을 입력하세요",
            key="find_email",
        )

        if st.button(
            "ID 확인",
            use_container_width=True,
            key="find_id_button",
        ):
            cleaned_email = (email or "").strip()
            if not cleaned_email or "@" not in cleaned_email:
                st.warning("이메일을 입력해주세요.")
            else:
                st.success(
                    "이 서비스의 로그인 ID는 가입 시 사용한 이메일입니다. "
                    "입력하신 이메일로 로그인해 주세요."
                )

    with tab_password:
        st.info(
            "비밀번호 변경은 로그인 후 마이페이지 > 프로필 수정에서 할 수 있습니다."
        )
        st.text_input(
            "이메일",
            placeholder="가입한 이메일을 입력하세요",
            key="reset_email",
        )

        if st.button(
            "비밀번호 변경 안내",
            use_container_width=True,
            key="find_password_button",
        ):
            st.success(
                "로그인할 수 있으면 마이페이지에서 비밀번호를 변경해 주세요. "
                "로그인할 수 없으면 관리자에게 문의해 주세요."
            )

    if st.button(
        "← 로그인 화면으로 돌아가기",
        key="find_account_back",
    ):
        st.session_state.page = "login"
        st.rerun()

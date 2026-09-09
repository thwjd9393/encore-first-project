"""일반 사용자 상단 메뉴.

HTML <a href="?page=..."> 링크는 새 세션이 열리면서 로그인이 풀릴 수 있다.
같은 세션에서 page만 바꾸도록 버튼을 사용한다.
"""

import streamlit as st


def go_page(page_name):
    st.session_state.page = page_name
    if page_name != "mypage":
        st.session_state["mypage_view"] = "main"
    st.rerun()


def logout():
    remembered = None
    if st.session_state.get("login_remember"):
        remembered = (
            st.session_state.get("remembered_email")
            or st.session_state.get("login_email")
        )
    st.session_state.clear()
    st.session_state.page = "login"
    if remembered:
        st.session_state.remembered_email = remembered
        st.session_state.login_remember = True
    st.rerun()


def render_user_navbar(active="home"):
    with st.container(key="playeat_user_navbar"):
        logo_col, menu_col = st.columns(
            [1.6, 1.4],
            vertical_alignment="center",
        )

        with logo_col:
            st.markdown(
                """
<div class="playeat-logo-area">
  <div class="playeat-symbol">🍴</div>
  <div class="playeat-logo-text">
    <div class="playeat-logo">Play<span>EAT</span></div>
    <div class="playeat-logo-sub">
      오늘의 한 끼, <strong>좋은 기억</strong>이 되도록
    </div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        with menu_col:
            is_admin = (st.session_state.get("user") or {}).get("profile_type") == "0"
            if is_admin:
                home_col, mypage_col, admin_col, logout_col = st.columns(
                    [1, 1, 1, 1.15],
                    vertical_alignment="center",
                )
            else:
                home_col, mypage_col, logout_col = st.columns(
                    [1, 1, 1.15],
                    vertical_alignment="center",
                )
                admin_col = None

            with home_col:
                if st.button(
                    "맛집 추천",
                    key="nav_home_button",
                    type="primary" if active == "home" else "secondary",
                    use_container_width=True,
                ):
                    go_page("home")

            with mypage_col:
                if st.button(
                    "마이페이지",
                    key="nav_mypage_button",
                    type="primary" if active == "mypage" else "secondary",
                    use_container_width=True,
                ):
                    go_page("mypage")

            if admin_col is not None:
                with admin_col:
                    if st.button(
                        "관리자",
                        key="nav_admin_button",
                        use_container_width=True,
                    ):
                        go_page("admin")

            with logout_col:
                if st.button(
                    "👤 로그아웃",
                    key="nav_logout_button",
                    use_container_width=True,
                ):
                    logout()

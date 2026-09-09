import streamlit as st

from src.views.admin import render_admin
from src.views.home import render_home
from src.views.login import render_login
from src.views.signup import render_signup
from src.views.mypage import render_mypage
from src.styles.find_account import render_find_account


# =========================
# Streamlit 기본 설정
# =========================

st.set_page_config(
    page_title="맛집친구",
    page_icon="🍴",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================
# 기본 페이지
# =========================

st.session_state.setdefault(
    "page",
    "login",
)


# =========================
# URL query parameter 처리
# 예: ?page=mypage
# =========================

query_page = st.query_params.get("page")


if query_page == "home":
    st.session_state["page"] = "home"

    st.query_params.clear()

    st.rerun()


elif query_page == "mypage":
    if st.session_state.get("access_token") or st.session_state.get("user"):
        st.session_state["page"] = "mypage"
    else:
        st.session_state["page"] = "login"
        st.session_state["login_notice"] = "로그인이 필요합니다."

    st.query_params.clear()

    st.rerun()


elif query_page == "login":
    st.session_state["page"] = "login"

    st.query_params.clear()

    st.rerun()


elif query_page == "signup":
    st.session_state["page"] = "signup"

    st.query_params.clear()

    st.rerun()


elif query_page == "find_account":
    st.session_state["page"] = "find_account"

    st.query_params.clear()

    st.rerun()


elif query_page == "admin":

    user = st.session_state.get("user")

    # 로그인하지 않은 사용자
    if not user:
        st.session_state["page"] = "login"

    # 관리자가 아닌 사용자
    elif user.get("profile_type") != "0":
        st.session_state["page"] = "home"

    # 관리자
    else:
        st.session_state["page"] = "admin"

    st.query_params.clear()

    st.rerun()


elif query_page == "logout":
    remembered = None
    if st.session_state.get("login_remember"):
        remembered = (
            st.session_state.get("remembered_email")
            or st.session_state.get("login_email")
        )
    st.session_state.clear()
    st.session_state["page"] = "login"
    if remembered:
        st.session_state["remembered_email"] = remembered
        st.session_state["login_remember"] = True

    st.query_params.clear()

    st.rerun()


# =========================
# 현재 페이지 출력
# =========================

page = st.session_state.page


if page == "home":
    render_home()


elif page == "login":
    render_login()


elif page == "signup":
    render_signup()


elif page == "mypage":
    if st.session_state.get("access_token") or st.session_state.get("user"):
        render_mypage()
    else:
        st.session_state.page = "login"
        st.session_state.login_notice = "로그인이 필요합니다."
        st.rerun()


elif page == "find_account":
    render_find_account()


# elif page == "login_success":
#     render_login_success()


elif page == "admin":

    user = st.session_state.get("user")

    # 로그인하지 않은 경우
    if not user:
        st.session_state.page = "login"
        st.rerun()

    # 관리자가 아닌 경우
    elif user.get("profile_type") != "0":
        st.session_state.page = "home"
        st.rerun()

    # 관리자만 대시보드 출력
    else:
        render_admin()
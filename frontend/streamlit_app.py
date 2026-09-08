import streamlit as st

from src.views.home import render_home
from src.views.login import render_login
from src.views.signup import render_signup
from src.views.mypage import render_mypage


# =========================
# Streamlit 기본 설정
# =========================

st.set_page_config(
    page_title="맛집친구",
    page_icon="🍴",
    layout="wide",
)


# =========================
# 기본 페이지
# =========================

st.session_state.setdefault("page", "home")


# =========================
# 임시 페이지 이동 버튼
# 개발할 때만 사용
# =========================

st.write("### 개발용 페이지 이동")

col1, col2, col3, col4 = st.columns(4)


with col1:
    if st.button("홈"):
        st.session_state.page = "home"
        st.rerun()


with col2:
    if st.button("로그인"):
        st.session_state.page = "login"
        st.rerun()


with col3:
    if st.button("회원가입"):
        st.session_state.page = "signup"
        st.rerun()


with col4:
    if st.button("마이페이지"):
        st.session_state.page = "mypage"
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
    render_mypage()
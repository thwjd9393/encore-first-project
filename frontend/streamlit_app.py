import streamlit as st

from src.views.home import render_home
from src.views.login import render_login
from src.views.signup import render_signup
from src.views.mypage import render_mypage


page = st.session_state.get("page", "home")

if page == "home":
    render_home()

elif page == "login":
    render_login()

elif page == "signup":
    render_signup()

elif page == "mypage":
    render_mypage()
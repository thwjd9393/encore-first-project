import streamlit as st

from src.views.login import render_login


st.set_page_config(
    page_title="맛집 추천",
    page_icon="🍽️",
    layout="wide",
)

def render_home():
    st.title("홈")

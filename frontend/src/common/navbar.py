from textwrap import dedent

import streamlit as st


def render_navbar(current_menu, profile_type=None):
    if profile_type == "0":
        left_caption = "오늘의 한 끼가, 좋은 기억이 되도록"
        right_caption = "AI 맛집 추천 서비스"
    else:
        left_caption = "AI 맛집 추천 서비스"
        right_caption = current_menu

    st.markdown(
        dedent(
            f"""
            <div class="playeat-navbar">
                <div>
                    <div class="playeat-logo">PlayEAT</div>
                    <div class="playeat-logo-caption">{left_caption}</div>
                </div>
                <div class="playeat-logo-caption">{right_caption}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

from pathlib import Path

import streamlit as st

PAGE_CONTENT_WIDTH = {
    "dashboard": "1320px",
}


def load_common_styles():
    css_path = Path(__file__).parent / "styles.css"
    css_text = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)


def apply_page_layout(page_type):
    load_common_styles()
    content_width = PAGE_CONTENT_WIDTH.get(page_type, "1320px")
    st.markdown(
        f"<style>.block-container {{ max-width: {content_width}; }}</style>",
        unsafe_allow_html=True,
    )

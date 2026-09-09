import streamlit as st

from src.common.layout import apply_page_layout
from src.common.navbar import render_navbar
from src.views.admin_analytics import render_admin_analytics
from src.views.admin_common import (
    ADMIN_MENU_ANALYTICS,
    ADMIN_MENU_FEEDBACK,
    ADMIN_MENU_LOGS,
    ADMIN_MENU_RESTAURANTS,
    resolve_admin_menu,
    render_admin_sidebar,
)
from src.views.admin_feedback import render_admin_feedback
from src.views.admin_logs import LOGS_MENU_ACTIVE_KEY, render_admin_logs
from src.views.admin_restaurants import render_admin_restaurants


def render_admin():
    apply_page_layout("dashboard")
    current_menu = resolve_admin_menu()
    st.markdown('<div class="playeat-admin-root"></div>', unsafe_allow_html=True)
    render_admin_sidebar(current_menu)
    render_navbar(current_menu, profile_type="0")

    if current_menu != ADMIN_MENU_LOGS:
        st.session_state[LOGS_MENU_ACTIVE_KEY] = False

    if current_menu == ADMIN_MENU_RESTAURANTS:
        render_admin_restaurants()
    elif current_menu == ADMIN_MENU_ANALYTICS:
        render_admin_analytics()
    elif current_menu == ADMIN_MENU_FEEDBACK:
        render_admin_feedback()
    elif current_menu == ADMIN_MENU_LOGS:
        render_admin_logs()
    else:
        render_admin_restaurants()

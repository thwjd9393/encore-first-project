from html import escape
from pathlib import Path

import streamlit as st

from src.common.api_client import get_json
from src.common.user_navbar import render_user_navbar
from src.views.profile_edit import render_password_change, render_profile_edit


def load_css(css_file: str) -> None:
    """외부 CSS 파일을 불러와 Streamlit 화면에 적용한다."""
    css = Path(css_file).read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_mypage_navbar():
    render_user_navbar(active="mypage")


def redirect_to_login(message=None):
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
    if message:
        st.session_state.login_notice = message
    st.rerun()


def raise_if_unauthorized(result):
    if result.get("status_code") == 401:
        redirect_to_login("로그인이 만료되었습니다. 다시 로그인해 주세요.")


def render_mypage():
    """마이페이지 화면을 보여준다."""

    load_css(Path(__file__).parent.parent / "styles" / "mypage.css")
    render_mypage_navbar()

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.error("로그인 정보를 확인할 수 없습니다. 다시 로그인해 주세요.")
        if st.button("로그인 화면으로", key="mypage_go_login"):
            redirect_to_login()
        return

    st.session_state.setdefault("mypage_view", "main")

    with st.spinner("마이페이지를 불러오는 중..."):
        user_result = get_json("/users/me", access_token=access_token)
    raise_if_unauthorized(user_result)
    if not user_result.get("ok"):
        error_body = user_result.get("error") or {}
        st.error(error_body.get("message") or "사용자 정보를 불러오지 못했습니다.")
        if st.button("다시 시도", key="mypage_retry"):
            st.rerun()
        return

    user = user_result.get("data") or {}
    session_user = st.session_state.get("user") or {}
    if user.get("nickname"):
        session_user["nickname"] = user.get("nickname")
        session_user["email"] = user.get("email") or session_user.get("email")
        st.session_state.user = session_user

    if st.session_state["mypage_view"] == "profile":
        render_profile_edit(user)
        return

    if st.session_state["mypage_view"] == "password":
        render_password_change()
        return

    likes_result = get_json("/users/me/likes", access_token=access_token)
    raise_if_unauthorized(likes_result)
    likes_error = None
    recent_restaurants = []
    if likes_result.get("ok"):
        recent_restaurants = (likes_result.get("data") or {}).get("restaurants") or []
    else:
        likes_error = (likes_result.get("error") or {}).get("message") or (
            "좋아요 식당 정보를 불러오지 못했습니다."
        )

    tags_result = get_json("/users/me/tags", access_token=access_token)
    raise_if_unauthorized(tags_result)
    tags_error = None
    favorite_tags = []
    if tags_result.get("ok"):
        favorite_tags = [
            f"#{tag}"
            for tag in (tags_result.get("data") or {}).get("tags") or []
            if tag
        ]
    else:
        tags_error = (tags_result.get("error") or {}).get("message") or (
            "태그 정보를 불러오지 못했습니다."
        )

    categories_result = get_json("/users/me/categories", access_token=access_token)
    raise_if_unauthorized(categories_result)
    categories_error = None
    favorite_categories = {}
    if categories_result.get("ok"):
        category_items = (categories_result.get("data") or {}).get("categories") or []
        if isinstance(category_items, dict):
            favorite_categories = category_items
        else:
            favorite_categories = {
                item.get("name"): item.get("percentage")
                for item in category_items
                if item.get("name") is not None
            }
    else:
        categories_error = (categories_result.get("error") or {}).get("message") or (
            "카테고리 정보를 불러오지 못했습니다."
        )

    title_col, button_col = st.columns([4, 1])
    with title_col:
        st.markdown(
            f'<p class="mypage-title">'
            f'안녕하세요, {escape(user.get("nickname") or "회원")} 님! 👋'
            f'</p>'
            f'<p class="mypage-subtitle">'
            f'오늘도 맛있는 하루 보내세요.'
            f'</p>',
            unsafe_allow_html=True,
        )

    with button_col:
        if st.button("프로필 수정 ❯", use_container_width=True):
            st.session_state["mypage_view"] = "profile"
            st.rerun()

    if tags_error:
        st.error(tags_error)
        tag_card = (
            '<div class="tag-card">'
            '<span class="tag-icon">◇</span>'
            '<strong>태그 정보를 표시하지 못했습니다.</strong>'
            '</div>'
        )
    elif favorite_tags:
        tags_html = "".join(
            f'<span class="tag">{escape(tag)}</span>'
            for tag in favorite_tags
        )
        tag_card = (
            '<div class="tag-card">'
            '<span class="tag-icon">◇</span>'
            '<strong>자주 사용한 태그는</strong>'
            f'{tags_html}'
            '<span> 이에요!</span>'
            '</div>'
        )
    else:
        tag_card = (
            '<div class="tag-card">'
            '<span class="tag-icon">◇</span>'
            '<strong>최근에는 사용한 태그가 없어요.</strong>'
            '</div>'
        )

    st.markdown(tag_card, unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")

    with left:
        if likes_error:
            restaurant_html = (
                f'<div class="empty-hint">{escape(likes_error)}</div>'
            )
        elif recent_restaurants:
            restaurant_html = ""
            for restaurant in recent_restaurants:
                restaurant_html += (
                    '<div class="restaurant-item">'
                    '<div class="restaurant-top">'
                    f'<span class="restaurant-name">'
                    f'{escape(restaurant.get("name") or "이름 없는 식당")}'
                    f'</span>'
                    '</div>'
                    f'<div class="restaurant-location">'
                    f'📍 {escape(restaurant.get("address") or "주소 정보 없음")}'
                    f'</div>'
                    '</div>'
                )
        else:
            restaurant_html = (
                '<div class="empty-hint">'
                '아직 좋아요한 식당이 없어요.'
                '</div>'
            )

        left_card = (
            '<div class="mypage-card">'
            '<div class="card-title">'
            '<span class="card-icon">♡</span>'
            '최근에 좋아요를 남겨주신 곳'
            '</div>'
            f'{restaurant_html}'
            '</div>'
        )
        st.markdown(left_card, unsafe_allow_html=True)

    with right:
        if categories_error:
            menu_content = (
                f'<div class="empty-hint">{escape(categories_error)}</div>'
            )
        elif favorite_categories:
            legend_html = ""
            for index, (category, value) in enumerate(
                favorite_categories.items(),
                start=1,
            ):
                legend_html += (
                    '<div class="legend-row">'
                    f'<span class="legend-dot dot-{index}"></span>'
                    f'<span class="legend-name">{escape(str(category))}</span>'
                    f'<span class="legend-value">{escape(str(value))}%</span>'
                    '</div>'
                )
            menu_content = (
                '<div class="menu-content">'
                '<div class="donut">'
                '<div class="donut-center">'
                '<div class="donut-label">총</div>'
                '<div class="donut-total">100%</div>'
                '</div>'
                '</div>'
                '<div class="menu-legend">'
                f'{legend_html}'
                '</div>'
                '</div>'
            )
        else:
            menu_content = (
                '<div class="empty-hint">'
                '아직 선호 메뉴를 계산할 기록이 없어요.'
                '</div>'
            )

        right_card = (
            '<div class="mypage-card">'
            '<div class="card-title">'
            '<span class="card-icon">🍴</span>'
            '자주 드시는 메뉴'
            '</div>'
            f'{menu_content}'
            '</div>'
        )
        st.markdown(right_card, unsafe_allow_html=True)

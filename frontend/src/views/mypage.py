import streamlit as st
from pathlib import Path


# ----------------------------------------
# CSS 불러오기
# ----------------------------------------

def load_css():
    css_path = (
        Path(__file__).parent.parent
        / "styles"
        / "mypage.css"
    )

    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True,
        )


# ----------------------------------------
# 마이페이지
# ----------------------------------------

def render_mypage():

    load_css()

    # ----------------------------------------
    # 임시 사용자 데이터
    # 나중에 DB/API 데이터로 변경
    # ----------------------------------------

    user = {
        "nickname": "맛집러버",
        "user_id": "EXAM_ID",
        "email": "example@email.com",
    }

    recent_restaurants = [
        {
            "name": "강남 손칼국수",
            "location": "서울 강남구 대치동",
            "date": "2026.09.03",
        },
        {
            "name": "싸다 김밥",
            "location": "서울 서초구 서초동",
            "date": "2026.09.02",
        },
        {
            "name": "역삼파스타",
            "location": "서울 강남구 역삼동",
            "date": "2026.09.01",
        },
    ]

    favorite_tags = [
        "#한식",
        "#가성비",
        "#혼밥",
    ]

    favorite_categories = {
        "한식": 40,
        "일식": 25,
        "양식": 15,
        "중식": 10,
        "카페/디저트": 7,
        "기타": 3,
    }


    # ----------------------------------------
    # 상단 인사
    # ----------------------------------------

    title_col, button_col = st.columns([4, 1])

    with title_col:

        st.markdown(
            f"""
            <p class="mypage-title">
                안녕하세요, {user["nickname"]} 님! 👋
            </p>

            <p class="mypage-subtitle">
                오늘도 맛있는 하루 보내세요.
            </p>
            """,
            unsafe_allow_html=True,
        )


    with button_col:

        if st.button(
            "프로필 수정 ❯",
            use_container_width=True,
        ):

            st.session_state["mypage_view"] = "profile"

            st.rerun()


    # ----------------------------------------
    # 자주 사용한 태그
    # ----------------------------------------

    if favorite_tags:

        tags_html = "".join(
            f'<span class="tag">{tag}</span>'
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


    st.markdown(
        tag_card,
        unsafe_allow_html=True,
    )


    # ----------------------------------------
    # 카드 영역
    # ----------------------------------------

    left, right = st.columns(
        2,
        gap="medium",
    )


    # ----------------------------------------
    # 최근 좋아요 식당
    # ----------------------------------------

    with left:

        restaurant_html = ""

        for restaurant in recent_restaurants:

            restaurant_html += (
                '<div class="restaurant-item">'
                '<div class="restaurant-top">'
                f'<span class="restaurant-name">'
                f'{restaurant["name"]}'
                '</span>'
                f'<span class="restaurant-date">'
                f'{restaurant["date"]}'
                '</span>'
                '</div>'
                f'<div class="restaurant-location">'
                f'📍 {restaurant["location"]}'
                '</div>'
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


        st.markdown(
            left_card,
            unsafe_allow_html=True,
        )


    # ----------------------------------------
    # 자주 드시는 메뉴
    # ----------------------------------------

    with right:

        categories = list(
            favorite_categories.items()
        )

        legend_html = ""

        for index, (category, value) in enumerate(
            categories,
            start=1,
        ):

            legend_html += (
                '<div class="legend-row">'
                f'<span class="legend-dot dot-{index}"></span>'
                f'<span class="legend-name">{category}</span>'
                f'<span class="legend-value">{value}%</span>'
                '</div>'
            )


        right_card = (
            '<div class="mypage-card">'
            '<div class="card-title">'
            '<span class="card-icon">🍴</span>'
            '자주 드시는 메뉴'
            '</div>'

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
            '</div>'
        )


        st.markdown(
            right_card,
            unsafe_allow_html=True,
        )
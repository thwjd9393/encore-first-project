import streamlit as st

ADMIN_MENU_RESTAURANTS = "식당정보"
ADMIN_MENU_ANALYTICS = "검색정보"
ADMIN_MENU_FEEDBACK = "유저반응"
ADMIN_MENU_LOGS = "로그분석"
ADMIN_MENU_KEY = "admin_menu"
ADMIN_NAV_ITEMS = (
    ("restaurants", ADMIN_MENU_RESTAURANTS, ":material/restaurant: 식당정보"),
    ("analytics", ADMIN_MENU_ANALYTICS, ":material/bar_chart: 검색정보"),
    ("feedback", ADMIN_MENU_FEEDBACK, ":material/chat: 유저반응"),
    ("logs", ADMIN_MENU_LOGS, ":material/monitoring: 로그분석"),
)
ADMIN_MENU_ALIASES = {
    "검색정보분석": ADMIN_MENU_ANALYTICS,
    "사용자피드백": ADMIN_MENU_FEEDBACK,
}

PRICE_FILTER_OPTIONS = ["전체", "상", "중", "하"]

REACTION_TO_FEEDBACK_VALUE = {
    "불만족": "1",
    "보통": "2",
    "만족": "3",
}

FEEDBACK_VALUE_TO_REACTION = {
    "1": "불만족",
    "2": "보통",
    "3": "만족",
}

FEATURE_TAG_MATCHERS = {
    "매운거": ("매운",),
    "든든한거": ("든든",),
    "국물": ("국물",),
}


def resolve_admin_menu():
    current_menu = st.session_state.get(ADMIN_MENU_KEY)
    if current_menu in ADMIN_MENU_ALIASES:
        current_menu = ADMIN_MENU_ALIASES[current_menu]
    valid_menus = {item[1] for item in ADMIN_NAV_ITEMS}
    if current_menu not in valid_menus:
        current_menu = ADMIN_MENU_RESTAURANTS
    st.session_state[ADMIN_MENU_KEY] = current_menu
    return current_menu


def render_admin_brand():
    st.markdown(
        """
        <div class="playeat-admin-brand-wrap">
            <p class="playeat-admin-brand">PlayEAT ADMIN</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_nav(current_menu):
    for menu_id, menu_name, label in ADMIN_NAV_ITEMS:
        if st.button(
            label,
            type="primary" if current_menu == menu_name else "secondary",
            width="stretch",
            key=f"admin_nav_v2_{menu_id}",
        ):
            st.session_state[ADMIN_MENU_KEY] = menu_name
            st.rerun()


def render_admin_sidebar(current_menu):
    with st.sidebar:
        render_admin_brand()
        render_admin_nav(current_menu)
        st.divider()
        if st.button(
            ":material/restaurant_menu: 맛집 추천",
            width="stretch",
            key="admin_go_user_home_button",
        ):
            st.session_state.page = "home"
            st.rerun()
        if st.button(
            ":material/logout: 로그아웃",
            width="stretch",
            key="admin_logout_button",
        ):
            st.query_params["page"] = "logout"
            st.rerun()


def get_category_name(item):
    return (
        item.get("category_name")
        or item.get("food_category")
        or item.get("category")
        or ""
    )


PRICE_TAG_TO_LABEL = {
    "상": "상",
    "중": "중",
    "하": "하",
    "인당가격_상": "상",
    "인당가격_중": "중",
    "인당가격_하": "하",
}


def get_price_label(item):
    direct = item.get("price_range") or item.get("price_range_tag")
    if direct in PRICE_FILTER_OPTIONS[1:]:
        return direct
    if direct in PRICE_TAG_TO_LABEL:
        return PRICE_TAG_TO_LABEL[direct]
    tags = item.get("matched_tags") or item.get("tags") or []
    for tag in tags:
        tag_text = str(tag)
        if tag_text in PRICE_TAG_TO_LABEL:
            return PRICE_TAG_TO_LABEL[tag_text]
        if "고가" in tag_text:
            return "상"
        if "중가" in tag_text:
            return "중"
        if "저가" in tag_text:
            return "하"
    return "-"


def get_feature_label(item):
    tags = item.get("matched_tags") or item.get("tags") or item.get("menu_features") or []
    labels = []
    joined_tags = [str(tag) for tag in tags]
    for option, matchers in FEATURE_TAG_MATCHERS.items():
        if any(any(matcher in tag for matcher in matchers) for tag in joined_tags):
            labels.append(option)
    if labels:
        return ", ".join(labels)
    if joined_tags:
        return ", ".join(joined_tags)
    return "-"


def get_representative_menu(item):
    menus = item.get("menus") or []
    if menus:
        first_menu = menus[0]
        if isinstance(first_menu, dict):
            return first_menu.get("name") or "-"
        return str(first_menu)
    return item.get("representative_menu") or item.get("signature_menu") or "-"

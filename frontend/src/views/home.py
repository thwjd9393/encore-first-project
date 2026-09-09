from pathlib import Path
from html import escape

import streamlit as st


from src.common.api_client import (
    get_json,
    post_json,
    stream_post,
)
from src.common.user_navbar import render_user_navbar


# =========================================================
# 경로 설정
# =========================================================

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent

CSS_PATH = SRC_DIR / "styles" / "home.css"


# =========================================================
# CSS 로드
# =========================================================

def load_home_css():
    """홈 화면 CSS를 불러온다."""

    if CSS_PATH.exists():
        css = CSS_PATH.read_text(encoding="utf-8")

        st.html(
            f'<style>{css}</style>'
        )


# =========================================================
# Navbar
# =========================================================

def render_navbar():
    render_user_navbar(active="home")


# =========================================================
# 채팅 화면
# =========================================================

def render_chat():

    messages = st.session_state.get("chat_messages", [])

    message_html = ""

    for message in messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")

        if role == "user":
            message_html += (
                f'<div class="chat-row user-row">'
                f'  <div class="chat-message user-message">'
                f'    {content}'
                f'  </div>'
                f'</div>'
            )

        else:
            message_html += (
                f'<div class="chat-row assistant-row">'
                f'  <div class="chat-message assistant-message">'
                f'    {content}'
                f'  </div>'
                f'</div>'
            )

    st.html(
        f'''
        <div class="chat-box">
            <div class="chat-header">
                🍴 PlayEAT 추천 대화
            </div>

            <div class="chat-message-list">
                {message_html}
            </div>
        </div>
        '''
    )


# =========================================================
# 메인 제목
# =========================================================

def render_hero():

    st.html(
        f'<div class="home-hero">'
        f'  <h1>'
        f'    오늘은 어떤<br>'
        f'    <span>맛집</span>을 찾고<br>'
        f'    계신가요?'
        f'  </h1>'
        f'</div>'
    )


# =========================================================
# 검색창
# =========================================================

def render_search():

    search_col, button_col = st.columns(
        [8, 2],
        gap="small",
    )

    with search_col:
        keyword = st.text_input(
            "검색",
            placeholder="지역, 음식, 분위기 등을 입력해보세요",
            label_visibility="collapsed",
            key="home_search_keyword",
        )

    with button_col:
        search_clicked = st.button(
            "검색하기",
            key="home_search_button",
            type="primary",
            use_container_width=True,
        )

    return keyword, search_clicked


# =========================================================
# 카테고리 필터
# =========================================================

def render_filters():
    """
    각 그룹별 하나씩 선택 가능

    restaurant_categories
        한식 / 중식 / 일식 / 양식 / 기타

    menu_types
        매운거 / 든든한거 / 국물여부

    price_levels
        인당가격_하 / 인당가격_중 / 인당가격_상
    """

    st.session_state.setdefault(
        "home_restaurant_category",
        None,
    )

    st.session_state.setdefault(
        "home_menu_type",
        None,
    )

    st.session_state.setdefault(
        "home_price_level",
        None,
    )


    # =====================================================
    # 1. 음식 종류
    # =====================================================

    st.markdown("#### 음식 종류")

    restaurant_categories = [
        ("🍲 한식", "한식"),
        ("🥟 중식", "중식"),
        ("🍱 일식", "일식"),
        ("🍕 양식", "양식"),
        ("🍴 기타", "기타"),
    ]

    cols = st.columns(
        5,
        gap="small",
    )

    for col, (label, value) in zip(
        cols,
        restaurant_categories,
    ):
        with col:
            selected = (
                st.session_state[
                    "home_restaurant_category"
                ]
                == value
            )

            if st.button(
                label,
                key=f"filter_restaurant_{value}",
                type=(
                    "primary"
                    if selected
                    else "secondary"
                ),
                use_container_width=True,
            ):
                if selected:
                    st.session_state[
                        "home_restaurant_category"
                    ] = None
                else:
                    st.session_state[
                        "home_restaurant_category"
                    ] = value

                st.rerun()


    # =====================================================
    # 2. 음식 특징 + 가격대
    # 한 줄에 출력
    # =====================================================

    st.markdown("#### 음식 특징 / 가격대")

    menu_types = [
        ("🔥 매운거", "매운거"),
        ("🥩 든든한거", "든든한거"),
        ("🍲 국물", "국물여부"),
    ]

    price_levels = [
        ("💰 가성비", "인당가격_하"),
        ("💵 중간쯤", "인당가격_중"),
        ("💎 비싼거", "인당가격_상"),
    ]

    # 총 6개 버튼 한 줄
    cols = st.columns(
        6,
        gap="small",
    )


    # -----------------------------
    # 음식 특징 3개
    # -----------------------------

    for col, (label, value) in zip(
        cols[:3],
        menu_types,
    ):
        with col:
            selected = (
                st.session_state[
                    "home_menu_type"
                ]
                == value
            )

            if st.button(
                label,
                key=f"filter_menu_{value}",
                type=(
                    "primary"
                    if selected
                    else "secondary"
                ),
                use_container_width=True,
            ):
                if selected:
                    st.session_state[
                        "home_menu_type"
                    ] = None
                else:
                    st.session_state[
                        "home_menu_type"
                    ] = value

                st.rerun()


    # -----------------------------
    # 가격대 3개
    # -----------------------------

    for col, (label, value) in zip(
        cols[3:],
        price_levels,
    ):
        with col:
            selected = (
                st.session_state[
                    "home_price_level"
                ]
                == value
            )

            if st.button(
                label,
                key=f"filter_price_{value}",
                type=(
                    "primary"
                    if selected
                    else "secondary"
                ),
                use_container_width=True,
            ):
                if selected:
                    st.session_state[
                        "home_price_level"
                    ] = None
                else:
                    st.session_state[
                        "home_price_level"
                    ] = value

                st.rerun()


    return {
        "restaurant_category": (
            st.session_state[
                "home_restaurant_category"
            ]
        ),
        "menu_type": (
            st.session_state[
                "home_menu_type"
            ]
        ),
        "price_level": (
            st.session_state[
                "home_price_level"
            ]
        ),
    }


# =========================================================
# 추천 식당
# =========================================================

def find_restaurant_image(restaurant: dict):
    """시드에 넣은 storage_path 또는 식당명 폴더에서 사진을 찾는다."""
    project_root = CURRENT_DIR.parents[2]
    photos_root = project_root / "frontend" / "assets" / "store" / "photos"
    suffixes = {".jpg", ".jpeg", ".png", ".webp"}

    def first_image(folder: Path):
        if not folder.is_dir():
            return None
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in suffixes:
                return str(path)
        return None

    storage_path = restaurant.get("storage_path")
    if storage_path:
        found = first_image(project_root / storage_path)
        if found:
            return found

    name = (restaurant.get("name") or "").strip()
    if name and photos_root.is_dir():
        for folder in photos_root.iterdir():
            if folder.is_dir() and (
                folder.name == name or folder.name.startswith(name)
            ):
                found = first_image(folder)
                if found:
                    return found
    return None


def render_restaurant():
    restaurant = st.session_state.get("recommended_restaurant")
    if not restaurant:
        st.info("조건에 맞는 저장된 식당을 찾지 못했습니다. 필터를 바꿔 다시 검색해 주세요.")
        return

    user = st.session_state.get("user") or {}
    nickname = escape(user.get("nickname") or "회원")
    name = escape(str(restaurant.get("name") or "식당"))
    address = escape(
        str(
            restaurant.get("road_address")
            or restaurant.get("address")
            or ""
        )
    )
    category = restaurant.get("category_name")
    tags = restaurant.get("matched_tags") or restaurant.get("matched_conditions") or []
    menus = restaurant.get("menus") or []
    kakao_url = restaurant.get("kakao_place_url")

    st.html(
        f'<div class="recommend-title">'
        f'  \'{nickname}\'님을 위한 오늘의 추천 식당'
        f'</div>'
    )

    image_path = find_restaurant_image(restaurant)
    card_col, info_col = st.columns([1.15, 1], gap="medium")
    with card_col:
        if image_path:
            st.image(image_path, use_container_width=True)
        else:
            st.html(
                '<div class="restaurant-image">'
                '<div class="image-placeholder">식당 이미지</div>'
                "</div>"
            )
    with info_col:
        menu_html = ""
        if menus:
            first = menus[0] if isinstance(menus[0], dict) else {}
            menu_name = escape(str(first.get("name") or ""))
            price = first.get("price")
            if menu_name:
                price_text = f" {price}원" if price is not None else ""
                menu_html = (
                    f'<div class="restaurant-address">'
                    f"대표 메뉴 {menu_name}{price_text}"
                    "</div>"
                )
        tag_html = "".join(
            f"<span>{escape(str(tag))}</span>"
            for tag in tags[:4]
        )
        if category:
            tag_html = f"<span>{escape(str(category))}</span>" + tag_html
        link_html = ""
        if kakao_url:
            safe_url = escape(str(kakao_url), quote=True)
            link_html = (
                f'<div class="restaurant-address">'
                f'<a href="{safe_url}" target="_blank" rel="noopener">카카오맵 보기</a>'
                "</div>"
            )
        st.html(
            f'<div class="restaurant-content">'
            f'  <div class="restaurant-name">{name}</div>'
            f'  <div class="restaurant-address">{address}</div>'
            f"  {menu_html}"
            f'  <div class="restaurant-tags">{tag_html}</div>'
            f"  {link_html}"
            f"</div>"
        )


# =========================================================
# 대화방이 없으면 생성하는 함수
# =========================================================

def clear_conversation_state():
    """다른 계정·없는 대화 ID가 남지 않게 채팅 상태를 지운다."""
    for key in (
        "conversation_id",
        "chat_loaded",
        "chat_messages",
        "last_message_id",
        "recommended_restaurant",
        "recommendation_id",
        "home_feedback_value",
        "home_feedback_notice",
    ):
        st.session_state.pop(key, None)


def ensure_conversation():

    access_token = st.session_state.get(
        "access_token"
    )

    # 로그인 토큰 확인
    if not access_token:
        st.warning(
            "access_token이 없습니다. 로그인 상태를 확인해주세요."
        )
        return False

    conversation_id = st.session_state.get(
        "conversation_id"
    )

    if conversation_id:
        check = get_json(
            f"/conversations/{conversation_id}/messages",
            access_token=access_token,
        )
        if check.get("ok"):
            return True
        # 없거나 내 대화가 아니면 새로 만든다.
        clear_conversation_state()

    # 대화방 생성
    result = post_json(
        "/conversations",
        json_body={
            "title": "맛집 추천 대화",
        },
        access_token=access_token,
    )

    # 생성 실패
    if not result["ok"]:
        error_body = result.get("error") or {}
        st.error(
            error_body.get("message") or "대화방을 만들지 못했습니다."
        )
        return False

    created = result.get("data") or {}
    conversation_id = created.get("id")
    if not conversation_id:
        st.error("대화방 ID를 받지 못했습니다.")
        return False

    st.session_state[
        "conversation_id"
    ] = conversation_id

    # 새 대화방이므로 기존 로드 상태 초기화
    st.session_state[
        "chat_loaded"
    ] = False

    return True

# =========================================================
# 추천 이유
# =========================================================

def render_recommendation_reason():

    st.html(
        f'<div class="recommend-reason">'
        f'</div>'
    )


# =========================================================
# 만족도 평가
# =========================================================

def request_next_restaurant():
    """같은 조건으로 다음 식당을 추천한다."""
    conversation_id = st.session_state.get("conversation_id")
    access_token = st.session_state.get("access_token")
    if not conversation_id or not access_token:
        st.error("로그인이 필요합니다.")
        return

    restaurant = None
    for event in stream_post(
        f"/conversations/{conversation_id}/regenerate",
        json_body={},
        access_token=access_token,
        timeout=90,
    ):
        if "error" in event:
            st.error(str(event["error"]))
            return
        if event.get("done"):
            st.session_state["last_message_id"] = event.get("message_id")
            restaurant = event.get("restaurant")
            if event.get("recommendation_id"):
                st.session_state["recommendation_id"] = event.get(
                    "recommendation_id"
                )

    st.session_state.recommended_restaurant = restaurant
    st.session_state.home_feedback_value = None
    st.session_state.chat_loaded = False
    st.session_state.home_feedback_notice = "다른 식당을 추천했습니다."
    st.rerun()


def submit_home_feedback(kind):
    """만족 3, 보통 2, 아쉬움 1을 저장한다. 아쉬움이면 다음 식당을 고른다."""
    access_token = st.session_state.get("access_token")
    recommendation_id = st.session_state.get("recommendation_id")
    if not access_token:
        st.error("로그인이 필요합니다.")
        return
    if not recommendation_id:
        st.warning("추천을 받은 뒤 평가할 수 있습니다.")
        return

    value = {"good": "3", "normal": "2", "bad": "1"}[kind]
    result = post_json(
        f"/recommendations/{recommendation_id}/feedback",
        json_body={"feedback_value": value},
        access_token=access_token,
    )
    if not result.get("ok"):
        error_body = result.get("error") or {}
        st.error(error_body.get("message") or "평가를 저장하지 못했습니다.")
        return

    st.session_state.home_feedback_value = value
    if kind == "bad":
        request_next_restaurant()
        return
    st.session_state.home_feedback_notice = "평가가 저장되었습니다."
    st.rerun()


def render_feedback():

    st.html(
        f'<div class="feedback-line"></div>'
        f'<div class="feedback-title">'
        f'  이 추천이 마음에 드셨나요?'
        f'</div>'
    )

    notice = st.session_state.pop("home_feedback_notice", None)
    if notice:
        st.success(notice)

    saved = st.session_state.get("home_feedback_value")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "☺ 만족해요",
            key="home_feedback_good",
            type="primary" if saved == "3" else "secondary",
            use_container_width=True,
        ):
            submit_home_feedback("good")

    with col2:
        if st.button(
            "😐 보통이에요",
            key="home_feedback_normal",
            type="primary" if saved == "2" else "secondary",
            use_container_width=True,
        ):
            submit_home_feedback("normal")

    with col3:
        if st.button(
            "☹ 아쉬워요 (다른 곳 골라줘)",
            key="home_feedback_bad",
            type="primary" if saved == "1" else "secondary",
            use_container_width=True,
        ):
            submit_home_feedback("bad")


# =========================================================
# Home
# =========================================================

def render_home():

    load_home_css()

    render_navbar()


    # -----------------------------------------
    # 1. 대화방 확인 / 생성
    # -----------------------------------------
    conversation_ready = ensure_conversation()

    # -----------------------------------------
    # 2. 기존 메시지 조회
    # -----------------------------------------
    if conversation_ready:
        load_chat_messages()

    with st.container(
        key="home_content",
    ):

        render_hero()

        keyword, search_clicked = render_search()

        # 필터 선택값
        filters = render_filters()

        # 기존 채팅
        if st.session_state.get(
            "chat_messages"
        ):
            render_chat()

        # 검색 버튼
        if search_clicked:

            keyword = keyword.strip()

            if keyword:

                st.session_state[
                    "search_keyword"
                ] = keyword

                handle_chat(
                    keyword,
                    filters,
                )

            else:
                st.warning(
                    "검색어를 입력해주세요."
                )

        # 추천 결과. 검색이 실패한 뒤에는 가짜 식당 카드를 보여주지 않는다.
        if st.session_state.get("last_message_id"):

            render_restaurant()

            render_recommendation_reason()

            render_feedback()


# 기존 대화 불러오기
def load_chat_messages():
    conversation_id = st.session_state.get("conversation_id")
    access_token = st.session_state.get("access_token")

    if not conversation_id or not access_token:
        return

    if st.session_state.get("chat_loaded"):
        return

    result = get_json(
        f"/conversations/{conversation_id}/messages",
        access_token=access_token,
    )

    if not result["ok"]:
        # 없는 대화면 홈 진입 시 ensure_conversation이 다시 만든다.
        if result.get("status_code") == 404:
            clear_conversation_state()
            return
        error_body = result.get("error") or {}
        st.error(
            error_body.get("message") or "대화를 불러오지 못했습니다."
        )
        return

    messages = result["data"] or []

    st.session_state.chat_messages = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in messages
        if message["role"] in ("user", "assistant")
    ]

    st.session_state.chat_loaded = True

#채팅 전송
def handle_chat(
    keyword: str,
    filters: dict,
):
    conversation_id = st.session_state.get(
        "conversation_id"
    )

    access_token = st.session_state.get(
        "access_token"
    )

    if not conversation_id:
        st.error("대화방 정보가 없습니다.")
        return

    if not access_token:
        st.error("로그인이 필요합니다.")
        return

    st.session_state.setdefault(
        "chat_messages",
        [],
    )

    assistant_text = ""
    restaurant = None

    for event in stream_post(
        f"/conversations/{conversation_id}/chat",
        json_body={
            "content": keyword,
            "restaurant_category": filters.get(
                "restaurant_category"
            ),
            "menu_type": filters.get(
                "menu_type"
            ),
            "price_level": filters.get(
                "price_level"
            ),
        },
        access_token=access_token,
        timeout=90,
    ):
        if "error" in event:
            error_text = str(event["error"])
            if "404" in error_text:
                clear_conversation_state()
                if ensure_conversation():
                    st.warning("대화를 다시 준비한 뒤 한번 더 검색해 주세요.")
                else:
                    st.error("대화를 다시 만들지 못했습니다.")
                return
            st.error(error_text)
            return

        if "text" in event:
            assistant_text += event["text"]

        if event.get("done"):
            st.session_state[
                "last_message_id"
            ] = event.get(
                "message_id"
            )
            restaurant = event.get("restaurant")
            if event.get("recommendation_id"):
                st.session_state["recommendation_id"] = event.get(
                    "recommendation_id"
                )

    st.session_state.recommended_restaurant = restaurant
    st.session_state.home_feedback_value = None
    st.session_state.chat_loaded = False
    st.rerun()
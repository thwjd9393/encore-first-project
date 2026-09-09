import pandas as pd
import streamlit as st

from src.common.api_client import (
    delete_json,
    get_json,
    list_resource_items,
)
from src.common.components import (
    render_download_button,
    render_empty_state,
    render_error_state,
    render_section_title,
    render_summary_strip,
    render_toolbar_row,
)
from src.views.admin_analytics import get_error_next_action
from src.views.admin_common import (
    get_category_name,
    get_feature_label,
    get_price_label,
    get_representative_menu,
)

DEFAULT_PAGE_SIZE = 10
RESTAURANT_STATE_KEYS = {
    "needs_fetch": "admin_restaurants_needs_fetch",
    "result": "admin_restaurants_result",
    "selected_id": "admin_restaurants_selected_id",
    "detail": "admin_restaurants_detail",
    "page": "admin_restaurants_page",
    "search": "admin_restaurants_search_input",
    "last_search": "admin_restaurants_last_search",
}


def get_access_token():
    return st.session_state.get("access_token")


def initialize_restaurant_state():
    st.session_state.setdefault(RESTAURANT_STATE_KEYS["needs_fetch"], True)
    st.session_state.setdefault(RESTAURANT_STATE_KEYS["result"], None)
    st.session_state.setdefault(RESTAURANT_STATE_KEYS["selected_id"], None)
    st.session_state.setdefault(RESTAURANT_STATE_KEYS["detail"], None)
    st.session_state.setdefault(RESTAURANT_STATE_KEYS["page"], 1)
    st.session_state.setdefault(RESTAURANT_STATE_KEYS["last_search"], "")
    result = st.session_state.get(RESTAURANT_STATE_KEYS["result"]) or {}
    restaurant_result = result.get("restaurants") or {}
    error = restaurant_result.get("error") or {}
    if error.get("code") in {"AUTH_REQUIRED", "TOKEN_EXPIRED", "ADMIN_REQUIRED"}:
        st.session_state[RESTAURANT_STATE_KEYS["result"]] = None
        st.session_state[RESTAURANT_STATE_KEYS["needs_fetch"]] = True


def fetch_restaurant_list():
    access_token = get_access_token()
    restaurant_result = get_json(
        "/restaurants",
        params={
            "page": 1,
            "page_size": 100,
        },
        access_token=access_token,
    )
    category_result = get_json(
        "/restaurant-categories",
        access_token=access_token,
    )
    return {
        "restaurants": restaurant_result,
        "categories": category_result,
    }


def fetch_restaurant_detail(restaurant_id):
    return get_json(
        f"/restaurants/{restaurant_id}",
        access_token=get_access_token(),
    )


def refresh_restaurants_if_needed():
    if not st.session_state.get(RESTAURANT_STATE_KEYS["needs_fetch"]):
        return
    with st.spinner("식당 목록을 조회합니다."):
        st.session_state[RESTAURANT_STATE_KEYS["result"]] = fetch_restaurant_list()
    st.session_state[RESTAURANT_STATE_KEYS["needs_fetch"]] = False


def matches_restaurant_search(item, keyword):
    if not keyword:
        return True
    haystack = " ".join(
        [
            str(item.get("name") or ""),
            str(get_representative_menu(item) or ""),
            str(item.get("address") or item.get("road_address") or ""),
        ]
    )
    return keyword in haystack


def list_searched_restaurants(items, keyword):
    return [item for item in items if matches_restaurant_search(item, keyword)]


def count_by_food(items):
    counts = {"한식": 0, "중식": 0, "일식": 0, "기타": 0}
    for item in items:
        category_name = get_category_name(item)
        if category_name == "한식":
            counts["한식"] += 1
        elif category_name == "중식":
            counts["중식"] += 1
        elif category_name == "일식":
            counts["일식"] += 1
        else:
            counts["기타"] += 1
    return counts


def build_restaurant_rows(items, page, page_size):
    start_index = (page - 1) * page_size
    page_items = items[start_index : start_index + page_size]
    rows = []
    for offset, item in enumerate(page_items, start=start_index + 1):
        rows.append(
            {
                "번호": offset,
                "식당명": item.get("name") or "-",
                "음식별": get_category_name(item) or "-",
                "대표 메뉴": get_representative_menu(item),
                "가격대": get_price_label(item),
                "메뉴 특성": get_feature_label(item),
                "주소": item.get("address")
                or item.get("road_address")
                or item.get("lot_address")
                or "-",
                "식당 ID": item.get("id") or item.get("restaurant_id"),
            }
        )
    return rows, page_items


def render_restaurant_summary(items, total_count):
    food_counts = count_by_food(items) if items else {}
    can_break_down = items and total_count == len(items)
    render_summary_strip(
        [
            {
                "label": "전체 식당 수",
                "value": None if total_count is None else f"{total_count}개",
            },
            {
                "label": "한식",
                "value": food_counts.get("한식") if can_break_down else None,
            },
            {
                "label": "중식",
                "value": food_counts.get("중식") if can_break_down else None,
            },
            {
                "label": "일식",
                "value": food_counts.get("일식") if can_break_down else None,
            },
            {
                "label": "기타",
                "value": food_counts.get("기타") if can_break_down else None,
            },
        ]
    )
    if items and not can_break_down:
        st.caption("카테고리 건수는 전체 목록을 받은 뒤에만 표시합니다.")


def render_pagination(total_count, page_size):
    page_count = max(1, (total_count + page_size - 1) // page_size)
    current_page = st.session_state.get(RESTAURANT_STATE_KEYS["page"], 1)
    if current_page > page_count:
        st.session_state[RESTAURANT_STATE_KEYS["page"]] = page_count

    with st.container(horizontal=True, horizontal_alignment="right"):
        return st.pagination(
            page_count,
            max_visible_pages=7,
            width="content",
            key=RESTAURANT_STATE_KEYS["page"],
        )


def render_restaurant_table(items, total_count):
    header = render_toolbar_row()
    header.container()
    actions = header.container(
        horizontal=True,
        vertical_alignment="center",
        gap="small",
        wrap=False,
        width="content",
    )
    download_box = None
    with actions:
        search_text = st.text_input(
            "검색",
            placeholder="식당명, 메뉴, 주소 검색",
            key=RESTAURANT_STATE_KEYS["search"],
            label_visibility="collapsed",
            width=260,
        )
        download_box = st.container()

    keyword = str(search_text or "").strip()
    if st.session_state.get(RESTAURANT_STATE_KEYS["last_search"]) != keyword:
        st.session_state[RESTAURANT_STATE_KEYS["last_search"]] = keyword
        st.session_state[RESTAURANT_STATE_KEYS["page"]] = 1

    searched_items = list_searched_restaurants(items, keyword)
    searched_count = len(searched_items)
    export_rows, _ = build_restaurant_rows(
        searched_items, 1, searched_count or 1
    )
    export_df = pd.DataFrame(export_rows)
    if not export_df.empty:
        export_df = export_df.drop(columns=["식당 ID"])

    with download_box:
        render_download_button(
            "전체 식당 내려받기",
            export_df,
            "playeat_restaurants.csv",
            "admin_restaurant_download",
            width="content",
        )

    if not searched_count:
        render_empty_state("조건에 맞는 식당이 없습니다.")
        return None

    table_slot = st.empty()
    page = render_pagination(searched_count, DEFAULT_PAGE_SIZE)
    rows, page_items = build_restaurant_rows(
        searched_items, page, DEFAULT_PAGE_SIZE
    )
    table_df = pd.DataFrame(rows)
    display_df = table_df.drop(columns=["식당 ID"]) if not table_df.empty else table_df
    with table_slot:
        selected = st.dataframe(
            display_df,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="admin_restaurant_table",
        )
    selected_rows = selected.selection.rows if selected and selected.selection else []
    if selected_rows:
        selected_id = rows[selected_rows[0]]["식당 ID"]
        st.session_state[RESTAURANT_STATE_KEYS["selected_id"]] = selected_id
        st.session_state[RESTAURANT_STATE_KEYS["detail"]] = fetch_restaurant_detail(
            selected_id
        )
    return page_items


def render_restaurant_detail():
    selected_id = st.session_state.get(RESTAURANT_STATE_KEYS["selected_id"])
    if not selected_id:
        st.caption("목록에서 식당을 선택하면 상세와 메뉴를 표시합니다.")
        return

    detail_result = st.session_state.get(RESTAURANT_STATE_KEYS["detail"])
    with st.container(border=True):
        action_box = None
        with render_toolbar_row():
            render_section_title("식당 상세")
            action_box = st.container()
        if not detail_result:
            render_empty_state("선택한 식당 상세가 없습니다.")
            return
        if not detail_result.get("ok"):
            error_body = detail_result.get("error") or {}
            render_error_state(
                error_body.get("message") or "식당 상세를 불러오지 못했습니다.",
                request_id=error_body.get("request_id"),
            )
            return

        restaurant = detail_result.get("data") or {}
        st.write(
            {
                "restaurant_id": restaurant.get("id") or selected_id,
                "name": restaurant.get("name"),
                "address": restaurant.get("address")
                or restaurant.get("road_address"),
                "phone": restaurant.get("phone"),
                "kakao_place_id": restaurant.get("kakao_place_id"),
                "kakao_place_url": restaurant.get("kakao_place_url"),
                "is_active": restaurant.get("is_active", True),
            }
        )
        menus = restaurant.get("menus") or []
        if menus:
            st.dataframe(pd.DataFrame(menus), hide_index=True)
        else:
            st.caption("등록된 메뉴가 없습니다.")

        with action_box:
            deactivate_clicked = st.button(
                "추천에서 제외",
                type="primary",
                key="admin_deactivate_restaurant",
                width="content",
            )
        if deactivate_clicked:
            deactivate_result = delete_json(
                f"/admin/restaurants/{selected_id}",
                access_token=get_access_token(),
            )
            if deactivate_result["ok"]:
                st.success("식당을 비활성화했습니다. 과거 추천·평가는 유지됩니다.")
                st.session_state[RESTAURANT_STATE_KEYS["needs_fetch"]] = True
                st.rerun()
            else:
                error_body = deactivate_result.get("error") or {}
                render_error_state(
                    error_body.get("message") or "비활성화에 실패했습니다.",
                    request_id=error_body.get("request_id"),
                    next_action=get_error_next_action(error_body),
                )


def render_admin_restaurants():
    initialize_restaurant_state()
    refresh_restaurants_if_needed()
    result = st.session_state.get(RESTAURANT_STATE_KEYS["result"])
    if result is None:
        render_empty_state("식당 목록을 아직 조회하지 않았습니다.")
        return

    restaurant_result = result.get("restaurants") or {}
    if not restaurant_result.get("ok"):
        error_body = restaurant_result.get("error") or {}
        render_error_state(
            error_body.get("message") or "식당 목록을 불러오지 못했습니다.",
            request_id=error_body.get("request_id"),
            next_action="FastAPI 식당 조회 API 연결 후 다시 확인해 주세요.",
        )
        render_summary_strip(
            [
                {"label": "전체 식당 수", "value": None},
                {"label": "한식", "value": None},
                {"label": "중식", "value": None},
                {"label": "일식", "value": None},
                {"label": "기타", "value": None},
            ]
        )
        return

    items, total_count = list_resource_items(restaurant_result.get("data"))
    render_restaurant_summary(items, total_count)
    render_restaurant_table(items, len(items))
    render_restaurant_detail()

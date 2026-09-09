import pandas as pd
import streamlit as st

from src.common.api_client import get_json, list_resource_items
from src.common.components import (
    render_empty_state,
    render_error_state,
    render_section_title,
    render_sentiment_cards,
)
from src.views.admin_analytics import get_error_next_action
from src.views.admin_common import (
    FEEDBACK_VALUE_TO_REACTION,
    get_category_name,
    get_feature_label,
    get_price_label,
)

FEEDBACK_TABLE_COLUMNS = [
    "번호",
    "작성일시",
    "식당명",
    "음식별",
    "가격대",
    "메뉴 특성",
    "사용자 반응",
]
FEEDBACK_STATE_KEYS = {
    "needs_fetch": "admin_feedback_needs_fetch",
    "result": "admin_feedback_result",
}


def get_access_token():
    return st.session_state.get("access_token")


def initialize_feedback_state():
    st.session_state.setdefault(FEEDBACK_STATE_KEYS["needs_fetch"], True)
    st.session_state.setdefault(FEEDBACK_STATE_KEYS["result"], None)
    result = st.session_state.get(FEEDBACK_STATE_KEYS["result"])
    if isinstance(result, dict):
        error = (result.get("error") or {})
        if error.get("code") in {"AUTH_REQUIRED", "TOKEN_EXPIRED", "ADMIN_REQUIRED"}:
            st.session_state[FEEDBACK_STATE_KEYS["result"]] = None
            st.session_state[FEEDBACK_STATE_KEYS["needs_fetch"]] = True


def list_admin_feedback():
    return get_json(
        "/admin/feedback",
        params={"page": 1, "page_size": 100},
        access_token=get_access_token(),
    )


def refresh_feedback_if_needed():
    if not st.session_state.get(FEEDBACK_STATE_KEYS["needs_fetch"]):
        return
    with st.spinner("평가 목록을 조회합니다."):
        st.session_state[FEEDBACK_STATE_KEYS["result"]] = list_admin_feedback()
    st.session_state[FEEDBACK_STATE_KEYS["needs_fetch"]] = False


def format_created_at(value):
    if not value:
        return "-"
    return str(value).replace("T", " ")[:19]


def get_counts(payload):
    counts = (payload or {}).get("counts") or {}
    return {
        "1": int(counts.get("feedback_1") or 0),
        "2": int(counts.get("feedback_2") or 0),
        "3": int(counts.get("feedback_3") or 0),
    }


def format_count_card(count, total_count):
    if total_count <= 0:
        return "0건", "0건"
    percent = round(count * 100 / total_count)
    return f"{percent}%", f"{count}건"


def build_feedback_rows(items):
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            {
                "번호": index,
                "작성일시": format_created_at(item.get("created_at")),
                "식당명": item.get("restaurant_name") or "-",
                "음식별": get_category_name(item) or "-",
                "가격대": get_price_label(item),
                "메뉴 특성": get_feature_label(item),
                "사용자 반응": FEEDBACK_VALUE_TO_REACTION.get(
                    str(item.get("feedback_value") or ""),
                    "-",
                ),
            }
        )
    return rows


def render_recommendation_satisfaction(counts, total_count):
    render_section_title(
        "추천 결과 만족도",
        "만족은 도움됨, 보통은 보통이야, 불만족은 아쉬움과 같습니다.",
    )
    satisfied_value, satisfied_count = format_count_card(counts["3"], total_count)
    normal_value, normal_count = format_count_card(counts["2"], total_count)
    bad_value, bad_count = format_count_card(counts["1"], total_count)
    render_sentiment_cards(
        [
            {
                "label": "만족",
                "value": satisfied_value if total_count else None,
                "count_text": satisfied_count if total_count else "",
                "tone": "success",
            },
            {
                "label": "보통",
                "value": normal_value if total_count else None,
                "count_text": normal_count if total_count else "",
                "tone": "warning",
            },
            {
                "label": "불만족",
                "value": bad_value if total_count else None,
                "count_text": bad_count if total_count else "",
                "tone": "danger",
            },
        ]
    )


def render_feedback_table(items):
    rows = build_feedback_rows(items)
    table_df = pd.DataFrame(rows, columns=FEEDBACK_TABLE_COLUMNS)
    render_section_title("사용자 피드백 내역", f"표시 {len(rows)}건")
    st.dataframe(table_df, hide_index=True)
    if not rows:
        render_empty_state("등록된 평가가 없습니다.")


def render_admin_feedback():
    initialize_feedback_state()
    refresh_feedback_if_needed()
    result = st.session_state.get(FEEDBACK_STATE_KEYS["result"])
    if result is None:
        render_empty_state("평가 목록을 아직 조회하지 않았습니다.")
        return

    if not result.get("ok"):
        error_body = result.get("error") or {}
        render_error_state(
            error_body.get("message") or "평가 목록을 불러오지 못했습니다.",
            request_id=error_body.get("request_id"),
            next_action=get_error_next_action(error_body),
        )
        render_recommendation_satisfaction({"1": 0, "2": 0, "3": 0}, 0)
        render_feedback_table([])
        return

    payload = result.get("data") or {}
    items, total_count = list_resource_items(payload)
    counts = get_counts(payload)
    counted_total = counts["1"] + counts["2"] + counts["3"]
    render_recommendation_satisfaction(counts, counted_total or total_count or 0)
    render_feedback_table(items)

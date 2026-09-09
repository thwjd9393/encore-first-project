import pandas as pd
import streamlit as st

from src.common.components import (
    render_empty_state,
    render_error_state,
    render_loading_state,
    render_section_title,
)
from src.views.admin_analytics import (
    ADMIN_ANALYTICS_KEYS,
    get_error_next_action,
    handle_refresh,
    initialize_admin_analytics_state,
    list_api_log_items,
    list_metric_points,
    refresh_admin_analytics_if_needed,
    render_applied_query_caption,
    render_evaluation_panel,
    render_filter_form,
    render_kpi_row,
    render_log_detail,
    render_log_table,
    render_operation_charts,
    render_summary_panel,
)

LOG_SECTION_STATS = "통계분석 및 요약"
LOG_SECTION_EVAL = "요약품질평가"
LOG_SECTION_LOGS = "최근요청로그"
LOG_SECTION_KEY = "admin_logs_section"
LOG_SECTION_NAV_KEY = "admin_logs_section_nav_v9"
LOGS_MENU_ACTIVE_KEY = "admin_logs_menu_active"
LOG_SECTION_ALIASES = {
    "운영 KPI": LOG_SECTION_STATS,
    "통계분석": LOG_SECTION_STATS,
    "LLM 로그요약": LOG_SECTION_STATS,
    "조회조건": LOG_SECTION_STATS,
    "품질평가": LOG_SECTION_EVAL,
}
LOG_SECTIONS = (
    LOG_SECTION_STATS,
    LOG_SECTION_EVAL,
    LOG_SECTION_LOGS,
)


def initialize_log_section():
    if not st.session_state.get("admin_logs_drop_filter_tab"):
        st.session_state["admin_logs_drop_filter_tab"] = True
        st.session_state[LOG_SECTION_KEY] = LOG_SECTION_STATS
    st.session_state.setdefault(LOG_SECTION_KEY, LOG_SECTION_STATS)


def refresh_on_logs_entry():
    was_on_logs = st.session_state.get(LOGS_MENU_ACTIVE_KEY)
    st.session_state[LOGS_MENU_ACTIVE_KEY] = True
    if was_on_logs:
        return
    handle_refresh()


def get_current_log_section():
    current_section = st.session_state.get(LOG_SECTION_KEY)
    if current_section in LOG_SECTION_ALIASES:
        current_section = LOG_SECTION_ALIASES[current_section]
    if current_section not in LOG_SECTIONS:
        current_section = LOG_SECTION_STATS
    st.session_state[LOG_SECTION_KEY] = current_section
    return current_section


def render_log_section_nav(current_section):
    selected = st.segmented_control(
        "조회 항목",
        options=list(LOG_SECTIONS),
        default=current_section,
        key=LOG_SECTION_NAV_KEY,
        required=True,
        label_visibility="collapsed",
        width="content",
    )
    if selected:
        st.session_state[LOG_SECTION_KEY] = selected


def list_stats_context(result):
    usage_result = result.get("usage") or {}
    latency_result = result.get("latency") or {}
    error_result = result.get("errors") or {}
    log_result = result.get("logs") or {}
    stats_error = None
    for item in (usage_result, latency_result, error_result):
        if not item.get("ok"):
            stats_error = item.get("error")
            break
    usage_points = list_metric_points(usage_result.get("data"))
    latency_points = list_metric_points(latency_result.get("data"))
    error_points = list_metric_points(error_result.get("data"))
    log_items, _total_count = list_api_log_items(log_result.get("data"))
    return (
        stats_error,
        usage_points,
        latency_points,
        error_points,
        log_items,
        log_result,
    )


def render_stats_error(stats_error):
    render_error_state(
        stats_error.get("message") or "통계를 불러오지 못했습니다.",
        request_id=stats_error.get("request_id"),
        next_action=get_error_next_action(stats_error),
    )


def render_stats_section(result):
    render_section_title("통계분석 및 요약")
    stats_error, usage_points, latency_points, error_points, log_items, _log_result = (
        list_stats_context(result)
    )
    if stats_error:
        render_stats_error(stats_error)
        return
    if not usage_points and not latency_points and not error_points:
        render_empty_state("선택한 기간에 표시할 통계가 없습니다.")
        return
    if usage_points:
        render_kpi_row(usage_points, log_items)
    render_operation_charts(usage_points, latency_points, error_points)


def render_recent_logs_section(result):
    log_result = result.get("logs") or {}
    empty_df = pd.DataFrame(
        columns=["발생 시각", "Method", "엔드포인트", "상태", "응답시간(ms)"]
    )
    if not log_result.get("ok"):
        error_body = log_result.get("error") or {}
        render_log_table([], 0, empty_df)
        render_error_state(
            error_body.get("message") or "최근 요청 로그를 불러오지 못했습니다.",
            request_id=error_body.get("request_id"),
            next_action=get_error_next_action(error_body),
        )
        return

    log_items, total_count = list_api_log_items(log_result.get("data"))
    export_rows = []
    for item in log_items:
        export_rows.append(
            {
                "발생 시각": item.get("occurred_at"),
                "Method": item.get("http_method"),
                "엔드포인트": item.get("endpoint") or item.get("endpoint_path"),
                "상태": item.get("status_code"),
                "응답시간(ms)": item.get("response_time_ms"),
            }
        )
    export_df = pd.DataFrame(export_rows) if export_rows else empty_df
    render_log_table(log_items, total_count, export_df)
    render_log_detail(log_items)


def render_admin_logs():
    initialize_admin_analytics_state()
    initialize_log_section()
    refresh_on_logs_entry()
    current_section = get_current_log_section()
    render_log_section_nav(current_section)
    current_section = get_current_log_section()
    st.caption(
        "통계분석 및 요약에서 기간·필터, 사용량·지연·에러, LLM 요약을 한 화면에서 확인합니다. "
        "요약품질평가는 같은 요약 실행 다음 품질평가, 그다음 개선실험입니다."
    )

    query = st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]]
    if current_section == LOG_SECTION_STATS:
        render_filter_form(query)
    refresh_admin_analytics_if_needed()
    query = st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]]
    result = st.session_state.get(ADMIN_ANALYTICS_KEYS["result"])

    if result is None:
        render_loading_state("처음 조회를 준비하고 있습니다.")
        return

    render_applied_query_caption(query, result.get("fetched_at"))
    if current_section == LOG_SECTION_STATS:
        render_stats_section(result)
        render_summary_panel(query)
    elif current_section == LOG_SECTION_EVAL:
        render_evaluation_panel(query)
    elif current_section == LOG_SECTION_LOGS:
        render_recent_logs_section(result)

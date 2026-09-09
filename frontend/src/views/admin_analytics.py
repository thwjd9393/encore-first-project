from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

from src.common.api_client import get_json, post_json
from src.common.components import (
    CHART_DANGER,
    CHART_PRIMARY,
    CHART_SECONDARY,
    render_donut_chart,
    render_download_button,
    render_empty_state,
    render_error_state,
    render_loading_state,
    render_section_title,
    render_toolbar_row,
)

HTTP_METHOD_OPTIONS = ["전체", "GET(조회)", "POST(생성)", "PATCH(수정)", "DELETE(삭제)"]
HTTP_METHOD_TO_PARAM = {
    "GET(조회)": "GET",
    "POST(생성)": "POST",
    "PATCH(수정)": "PATCH",
    "DELETE(삭제)": "DELETE",
}
HTTP_METHOD_TO_LABEL = {
    "GET": "GET(조회)",
    "POST": "POST(생성)",
    "PATCH": "PATCH(수정)",
    "DELETE": "DELETE(삭제)",
}
ENDPOINT_ALL_OPTION = "전체"
STATUS_CLASS_OPTIONS = ["전체", "성공", "실패", "서버 오류"]
STATUS_CLASS_TO_PARAM = {
    "성공": "2xx",
    "실패": "4xx",
    "서버 오류": "5xx",
}
STATUS_CLASS_TO_LABEL = {
    "2xx": "성공",
    "4xx": "실패",
    "5xx": "서버 오류",
}
DEFAULT_PAGE_SIZE = 20
ADMIN_ANALYTICS_KEYS = {
    "draft_query": "admin_analytics_draft_query",
    "applied_query": "admin_analytics_applied_query",
    "needs_fetch": "admin_analytics_needs_fetch",
    "is_loading": "admin_analytics_is_loading",
    "result": "admin_analytics_result",
    "selected_log_id": "admin_analytics_selected_log_id",
    "log_page": "admin_analytics_log_page",
    "cleaning_run_id": "admin_analytics_cleaning_run_id",
    "cleaning_result": "admin_analytics_cleaning_result",
    "summary_result": "admin_analytics_summary_result",
    "selected_claim_text": "admin_analytics_selected_claim_text",
    "search_stats": "admin_analytics_search_stats",
    "evaluation_result": "admin_analytics_evaluation_result",
    "experiment_result": "admin_analytics_experiment_result",
    "summary_panel_view": "admin_analytics_summary_panel_view",
    "eval_panel_view": "admin_analytics_eval_panel_view",
}


def get_default_period():
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=7)
    return period_start, period_end


def build_default_query():
    period_start, period_end = get_default_period()
    return {
        "period_start": period_start,
        "period_end": period_end,
        "endpoint": "",
        "http_method": "전체",
        "status_class": None,
        "status_code": None,
        "error_only": False,
        "page": 1,
        "page_size": DEFAULT_PAGE_SIZE,
    }


def status_class_from_query(query):
    status_class = query.get("status_class")
    if status_class in STATUS_CLASS_TO_LABEL:
        return status_class
    status_code = query.get("status_code")
    if not status_code:
        return None
    code = int(status_code)
    if 200 <= code <= 299:
        return "2xx"
    if 400 <= code <= 499:
        return "4xx"
    if 500 <= code <= 599:
        return "5xx"
    return None


def status_class_to_label(status_class):
    return STATUS_CLASS_TO_LABEL.get(status_class) or STATUS_CLASS_OPTIONS[0]


def parse_status_class_label(label):
    return STATUS_CLASS_TO_PARAM.get(label)


def parse_http_method_label(label):
    if not label or label == "전체":
        return "전체"
    return HTTP_METHOD_TO_PARAM.get(label, "전체")


def http_method_to_label(http_method):
    if not http_method or http_method == "전체":
        return "전체"
    return HTTP_METHOD_TO_LABEL.get(http_method, http_method)


def option_index(options, value):
    if value in options:
        return options.index(value)
    return 0


def list_endpoint_filter_options(query):
    options = [ENDPOINT_ALL_OPTION]
    seen = {ENDPOINT_ALL_OPTION}
    result = st.session_state.get(ADMIN_ANALYTICS_KEYS["result"]) or {}
    for key in ("usage", "latency", "errors"):
        payload = (result.get(key) or {}).get("data")
        for point in list_metric_points(payload):
            path = str(point.get("endpoint") or "").strip()
            if path and path not in seen:
                seen.add(path)
                options.append(path)
    log_items, _total_count = list_api_log_items(
        (result.get("logs") or {}).get("data")
    )
    for item in log_items:
        path = str(item.get("endpoint") or item.get("endpoint_path") or "").strip()
        if path and path not in seen:
            seen.add(path)
            options.append(path)
    current = (query.get("endpoint") or "").strip()
    if current and current not in seen:
        options.append(current)
    return options


def format_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_statistics_params(query):
    params = {
        "period_start": format_datetime(query["period_start"]),
        "period_end": format_datetime(query["period_end"]),
        "error_only": query["error_only"],
    }
    cleaning_run_id = (
        st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_run_id"]) or ""
    ).strip()
    if cleaning_run_id:
        params["cleaning_run_id"] = cleaning_run_id

    endpoint = (query.get("endpoint") or "").strip()
    if endpoint:
        params["endpoint"] = endpoint

    http_method = query.get("http_method")
    if http_method and http_method != "전체":
        params["http_method"] = http_method

    status_class = status_class_from_query(query)
    if status_class:
        params["status_class"] = status_class
    status_code = query.get("status_code")
    if status_code and not status_class:
        params["status_code"] = int(status_code)

    return params


def build_api_log_params(query):
    params = build_statistics_params(query)
    params["page"] = query.get("page", 1)
    params["page_size"] = query.get("page_size", DEFAULT_PAGE_SIZE)
    cleaning_run_id = (
        st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_run_id"]) or ""
    ).strip()
    if cleaning_run_id:
        params["cleaning_run_id"] = cleaning_run_id
    return params


def build_log_filters(query):
    filters = {
        "error_only": bool(query.get("error_only")),
    }
    endpoint = (query.get("endpoint") or "").strip()
    if endpoint:
        filters["endpoint"] = endpoint
    http_method = query.get("http_method")
    if http_method and http_method != "전체":
        filters["http_method"] = http_method
    status_class = status_class_from_query(query)
    if status_class:
        filters["status_class"] = status_class
    status_code = query.get("status_code")
    if status_code and not status_class:
        filters["status_code"] = int(status_code)
    return filters


def get_access_token():
    return st.session_state.get("access_token")


def list_metric_points(payload):
    if isinstance(payload, dict):
        points = payload.get("points")
        if isinstance(points, list):
            return points
        return []
    if isinstance(payload, list):
        return payload
    return []


def list_api_log_items(payload):
    if isinstance(payload, list):
        return payload, len(payload)
    if not isinstance(payload, dict):
        return [], 0

    items = (
        payload.get("items")
        or payload.get("logs")
        or payload.get("results")
        or []
    )
    total_count = payload.get("total_count", payload.get("total", len(items)))
    return items, total_count


def aggregate_request_count(points):
    return sum(int(point.get("request_count") or 0) for point in points)


def aggregate_error_count(points):
    return sum(int(point.get("error_count") or 0) for point in points)


def aggregate_average_response_time(points):
    weighted_total = 0.0
    request_count = 0
    for point in points:
        point_request_count = int(point.get("request_count") or 0)
        average_time = point.get("avg_response_time_ms")
        if average_time is None or point_request_count == 0:
            continue
        weighted_total += float(average_time) * point_request_count
        request_count += point_request_count

    if request_count == 0:
        return None
    return weighted_total / request_count


def aggregate_p95_response_time(points):
    values = [
        float(point["p95_response_time_ms"])
        for point in points
        if point.get("p95_response_time_ms") is not None
    ]
    if not values:
        return None
    return max(values)


def fetch_admin_analytics(query):
    access_token = get_access_token()
    statistics_params = build_statistics_params(query)
    log_params = build_api_log_params(query)

    usage_result = get_json(
        "/admin/api-statistics/usage",
        params=statistics_params,
        access_token=access_token,
    )
    latency_result = get_json(
        "/admin/api-statistics/latency",
        params=statistics_params,
        access_token=access_token,
    )
    error_result = get_json(
        "/admin/api-statistics/errors",
        params=statistics_params,
        access_token=access_token,
    )
    log_result = get_json(
        "/admin/api-logs",
        params=log_params,
        access_token=access_token,
    )

    return {
        "usage": usage_result,
        "latency": latency_result,
        "errors": error_result,
        "logs": log_result,
        "fetched_at": datetime.now(timezone.utc),
    }


def is_auth_error_payload(result):
    if not isinstance(result, dict):
        return False
    error = result.get("error") or {}
    if error.get("code") in {"AUTH_REQUIRED", "TOKEN_EXPIRED", "ADMIN_REQUIRED"}:
        return True
    if result.get("ok") is False and result.get("status_code") in {401, 403}:
        return True
    for key in ("usage", "latency", "errors", "logs", "restaurants", "categories"):
        nested = result.get(key)
        if isinstance(nested, dict) and is_auth_error_payload(nested):
            return True
    return False


def clear_stale_admin_auth_results():
    result = st.session_state.get(ADMIN_ANALYTICS_KEYS["result"])
    if is_auth_error_payload(result):
        st.session_state[ADMIN_ANALYTICS_KEYS["result"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = True
    search_stats = st.session_state.get(ADMIN_ANALYTICS_KEYS["search_stats"])
    if is_auth_error_payload(search_stats):
        st.session_state[ADMIN_ANALYTICS_KEYS["search_stats"]] = None


def initialize_admin_analytics_state():
    if ADMIN_ANALYTICS_KEYS["applied_query"] not in st.session_state:
        default_query = build_default_query()
        st.session_state[ADMIN_ANALYTICS_KEYS["draft_query"]] = default_query.copy()
        st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]] = default_query.copy()
        st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = True
        st.session_state[ADMIN_ANALYTICS_KEYS["is_loading"]] = False
        st.session_state[ADMIN_ANALYTICS_KEYS["result"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["selected_log_id"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["log_page"]] = 1
        st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_run_id"]] = ""
        st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_result"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["summary_result"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["selected_claim_text"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["search_stats"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["evaluation_result"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["experiment_result"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["summary_panel_view"]] = None
        st.session_state[ADMIN_ANALYTICS_KEYS["eval_panel_view"]] = None

    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["search_stats"], None)
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["cleaning_run_id"], "")
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["cleaning_result"], None)
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["summary_result"], None)
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["selected_claim_text"], None)
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["evaluation_result"], None)
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["experiment_result"], None)
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["summary_panel_view"], None)
    st.session_state.setdefault(ADMIN_ANALYTICS_KEYS["eval_panel_view"], None)
    clear_stale_admin_auth_results()


def handle_filter_apply(
    period_start,
    period_end,
    endpoint,
    http_method,
    status_class,
):
    applied_query = st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]].copy()
    applied_query["period_start"] = period_start
    applied_query["period_end"] = period_end
    applied_query["endpoint"] = endpoint
    applied_query["http_method"] = http_method
    applied_query["status_class"] = status_class
    applied_query["status_code"] = None
    applied_query["error_only"] = False
    applied_query["page"] = 1
    st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]] = applied_query
    st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = True
    st.session_state[ADMIN_ANALYTICS_KEYS["selected_log_id"]] = None


def handle_filter_reset():
    default_query = build_default_query()
    st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]] = default_query
    st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = True
    st.session_state[ADMIN_ANALYTICS_KEYS["selected_log_id"]] = None
    st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_run_id"]] = ""
    st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_result"]] = None
    for widget_key in (
        "admin_analytics_period_input",
        "admin_analytics_endpoint_input",
        "admin_analytics_endpoint_select",
        "admin_analytics_method_input",
        "admin_analytics_method_select",
        "admin_analytics_status_input",
        "admin_analytics_status_class_input",
        "admin_analytics_error_only_input",
    ):
        st.session_state.pop(widget_key, None)


def extend_open_period_end(query):
    updated_query = query.copy()
    now = datetime.now(timezone.utc)
    period_end = updated_query.get("period_end")
    if isinstance(period_end, datetime) and period_end.date() == now.date():
        updated_query["period_end"] = now
    return updated_query


def clear_failed_cleaning_run():
    cleaning_result = st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_result"])
    if not cleaning_result:
        return
    if cleaning_result.get("ok"):
        status = (cleaning_result.get("data") or {}).get("status")
        if status in (None, "succeeded", "running"):
            return
    st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_run_id"]] = ""
    st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_result"]] = None


def handle_refresh():
    if st.session_state.get(ADMIN_ANALYTICS_KEYS["is_loading"]):
        return
    applied_query = extend_open_period_end(
        st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]]
    )
    st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]] = applied_query
    clear_failed_cleaning_run()
    st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = True


def refresh_admin_analytics_if_needed():
    if not st.session_state.get(ADMIN_ANALYTICS_KEYS["needs_fetch"]):
        return

    query = extend_open_period_end(
        st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]]
    )
    st.session_state[ADMIN_ANALYTICS_KEYS["applied_query"]] = query
    try:
        with st.spinner("통계와 원본 로그를 조회합니다."):
            st.session_state[ADMIN_ANALYTICS_KEYS["result"]] = fetch_admin_analytics(
                query
            )
    finally:
        st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = False


def parse_period_input(period_value, fallback_query):
    if isinstance(period_value, (list, tuple)) and len(period_value) == 2:
        start_date, end_date = period_value
    else:
        start_date = period_value or fallback_query["period_start"].date()
        end_date = start_date

    period_start = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    now = datetime.now(timezone.utc)
    if end_date == now.date():
        period_end = now
    else:
        period_end = datetime.combine(
            end_date,
            datetime.max.time().replace(microsecond=0),
            tzinfo=timezone.utc,
        )

    if period_start >= period_end:
        period_end = period_start + timedelta(days=1)
    return period_start, period_end


def render_filter_form(query):
    with st.form("admin_analytics_filter_form"):
        with render_toolbar_row():
            render_section_title(
                "조회 조건",
                "기간과 필터를 적용하면 통계와 LLM 요약을 같은 조건으로 조회합니다.",
            )
            with st.container(
                horizontal=True,
                vertical_alignment="center",
                gap="small",
                wrap=False,
                width="content",
            ):
                apply_clicked = st.form_submit_button("적용", type="primary")
                reset_clicked = st.form_submit_button("초기화")
                refresh_clicked = st.form_submit_button("새로고침")

        period_value = st.date_input(
            "조회 기간",
            value=(
                query["period_start"].date(),
                query["period_end"].date(),
            ),
            key="admin_analytics_period_input",
        )
        endpoint_options = list_endpoint_filter_options(query)
        current_endpoint = (query.get("endpoint") or "").strip() or ENDPOINT_ALL_OPTION
        current_status_label = status_class_to_label(status_class_from_query(query))
        with st.container(horizontal=True, gap="small", wrap=True):
            endpoint_label = st.selectbox(
                "엔드포인트",
                options=endpoint_options,
                index=option_index(endpoint_options, current_endpoint),
                key="admin_analytics_endpoint_select",
            )
            http_method_label = st.selectbox(
                "HTTP Method",
                options=HTTP_METHOD_OPTIONS,
                index=option_index(
                    HTTP_METHOD_OPTIONS,
                    http_method_to_label(query.get("http_method") or "전체"),
                ),
                key="admin_analytics_method_select",
            )
            status_label = st.selectbox(
                "상태 코드",
                options=STATUS_CLASS_OPTIONS,
                index=option_index(STATUS_CLASS_OPTIONS, current_status_label),
                help="성공은 2xx, 실패는 4xx, 서버 오류는 5xx입니다.",
                key="admin_analytics_status_class_input",
            )

    if apply_clicked:
        period_start, period_end = parse_period_input(period_value, query)
        endpoint = "" if endpoint_label == ENDPOINT_ALL_OPTION else endpoint_label
        handle_filter_apply(
            period_start,
            period_end,
            endpoint,
            parse_http_method_label(http_method_label),
            parse_status_class_label(status_label),
        )
        st.rerun()

    if reset_clicked:
        handle_filter_reset()
        st.rerun()

    if refresh_clicked:
        handle_refresh()
        st.rerun()


def render_applied_query_caption(query, fetched_at):
    period_start = query["period_start"].strftime("%Y-%m-%d %H:%M")
    period_end = query["period_end"].strftime("%Y-%m-%d %H:%M")
    refreshed_at = fetched_at.strftime("%Y-%m-%d %H:%M:%S") if fetched_at else "-"
    st.caption(
        f"적용 기간: {period_start} ~ {period_end} UTC / 마지막 갱신 시각: {refreshed_at}"
    )


def render_kpi_row(usage_points, log_items=None):
    request_count = aggregate_request_count(usage_points)
    error_count = aggregate_error_count(usage_points)
    average_response_time = aggregate_average_response_time(usage_points)
    p95_response_time = aggregate_p95_response_time(usage_points)
    error_rate = (
        (error_count / request_count) * 100
        if request_count
        else None
    )

    with st.container(horizontal=True):
        st.metric("총 요청 수", f"{request_count:,}", border=True)
        st.metric(
            "평균 응답시간",
            "-" if average_response_time is None else f"{average_response_time:.0f} ms",
            border=True,
        )
        st.metric(
            "p95 응답시간",
            "-" if p95_response_time is None else f"{p95_response_time:.0f} ms",
            delta="요청 100건 중 95건이 이 시간 이하",
            delta_color="off",
            border=True,
        )
        st.metric(
            "에러율",
            "-" if error_rate is None else f"{error_rate:.1f}%",
            delta=f"분모: 총 요청 수 {request_count}건, 분자: 에러 {error_count}건",
            delta_color="off",
            border=True,
        )


def shorten_chart_endpoint(endpoint):
    path = str(endpoint or "").strip() or "-"
    for prefix in ("/api/v1/admin", "/api/v1"):
        if path == prefix:
            return "/"
        if path.startswith(prefix + "/"):
            return path[len(prefix):]
        if path.startswith(prefix):
            remainder = path[len(prefix):]
            return remainder or "/"
    return path


def format_chart_label(point):
    method = str(point.get("http_method") or "").strip()
    short_path = shorten_chart_endpoint(
        point.get("endpoint") or point.get("endpoint_path")
    )
    if method:
        return f"{method} {short_path}"
    return short_path


def format_chart_value_text(y_field, value):
    if y_field in {"request_count", "error_count"}:
        return f"{int(value)}건"
    return f"{value:.0f} ms"


CHART_TOP_N = 7


def take_top_chart_rows(rows, y_field, limit=CHART_TOP_N):
    ranked = sorted(rows, key=lambda row: row[y_field], reverse=True)
    return ranked[:limit]


def summarize_chart_trend(all_rows, display_rows, y_field):
    ranked = sorted(display_rows, key=lambda row: row[y_field], reverse=True)
    top = ranked[0]
    top_text = f"{top['label']} {format_chart_value_text(y_field, top[y_field])}"
    if len(ranked) == 1:
        return f"최댓값은 {top_text}입니다."

    if y_field in {"request_count", "error_count"}:
        total = sum(row[y_field] for row in all_rows)
        share = (top[y_field] / total) * 100 if total else 0
        return f"최댓값은 {top_text}이며 전체 {int(total)}건의 {share:.0f}%입니다."

    lowest = ranked[-1]
    lowest_text = f"{lowest['label']} {format_chart_value_text(y_field, lowest[y_field])}"
    return f"최댓값은 {top_text},\n최솟값은 {lowest_text}입니다."


def render_chart_title(title, subtitle=None):
    with st.container(
        horizontal=True,
        vertical_alignment="center",
        gap="small",
        wrap=True,
    ):
        st.subheader(title)
        if subtitle:
            st.caption(subtitle.replace("\n", "<br>"), unsafe_allow_html=True)


def render_points_chart(title, points, y_field, color, y_title):
    with st.container(border=True):
        if not points:
            render_chart_title(title)
            render_empty_state("표시할 통계가 없습니다.")
            return

        rows = []
        for point in points:
            value = point.get(y_field)
            if value is None:
                continue
            numeric_value = float(value)
            if y_field == "error_count" and numeric_value <= 0:
                continue
            rows.append(
                {
                    "label": format_chart_label(point),
                    "full_endpoint": point.get("endpoint")
                    or point.get("endpoint_path")
                    or "-",
                    "http_method": point.get("http_method") or "-",
                    y_field: numeric_value,
                }
            )
        if not rows:
            render_chart_title(title)
            render_empty_state("표시할 통계가 없습니다.")
            return

        display_rows = take_top_chart_rows(rows, y_field)
        render_chart_title(title, summarize_chart_trend(rows, display_rows, y_field))

        import altair as alt

        chart_df = pd.DataFrame(display_rows)
        row_count = len(chart_df)
        chart_height = 32 * row_count
        chart = (
            alt.Chart(chart_df)
            .mark_bar(color=color)
            .encode(
                x=alt.X(
                    f"{y_field}:Q",
                    title=y_title,
                    axis=alt.Axis(titlePadding=2, labelPadding=0),
                ),
                y=alt.Y(
                    "label:N",
                    sort="-x",
                    title=None,
                    scale=alt.Scale(paddingInner=0.35, paddingOuter=0.05),
                    axis=alt.Axis(
                        labelLimit=0,
                        labelOverlap=False,
                        labelPadding=4,
                        ticks=False,
                        domain=False,
                    ),
                ),
                tooltip=[
                    alt.Tooltip("http_method:N", title="Method"),
                    alt.Tooltip("full_endpoint:N", title="전체 경로"),
                    alt.Tooltip(f"{y_field}:Q", title=y_title),
                ],
            )
            .properties(
                height=chart_height,
                padding={"top": 2, "bottom": 2, "left": 0, "right": 4},
            )
            .configure_axisY(minExtent=168, labelLimit=0)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart)


def render_operation_charts(usage_points, latency_points, error_points):
    st.caption(
        "엔드포인트는 값이 큰 상위 7개만 비교합니다. 공통 접두 /api/v1/admin 은 생략하고 "
        "Method와 나머지 경로를 모두 표시합니다."
    )
    left_column, right_column = st.columns(2, gap="medium")

    with left_column:
        render_points_chart(
            "사용량",
            usage_points,
            "request_count",
            CHART_PRIMARY,
            "요청 수",
        )
        render_points_chart(
            "에러 건수",
            error_points,
            "error_count",
            CHART_DANGER,
            "에러 건수",
        )

    with right_column:
        render_points_chart(
            "평균 응답시간",
            latency_points,
            "avg_response_time_ms",
            CHART_SECONDARY,
            "평균 ms",
        )
        render_points_chart(
            "p95 응답시간",
            latency_points,
            "p95_response_time_ms",
            CHART_PRIMARY,
            "p95 ms",
        )


CLEANING_CRITERIA_LINES = (
    "결측은 request_id·Method·엔드포인트·상태 코드·응답시간이 없으면 제외하고, "
    "중복은 같은 Method·정규화 경로·발생 시각·상태·사용자면 한 건만 남깁니다.",
    "테스트 트래픽은 client_type이 test이거나 /health·/docs·/openapi.json·/redoc 요청입니다.",
)


def format_report_period(data):
    start = data.get("period_start") or "-"
    end = data.get("period_end") or "-"
    if hasattr(start, "strftime"):
        start = start.strftime("%Y-%m-%d %H:%M")
    if hasattr(end, "strftime"):
        end = end.strftime("%Y-%m-%d %H:%M")
    return f"{start} ~ {end}"


def format_cleaning_report_lines(cleaning_data):
    source_count = int(cleaning_data.get("source_count") or 0)
    included_count = int(cleaning_data.get("included_count") or 0)
    excluded_count = int(cleaning_data.get("excluded_count") or 0)
    line1 = (
        "결측 필드·중복 로그·테스트 트래픽을 제거했습니다. "
        f"원본 {source_count}건 중 포함 {included_count}건, 제외 {excluded_count}건입니다."
    )
    line2 = (
        "엔드포인트 경로의 UUID는 {id}로, 에러 코드는 빈 값을 없애 한 표기로 통일했습니다."
    )
    return line1, line2


def poll_cleaning_result(cleaning_result):
    if not cleaning_result or not cleaning_result.get("ok"):
        return cleaning_result
    cleaning_data = cleaning_result.get("data") or {}
    cleaning_status = cleaning_data.get("status")
    cleaning_id = cleaning_data.get("id") or cleaning_data.get("cleaning_run_id")
    if cleaning_status == "running" and cleaning_id:
        polled_cleaning = get_cleaning_run(cleaning_id)
        if polled_cleaning.get("ok"):
            st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_result"]] = polled_cleaning
            return polled_cleaning
    return cleaning_result


def poll_summary_result(summary_result):
    if not summary_result or not summary_result.get("ok"):
        return summary_result
    summary_data = summary_result.get("data") or {}
    summary_id = summary_data.get("summary_id") or summary_data.get("id")
    summary_status = summary_data.get("status")
    if summary_status == "running" and summary_id:
        polled_result = get_log_summary(summary_id)
        if polled_result.get("ok"):
            st.session_state[ADMIN_ANALYTICS_KEYS["summary_result"]] = polled_result
            return polled_result
    return summary_result


def render_cleaning_report_column(cleaning_result):
    st.subheader("정제 결과")
    if not cleaning_result:
        render_empty_state(
            "아직 정제를 실행하지 않았습니다.",
            next_action="주황색 정제 실행을 누릅니다.",
        )
        st.write(CLEANING_CRITERIA_LINES[0])
        st.write(CLEANING_CRITERIA_LINES[1])
        return
    if not cleaning_result.get("ok"):
        error_body = cleaning_result.get("error") or {}
        render_error_state(
            error_body.get("message") or "정제 실행에 실패했습니다.",
            request_id=error_body.get("request_id"),
        )
        return

    cleaning_data = cleaning_result.get("data") or {}
    cleaning_status = cleaning_data.get("status")
    if cleaning_status == "running":
        render_loading_state("로그를 정제하고 있습니다.")
        return
    if cleaning_status == "failed":
        render_error_state("로그 정제가 실패했습니다.")
        return

    line1, line2 = format_cleaning_report_lines(cleaning_data)
    st.write(line1)
    st.write(line2)
    st.write(CLEANING_CRITERIA_LINES[0])
    st.write(CLEANING_CRITERIA_LINES[1])
    st.caption(
        f"실행 ID: {cleaning_data.get('id') or cleaning_data.get('cleaning_run_id') or '-'} / "
        f"상태: {cleaning_status or 'succeeded'} / "
        f"기간: {format_report_period(cleaning_data)} UTC"
    )


def render_summary_report_column(summary_result):
    st.subheader("요약 결과")
    if summary_result is None:
        render_empty_state(
            "아직 요약을 실행하지 않았습니다.",
            next_action="정제 완료 후 요약 실행을 누릅니다.",
        )
        return None
    if not summary_result.get("ok"):
        error_body = summary_result.get("error") or {}
        render_error_state(
            error_body.get("message") or "요약을 불러오지 못했습니다.",
            request_id=error_body.get("request_id"),
        )
        return None

    summary_data = summary_result.get("data") or {}
    summary_status = summary_data.get("status")
    if summary_status == "running":
        render_loading_state("요약을 생성하고 있습니다.")
        return None
    if summary_status == "failed":
        render_error_state(
            "요약 생성이 실패했습니다.",
            next_action="부분 결과를 성공처럼 표시하지 않습니다.",
        )
        return None

    evidence_items = summary_data.get("evidence") or []
    summary_text = summary_data.get("summary_text")
    if not evidence_items or not summary_text:
        render_empty_state(
            "판단할 데이터 부족",
            next_action="근거가 없는 내용은 사실로 표시하지 않습니다.",
        )
        return None

    sections = split_summary_sections(summary_text)
    st.write(f"현황: {sections['현황']}")
    st.write(f"문제·이상 징후: {sections['문제·이상 징후']}")
    st.caption(
        f"확인할 조치: {sections['확인할 조치']} / "
        f"model: {summary_data.get('model_name') or '-'} / "
        f"prompt: {summary_data.get('prompt_version') or '-'}"
    )
    if summary_data.get("model_name") == "db_stats_v1":
        error_code = summary_data.get("error_code")
        if error_code:
            st.caption(
                f"Gemini 호출이 실패해 정제 로그 집계로 대체했습니다. ({error_code}) "
                "backend/.env의 GEMINI_MODEL_NAME을 사용 가능한 모델로 바꾼 뒤 요약을 다시 실행하세요."
            )
        else:
            st.caption(
                "GEMINI_API_KEY가 없어 LLM 호출 없이 정제 로그 집계로 요약했습니다. "
                "backend/.env에 키를 넣으면 지정 기간 포함 로그를 Gemini에 전달합니다."
            )
    st.write("요약 근거 로그")
    render_evidence_table(evidence_items)
    return evidence_items


def split_summary_sections(summary_text):
    if not summary_text:
        return {
            "현황": "판단할 데이터 부족",
            "문제·이상 징후": "판단할 데이터 부족",
            "확인할 조치": "판단할 데이터 부족",
        }

    sections = {
        "현황": "",
        "문제·이상 징후": "",
        "확인할 조치": "",
    }
    current_name = "현황"
    for line in summary_text.splitlines():
        stripped_line = line.strip()
        for section_name in sections:
            if stripped_line.startswith(section_name):
                current_name = section_name
                remainder = stripped_line[len(section_name):].lstrip(" ::-")
                if remainder:
                    sections[current_name] += remainder + "\n"
                stripped_line = ""
                break
        if stripped_line:
            sections[current_name] += stripped_line + "\n"

    for section_name, section_text in sections.items():
        cleaned_text = section_text.strip()
        sections[section_name] = cleaned_text or summary_text.strip()
    return sections


def create_cleaning_run(query):
    return post_json(
        "/admin/log-cleaning-runs",
        json_body={
            "period_start": format_datetime(query["period_start"]),
            "period_end": format_datetime(query["period_end"]),
        },
        access_token=get_access_token(),
        idempotency_key=str(uuid4()),
    )


def create_log_summary(query, cleaning_run_id):
    return post_json(
        "/admin/log-summaries",
        json_body={
            "period_start": format_datetime(query["period_start"]),
            "period_end": format_datetime(query["period_end"]),
            "cleaning_run_id": cleaning_run_id,
            "filters": build_log_filters(query),
        },
        access_token=get_access_token(),
        idempotency_key=str(uuid4()),
    )


def cleaning_run_succeeded(cleaning_run_id, cleaning_result):
    return bool(
        (cleaning_run_id or "").strip()
        and cleaning_result
        and cleaning_result.get("ok")
        and (cleaning_result.get("data") or {}).get("status") in (None, "succeeded")
    )


def ensure_succeeded_cleaning_run(query):
    cleaning_run_id = (
        st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_run_id"]) or ""
    ).strip()
    cleaning_result = st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_result"]) or {}
    if cleaning_run_succeeded(cleaning_run_id, cleaning_result):
        return cleaning_run_id, None

    cleaning_result = create_cleaning_run(query)
    st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_result"]] = cleaning_result
    if not cleaning_result.get("ok"):
        return "", cleaning_result.get("error") or {
            "message": "로그 정제가 실패했습니다."
        }

    cleaning_result = poll_cleaning_result(cleaning_result)
    cleaning_data = cleaning_result.get("data") or {}
    created_id = cleaning_data.get("id") or cleaning_data.get("cleaning_run_id")
    cleaning_run_id = str(created_id or "")
    st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_run_id"]] = cleaning_run_id
    st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = True

    status = cleaning_data.get("status")
    if not cleaning_run_id or status == "failed":
        return cleaning_run_id, {"message": "로그 정제가 실패했습니다."}
    if status == "running":
        return cleaning_run_id, {
            "message": "로그 정제가 아직 끝나지 않았습니다. 잠시 후 다시 요약 실행을 눌러 주세요."
        }
    return cleaning_run_id, None


def run_log_summary_like_stats(query):
    cleaning_run_id, error = ensure_succeeded_cleaning_run(query)
    if error:
        return {"ok": False, "error": error}
    summary_result = create_log_summary(query, cleaning_run_id)
    st.session_state[ADMIN_ANALYTICS_KEYS["summary_result"]] = summary_result
    st.session_state[ADMIN_ANALYTICS_KEYS["summary_panel_view"]] = "summary"
    return summary_result


def get_log_summary(summary_id):
    return get_json(
        f"/admin/log-summaries/{summary_id}",
        access_token=get_access_token(),
    )


def get_cleaning_run(run_id):
    return get_json(
        f"/admin/log-cleaning-runs/{run_id}",
        access_token=get_access_token(),
    )


def get_api_log_detail(api_log_id):
    return get_json(
        f"/admin/api-logs/{api_log_id}",
        access_token=get_access_token(),
    )


def get_current_summary_id():
    summary_result = st.session_state.get(ADMIN_ANALYTICS_KEYS["summary_result"]) or {}
    if not summary_result.get("ok"):
        return ""
    summary_data = summary_result.get("data") or {}
    return str(
        summary_data.get("summary_id") or summary_data.get("id") or ""
    ).strip()


def create_evaluation_run(summary_id, run_type="baseline", experiment_id=None):
    body = {
        "summary_id": summary_id,
        "run_type": run_type,
    }
    if experiment_id:
        body["experiment_id"] = experiment_id
    return post_json(
        "/admin/summary-evaluation-runs",
        json_body=body,
        access_token=get_access_token(),
        idempotency_key=str(uuid4()),
        timeout=120.0,
    )


def create_improvement_experiment():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return post_json(
        "/admin/improvement-experiments",
        json_body={
            "name": f"error-code-in-summary-{stamp}",
            "hypothesis": "요약 현황에 포함 로그·에러·응답시간이 빠지면 완전성 점수가 낮다.",
            "change_description": "v2는 모델은 그대로 두고, 현황에 포함 로그·에러·응답시간 집계 한 줄을 후처리로 넣는다.",
            "before_version": "v1",
            "after_version": "v2",
        },
        access_token=get_access_token(),
        idempotency_key=str(uuid4()),
    )


def get_improvement_experiment(experiment_id):
    return get_json(
        f"/admin/improvement-experiments/{experiment_id}",
        access_token=get_access_token(),
    )


def render_evidence_table(evidence_items):
    if not evidence_items:
        render_empty_state(
            "근거 로그가 없어 요약 주장을 사실로 표시하지 않습니다.",
            next_action="판단할 데이터 부족으로 둡니다.",
        )
        return

    evidence_rows = []
    for item in evidence_items:
        evidence_rows.append(
            {
                "로그 ID": item.get("api_log_id"),
                "발생 시각": item.get("occurred_at"),
                "Method": item.get("http_method"),
                "엔드포인트": item.get("endpoint"),
                "상태": item.get("status_code"),
                "응답시간(ms)": item.get("response_time_ms"),
                "에러 코드": item.get("error_code") or "-",
                "연결 주장": item.get("claim_text") or "-",
            }
        )
    selected = st.dataframe(
        pd.DataFrame(evidence_rows),
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="admin_analytics_evidence_table",
        column_config={
            "응답시간(ms)": st.column_config.NumberColumn(
                "응답시간(ms)",
                format="%d",
            ),
        },
    )
    selected_rows = selected.selection.rows if selected and selected.selection else []
    if selected_rows:
        selected_evidence = evidence_rows[selected_rows[0]]
        st.session_state[ADMIN_ANALYTICS_KEYS["selected_log_id"]] = selected_evidence[
            "로그 ID"
        ]
        claim_text = selected_evidence.get("연결 주장")
        st.session_state[ADMIN_ANALYTICS_KEYS["selected_claim_text"]] = (
            None if claim_text in (None, "-") else claim_text
        )


def render_summary_panel(query):
    current_cleaning_run_id = (
        st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_run_id"]) or ""
    ).strip()
    cleaning_result = st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_result"]) or {}
    cleaning_succeeded = cleaning_run_succeeded(
        current_cleaning_run_id, cleaning_result
    )

    with render_toolbar_row():
        render_section_title(
            "LLM 로그 요약",
            "정제 실행은 정제 결과만, 요약 실행은 요약과 근거 로그만 전체 너비로 표시합니다.",
        )
        with st.container(
            horizontal=True,
            vertical_alignment="center",
            gap="small",
            wrap=False,
            width="content",
        ):
            with st.form("admin_analytics_cleaning_form", border=False):
                cleaning_clicked = st.form_submit_button(
                    "정제 실행",
                    type="primary",
                    width="content",
                )
            with st.form("admin_analytics_summary_form", border=False):
                summary_clicked = st.form_submit_button(
                    "요약 실행",
                    width="content",
                    disabled=not cleaning_succeeded,
                )

    if cleaning_clicked:
        with st.spinner("로그를 정제하고 있습니다."):
            cleaning_result = create_cleaning_run(query)
        st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_result"]] = cleaning_result
        st.session_state[ADMIN_ANALYTICS_KEYS["summary_panel_view"]] = "cleaning"
        if cleaning_result.get("ok"):
            cleaning_data = cleaning_result.get("data") or {}
            created_id = (
                cleaning_data.get("id")
                or cleaning_data.get("cleaning_run_id")
            )
            st.session_state[ADMIN_ANALYTICS_KEYS["cleaning_run_id"]] = str(
                created_id or current_cleaning_run_id
            )
            st.session_state[ADMIN_ANALYTICS_KEYS["needs_fetch"]] = True
        st.rerun()

    if summary_clicked:
        if not current_cleaning_run_id:
            render_error_state(
                "요약을 실행하려면 먼저 정제를 실행해 주세요.",
                next_action="주황색 정제 실행을 먼저 누릅니다.",
            )
        else:
            with st.spinner("로그 요약을 실행하고 있습니다."):
                summary_result = create_log_summary(query, current_cleaning_run_id)
            st.session_state[ADMIN_ANALYTICS_KEYS["summary_result"]] = summary_result
            st.session_state[ADMIN_ANALYTICS_KEYS["summary_panel_view"]] = "summary"
            st.rerun()

    cleaning_result = poll_cleaning_result(
        st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_result"])
    )
    summary_result = poll_summary_result(
        st.session_state.get(ADMIN_ANALYTICS_KEYS["summary_result"])
    )
    panel_view = st.session_state.get(ADMIN_ANALYTICS_KEYS["summary_panel_view"])
    if panel_view is None:
        if summary_result is not None:
            panel_view = "summary"
        elif cleaning_result:
            panel_view = "cleaning"
    evidence_items = None

    with st.container(border=True):
        if panel_view == "cleaning":
            render_cleaning_report_column(cleaning_result)
        elif panel_view == "summary":
            evidence_items = render_summary_report_column(summary_result)
        else:
            render_empty_state(
                "아직 정제를 실행하지 않았습니다.",
                next_action="정제 실행을 누르면 정제 결과만 보입니다. 이어서 요약 실행을 누르면 요약과 근거 로그만 보입니다.",
            )

    result = st.session_state.get(ADMIN_ANALYTICS_KEYS["result"]) or {}
    log_items, _total_count = list_api_log_items(
        (result.get("logs") or {}).get("data")
    )
    if panel_view == "summary" and evidence_items:
        render_log_detail(log_items)


def get_run_score_averages(runs, run_type):
    totals = []
    facts = []
    for run in runs:
        if run.get("run_type") != run_type:
            continue
        totals.append(float(run.get("total_score") or 0))
        facts.append(float(run.get("factuality_score") or 0))
    if not totals:
        return None
    return {
        "total": round(sum(totals) / len(totals), 2),
        "factuality": round(sum(facts) / len(facts), 2),
    }


def render_experiment_change_explanation(experiment_data):
    before_version = experiment_data.get("before_version") or "v1"
    after_version = experiment_data.get("after_version") or "v2"
    hypothesis = experiment_data.get("hypothesis") or ""
    change_description = experiment_data.get("change_description") or ""
    st.write("어떻게 바꿨는지")
    if hypothesis:
        st.write(hypothesis)
    if change_description:
        st.write(change_description)
    st.caption(f"버전: {before_version} → {after_version}")

    runs = experiment_data.get("runs") or []
    before = get_run_score_averages(runs, "before")
    after = get_run_score_averages(runs, "after")
    st.write("어떻게 개선되었는지")
    if not before or not after:
        st.caption("같은 사례의 전후 점수가 아직 없습니다. 개선실험이 끝나면 여기에 표시합니다.")
        return
    delta = round(after["total"] - before["total"], 2)
    improved = delta >= 5 and after["factuality"] >= before["factuality"]
    st.write(
        f"{before_version} 총점 평균 {before['total']}점, "
        f"{after_version} {after['total']}점입니다. 차이는 {delta}점입니다. "
        f"사실 일치도는 {before['factuality']}점에서 {after['factuality']}점입니다."
    )
    if improved:
        st.write("총점이 5점 이상 오르고 사실 일치도가 떨어지지 않아 성공 기준을 충족합니다.")
    else:
        st.write("성공 기준(총점 +5·사실 미하락)을 충족하지 못했습니다. 결과를 성공으로 과장하지 않습니다.")


def render_evaluation_result_column(evaluation_result, summary_id):
    st.subheader("품질평가 결과")
    if not summary_id:
        render_error_state(
            "품질평가를 실행하려면 먼저 요약을 실행해 주세요.",
            next_action="요약 실행을 먼저 누릅니다.",
        )
        return
    if evaluation_result is None:
        render_empty_state(
            "아직 품질평가를 실행하지 않았습니다.",
            next_action="품질평가를 누르면 이 결과만 보입니다.",
        )
        return
    if not evaluation_result.get("ok"):
        error_body = evaluation_result.get("error") or {}
        render_error_state(
            error_body.get("message") or "품질평가에 실패했습니다.",
            request_id=error_body.get("request_id"),
        )
        return

    evaluation_data = evaluation_result.get("data") or {}
    factuality = float(evaluation_data.get("factuality_score") or 0)
    completeness = float(evaluation_data.get("completeness_score") or 0)
    total_score = float(evaluation_data.get("total_score") or 0)
    passed = total_score >= 80 and factuality >= 80
    st.write("점수 측정 결과")
    st.write(
        {
            "run_type": evaluation_data.get("run_type"),
            "factuality_score": factuality,
            "completeness_score": completeness,
            "total_score": total_score,
            "notes": evaluation_data.get("notes"),
        }
    )
    st.write(
        "factuality_score(사실 일치)는 금지 사실이나 근거 없는 단정이 없으면 높고, "
        "있으면 그 항목은 0점입니다. completeness_score(완전성)는 기대 사실이 요약 문에 "
        "얼마나 나왔는지입니다. 총점은 사실 60% + 완전 30% + 근거 연결 10%입니다."
    )
    st.caption(
        f"{'합격' if passed else '불합격'} (총점 80 이상이고 사실 일치 80 이상). "
        "notes에는 활성 사례 몇 건을 채점했는지, 기대 사실 확인 건수, 전후 비교가 있습니다."
    )


def render_experiment_result_column(experiment_result, summary_id):
    st.subheader("개선실험 결과")
    if not summary_id:
        render_error_state(
            "개선실험을 실행하려면 먼저 요약을 실행해 주세요.",
            next_action="요약 실행을 먼저 누릅니다.",
        )
        return
    if experiment_result is None:
        render_empty_state(
            "아직 개선실험을 실행하지 않았습니다.",
            next_action="개선실험을 누르면 이 결과만 보입니다.",
        )
        return
    if not experiment_result.get("ok"):
        error_body = experiment_result.get("error") or {}
        render_error_state(
            error_body.get("message") or "개선실험 저장에 실패했습니다.",
            request_id=error_body.get("request_id"),
        )
        return

    experiment_data = experiment_result.get("data") or {}
    experiment_id = experiment_data.get("id")
    if experiment_id:
        polled = get_improvement_experiment(experiment_id)
        if polled.get("ok"):
            experiment_data = polled.get("data") or experiment_data
            st.session_state[ADMIN_ANALYTICS_KEYS["experiment_result"]] = polled
    render_experiment_change_explanation(experiment_data)
    runs = experiment_data.get("runs") or []
    if runs:
        st.dataframe(pd.DataFrame(runs), hide_index=True)


def render_evaluation_panel(query=None):
    query = query or st.session_state.get(ADMIN_ANALYTICS_KEYS["applied_query"])
    current_cleaning_run_id = (
        st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_run_id"]) or ""
    ).strip()
    cleaning_result = st.session_state.get(ADMIN_ANALYTICS_KEYS["cleaning_result"]) or {}
    cleaning_succeeded = cleaning_run_succeeded(
        current_cleaning_run_id, cleaning_result
    )
    summary_id = get_current_summary_id()

    with render_toolbar_row():
        render_section_title(
            "요약품질평가",
            "요약 실행·품질평가·개선실험은 한 번에 한 결과만 전체 너비로 표시합니다.",
        )
        with st.container(
            horizontal=True,
            vertical_alignment="center",
            gap="small",
            wrap=False,
            width="content",
        ):
            summary_clicked = st.button(
                "요약 실행",
                type="primary",
                width="content",
                key="admin_eval_summary_button",
            )
            evaluation_clicked = st.button(
                "품질평가",
                width="content",
                key="admin_analytics_evaluation_button",
            )
            experiment_clicked = st.button(
                "개선실험",
                width="content",
                key="admin_analytics_experiment_button",
            )

    if summary_clicked:
        st.session_state[ADMIN_ANALYTICS_KEYS["eval_panel_view"]] = "summary"
        if not query:
            render_error_state(
                "요약을 실행하려면 조회 기간이 필요합니다.",
                next_action="통계분석 및 요약에서 기간을 적용한 뒤 다시 눌러 주세요.",
            )
        else:
            spinner_text = (
                "로그 요약을 실행하고 있습니다."
                if cleaning_succeeded
                else "로그를 정제한 뒤 요약을 실행하고 있습니다."
            )
            with st.spinner(spinner_text):
                summary_result = run_log_summary_like_stats(query)
            st.session_state[ADMIN_ANALYTICS_KEYS["summary_result"]] = summary_result
            st.session_state[ADMIN_ANALYTICS_KEYS["summary_panel_view"]] = "summary"
            st.rerun()

    poll_summary_result(
        st.session_state.get(ADMIN_ANALYTICS_KEYS["summary_result"])
    )
    summary_id = get_current_summary_id()

    if evaluation_clicked:
        st.session_state[ADMIN_ANALYTICS_KEYS["eval_panel_view"]] = "evaluation"
        if summary_id:
            with st.spinner("품질평가를 실행하고 있습니다."):
                evaluation_result = create_evaluation_run(
                    summary_id,
                    run_type="baseline",
                )
            st.session_state[ADMIN_ANALYTICS_KEYS["evaluation_result"]] = (
                evaluation_result
            )
            st.rerun()

    if experiment_clicked:
        st.session_state[ADMIN_ANALYTICS_KEYS["eval_panel_view"]] = "experiment"
        if summary_id:
            with st.spinner("개선실험을 저장하고 전후 평가를 실행하고 있습니다."):
                created = create_improvement_experiment()
                st.session_state[ADMIN_ANALYTICS_KEYS["experiment_result"]] = created
                if created.get("ok"):
                    experiment_id = (created.get("data") or {}).get("id")
                    before_result = create_evaluation_run(
                        summary_id,
                        run_type="before",
                        experiment_id=experiment_id,
                    )
                    if before_result.get("ok"):
                        evaluation_result = create_evaluation_run(
                            summary_id,
                            run_type="after",
                            experiment_id=experiment_id,
                        )
                    else:
                        evaluation_result = before_result
                    st.session_state[ADMIN_ANALYTICS_KEYS["evaluation_result"]] = (
                        evaluation_result
                    )
            st.rerun()

    summary_result = st.session_state.get(ADMIN_ANALYTICS_KEYS["summary_result"])
    evaluation_result = st.session_state.get(
        ADMIN_ANALYTICS_KEYS["evaluation_result"]
    )
    experiment_result = st.session_state.get(
        ADMIN_ANALYTICS_KEYS["experiment_result"]
    )
    panel_view = st.session_state.get(ADMIN_ANALYTICS_KEYS["eval_panel_view"])
    if panel_view is None:
        if summary_result is not None:
            panel_view = "summary"

    with st.container(border=True):
        if panel_view == "summary":
            render_summary_report_column(summary_result)
        elif panel_view == "evaluation":
            render_evaluation_result_column(evaluation_result, summary_id)
        elif panel_view == "experiment":
            render_experiment_result_column(experiment_result, summary_id)
        else:
            render_empty_state(
                "아직 요약을 실행하지 않았습니다.",
                next_action="요약 실행을 누르면 요약만 보입니다. 품질평가·개선실험도 각각 그 결과만 보입니다.",
            )


def render_log_table(log_items, total_count, export_df=None):
    caption = f"전체 {total_count}건, 기본 정렬 occurred_at DESC"
    with render_toolbar_row():
        render_section_title("최근 요청 로그", caption)
        with st.container(
            horizontal=True,
            vertical_alignment="center",
            gap="small",
            wrap=False,
            width="content",
        ):
            refresh_clicked = st.button(
                "새로고침",
                width="content",
                key="admin_logs_table_refresh",
            )
            if export_df is not None:
                render_download_button(
                    "전체 로그 내려받기",
                    export_df,
                    "playeat_request_logs.csv",
                    "admin_logs_download",
                    width="content",
                )
    if refresh_clicked:
        handle_refresh()
        st.rerun()

    if not log_items:
        render_empty_state("조건에 맞는 원본 로그가 없습니다.")
        return

    table_rows = []
    for item in log_items:
        profile_id = item.get("profile_id")
        table_rows.append(
            {
                "로그 ID": item.get("id") or item.get("api_log_id"),
                "발생 시각": item.get("occurred_at"),
                "Method": item.get("http_method"),
                "엔드포인트": item.get("endpoint") or item.get("endpoint_path"),
                "상태": item.get("status_code"),
                "응답시간(ms)": item.get("response_time_ms"),
                "사용자 식별": "식별" if profile_id else "미식별",
                "에러 코드": item.get("error_code") or "-",
            }
        )

    log_df = pd.DataFrame(table_rows)
    selected = st.dataframe(
        log_df,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="admin_analytics_log_table",
        column_config={
            "로그 ID": None,
            "응답시간(ms)": st.column_config.NumberColumn(
                "응답시간(ms)",
                format="%d",
            ),
        },
    )

    selected_rows = selected.selection.rows if selected and selected.selection else []
    if selected_rows:
        selected_index = selected_rows[0]
        selected_log_id = table_rows[selected_index]["로그 ID"]
        st.session_state[ADMIN_ANALYTICS_KEYS["selected_log_id"]] = selected_log_id
        st.session_state[ADMIN_ANALYTICS_KEYS["selected_claim_text"]] = None


def render_log_detail(log_items):
    selected_log_id = st.session_state.get(ADMIN_ANALYTICS_KEYS["selected_log_id"])
    if not selected_log_id:
        st.caption("로그 행이나 요약 근거를 선택하면 상세를 표시합니다.")
        return

    detail_result = get_api_log_detail(selected_log_id)
    detail_error = None
    selected_item = None
    if detail_result.get("ok"):
        selected_item = detail_result.get("data")
    else:
        detail_error = detail_result.get("error") or {}

    with st.container(border=True):
        st.subheader("로그 상세")
        if detail_error:
            render_error_state(
                detail_error.get("message") or "선택한 로그 상세를 불러오지 못했습니다.",
                request_id=detail_error.get("request_id"),
            )
            return
        if selected_item is None:
            render_empty_state("선택한 로그 상세를 찾을 수 없습니다.")
            return

        claim_text = st.session_state.get(ADMIN_ANALYTICS_KEYS["selected_claim_text"])
        if claim_text:
            st.caption(f"요약 연결 주장: {claim_text}")

        is_included = selected_item.get("is_included")
        exclusion_reason = selected_item.get("exclusion_reason")
        st.write(
            {
                "api_log_id": selected_item.get("id") or selected_item.get("api_log_id"),
                "request_id": selected_item.get("request_id"),
                "occurred_at": selected_item.get("occurred_at"),
                "http_method": selected_item.get("http_method"),
                "endpoint": selected_item.get("endpoint")
                or selected_item.get("endpoint_path"),
                "normalized_endpoint": selected_item.get("normalized_endpoint"),
                "status_code": selected_item.get("status_code"),
                "response_time_ms": selected_item.get("response_time_ms"),
                "error_code": selected_item.get("error_code"),
                "profile_id": selected_item.get("profile_id"),
                "is_included": is_included,
                "exclusion_reason": exclusion_reason,
            }
        )
        if is_included is False:
            st.caption(
                f"정제에서 제외된 로그입니다. 사유: {exclusion_reason or '-'}"
            )
        elif is_included is True:
            st.caption(
                "정제 결과에 포함된 로그입니다. "
                f"정규화 경로: {selected_item.get('normalized_endpoint') or '-'}"
            )
        else:
            st.caption("이 기간의 정제 결과가 없으면 포함/제외 사유를 표시하지 않습니다.")


def render_recent_summary_preview():
    summary_result = st.session_state.get(ADMIN_ANALYTICS_KEYS["summary_result"])
    if not summary_result or not summary_result.get("ok"):
        return
    summary_data = summary_result.get("data") or {}
    summary_text = summary_data.get("summary_text")
    if not summary_text:
        return
    sections = split_summary_sections(summary_text)
    evidence_items = summary_data.get("evidence") or []
    st.subheader("최근 요약 미리보기")
    st.write(f"현황: {sections['현황']}")
    st.write(f"문제·이상 징후: {sections['문제·이상 징후']}")
    st.caption(
        f"근거 {len(evidence_items)}건 / "
        f"model: {summary_data.get('model_name') or '-'} / "
        f"prompt: {summary_data.get('prompt_version') or '-'}"
    )
    if evidence_items:
        preview_rows = []
        for item in evidence_items[:3]:
            preview_rows.append(
                {
                    "로그 ID": item.get("api_log_id"),
                    "상태": item.get("status_code"),
                    "연결 주장": item.get("claim_text") or "-",
                }
            )
        st.dataframe(pd.DataFrame(preview_rows), hide_index=True)


def render_product_metrics_tab():
    render_empty_state(
        "제품 지표는 API 운영 지표와 같은 화면에 합산하지 않습니다.",
        next_action="제품 통계 API가 연결되면 이 탭에서 별도로 표시합니다.",
    )


def get_error_next_action(error_body):
    error_code = (error_body or {}).get("code")
    status_code = (error_body or {}).get("status")
    if error_code in {"AUTH_REQUIRED", "TOKEN_EXPIRED"} or status_code == 401:
        return "로그인 화면으로 이동해 다시 인증해 주세요."
    if error_code == "ADMIN_REQUIRED" or status_code == 403:
        return "관리자 권한이 있는 계정으로 다시 시도해 주세요."
    return "기존 화면을 성공 결과처럼 바꾸지 않고 다시 조회하세요."


def build_recent_request_rows(log_items):
    rows = []
    for index, item in enumerate(log_items, start=1):
        rows.append(
            {
                "번호": index,
                "요청 시간": item.get("occurred_at") or "-",
                "음식별": item.get("food_category") or "-",
                "가격대": item.get("price_range") or "-",
                "메뉴 특성": item.get("menu_feature") or "-",
                "검색 키워드": item.get("search_keyword")
                or item.get("endpoint")
                or item.get("endpoint_path")
                or "-",
                "사용자 반응": item.get("user_reaction") or "-",
            }
        )
    return rows


def list_search_stats():
    return get_json(
        "/admin/search-stats",
        access_token=get_access_token(),
    )


def refresh_search_stats_if_needed():
    st.session_state[ADMIN_ANALYTICS_KEYS["search_stats"]] = list_search_stats()


def render_search_ratio_summary(search_result):
    render_section_title("검색정보 요약")
    if not search_result:
        food_column, price_column, feature_column = st.columns(3, gap="medium")
        with food_column:
            render_donut_chart("음식별 검색 비율", [])
        with price_column:
            render_donut_chart("가격대별 검색 비율", [])
        with feature_column:
            render_donut_chart("메뉴 특성별 검색 비율", [])
        return

    if not search_result.get("ok"):
        error_body = search_result.get("error") or {}
        render_error_state(
            error_body.get("message") or "검색 통계를 불러오지 못했습니다.",
            request_id=error_body.get("request_id"),
            next_action=get_error_next_action(error_body),
        )
        return

    payload = search_result.get("data") or {}
    food_column, price_column, feature_column = st.columns(3, gap="medium")
    with food_column:
        render_donut_chart("음식별 검색 비율", payload.get("food") or [])
    with price_column:
        render_donut_chart("가격대별 검색 비율", payload.get("price") or [])
    with feature_column:
        render_donut_chart("메뉴 특성별 검색 비율", payload.get("feature") or [])


def render_recent_request_logs(log_result):
    empty_columns = [
        "번호",
        "요청 시간",
        "음식별",
        "가격대",
        "메뉴 특성",
        "검색 키워드",
        "사용자 반응",
    ]
    log_items, _total_count = list_api_log_items(
        log_result.get("data") if log_result.get("ok") else None
    )
    log_df = (
        pd.DataFrame(build_recent_request_rows(log_items))
        if log_result.get("ok")
        else pd.DataFrame(columns=empty_columns)
    )
    export_df = log_df if not log_df.empty else pd.DataFrame(columns=empty_columns)

    with render_toolbar_row():
        render_section_title(
            "최근 요청 로그",
            "원본 API 로그의 시각·엔드포인트를 표시합니다. 음식·가격·반응 컬럼은 해당 필드가 없으면 비웁니다.",
        )
        render_download_button(
            "전체 로그 내려받기",
            export_df,
            "playeat_request_logs.csv",
            "admin_analytics_log_download",
            width="content",
        )

    if not log_result.get("ok"):
        error_body = log_result.get("error") or {}
        render_error_state(
            error_body.get("message") or "요청 로그를 불러오지 못했습니다.",
            request_id=error_body.get("request_id"),
            next_action=get_error_next_action(error_body),
        )
        return
    if log_df.empty:
        render_empty_state("조건에 맞는 요청 로그가 없습니다.")
        return
    st.dataframe(log_df, hide_index=True)


def render_admin_analytics():
    initialize_admin_analytics_state()
    refresh_search_stats_if_needed()
    refresh_admin_analytics_if_needed()
    render_search_ratio_summary(
        st.session_state.get(ADMIN_ANALYTICS_KEYS["search_stats"])
    )
    result = st.session_state.get(ADMIN_ANALYTICS_KEYS["result"])
    if result is None:
        render_loading_state("처음 조회를 준비하고 있습니다.")
        return
    render_recent_request_logs(result.get("logs") or {})


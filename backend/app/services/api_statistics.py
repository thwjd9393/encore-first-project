from app.db import supabase
from app.schemas.api_log import MetricPoint
from app.services.log_cleaning import (
    calculate_p95,
    is_error_status,
    normalize_endpoint,
)

STATUS_CLASS_RANGES = {
    "2xx": (200, 299),
    "4xx": (400, 499),
    "5xx": (500, 599),
}


def calculate_error_rate(error_count, request_count):
    if not request_count:
        return None
    return error_count / request_count


def get_status_class_range(status_class):
    return STATUS_CLASS_RANGES.get(status_class)


def matches_status_filter(row_status, status_code=None, status_class=None, error_only=False):
    try:
        code = int(row_status)
    except (TypeError, ValueError):
        return False
    if status_code is not None:
        return code == int(status_code)
    status_range = get_status_class_range(status_class)
    if status_range:
        return status_range[0] <= code <= status_range[1]
    if error_only:
        return is_error_status(code)
    return True


def apply_status_query_filters(query, status_code=None, status_class=None, error_only=False):
    if status_code is not None:
        return query.eq("status_code", int(status_code))
    status_range = get_status_class_range(status_class)
    if status_range:
        return query.gte("status_code", status_range[0]).lte(
            "status_code", status_range[1]
        )
    if error_only:
        return query.gte("status_code", 400)
    return query


def filter_log_row(
    row,
    endpoint,
    http_method,
    status_code,
    error_only,
    status_class=None,
):
    path = row.get("endpoint_path") or ""
    normalized = row.get("normalized_endpoint") or normalize_endpoint(path)
    if endpoint:
        if endpoint not in (path, normalized) and not path.startswith(endpoint):
            return False
    if http_method and row.get("http_method") != http_method:
        return False
    if not matches_status_filter(
        row.get("status_code"),
        status_code=status_code,
        status_class=status_class,
        error_only=error_only,
    ):
        return False
    return True


def build_metric_points(rows, endpoint_key="endpoint"):
    grouped = {}
    for row in rows:
        endpoint = row.get(endpoint_key) or normalize_endpoint(row.get("endpoint_path"))
        http_method = row.get("http_method")
        grouped.setdefault((endpoint, http_method), []).append(row)

    points = []
    for (endpoint, http_method), items in sorted(grouped.items()):
        times = [int(item["response_time_ms"]) for item in items]
        request_count = len(items)
        error_count = sum(
            1 for item in items if is_error_status(item.get("status_code"))
        )
        points.append(
            MetricPoint(
                endpoint=endpoint,
                http_method=http_method,
                request_count=request_count,
                error_count=error_count,
                error_rate=calculate_error_rate(error_count, request_count),
                avg_response_time_ms=round(sum(times) / request_count, 2)
                if request_count
                else None,
                p95_response_time_ms=calculate_p95(times),
            )
        )
    return points


def list_statistics_from_cleaning_run(
    cleaning_run_id,
    endpoint=None,
    http_method=None,
    status_code=None,
    error_only=False,
):
    result = (
        supabase.table("api_statistics")
        .select(
            "endpoint, http_method, request_count, error_count, "
            "avg_response_time_ms, p95_response_time_ms"
        )
        .eq("cleaning_run_id", str(cleaning_run_id))
        .execute()
    )
    points = []
    for row in result.data or []:
        if endpoint and row.get("endpoint") != endpoint:
            continue
        if http_method and row.get("http_method") != http_method:
            continue
        request_count = int(row.get("request_count") or 0)
        error_count = int(row.get("error_count") or 0)
        if error_only and error_count == 0:
            continue
        if status_code is not None:
            continue
        points.append(
            MetricPoint(
                endpoint=row["endpoint"],
                http_method=row["http_method"],
                request_count=request_count,
                error_count=error_count,
                error_rate=calculate_error_rate(error_count, request_count),
                avg_response_time_ms=float(row["avg_response_time_ms"])
                if row.get("avg_response_time_ms") is not None
                else None,
                p95_response_time_ms=float(row["p95_response_time_ms"])
                if row.get("p95_response_time_ms") is not None
                else None,
            )
        )
    return points


def list_statistics_from_raw_logs(
    period_start,
    period_end,
    endpoint=None,
    http_method=None,
    status_code=None,
    error_only=False,
    status_class=None,
):
    query = (
        supabase.table("api_request_logs")
        .select("endpoint_path, http_method, status_code, response_time_ms")
        .gte("occurred_at", period_start.isoformat())
        .lte("occurred_at", period_end.isoformat())
    )
    if http_method:
        query = query.eq("http_method", http_method)
    query = apply_status_query_filters(
        query,
        status_code=status_code,
        status_class=status_class,
        error_only=error_only,
    )
    result = query.execute()
    rows = []
    for row in result.data or []:
        normalized = normalize_endpoint(row.get("endpoint_path"))
        row["normalized_endpoint"] = normalized
        if not filter_log_row(
            row,
            endpoint,
            http_method,
            status_code,
            error_only,
            status_class=status_class,
        ):
            continue
        rows.append(row)
    return build_metric_points(rows, endpoint_key="normalized_endpoint")

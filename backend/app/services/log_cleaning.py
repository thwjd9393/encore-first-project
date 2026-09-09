import math
import re
from collections import defaultdict

from app.db import supabase
from app.schemas.common import utc_now

CLEANING_CRITERIA_VERSION = "v1"
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
TEST_ENDPOINTS = {"/health", "/docs", "/openapi.json", "/redoc"}


def normalize_endpoint(endpoint_path):
    path = (endpoint_path or "").split("?", 1)[0].strip()
    if not path:
        return path
    return UUID_PATTERN.sub("{id}", path)


def normalize_error_code(error_code):
    if error_code is None:
        return None
    cleaned = str(error_code).strip()
    return cleaned or None


def is_error_status(status_code):
    try:
        return int(status_code) >= 400
    except (TypeError, ValueError):
        return False


def calculate_p95(values):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])


def classify_log_row(row, seen_keys):
    http_method = row.get("http_method")
    endpoint_path = row.get("endpoint_path")
    status_code = row.get("status_code")
    response_time_ms = row.get("response_time_ms")
    request_id = row.get("request_id")
    client_type = (row.get("client_type") or "").strip().lower()
    normalized_endpoint = normalize_endpoint(endpoint_path)
    normalized_error_code = normalize_error_code(row.get("error_code"))

    if not request_id or not http_method or not endpoint_path:
        return False, normalized_endpoint, normalized_error_code, "MISSING_FIELD"
    if status_code is None or response_time_ms is None:
        return False, normalized_endpoint, normalized_error_code, "MISSING_FIELD"
    if client_type == "test" or endpoint_path in TEST_ENDPOINTS:
        return False, normalized_endpoint, normalized_error_code, "TEST_TRAFFIC"

    duplicate_key = (
        http_method,
        normalized_endpoint,
        str(row.get("occurred_at") or ""),
        str(status_code),
        str(row.get("profile_id") or ""),
    )
    if duplicate_key in seen_keys:
        return False, normalized_endpoint, normalized_error_code, "DUPLICATE"
    seen_keys.add(duplicate_key)
    return True, normalized_endpoint, normalized_error_code, None


def list_logs_in_period(period_start, period_end):
    result = (
        supabase.table("api_request_logs")
        .select(
            "id, request_id, profile_id, occurred_at, http_method, "
            "endpoint_path, status_code, response_time_ms, error_code, "
            "client_type, created_at"
        )
        .gte("occurred_at", period_start.isoformat())
        .lte("occurred_at", period_end.isoformat())
        .order("occurred_at")
        .execute()
    )
    return result.data or []


def create_cleaning_run(period_start, period_end, criteria_version=None):
    version = criteria_version or CLEANING_CRITERIA_VERSION
    created = (
        supabase.table("log_cleaning_runs")
        .insert(
            {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "criteria_version": version,
                "status": "running",
            }
        )
        .execute()
    )
    run = (created.data or [None])[0]
    if not run:
        raise RuntimeError("정제 실행을 생성하지 못했습니다.")

    source_rows = []
    try:
        source_rows = list_logs_in_period(period_start, period_end)
        seen_keys = set()
        result_rows = []
        included_logs = []
        for row in source_rows:
            is_included, normalized_endpoint, normalized_error_code, reason = (
                classify_log_row(row, seen_keys)
            )
            result_rows.append(
                {
                    "cleaning_run_id": run["id"],
                    "api_log_id": row["id"],
                    "is_included": is_included,
                    "normalized_endpoint": normalized_endpoint or None,
                    "normalized_error_code": normalized_error_code,
                    "exclusion_reason": reason,
                }
            )
            if is_included:
                included_logs.append(
                    {
                        **row,
                        "normalized_endpoint": normalized_endpoint,
                    }
                )

        if result_rows:
            supabase.table("log_cleaning_results").insert(result_rows).execute()

        statistic_rows = build_statistic_rows(
            run["id"],
            period_start,
            period_end,
            included_logs,
        )
        if statistic_rows:
            supabase.table("api_statistics").insert(statistic_rows).execute()

        updated = (
            supabase.table("log_cleaning_runs")
            .update(
                {
                    "status": "succeeded",
                    "source_count": len(source_rows),
                    "included_count": len(included_logs),
                    "excluded_count": len(source_rows) - len(included_logs),
                    "completed_at": utc_now().isoformat(),
                }
            )
            .eq("id", run["id"])
            .execute()
        )
        return (updated.data or [run])[0], included_logs
    except Exception:
        mark_cleaning_run_failed(run["id"], len(source_rows))
        raise


def mark_cleaning_run_failed(run_id, source_count=0):
    supabase.table("log_cleaning_runs").update(
        {
            "status": "failed",
            "source_count": source_count,
            "included_count": 0,
            "excluded_count": 0,
            "completed_at": utc_now().isoformat(),
        }
    ).eq("id", run_id).execute()


def build_statistic_rows(cleaning_run_id, period_start, period_end, included_logs):
    grouped = defaultdict(list)
    for row in included_logs:
        endpoint = row.get("normalized_endpoint") or normalize_endpoint(
            row.get("endpoint_path")
        )
        http_method = row.get("http_method")
        grouped[(endpoint, http_method)].append(row)

    statistic_rows = []
    for (endpoint, http_method), rows in grouped.items():
        times = [int(item["response_time_ms"]) for item in rows]
        error_count = sum(
            1 for item in rows if is_error_status(item.get("status_code"))
        )
        request_count = len(rows)
        statistic_rows.append(
            {
                "cleaning_run_id": cleaning_run_id,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "endpoint": endpoint,
                "http_method": http_method,
                "request_count": request_count,
                "error_count": error_count,
                "avg_response_time_ms": round(sum(times) / request_count, 2)
                if request_count
                else None,
                "p95_response_time_ms": calculate_p95(times),
            }
        )
    return statistic_rows

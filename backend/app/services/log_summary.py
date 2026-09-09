import os
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.db import supabase
from app.schemas.api_log import EvidenceLog, LogFilters, LogSummaryResponse
from app.schemas.common import utc_now
from app.services.api_statistics import list_statistics_from_cleaning_run
from app.services.log_cleaning import is_error_status, normalize_endpoint

SUMMARY_PROMPT_VERSION = "v1"
FALLBACK_MODEL_NAME = "db_stats_v1"
DEFAULT_GEMINI_MODEL_NAME = "gemini-3.5-flash-lite"
GEMINI_TIMEOUT_SECONDS = 30.0
LLM_LOG_ROW_LIMIT = 40
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_gemini_settings():
    load_dotenv(ENV_PATH, override=True)
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    model_name = (os.getenv("GEMINI_MODEL_NAME") or DEFAULT_GEMINI_MODEL_NAME).strip()
    return api_key or None, model_name or DEFAULT_GEMINI_MODEL_NAME


def get_system_profile_id():
    admin_result = (
        supabase.table("profiles")
        .select("id")
        .eq("profile_type", "0")
        .limit(1)
        .execute()
    )
    if admin_result.data:
        return admin_result.data[0]["id"]
    any_result = supabase.table("profiles").select("id").limit(1).execute()
    if any_result.data:
        return any_result.data[0]["id"]
    return None


def list_included_logs(cleaning_run_id):
    results = (
        supabase.table("log_cleaning_results")
        .select("api_log_id, normalized_endpoint")
        .eq("cleaning_run_id", str(cleaning_run_id))
        .eq("is_included", True)
        .execute()
    )
    included = results.data or []
    if not included:
        return []
    log_ids = [row["api_log_id"] for row in included]
    logs = (
        supabase.table("api_request_logs")
        .select(
            "id, occurred_at, http_method, endpoint_path, status_code, "
            "response_time_ms, error_code"
        )
        .in_("id", log_ids)
        .order("occurred_at", desc=True)
        .execute()
    )
    normalized_by_id = {
        row["api_log_id"]: row.get("normalized_endpoint") for row in included
    }
    rows = []
    for row in logs.data or []:
        row["normalized_endpoint"] = normalized_by_id.get(row["id"]) or normalize_endpoint(
            row.get("endpoint_path")
        )
        rows.append(row)
    return rows


def build_fact_summary(included_logs, points):
    total_count = len(included_logs)
    error_logs = [
        row for row in included_logs if is_error_status(row.get("status_code"))
    ]
    error_count = len(error_logs)
    times = [int(row["response_time_ms"]) for row in included_logs]
    average_ms = round(sum(times) / total_count, 1) if times else None
    error_codes = Counter(
        str(row.get("error_code") or row.get("status_code"))
        for row in error_logs
    )
    top_endpoints = Counter(
        row.get("normalized_endpoint") or row.get("endpoint_path")
        for row in included_logs
    )

    if total_count == 0:
        return (
            "현황: 판단할 데이터 부족\n"
            "문제·이상 징후: 판단할 데이터 부족\n"
            "확인할 조치: 판단할 데이터 부족"
        )

    top_endpoint_text = ", ".join(
        f"{name} {count}건" for name, count in top_endpoints.most_common(3)
    )
    error_code_text = ", ".join(
        f"{name} {count}건" for name, count in error_codes.most_common(5)
    ) or "없음"
    slowest = max(points, key=lambda item: item.p95_response_time_ms or 0, default=None)

    problem_line = (
        f"에러 {error_count}건, 에러 코드 {error_code_text}."
        if error_count
        else "선택한 정제 결과에 4xx·5xx 로그가 없습니다."
    )
    if slowest and (slowest.p95_response_time_ms or 0) > 0:
        problem_line += (
            f" p95가 가장 큰 엔드포인트는 {slowest.endpoint} "
            f"({slowest.p95_response_time_ms:.0f} ms)입니다."
        )

    action_line = (
        "에러 코드와 느린 엔드포인트의 원본 로그를 상세에서 확인합니다."
        if error_count
        else "포함 로그 건수와 사용량 통계를 기준으로 추이를 확인합니다."
    )
    return (
        f"현황: 포함 로그 {total_count}건, 에러 {error_count}건"
        f"{f', 평균 응답시간 {average_ms} ms' if average_ms is not None else ''}"
        f". 사용량 상위 엔드포인트는 {top_endpoint_text or '없음'}입니다.\n"
        f"문제·이상 징후: {problem_line}\n"
        f"확인할 조치: {action_line}"
    )


def select_evidence_logs(included_logs):
    if not included_logs:
        return []
    selected = []
    seen_ids = set()

    def add_row(row, claim_text):
        log_id = row["id"]
        if log_id in seen_ids:
            return
        seen_ids.add(log_id)
        selected.append((row, claim_text))

    error_logs = [
        row for row in included_logs if is_error_status(row.get("status_code"))
    ]
    for row in error_logs[:2]:
        add_row(
            row,
            f"상태 {row.get('status_code')} 에러 로그를 문제·이상 징후의 근거로 사용합니다.",
        )
    slowest = max(
        included_logs,
        key=lambda item: int(item.get("response_time_ms") or 0),
        default=None,
    )
    if slowest:
        add_row(
            slowest,
            f"응답시간 {slowest.get('response_time_ms')} ms 로그를 지연 근거의 근거로 사용합니다.",
        )
    add_row(
        included_logs[0],
        "선택한 기간의 포함 로그 건수와 사용량 현황 근거입니다.",
    )
    return selected[:5]


def format_logs_for_llm(included_logs):
    lines = []
    for row in included_logs[:LLM_LOG_ROW_LIMIT]:
        endpoint = row.get("normalized_endpoint") or row.get("endpoint_path")
        lines.append(
            f"{row.get('occurred_at')} {row.get('http_method')} {endpoint} "
            f"status={row.get('status_code')} ms={row.get('response_time_ms')} "
            f"error={row.get('error_code') or '-'}"
        )
    omitted = len(included_logs) - min(len(included_logs), LLM_LOG_ROW_LIMIT)
    if omitted > 0:
        lines.append(f"... 나머지 {omitted}건은 집계 사실에만 포함합니다.")
    return "\n".join(lines)


def post_gemini_generate(api_key, model_name, payload):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent"
    )
    try:
        response = httpx.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        return None, "GEMINI_TIMEOUT"
    except httpx.HTTPError:
        return None, "GEMINI_INVALID_RESPONSE"

    if response.status_code == 429:
        return None, "GEMINI_RATE_LIMITED"
    if response.status_code == 404:
        return None, "GEMINI_MODEL_NOT_FOUND"
    if response.status_code >= 400:
        return None, "GEMINI_INVALID_RESPONSE"
    try:
        body = response.json()
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None, "GEMINI_INVALID_RESPONSE"
    if not str(text).strip():
        return None, "GEMINI_INVALID_RESPONSE"
    return str(text).strip(), None


def call_gemini_summary(fact_summary, included_logs):
    api_key, model_name = load_gemini_settings()
    if not api_key or not included_logs:
        return None, None, model_name
    log_text = format_logs_for_llm(included_logs)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "아래는 PlayEAT에서 정제한 API 요청 로그와 집계 사실이다. "
                            "이 목록과 집계에 없는 식당·원인·수치는 만들지 마라. "
                            "이상 징후와 주요 이슈만 한국어로 요약하라. "
                            "반드시 다음 세 제목으로만 작성하라: "
                            "현황, 문제·이상 징후, 확인할 조치.\n\n"
                            f"[집계 사실]\n{fact_summary}\n\n"
                            f"[지정 기간 포함 로그 {len(included_logs)}건]\n"
                            f"{log_text}"
                        )
                    }
                ]
            }
        ]
    }
    text, error = post_gemini_generate(api_key, model_name, payload)
    used_model = model_name
    if error == "GEMINI_MODEL_NOT_FOUND" and model_name != DEFAULT_GEMINI_MODEL_NAME:
        text, error = post_gemini_generate(
            api_key, DEFAULT_GEMINI_MODEL_NAME, payload
        )
        used_model = DEFAULT_GEMINI_MODEL_NAME
    if error == "GEMINI_MODEL_NOT_FOUND":
        error = "GEMINI_INVALID_RESPONSE"
    if error:
        return None, error, used_model
    return text, None, used_model


def build_summary_response(row, evidence_items, filters):
    return LogSummaryResponse(
        summary_id=row["id"],
        status=row["status"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        filters=filters,
        summary_text=row.get("summary_text"),
        evidence=evidence_items,
        model_name=row["model_name"],
        prompt_version=row["prompt_version"],
        error_code=row.get("error_code"),
        created_at=row["created_at"],
    )


def apply_prompt_postprocess(summary_text, prompt_version):
    if prompt_version != "v2" or not summary_text:
        return summary_text
    if "판단할 데이터 부족" in summary_text:
        return summary_text
    extra = " 포함 로그·에러·응답시간 집계를 현황에 반영합니다."
    status_block = summary_text.split("문제", 1)[0]
    if "현황:" in summary_text and "포함 로그" not in status_block:
        return summary_text.replace("현황:", "현황:" + extra, 1)
    if "포함 로그" not in summary_text:
        return "현황: 포함 로그, 에러, 응답시간을 집계했습니다.\n" + summary_text
    return summary_text


def create_log_summary(
    period_start,
    period_end,
    cleaning_run_id,
    filters=None,
    prompt_version=None,
):
    filters = filters or LogFilters()
    if not isinstance(filters, LogFilters):
        filters = LogFilters.model_validate(filters)
    prompt_version = prompt_version or SUMMARY_PROMPT_VERSION
    profile_id = get_system_profile_id()
    if not profile_id:
        raise RuntimeError("요약을 저장할 관리자 프로필이 없습니다.")

    created = (
        supabase.table("log_summaries")
        .insert(
            {
                "requested_by": profile_id,
                "cleaning_run_id": str(cleaning_run_id),
                "period_start": (
                    period_start.isoformat()
                    if hasattr(period_start, "isoformat")
                    else str(period_start)
                ),
                "period_end": (
                    period_end.isoformat()
                    if hasattr(period_end, "isoformat")
                    else str(period_end)
                ),
                "filters": filters.model_dump(mode="json"),
                "model_name": FALLBACK_MODEL_NAME,
                "prompt_version": prompt_version,
                "status": "running",
            }
        )
        .execute()
    )
    row = (created.data or [None])[0]
    if not row:
        raise RuntimeError("로그 요약을 생성하지 못했습니다.")

    try:
        included_logs = list_included_logs(cleaning_run_id)
        points = list_statistics_from_cleaning_run(cleaning_run_id)
        fact_summary = build_fact_summary(included_logs, points)
        _api_key, gemini_model = load_gemini_settings()
        gemini_text, gemini_error, gemini_model = call_gemini_summary(
            fact_summary, included_logs
        )
        if gemini_error and not included_logs:
            supabase.table("log_summaries").update(
                {
                    "status": "failed",
                    "error_code": gemini_error,
                    "model_name": gemini_model,
                }
            ).eq("id", row["id"]).execute()
            row = get_log_summary_row(row["id"])
            return build_summary_response(row, [], filters)

        summary_text = apply_prompt_postprocess(
            gemini_text or fact_summary,
            prompt_version,
        )
        model_name = gemini_model if gemini_text else FALLBACK_MODEL_NAME
        stored_error = None if gemini_text else gemini_error
        evidence_pairs = select_evidence_logs(included_logs)
        evidence_rows = []
        evidence_items = []
        for order, (log_row, claim_text) in enumerate(evidence_pairs, start=1):
            evidence_rows.append(
                {
                    "summary_id": row["id"],
                    "api_log_id": log_row["id"],
                    "evidence_order": order,
                    "claim_text": claim_text,
                }
            )
            evidence_items.append(
                EvidenceLog(
                    api_log_id=log_row["id"],
                    occurred_at=log_row["occurred_at"],
                    http_method=log_row["http_method"],
                    endpoint=log_row.get("normalized_endpoint")
                    or log_row.get("endpoint_path"),
                    status_code=log_row["status_code"],
                    response_time_ms=log_row["response_time_ms"],
                    error_code=log_row.get("error_code"),
                    claim_text=claim_text,
                )
            )
        supabase.table("log_summaries").update(
            {
                "status": "succeeded",
                "summary_text": summary_text,
                "model_name": model_name,
                "prompt_version": prompt_version,
                "error_code": stored_error,
            }
        ).eq("id", row["id"]).execute()
        if evidence_rows:
            supabase.table("log_summary_evidence").insert(evidence_rows).execute()
        row = get_log_summary_row(row["id"])
        return build_summary_response(row, evidence_items, filters)
    except Exception:
        supabase.table("log_summaries").update(
            {
                "status": "failed",
                "error_code": "INTERNAL_ERROR",
            }
        ).eq("id", row["id"]).execute()
        raise


def get_log_summary_row(summary_id):
    result = (
        supabase.table("log_summaries")
        .select(
            "id, requested_by, cleaning_run_id, period_start, period_end, "
            "filters, summary_text, model_name, prompt_version, status, "
            "error_code, created_at"
        )
        .eq("id", str(summary_id))
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def get_log_summary(summary_id):
    row = get_log_summary_row(summary_id)
    if not row:
        return None
    filters = LogFilters.model_validate(row.get("filters") or {})
    evidence_result = (
        supabase.table("log_summary_evidence")
        .select("api_log_id, evidence_order, claim_text")
        .eq("summary_id", str(summary_id))
        .order("evidence_order")
        .execute()
    )
    evidence_items = []
    for item in evidence_result.data or []:
        log_result = (
            supabase.table("api_request_logs")
            .select(
                "id, occurred_at, http_method, endpoint_path, status_code, "
                "response_time_ms, error_code"
            )
            .eq("id", item["api_log_id"])
            .limit(1)
            .execute()
        )
        log_row = (log_result.data or [None])[0]
        if not log_row:
            continue
        evidence_items.append(
            EvidenceLog(
                api_log_id=log_row["id"],
                occurred_at=log_row["occurred_at"],
                http_method=log_row["http_method"],
                endpoint=normalize_endpoint(log_row.get("endpoint_path")),
                status_code=log_row["status_code"],
                response_time_ms=log_row["response_time_ms"],
                error_code=log_row.get("error_code"),
                claim_text=item.get("claim_text"),
            )
        )
    return build_summary_response(row, evidence_items, filters)

"""관리자 로그분석 API.

원본 로그 조회, 정제, 사용량·지연·오류 통계, LLM 요약, 품질평가, 개선 실험을 제공한다.
원본 로그를 정제 결과로 덮어쓰지 않는다.
관리자(profile_type=0)만 호출할 수 있다.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.admin_auth import require_admin

from app.db import supabase
from app.schemas.api_log import (
    ApiLogDetailResponse,
    ApiLogItem,
    ApiStatisticsResponse,
    CleaningRunRequest,
    CleaningRunResponse,
    EvaluationRunRequest,
    ExperimentCreateRequest,
    LogSummaryRequest,
)
from app.schemas.common import build_error_response, build_success_response
from app.services.api_statistics import (
    apply_status_query_filters,
    filter_log_row,
    list_statistics_from_cleaning_run,
    list_statistics_from_raw_logs,
)
from app.services.improvement_experiments import (
    create_improvement_experiment,
    get_improvement_experiment,
)
from app.services.log_cleaning import (
    CLEANING_CRITERIA_VERSION,
    create_cleaning_run,
    normalize_endpoint,
)
from app.services.log_summary import create_log_summary, get_log_summary
from app.services.summary_evaluation import (
    create_evaluation_run,
    get_evaluation_run,
)

router = APIRouter(
    tags=["admin-logs"],
    dependencies=[Depends(require_admin)],
)


def parse_period(period_start, period_end):
    """조회 기간을 검사한다. 시작은 종료보다 이전이어야 한다."""
    if period_start is None or period_end is None:
        return None, build_error_response(
            422,
            "VALIDATION_ERROR",
            "조회 기간을 확인해 주세요.",
            details=[
                {
                    "field": "period_start",
                    "reason": "period_start와 period_end가 필요합니다.",
                }
            ],
        )
    if period_start >= period_end:
        return None, build_error_response(
            400,
            "INVALID_REQUEST",
            "조회 기간을 확인해 주세요.",
            details=[
                {
                    "field": "period_start",
                    "reason": "period_start는 period_end보다 이전이어야 합니다.",
                }
            ],
        )
    return (period_start, period_end), None


def get_cleaning_run_row(run_id):
    """정제 실행 한 건을 조회한다."""
    result = (
        supabase.table("log_cleaning_runs")
        .select(
            "id, period_start, period_end, criteria_version, status, "
            "source_count, included_count, excluded_count, started_at, completed_at"
        )
        .eq("id", str(run_id))
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def build_cleaning_run_payload(row):
    """정제 실행 행을 API 응답 형식으로 바꾼다."""
    return CleaningRunResponse(
        id=row["id"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        criteria_version=row["criteria_version"],
        status=row["status"],
        source_count=row.get("source_count") or 0,
        included_count=row.get("included_count") or 0,
        excluded_count=row.get("excluded_count") or 0,
        started_at=row["started_at"],
        completed_at=row.get("completed_at"),
    ).model_dump(mode="json")


def build_log_item(row):
    """원본 로그 행을 목록 항목으로 바꾼다. 본문은 넣지 않는다."""
    endpoint_path = row.get("endpoint_path") or ""
    return ApiLogItem(
        id=row["id"],
        request_id=row["request_id"],
        profile_id=row.get("profile_id"),
        occurred_at=row["occurred_at"],
        http_method=row["http_method"],
        endpoint=row.get("normalized_endpoint") or normalize_endpoint(endpoint_path),
        endpoint_path=endpoint_path,
        status_code=row["status_code"],
        response_time_ms=row["response_time_ms"],
        error_code=row.get("error_code"),
        client_type=row.get("client_type"),
        created_at=row["created_at"],
    ).model_dump(mode="json")


def list_included_log_ids(cleaning_run_id):
    """정제에서 통계에 포함한 로그 ID 집합을 반환한다."""
    result = (
        supabase.table("log_cleaning_results")
        .select("api_log_id")
        .eq("cleaning_run_id", str(cleaning_run_id))
        .eq("is_included", True)
        .execute()
    )
    return [row["api_log_id"] for row in result.data or []]


@router.get("/admin/api-logs")
def list_api_logs(
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    status_code: int | None = Query(default=None, ge=100, le=599),
    status_class: str | None = Query(default=None, pattern="^(2xx|4xx|5xx)$"),
    error_only: bool = False,
    cleaning_run_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """원본 API 로그 목록을 기간·필터로 조회한다. 본문은 반환하지 않는다."""
    period, error_response = parse_period(period_start, period_end)
    if error_response:
        return error_response

    try:
        query = (
            supabase.table("api_request_logs")
            .select(
                "id, request_id, profile_id, occurred_at, http_method, "
                "endpoint_path, status_code, response_time_ms, error_code, "
                "client_type, created_at"
            )
            .gte("occurred_at", period[0].isoformat())
            .lte("occurred_at", period[1].isoformat())
            .order("occurred_at", desc=True)
        )
        if http_method:
            query = query.eq("http_method", http_method)
        query = apply_status_query_filters(
            query,
            status_code=status_code,
            status_class=status_class,
            error_only=error_only,
        )
        if cleaning_run_id:
            included_ids = list_included_log_ids(cleaning_run_id)
            if not included_ids:
                return build_success_response(
                    {"items": []},
                    page=page,
                    page_size=page_size,
                    total_count=0,
                )
            query = query.in_("id", included_ids)
        result = query.execute()
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    rows = []
    for row in result.data or []:
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

    total_count = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return build_success_response(
        {"items": [build_log_item(row) for row in page_rows]},
        page=page,
        page_size=page_size,
        total_count=total_count,
    )


@router.get("/admin/api-logs/{api_log_id}")
def get_api_log(api_log_id: UUID):
    """원본 로그 한 건과 정제 포함 여부를 반환한다."""
    try:
        result = (
            supabase.table("api_request_logs")
            .select(
                "id, request_id, profile_id, occurred_at, http_method, "
                "endpoint_path, status_code, response_time_ms, error_code, "
                "client_type, created_at"
            )
            .eq("id", str(api_log_id))
            .limit(1)
            .execute()
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    rows = result.data or []
    if not rows:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "로그를 찾을 수 없습니다.",
        )

    row = rows[0]
    cleaning = (
        supabase.table("log_cleaning_results")
        .select("is_included, normalized_endpoint, exclusion_reason")
        .eq("api_log_id", str(api_log_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    cleaning_row = (cleaning.data or [None])[0] or {}
    item = build_log_item(row)
    detail = ApiLogDetailResponse(
        **item,
        is_included=cleaning_row.get("is_included"),
        normalized_endpoint=cleaning_row.get("normalized_endpoint"),
        exclusion_reason=cleaning_row.get("exclusion_reason"),
    )
    return build_success_response(detail.model_dump(mode="json"))


@router.post("/admin/log-cleaning-runs", status_code=201)
def create_admin_cleaning_run(payload: CleaningRunRequest):
    """지정 기간의 원본 로그를 정제한다. 원본은 덮어쓰지 않는다."""
    try:
        run_row, _included = create_cleaning_run(
            payload.period_start,
            payload.period_end,
            payload.criteria_version or CLEANING_CRITERIA_VERSION,
        )
        return build_success_response(build_cleaning_run_payload(run_row))
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "로그 정제를 실행하지 못했습니다.",
        )


@router.get("/admin/log-cleaning-runs/{run_id}")
def get_admin_cleaning_run(run_id: UUID):
    """정제 실행 결과를 조회한다."""
    try:
        row = get_cleaning_run_row(run_id)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    if not row:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "정제 실행을 찾을 수 없습니다.",
        )
    return build_success_response(build_cleaning_run_payload(row))


def get_statistics_payload(
    period_start,
    period_end,
    endpoint,
    http_method,
    status_code,
    error_only,
    cleaning_run_id,
    status_class=None,
):
    """사용량·지연·오류 통계 공통 조회."""
    period, error_response = parse_period(period_start, period_end)
    if error_response:
        return error_response

    try:
        if cleaning_run_id:
            run_row = get_cleaning_run_row(cleaning_run_id)
            if not run_row:
                return build_error_response(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "정제 실행을 찾을 수 없습니다.",
                )
            if status_code is None and not status_class:
                points = list_statistics_from_cleaning_run(
                    cleaning_run_id,
                    endpoint=endpoint,
                    http_method=http_method,
                    status_code=None,
                    error_only=error_only,
                )
            else:
                points = list_statistics_from_raw_logs(
                    period[0],
                    period[1],
                    endpoint=endpoint,
                    http_method=http_method,
                    status_code=status_code,
                    error_only=error_only,
                    status_class=status_class,
                )
        else:
            points = list_statistics_from_raw_logs(
                period[0],
                period[1],
                endpoint=endpoint,
                http_method=http_method,
                status_code=status_code,
                error_only=error_only,
                status_class=status_class,
            )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    payload = ApiStatisticsResponse(
        period_start=period[0],
        period_end=period[1],
        cleaning_run_id=cleaning_run_id,
        points=points,
    )
    return build_success_response(payload.model_dump(mode="json"))


# 요청 건수 통계
@router.get("/admin/api-statistics/usage")
def get_usage_statistics(
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    status_code: int | None = Query(default=None, ge=100, le=599),
    status_class: str | None = Query(default=None, pattern="^(2xx|4xx|5xx)$"),
    error_only: bool = False,
    cleaning_run_id: UUID | None = None,
):
    return get_statistics_payload(
        period_start,
        period_end,
        endpoint,
        http_method,
        status_code,
        error_only,
        cleaning_run_id,
        status_class=status_class,
    )


# 응답시간 통계
@router.get("/admin/api-statistics/latency")
def get_latency_statistics(
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    status_code: int | None = Query(default=None, ge=100, le=599),
    status_class: str | None = Query(default=None, pattern="^(2xx|4xx|5xx)$"),
    error_only: bool = False,
    cleaning_run_id: UUID | None = None,
):
    return get_statistics_payload(
        period_start,
        period_end,
        endpoint,
        http_method,
        status_code,
        error_only,
        cleaning_run_id,
        status_class=status_class,
    )


# 오류 건수·비율 통계
@router.get("/admin/api-statistics/errors")
def get_error_statistics(
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    status_code: int | None = Query(default=None, ge=100, le=599),
    status_class: str | None = Query(default=None, pattern="^(2xx|4xx|5xx)$"),
    error_only: bool = False,
    cleaning_run_id: UUID | None = None,
):
    return get_statistics_payload(
        period_start,
        period_end,
        endpoint,
        http_method,
        status_code,
        error_only,
        cleaning_run_id,
        status_class=status_class,
    )


@router.post("/admin/log-summaries", status_code=201)
def create_admin_log_summary(payload: LogSummaryRequest):
    """정제된 로그를 LLM으로 요약하고 근거 로그를 남긴다."""
    run_row = get_cleaning_run_row(payload.cleaning_run_id)
    if not run_row:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "정제 실행을 찾을 수 없습니다.",
        )
    try:
        summary = create_log_summary(
            payload.period_start,
            payload.period_end,
            payload.cleaning_run_id,
            payload.filters,
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "로그 요약을 실행하지 못했습니다.",
        )
    return build_success_response(summary.model_dump(mode="json"))


@router.get("/admin/log-summaries/{summary_id}")
def get_admin_log_summary(summary_id: UUID):
    """저장된 로그 요약과 근거를 조회한다."""
    try:
        summary = get_log_summary(summary_id)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    if not summary:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "로그 요약을 찾을 수 없습니다.",
        )
    return build_success_response(summary.model_dump(mode="json"))


@router.post("/admin/summary-evaluation-runs", status_code=201)
def create_admin_evaluation_run(payload: EvaluationRunRequest):
    """요약 품질평가를 실행한다. 사실성·완전성 점수를 저장한다."""
    try:
        evaluation, error_code = create_evaluation_run(
            payload.summary_id,
            payload.case_id,
            payload.experiment_id,
            payload.run_type,
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "품질평가를 실행하지 못했습니다.",
        )
    if error_code == "RESOURCE_NOT_FOUND":
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "요약 또는 평가 사례를 찾을 수 없습니다.",
        )
    if not evaluation:
        return build_error_response(
            500,
            "INTERNAL_ERROR",
            "품질평가를 저장하지 못했습니다.",
        )
    return build_success_response(evaluation.model_dump(mode="json"))


@router.get("/admin/summary-evaluation-runs/{run_id}")
def get_admin_evaluation_run(run_id: UUID):
    """품질평가 실행 결과를 조회한다."""
    try:
        evaluation = get_evaluation_run(run_id)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    if not evaluation:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "품질평가 실행을 찾을 수 없습니다.",
        )
    return build_success_response(evaluation.model_dump(mode="json"))


@router.post("/admin/improvement-experiments", status_code=201)
def create_admin_improvement_experiment(payload: ExperimentCreateRequest):
    """요약 개선 실험을 등록한다."""
    try:
        experiment = create_improvement_experiment(payload)
    except Exception as exc:
        message = str(exc)
        if "duplicate" in message.lower() or "unique" in message.lower():
            return build_error_response(
                409,
                "INVALID_REQUEST",
                "같은 이름의 개선 실험이 이미 있습니다.",
            )
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "개선 실험을 생성하지 못했습니다.",
        )
    return build_success_response(experiment.model_dump(mode="json"))


@router.get("/admin/improvement-experiments/{experiment_id}")
def get_admin_improvement_experiment(experiment_id: UUID):
    """개선 실험과 연결된 평가 실행을 조회한다."""
    try:
        experiment = get_improvement_experiment(experiment_id)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    if not experiment:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "개선 실험을 찾을 수 없습니다.",
        )
    return build_success_response(experiment.model_dump(mode="json"))

"""관리자 API 로그·정제·요약·품질평가 스키마.

원본 로그는 api_request_logs를 쓰고, 정제 결과로 덮어쓰지 않는다.
요청·응답 본문, 비밀번호, 토큰은 모델에 넣지 않는다.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class LogFilters(BaseModel):
    """로그 조회·요약에 쓰는 필터."""

    endpoint: str | None = Field(default=None, max_length=255)  # 엔드포인트 경로
    http_method: Literal["GET", "POST", "PATCH", "DELETE"] | None = None  # HTTP 메서드
    status_code: int | None = Field(default=None, ge=100, le=599)  # 상태 코드
    error_only: bool = False  # True면 오류 로그만


class PeriodRequest(BaseModel):
    """조회 기간. 시작은 종료보다 이전이어야 한다."""

    period_start: datetime  # 기간 시작
    period_end: datetime  # 기간 종료

    @model_validator(mode="after")
    def validate_period(self):
        """시작이 종료보다 이전이 아니면 거부한다."""
        if self.period_start >= self.period_end:
            raise ValueError("period_start는 period_end보다 이전이어야 합니다.")
        return self


class CleaningRunRequest(PeriodRequest):
    """로그 정제 실행 요청."""

    criteria_version: str | None = Field(default=None, max_length=50)  # 정제 규칙 버전


class CleaningRunResponse(BaseModel):
    """로그 정제 실행 결과."""

    id: UUID  # 정제 실행 ID
    period_start: datetime  # 정제 대상 시작
    period_end: datetime  # 정제 대상 종료
    criteria_version: str  # 적용한 규칙 버전
    status: Literal["running", "succeeded", "failed"]  # 실행 상태
    source_count: int = Field(ge=0)  # 원본 건수
    included_count: int = Field(ge=0)  # 통계에 포함한 건수
    excluded_count: int = Field(ge=0)  # 제외한 건수
    started_at: datetime  # 시작 시각
    completed_at: datetime | None = None  # 완료 시각


class ApiLogItem(BaseModel):
    """원본 API 로그 한 건. 본문은 포함하지 않는다."""

    id: UUID  # 로그 ID
    request_id: UUID  # 요청 추적 ID
    profile_id: UUID | None = None  # 인증 사용자. 비로그인은 None
    occurred_at: datetime  # 요청 시작 시각
    http_method: str  # HTTP 메서드
    endpoint: str  # 정규화 전 경로 표시용
    endpoint_path: str  # 실제 요청 경로
    status_code: int  # HTTP 상태 코드
    response_time_ms: int  # 응답시간(ms)
    error_code: str | None = None  # 애플리케이션 에러 코드
    client_type: str | None = None  # Streamlit·test 등
    created_at: datetime  # 적재 시각


class ApiLogDetailResponse(ApiLogItem):
    """로그 상세. 정제 포함 여부와 제외 이유를 추가한다."""

    is_included: bool | None = None  # 통계 포함 여부
    normalized_endpoint: str | None = None  # 정규화 경로
    exclusion_reason: str | None = None  # 제외 이유


class MetricPoint(BaseModel):
    """엔드포인트별 운영 지표 한 점."""

    endpoint: str  # 엔드포인트
    http_method: str  # HTTP 메서드
    request_count: int = Field(ge=0)  # 요청 건수
    error_count: int = Field(ge=0)  # 오류 건수
    error_rate: float | None = Field(default=None, ge=0, le=1)  # 오류율 0~1
    avg_response_time_ms: float | None = Field(default=None, ge=0)  # 평균 응답시간
    p95_response_time_ms: float | None = Field(default=None, ge=0)  # p95 응답시간


class ApiStatisticsResponse(BaseModel):
    """사용량·지연·오류 통계 응답."""

    period_start: datetime  # 집계 시작
    period_end: datetime  # 집계 종료
    cleaning_run_id: UUID | None = None  # 사용한 정제 실행 ID
    points: list[MetricPoint]  # 엔드포인트별 지표


class LogSummaryRequest(PeriodRequest):
    """LLM 로그 요약 요청."""

    cleaning_run_id: UUID  # 요약에 쓸 정제 실행
    filters: LogFilters = Field(default_factory=LogFilters)  # 추가 필터


class EvidenceLog(BaseModel):
    """요약 주장의 근거가 된 원본 로그."""

    api_log_id: UUID  # 원본 로그 ID
    occurred_at: datetime  # 발생 시각
    http_method: str  # HTTP 메서드
    endpoint: str  # 엔드포인트
    status_code: int  # 상태 코드
    response_time_ms: int  # 응답시간
    error_code: str | None = None  # 에러 코드
    claim_text: str | None = None  # 이 로그가 뒷받침하는 문장


class LogSummaryResponse(BaseModel):
    """LLM 로그 요약 결과."""

    summary_id: UUID  # 요약 ID
    status: Literal["running", "succeeded", "failed"]  # 실행 상태
    period_start: datetime  # 대상 시작
    period_end: datetime  # 대상 종료
    filters: LogFilters  # 적용한 필터
    summary_text: str | None = None  # 요약 문장
    evidence: list[EvidenceLog] = Field(default_factory=list)  # 근거 로그
    model_name: str  # 사용한 모델
    prompt_version: str  # 프롬프트 버전
    error_code: str | None = None  # 실패 시 에러 코드
    created_at: datetime  # 생성 시각


class EvaluationRunRequest(BaseModel):
    """요약 품질평가 실행 요청."""

    summary_id: UUID  # 평가할 요약
    case_id: UUID | None = None  # 평가 케이스. 없으면 기본 케이스
    experiment_id: UUID | None = None  # 개선 실험에 묶을 때
    run_type: Literal["baseline", "before", "after"] = "baseline"  # 실험 단계


class EvaluationRunResponse(BaseModel):
    """요약 품질평가 결과."""

    id: UUID  # 평가 실행 ID
    case_id: UUID  # 평가 케이스
    summary_id: UUID  # 평가한 요약
    experiment_id: UUID | None = None  # 연결된 실험
    run_type: Literal["baseline", "before", "after"]  # 실험 단계
    factuality_score: float  # 사실성 점수
    completeness_score: float  # 완전성 점수
    total_score: float  # 합산 점수
    notes: str | None = None  # 메모
    created_at: datetime  # 생성 시각


class ExperimentCreateRequest(BaseModel):
    """개선 실험 생성 요청."""

    name: str = Field(min_length=1, max_length=100)  # 실험명
    hypothesis: str = Field(min_length=1)  # 가설
    change_description: str = Field(min_length=1)  # 변경 내용
    before_version: str = Field(min_length=1, max_length=50)  # 변경 전 버전
    after_version: str = Field(min_length=1, max_length=50)  # 변경 후 버전


class ExperimentResponse(BaseModel):
    """개선 실험과 연결된 평가 실행."""

    id: UUID  # 실험 ID
    name: str  # 실험명
    hypothesis: str  # 가설
    change_description: str  # 변경 내용
    before_version: str  # 변경 전 버전
    after_version: str  # 변경 후 버전
    status: Literal["planned", "running", "completed", "failed"]  # 실험 상태
    created_at: datetime  # 생성 시각
    runs: list[EvaluationRunResponse] = Field(default_factory=list)  # 평가 실행 목록

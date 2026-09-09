# PlayEAT API 설계서

> 관련 PRD: [`PRD_개정본.md`](./PRD_개정본.md)  
> Base URL: `/api/v1`  
> 인증: Bearer Access Token  
> 문서 상태: `PRD-BASELINE-1.0` 구현 계약 확정

## 1. 설계 원칙

- URL은 명사형 복수 리소스를 사용한다.
- `GET`은 조회, `POST`는 생성·실행, `PATCH`는 일부 수정, `DELETE`는 삭제에 사용한다.
- 목록은 `/resources`, 상세는 `/resources/{resource_id}` 형식으로 통일한다.
- 요청·응답은 JSON을 기본으로 한다.
- 날짜·시각은 ISO 8601 UTC 문자열을 사용한다.
- ID는 UUID 문자열을 사용한다.
- 목록 API는 `page`, `page_size` 또는 cursor 방식 중 엔드포인트별로 한 방식을 고정한다.
- 생성·실행 API는 `X-Idempotency-Key`를 지원한다.

## 2. 공통 성공 응답

```json
{
  "data": {},
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-09-08T12:00:00Z"
  }
}
```

목록 응답의 `meta`에는 `page`, `page_size`, `total_count`를 추가한다. 삭제 성공은 `204 No Content`를 사용하며 응답 본문을 반환하지 않는다.

## 3. 표준 에러 응답

```json
{
  "error": {
    "status": 422,
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "details": [
      {
        "field": "nickname",
        "reason": "45자 이하여야 합니다."
      }
    ],
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-09-08T12:00:00Z"
  }
}
```

| 상태 | 사용 조건 | 대표 에러 코드 |
| --- | --- | --- |
| `400` | 문법은 맞지만 업무 규칙을 수행할 수 없음 | `INVALID_REQUEST`, `CONDITION_CONFLICT` |
| `401` | 토큰 없음·만료·유효하지 않음 | `AUTH_REQUIRED`, `TOKEN_EXPIRED`, `INVALID_TOKEN` |
| `403` | 인증됐지만 권한 없음 | `ADMIN_REQUIRED`, `RESOURCE_FORBIDDEN` |
| `404` | 화면·리소스·외부 장소를 찾지 못함 | `RESOURCE_NOT_FOUND`, `KAKAO_PLACE_NOT_FOUND` |
| `409` | 중복·상태·멱등성 충돌 | `EMAIL_CONFLICT`, `NICKNAME_CONFLICT`, `IDEMPOTENCY_CONFLICT` |
| `422` | Pydantic 필드·타입·범위 검증 실패 | `VALIDATION_ERROR` |
| `429` | 사용자 또는 API 요청 제한 초과 | `RATE_LIMITED` |
| `500` | 처리되지 않은 내부 오류 | `INTERNAL_ERROR` |
| `502` | 외부 서비스가 잘못된 응답을 반환 | `GEMINI_INVALID_RESPONSE`, `KAKAO_AUTH_FAILED` |
| `503` | DB·외부 서비스 일시 사용 불가 | `DATABASE_UNAVAILABLE`, `GEMINI_RATE_LIMITED` |
| `504` | 외부 서비스 timeout | `GEMINI_TIMEOUT`, `KAKAO_TIMEOUT` |

4xx는 클라이언트 입력·인증·권한·리소스 상태 오류로 사용한다. 5xx는 서버 또는 외부 의존성 실패로 사용한다. 내부 예외를 무조건 400으로 변환하지 않는다.

## 4. 엔드포인트 목록

### 4.1 인증

| Method | URL | 인증 | 요청 모델 | 응답 모델 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/auth/signups` | 없음 | `SignUpRequest` | `SignUpResponse` | 이메일 회원 생성 |
| `POST` | `/auth/sessions` | 없음 | `LoginRequest` | `SessionResponse` | 일반 로그인 세션 생성 |
| `DELETE` | `/auth/sessions/current` | 필요 | 없음 | 204 | 현재 세션 로그아웃 |
| `PATCH` | `/auth/password` | 필요 | `PasswordChangeRequest` | `MessageResponse` | 비밀번호 변경 |
| `GET` | `/auth/oauth/kakao/authorize` | 없음 | query | redirect | Kakao OAuth 시작 |
| `GET` | `/auth/oauth/kakao/callback` | 없음 | query | redirect | OAuth callback 처리 |
| `POST` | `/auth/oauth/handoffs/{handoff_code}/exchange` | 없음 | 없음 | `SessionResponse` | 60초 단일 사용 handoff code를 로그인 세션으로 교환 |

### 4.2 내 정보

| Method | URL | 인증 | 요청 모델 | 응답 모델 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/users/me` | 사용자 | 없음 | `ProfileResponse` | 내 프로필 조회 |
| `PATCH` | `/users/me` | 사용자 | `ProfileUpdateRequest` | `ProfileResponse` | 닉네임 수정 |
| `GET` | `/users/me/statistics/tags` | 사용자 | 기간 query | `TagUsageResponse` | 자주 사용한 태그 |
| `GET` | `/users/me/statistics/positive-restaurants` | 사용자 | 기간 query | `PositiveRestaurantResponse` | 최근 긍정 식당 3개 |
| `GET` | `/users/me/statistics/categories` | 사용자 | 기간 query | `CategoryPreferenceResponse` | 긍정 평가 카테고리 비율 |

### 4.3 대화와 추천

| Method | URL | 인증 | 요청 모델 | 응답 모델 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/conversations` | 사용자 | `ConversationCreateRequest` | `ConversationResponse` | 새 대화 생성 |
| `GET` | `/conversations` | 사용자 | 목록 query | `ConversationListResponse` | 내 대화 목록 |
| `GET` | `/conversations/{conversation_id}` | 사용자 | 없음 | `ConversationDetailResponse` | 대화 상세 |
| `DELETE` | `/conversations/{conversation_id}` | 사용자 | 없음 | 204 | 대화 삭제 |
| `GET` | `/conversations/{conversation_id}/messages` | 사용자 | 목록 query | `MessageListResponse` | 대화 메시지 조회 |
| `POST` | `/conversations/{conversation_id}/messages` | 사용자 | `MessageCreateRequest` | `MessageCreateResponse` | 사용자 메시지 저장·조건 분석·추천 실행 |
| `GET` | `/conversations/{conversation_id}/recommendations` | 사용자 | 목록 query | `RecommendationListResponse` | 대화 추천 기록 조회 |
| `GET` | `/recommendations/{recommendation_id}` | 사용자 | 없음 | `RecommendationResponse` | 추천 결과 상세 |
| `POST` | `/recommendations/{recommendation_id}/alternatives` | 사용자 | 없음 | `AlternativeRecommendationResponse` | 같은 조건으로 다음 식당 추천 |

기존 보조 명세의 대화 목록과 상세 경로 설명이 뒤바뀐 부분은 위 기준으로 수정한다.

### 4.4 추천 평가

| Method | URL | 인증 | 요청 모델 | 응답 모델 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/recommendations/{recommendation_id}/feedback` | 사용자 | `FeedbackCreateRequest` | `FeedbackResponse` | 추천 평가 생성 |
| `PATCH` | `/recommendations/{recommendation_id}/feedback` | 사용자 | `FeedbackUpdateRequest` | `FeedbackResponse` | 기존 평가 수정 |
| `DELETE` | `/recommendations/{recommendation_id}/feedback` | 사용자 | 없음 | 204 | 평가 삭제 |
| `GET` | `/admin/feedback` | 관리자 | 목록 query | `AdminFeedbackListResponse` | 관리자 추천 평가 목록·값별 건수 |

### 4.5 식당·태그

| Method | URL | 인증 | 설명 |
| --- | --- | --- | --- |
| `GET` | `/restaurants` | 사용자 | 조건에 따른 식당 목록 조회 |
| `GET` | `/restaurants/{restaurant_id}` | 사용자 | 식당 상세 조회 |
| `POST` | `/admin/restaurants` | 관리자 | 식당 생성 |
| `PATCH` | `/admin/restaurants/{restaurant_id}` | 관리자 | 식당 일부 수정 |
| `DELETE` | `/admin/restaurants/{restaurant_id}` | 관리자 | 물리 삭제 없이 식당 비활성화 |
| `POST` | `/admin/restaurants/{restaurant_id}/menus` | 관리자 | 메뉴 생성 |
| `PATCH` | `/admin/menus/{menu_id}` | 관리자 | 메뉴 수정 |
| `DELETE` | `/admin/menus/{menu_id}` | 관리자 | 메뉴 삭제 |
| `GET` | `/restaurant-categories` | 사용자 | 음식 카테고리 목록 |
| `GET` | `/tag-categories` | 사용자 | 태그 카테고리 목록 |
| `GET` | `/restaurant-tags` | 사용자 | 추천 태그 목록 |

### 4.6 관리자 로그·통계·요약

| Method | URL | 요청 모델 | 응답 모델 | 설명 |
| --- | --- | --- | --- | --- |
| `GET` | `/admin/api-logs` | `ApiLogQuery` | `ApiLogListResponse` | 원본 API 로그 목록 |
| `GET` | `/admin/api-logs/{api_log_id}` | 없음 | `ApiLogDetailResponse` | 로그 상세 |
| `POST` | `/admin/log-cleaning-runs` | `CleaningRunRequest` | `CleaningRunResponse` | 로그 정제 실행 생성 |
| `GET` | `/admin/log-cleaning-runs/{run_id}` | 없음 | `CleaningRunResponse` | 정제 상태·결과 요약 |
| `GET` | `/admin/api-statistics/usage` | `StatisticsQuery` | `UsageStatisticsResponse` | 사용량 통계 |
| `GET` | `/admin/api-statistics/latency` | `StatisticsQuery` | `LatencyStatisticsResponse` | 응답시간 통계 |
| `GET` | `/admin/api-statistics/errors` | `StatisticsQuery` | `ErrorStatisticsResponse` | 에러율·에러 코드 통계 |
| `POST` | `/admin/log-summaries` | `LogSummaryRequest` | `LogSummaryResponse` | LLM 로그 요약 실행 |
| `GET` | `/admin/log-summaries/{summary_id}` | 없음 | `LogSummaryResponse` | 요약·근거 조회 |
| `POST` | `/admin/summary-evaluation-runs` | `EvaluationRunRequest` | `EvaluationRunResponse` | 품질평가 실행 |
| `GET` | `/admin/summary-evaluation-runs/{run_id}` | 없음 | `EvaluationRunResponse` | 평가 결과 조회 |
| `POST` | `/admin/improvement-experiments` | `ExperimentCreateRequest` | `ExperimentResponse` | 개선 실험 생성 |
| `GET` | `/admin/improvement-experiments/{experiment_id}` | 없음 | `ExperimentResponse` | 전후 결과 조회 |

관리자 로그·통계·요약 API는 모두 관리자 인증이 필요하다. 아래 제품 검색 통계는 API 사용량·응답시간·에러율과 합산하지 않는다.

### 4.7 관리자 제품 검색 통계

| Method | URL | 인증 | 요청 모델 | 응답 모델 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/admin/search-stats` | 관리자 | 없음 | `SearchStatsResponse` | `dashboard_search_stats`의 음식·가격대·상황 태그 비율 |

## 5. Pydantic 공통 모델

```python
from datetime import datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    request_id: UUID
    timestamp: datetime


class SuccessResponse(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta


class ErrorDetail(BaseModel):
    field: str | None = Field(default=None, examples=["nickname"])
    reason: str = Field(examples=["45자 이하여야 합니다."])


class ErrorBody(BaseModel):
    status: int = Field(ge=400, le=599, examples=[422])
    code: str = Field(examples=["VALIDATION_ERROR"])
    message: str = Field(examples=["입력값을 확인해 주세요."])
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: UUID
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: ErrorBody
```

## 6. 인증 모델

```python
class SignUpRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "<PASSWORD>",
                "nickname": "점심탐험가",
                "terms_agreed": True,
                "privacy_agreed": True,
            }
        }
    )

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=45)
    terms_agreed: Literal[True]
    privacy_agreed: Literal[True]


class SignUpResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    nickname: str
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["<PASSWORD>"])


class SessionResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0, examples=[3600])
    user_id: UUID
    profile_type: Literal["0", "1"]
```

비밀번호 example은 실제 비밀번호가 아니며 API 로그와 문서 실행 결과에 값을 남기지 않는다.

## 7. 추천 nested 모델

```python
class RecommendationConditions(BaseModel):
    category_id: UUID
    price_range_tag_id: UUID
    include_tag_ids: list[UUID] = Field(default_factory=list, max_length=3)
    exclude_tag_ids: list[UUID] = Field(default_factory=list)


class MessageCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "국물 있는 한식이 먹고 싶어요.",
                "selected_conditions": {
                    "category_id": "11111111-1111-1111-1111-111111111111",
                    "price_range_tag_id": "22222222-2222-2222-2222-222222222222",
                    "include_tag_ids": [],
                    "exclude_tag_ids": [],
                },
            }
        }
    )

    content: str | None = Field(default=None, max_length=1000)
    selected_conditions: RecommendationConditions


class MenuSummary(BaseModel):
    id: UUID
    name: str
    price: int = Field(ge=0)


class RestaurantSummary(BaseModel):
    id: UUID
    name: str
    address: str | None = None
    kakao_place_url: str | None = None
    menus: list[MenuSummary]
    matched_tags: list[str]


class RecommendationResponse(BaseModel):
    recommendation_id: UUID
    conversation_id: UUID
    restaurant: RestaurantSummary
    applied_conditions: RecommendationConditions
    reason_text: str | None = Field(default=None, max_length=300)
    reason_source: Literal["gemini", "db_fallback"]
    created_at: datetime


class MessageCreateResponse(BaseModel):
    user_message_id: UUID
    assistant_message_id: UUID | None = None
    recommendation: RecommendationResponse | None = None
    empty_reason: "RecommendationEmptyReason | None" = None
```

```python
class AdjustableCondition(BaseModel):
    field: Literal["category_id", "price_range_tag_id", "include_tag_ids"]
    label: str


class RecommendationEmptyReason(BaseModel):
    code: Literal["NO_MATCHING_RESTAURANT"] = "NO_MATCHING_RESTAURANT"
    message: str = "조건에 맞는 식당이 없습니다."
    adjustable_conditions: list[AdjustableCondition] = Field(default_factory=list)
```

후보 없음은 `200` 성공 응답에서 `data.recommendation = null`과 `empty_reason`을 반환한다. 가짜 추천 객체를 만들거나 API 장애로 집계하지 않는다.

## 8. 피드백·재추천 모델

```python
class FeedbackCreateRequest(BaseModel):
    feedback_value: Literal["1", "2", "3"] = Field(examples=["3"])


class FeedbackResponse(BaseModel):
    feedback_id: UUID
    recommendation_id: UUID
    feedback_value: Literal["1", "2", "3"]
    created_at: datetime
    updated_at: datetime | None = None


class AdminFeedbackItem(BaseModel):
    feedback_id: UUID
    profile_id: UUID
    conversation_id: UUID
    restaurant_id: UUID
    restaurant_name: str | None = None
    category_name: str | None = None
    feedback_value: Literal["1", "2", "3"]
    matched_tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None


class AdminFeedbackCounts(BaseModel):
    feedback_1: int = Field(ge=0)
    feedback_2: int = Field(ge=0)
    feedback_3: int = Field(ge=0)


class AdminFeedbackListResponse(BaseModel):
    items: list[AdminFeedbackItem]
    counts: AdminFeedbackCounts


class AlternativeRecommendationResponse(BaseModel):
    previous_recommendation_id: UUID
    recommendation: RecommendationResponse
    recycled_oldest_candidate: bool = False
```

재추천은 거절 이유나 조건 변경을 입력받지 않는다. 같은 조건과 대화의 이전 추천 이력을 사용하며, 후보가 모두 소진되면 가장 오래된 추천부터 다시 포함하고 `recycled_oldest_candidate=true`로 알린다.

## 9. 로그·통계·요약 모델

```python
class LogFilters(BaseModel):
    endpoint: str | None = Field(default=None, max_length=255)
    http_method: Literal["GET", "POST", "PATCH", "DELETE"] | None = None
    status_code: int | None = Field(default=None, ge=100, le=599)
    error_only: bool = False


class PeriodRequest(BaseModel):
    period_start: datetime
    period_end: datetime


class LogSummaryRequest(PeriodRequest):
    cleaning_run_id: UUID
    filters: LogFilters = Field(default_factory=LogFilters)


class EvidenceLog(BaseModel):
    api_log_id: UUID
    occurred_at: datetime
    http_method: str
    endpoint: str
    status_code: int
    response_time_ms: int
    error_code: str | None = None
    claim_text: str | None = None


class LogSummaryResponse(BaseModel):
    summary_id: UUID
    status: Literal["running", "succeeded", "failed"]
    period_start: datetime
    period_end: datetime
    filters: LogFilters
    summary_text: str | None = None
    evidence: list[EvidenceLog] = Field(default_factory=list)
    model_name: str
    prompt_version: str
    error_code: str | None = None
    created_at: datetime


class MetricPoint(BaseModel):
    endpoint: str
    http_method: str
    request_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    error_rate: float | None = Field(default=None, ge=0, le=1)
    avg_response_time_ms: float | None = Field(default=None, ge=0)
    p95_response_time_ms: float | None = Field(default=None, ge=0)


class ApiStatisticsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    cleaning_run_id: UUID
    points: list[MetricPoint]


class SearchStatPoint(BaseModel):
    label: str
    value: int = Field(ge=0)


class SearchStatsResponse(BaseModel):
    food: list[SearchStatPoint]
    price: list[SearchStatPoint]
    feature: list[SearchStatPoint]
```

기간 요청 모델은 `period_start < period_end`를 검증한다. 성공한 로그 요약은 근거가 1개 이상이어야 하며, 데이터 부족 상태는 성공 요약과 구분한다.

## 10. 엔드포인트별 예외 규칙

| 영역 | 상황 | 상태·코드 |
| --- | --- | --- |
| 회원가입 | 이메일 중복 | `409 EMAIL_CONFLICT` |
| 회원가입·프로필 | 닉네임 중복 | `409 NICKNAME_CONFLICT` |
| 인증 | 토큰 없음·만료 | `401 AUTH_REQUIRED`·`TOKEN_EXPIRED` |
| 관리자 | 일반 사용자 접근 | `403 ADMIN_REQUIRED` |
| 대화·추천·평가 | 다른 사용자의 리소스 | 존재 여부를 노출하지 않는 `404 RESOURCE_NOT_FOUND` |
| 추천 | 명시 조건과 자연어 조건 충돌 | `400 CONDITION_CONFLICT` |
| 추천 | 후보 없음 | `200`, `recommendation=null`, `empty_reason.code=NO_MATCHING_RESTAURANT` |
| 추천 | 동일 멱등성 키·다른 본문 | `409 IDEMPOTENCY_CONFLICT` |
| 평가 | 다른 사용자의 추천 | `404 RESOURCE_NOT_FOUND` |
| 평가 | 없는 추천 | `404 RESOURCE_NOT_FOUND` |
| 외부 LLM | timeout | `504 GEMINI_TIMEOUT` |
| 외부 LLM | 응답 모델 불일치 | `502 GEMINI_INVALID_RESPONSE` |
| DB | 연결 실패 | `503 DATABASE_UNAVAILABLE` |

## 11. API 문서 완료 조건

- 모든 엔드포인트의 URL·Method·인증·Request·Response가 정의되어 있다.
- 모든 요청·응답 모델에 필수·선택 여부와 타입이 있다.
- 핵심 모델에 example이 있고 중첩 JSON이 nested model로 표현된다.
- 모든 4xx·5xx 응답이 표준 에러 포맷을 사용한다.
- Swagger/OpenAPI에서 요청 example과 응답 schema를 확인할 수 있다.
- 구현된 FastAPI 라우트와 이 문서의 경로·Method·모델이 일치한다.
- 권한 실패·검증 실패·중복·외부 장애를 대표 시나리오로 실행할 수 있다.

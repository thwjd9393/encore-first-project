"""공통 API 응답 스키마.

표준 성공·오류 본문과 응답 생성 함수를 둔다.
요청·응답 본문, 비밀번호, 토큰은 여기에 담지 않는다.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.request_context import get_current_request_id


def utc_now():
    """UTC 현재 시각을 반환한다."""
    return datetime.now(timezone.utc)


def new_request_id():
    """현재 요청의 request_id를 가져온다."""
    return get_current_request_id()


class ResponseMeta(BaseModel):
    """성공 응답 메타데이터."""

    request_id: UUID  # 요청 추적 ID
    timestamp: datetime  # 응답 시각
    page: int | None = None  # 목록 페이지 번호
    page_size: int | None = None  # 페이지 크기
    total_count: int | None = None  # 전체 건수


class ErrorDetail(BaseModel):
    """필드 단위 검증 오류."""

    field: str | None = None  # 오류가 난 필드명
    reason: str  # 오류 이유


class ErrorBody(BaseModel):
    """표준 에러 본문. API_설계서 ErrorBody와 맞춘다."""

    status: int = Field(ge=400, le=599)  # HTTP 상태 코드
    code: str  # 애플리케이션 에러 코드
    message: str  # 사용자에게 보여줄 메시지
    details: list[ErrorDetail] = Field(default_factory=list)  # 필드별 상세
    request_id: UUID  # 요청 추적 ID
    timestamp: datetime  # 오류 시각


class ErrorResponse(BaseModel):
    """표준 에러 응답 래퍼."""

    error: ErrorBody


def build_error_response(status, code, message, details=None):
    """표준 에러 JSON 응답을 만든다."""
    request_id = new_request_id()
    response = JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=ErrorBody(
                status=status,
                code=code,
                message=message,
                details=details or [],
                request_id=request_id,
                timestamp=utc_now(),
            )
        ).model_dump(mode="json"),
    )
    response.headers["X-Request-ID"] = str(request_id)
    return response


def build_success_response(data, page=None, page_size=None, total_count=None):
    """data + meta 형식의 성공 응답을 만든다."""
    meta = ResponseMeta(
        request_id=new_request_id(),
        timestamp=utc_now(),
        page=page,
        page_size=page_size,
        total_count=total_count,
    )
    payload = {"data": data, "meta": meta.model_dump(mode="json")}
    if page is None:
        payload["meta"].pop("page", None)
        payload["meta"].pop("page_size", None)
        payload["meta"].pop("total_count", None)
    return payload

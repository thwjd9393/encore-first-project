"""추천 평가·관리자 피드백 스키마.

일반 사용자 채팅 피드백과 관리자 대시보드 목록을 나눈다.
feedback_value 1=싫어요, 2=보통, 3=좋아요.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ── 채팅 피드백 ────────────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    """대화 메시지에 대한 좋아요/싫어요."""

    message_id: UUID  # 평가 대상 메시지 ID
    # None이면 취소다. 한 번 누른 것을 되돌릴 수 있어야 한다.
    value: Literal["up", "down"] | None = None


class FeedbackCreateRequest(BaseModel):
    """POST /recommendations/{id}/feedback 요청."""

    feedback_value: Literal["1", "2", "3"]  # 1 아쉬움, 2 보통, 3 만족


class FeedbackResponse(BaseModel):
    """추천 평가 저장 결과."""

    feedback_id: UUID  # 평가 ID
    recommendation_id: UUID  # 평가한 추천
    feedback_value: Literal["1", "2", "3"]  # 저장한 값
    created_at: datetime  # 작성 시각
    updated_at: datetime | None = None  # 수정 시각


class AdminFeedbackItem(BaseModel):
    """관리자 추천 평가 한 건."""

    feedback_id: UUID  # 평가 ID
    profile_id: UUID  # 평가한 사용자
    conversation_id: UUID  # 평가가 발생한 대화
    restaurant_id: UUID  # 평가 대상 식당
    restaurant_name: str | None = None  # 식당명
    category_name: str | None = None  # 음식 카테고리명
    feedback_value: Literal["1", "2", "3"]  # 1 불만족, 2 보통, 3 만족
    matched_tags: list[str] = Field(default_factory=list)  # 식당에 붙은 태그
    created_at: datetime  # 작성 시각
    updated_at: datetime | None = None  # 수정 시각


class AdminFeedbackCounts(BaseModel):
    """평가 값별 건수. 관리자 KPI 카드에 사용한다."""

    feedback_1: int = Field(ge=0)  # 불만족 건수
    feedback_2: int = Field(ge=0)  # 보통 건수
    feedback_3: int = Field(ge=0)  # 만족 건수

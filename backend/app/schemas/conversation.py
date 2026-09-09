"""대화 생성·조회 스키마.

대화는 로그인한 사용자 명의로만 만든다.
요청 본문의 user_id는 신뢰하지 않는다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── 대화 ──────────────────────────────────────────────────────────
class ConversationCreate(BaseModel):
    """대화 생성 초안. 실제 생성은 MyConversationCreate를 사용한다."""

    user_id: UUID  # 대화 소유자. 라우터에서는 토큰의 사용자 ID를 쓴다
    title: str = Field(min_length=1, max_length=100)  # 대화 제목


class ConversationOut(BaseModel):
    """대화 생성·조회 응답."""

    id: UUID  # 대화 ID
    user_id: UUID  # 소유자 프로필 ID
    title: str  # 대화 제목
    created_at: datetime  # 생성 시각


class MyConversationCreate(BaseModel):
    """POST /conversations 요청.

    user_id는 받지 않는다. 토큰에서 꺼낸 값만 신뢰한다.
    받으면 남의 명의로 대화를 만들 수 있다.
    """

    title: str | None = None  # 없으면 기본 제목을 사용한다


class ConversationUpdate(BaseModel):
    """대화 제목 수정 요청."""

    title: str  # 변경할 제목

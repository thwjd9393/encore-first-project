"""대화 메시지 요청/응답 스키마.

대화에 사용자·AI·시스템 메시지를 저장하고 조회할 때 사용한다.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ── 메시지 ────────────────────────────────────────────────────────
class MessageCreate(BaseModel):
    """대화에 메시지를 저장할 때 받는 값."""

    role: Literal["user", "assistant", "system"]  # 발화 주체
    content: str = Field(min_length=1)  # 메시지 본문. 1자 이상


class MessageOut(BaseModel):
    """저장된 메시지 조회 응답."""

    id: UUID  # 메시지 ID
    conversation_id: UUID  # 소속 대화 ID
    role: str  # user / assistant / system
    content: str  # 메시지 본문
    created_at: datetime  # 저장 시각

"""홈 화면 추천 챗봇 요청 스키마.

선택지 기본값은 이 파일에 두지 않는다.
한식/가격대 등 목록은 gemini_client.py 한 곳에서만 관리한다.
"""

from pydantic import BaseModel


# ── 채팅 요청 ──────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """POST /conversations/{id}/chat 사용자 메시지."""

    content: str  # 사용자가 입력한 자연어 질문
    restaurant_category: str | None = None  # 화면에서 고른 음식 종류
    menu_type: str | None = None  # 화면에서 고른 메뉴 특성
    price_level: str | None = None  # 화면에서 고른 가격대
    tone: str | None = None  # 말투 선택. 선택지 목록은 gemini_client에만 둔다
    length: str | None = None  # 답변 길이 선택


# ── 다시 생성 ──────────────────────────────────────────────────────
class RegenerateRequest(BaseModel):
    """같은 대화에서 답변만 다시 생성할 때 쓰는 요청.

    ChatRequest를 재사용하면 안 된다. 거기에는 content가 필수라서
    질문을 다시 보내지 않는 이 요청은 422로 거부당한다.
    """

    tone: str | None = None  # 말투 선택
    length: str | None = None  # 답변 길이 선택

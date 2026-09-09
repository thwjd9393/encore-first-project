"""대화·메시지 API.

POST /conversations                        대화 생성               201
POST /conversations/{id}/messages           메시지 저장             201
GET  /conversations/{id}/messages          메시지 목록             200

대화 소유자는 토큰의 사용자 ID로만 확인한다.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.db import supabase
from uuid import UUID
from app.schemas.conversation import MyConversationCreate
from app.schemas.message import MessageCreate, MessageOut
from app.schemas.user import CurrentUser

# 캐싱을 위한 import
import json
from app.cache import cache_delete, cache_get, cache_set

from app.deps import get_current_user, require_own_conversation

MESSAGES_CACHE_TTL_SECONDS = 300

# 메세지 캐싱 시작
def _messages_cache_key(conversation_id: UUID) -> str:
    """대화별 메시지 목록 캐시 키."""
    return f"messages:{conversation_id}"

conversation_router = APIRouter(prefix="/conversations", tags=["conversations"])


@conversation_router.post("", status_code=201)
@conversation_router.post("/", status_code=201)
def create_conversation(
    payload: MyConversationCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """로그인한 사용자 명의로 새 대화를 만든다."""
    title = (payload.title or "맛집 추천 대화").strip() or "맛집 추천 대화"
    result = (
        supabase.table("conversations")
        .insert(
            {
                "user_id": current_user.id,
                "title": title[:100],
            }
        )
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="대화를 만들지 못했습니다.")
    row = result.data[0]
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "created_at": row["created_at"],
    }

# POST "/{conversation_id}/messages" — 메시지 저장
#   · 대화가 없으면 404 "대화를 찾을 수 없습니다"
def create_message(conversation_id: UUID, payload: MessageCreate):
    """대화에 메시지를 저장하고 메시지 캐시를 지운다."""

    conversation = (
        supabase.table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .execute()
    )
    if not conversation.data:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다")

    #db에 메세지 추가
    result = (
        supabase.table("messages")
        .insert(
            {
                "conversation_id": str(conversation_id),
                "role": payload.role,
                "content": payload.content,
            }
        )
        .execute()
    )

    #캐시에 반영 > 무효화
    cache_delete(_messages_cache_key(conversation_id))

    #메세지 목록 반환
    return result.data[0]

# GET "/{conversation_id}/messages" — 메시지 목록
#   · 대화가 없으면 404
#   · .order("created_at", desc=False)
def list_messages(conversation_id: UUID):
    """대화 메시지를 오래된 순으로 반환한다. 캐시가 있으면 캐시를 쓴다."""

    #메세지 캐시
    cache_key = _messages_cache_key(conversation_id)
    #캐시에서 get
    cached = cache_get(cache_key)

    #hit
    if cached:
        return json.loads(cached) #캐시 값 리턴 > json형식으로

    #miss
    #DB에서 대화 id 확인

    # 너 아이디 탈취된 거 아닌지 확인
    conversation = (
        supabase.table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .execute()
    )
    if not conversation.data:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다")

    #db에서 가져오기
    result = (
        supabase.table("messages")
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=False)
        .execute()
    )

    #캐시 등록
    cache_set(cache_key, json.dumps(result.data, default=str), MESSAGES_CACHE_TTL_SECONDS)

    return result.data


@conversation_router.post("/{conversation_id}/messages", response_model=MessageOut)
def post_message(
    payload: MessageCreate, conversation_id: UUID = Depends(require_own_conversation)
):
    """내 대화에만 메시지를 추가한다."""
    return create_message(conversation_id, payload)


@conversation_router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: UUID = Depends(require_own_conversation)):
    """내 대화의 메시지 목록을 반환한다."""
    return list_messages(conversation_id)


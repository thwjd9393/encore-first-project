"""음식점 추천 챗봇 응답을 만드는 라우터.

주요 역할

1. 음식점 추천 카테고리 옵션 제공
2. 이전 대화 내역 구성
3. Gemini 스트리밍 응답 생성
4. 사용자/AI 메시지 저장
5. 답변 다시 생성
6. 대화 맥락 초기화
7. 사용량 로그 및 피드백 저장
"""

import datetime
import json
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.deps import get_current_user, require_own_conversation
from app.db import supabase
from app.gemini_client import (
    GEMINI_MODEL,
    MENU_TYPES,
    PRICE_LEVELS,
    RESTAURANT_CATEGORIES,
    extract_conditions,
    generate_reason_from_facts,
)
from app.redis_client import r
from app.request_context import get_current_request_id
from app.routers.restaurants import select_matching_restaurant
from app.routers.search_stats import record_search_conditions
from app.schemas.user import CurrentUser

from app.routers.conversations import (
    create_message,
    list_messages,
)

from app.schemas.chat import ChatRequest, RegenerateRequest
from app.schemas.feedback import FeedbackRequest
from app.schemas.message import MessageCreate, MessageOut


# =========================================================
# 기본 설정
# =========================================================

# Gemini에게 전달할 최근 메시지 개수
MAX_HISTORY_MESSAGES = 20


# 맥락 초기화 표시
CONTEXT_RESET_MARKER = (
    "[맥락 초기화] 이 지점 이전의 대화는 "
    "음식점 추천에 사용하지 않습니다."
)


# 우리 DB role → Gemini role
_ROLE_MAP = {
    "user": "user",
    "assistant": "model",
}


# Redis 사용량 로그 최대 개수
MAX_USAGE_LOGS = 50


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/conversations",
    tags=["chat"],
)


options_router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


# =========================================================
# 1. 추천 옵션
# =========================================================

@options_router.get("/options")
def chat_options():
    """
    음식점 추천 화면에서 사용할 선택지를 반환한다.

    restaurant_categories
        한식 / 중식 / 일식 / 양식 / 기타

    menu_types
        매운거 / 든든한거 / 국물여부

    price_levels
        인당가격_하 / 인당가격_중 / 인당가격_상
    """

    return {
        "restaurant_categories": RESTAURANT_CATEGORIES,
        "menu_types": MENU_TYPES,
        "price_levels": PRICE_LEVELS,
        "max_history_messages": MAX_HISTORY_MESSAGES,
    }


# =========================================================
# 2. Gemini에 전달할 이전 대화 구성
# =========================================================

def _build_history(
    conversation_id: UUID,
) -> list[dict]:
    """
    Gemini에게 전달할 이전 대화를 만든다.

    가장 최근 context reset 이후의 대화만 사용한다.
    """

    messages = list_messages(conversation_id)

    # -----------------------------------------------------
    # 마지막 system 메시지 이후의 대화만 사용
    # -----------------------------------------------------

    for index in range(
        len(messages) - 1,
        -1,
        -1,
    ):
        if messages[index]["role"] == "system":
            messages = messages[index + 1:]
            break

    # -----------------------------------------------------
    # user / assistant 메시지만 Gemini에게 전달
    # -----------------------------------------------------

    usable = [
        message
        for message in messages
        if message["role"] in _ROLE_MAP
    ]

    # 최근 메시지만 사용
    recent = usable[-MAX_HISTORY_MESSAGES:]

    return [
        {
            "role": _ROLE_MAP[message["role"]],
            "parts": [
                {
                    "text": message["content"],
                }
            ],
        }
        for message in recent
    ]


# =========================================================
# 3. Redis 로그
# =========================================================

def _usage_log_key(
    conversation_id: UUID,
) -> str:
    """대화별 Gemini 사용량 로그 Redis 키."""
    return f"usage_log:{conversation_id}"


def _feedback_key(
    conversation_id: UUID,
) -> str:
    """대화별 메시지 피드백 Redis 키."""
    return f"feedback:{conversation_id}"


def _log_usage(
    conversation_id: UUID,
    started_at: float,
    usage,
) -> None:
    """
    Gemini 요청 시간과 토큰 사용량을 Redis에 기록한다.
    """

    entry = {
        "requested_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

        "latency_ms": round(
            (
                time.monotonic()
                - started_at
            )
            * 1000
        ),

        "prompt_tokens": getattr(
            usage,
            "prompt_token_count",
            None,
        ),

        "response_tokens": getattr(
            usage,
            "candidates_token_count",
            None,
        ),

        "total_tokens": getattr(
            usage,
            "total_token_count",
            None,
        ),
    }

    key = _usage_log_key(
        conversation_id
    )

    if r is None:
        return

    r.lpush(
        key,
        json.dumps(entry),
    )

    r.ltrim(
        key,
        0,
        MAX_USAGE_LOGS - 1,
    )


# =========================================================
# 4. 피드백
# =========================================================

@router.post(
    "/{conversation_id}/feedback"
)
def save_feedback(
    payload: FeedbackRequest,
    conversation_id: UUID = Depends(
        require_own_conversation
    ),
):
    """
    AI 추천 답변에 대한 피드백을 저장한다.
    """

    key = _feedback_key(
        conversation_id
    )

    if r is None:
        return {
            "message_id": str(payload.message_id),
            "value": payload.value,
        }

    if payload.value is None:

        r.hdel(
            key,
            str(payload.message_id),
        )

    else:

        r.hset(
            key,
            str(payload.message_id),
            payload.value,
        )

    return {
        "message_id": str(
            payload.message_id
        ),
        "value": payload.value,
    }


@router.get(
    "/{conversation_id}/feedback"
)
def read_feedback(
    conversation_id: UUID = Depends(
        require_own_conversation
    ),
):
    """
    현재 대화방의 피드백 상태를 반환한다.
    """

    if r is None:
        return {}

    return r.hgetall(
        _feedback_key(
            conversation_id
        )
    )


# =========================================================
# 5. 사용량 로그
# =========================================================

@router.get(
    "/{conversation_id}/usage-logs"
)
def usage_logs(
    conversation_id: UUID = Depends(
        require_own_conversation
    ),
):
    """대화에서 Gemini를 호출한 사용량 로그를 반환한다."""

    if r is None:
        return []

    raw = r.lrange(
        _usage_log_key(
            conversation_id
        ),
        0,
        MAX_USAGE_LOGS - 1,
    )

    return [
        json.loads(item)
        for item in raw
    ]


# =========================================================
# 6. 맥락 초기화
# =========================================================

@router.post(
    "/{conversation_id}/reset-context",
    response_model=MessageOut,
)
def reset_context(
    conversation_id: UUID = Depends(
        require_own_conversation
    ),
):
    """
    이전 음식 추천 맥락을 초기화한다.

    DB의 기존 메시지를 삭제하지 않고
    이 지점 이후의 메시지만 Gemini에게 전달한다.
    """

    return create_message(
        conversation_id,
        MessageCreate(
            role="system",
            content=CONTEXT_RESET_MARKER,
        ),
    )


# =========================================================
# 7. DB 식당 추천 + 이유 생성
# =========================================================

def _list_recommended_restaurant_ids(conversation_id: UUID) -> list[str]:
    """같은 대화에서 이미 추천한 식당 ID."""
    result = (
        supabase.table("recommendations")
        .select("restaurant_id")
        .eq("conversation_id", str(conversation_id))
        .order("created_at")
        .execute()
    )
    return [str(row["restaurant_id"]) for row in result.data or []]


def _merge_conditions(selected: dict, extracted: dict) -> dict:
    """화면 선택값이 있으면 그 값을 쓰고, 없으면 자연어 추출값을 쓴다."""
    return {
        "restaurant_category": (
            selected.get("restaurant_category")
            or extracted.get("restaurant_category")
        ),
        "menu_type": selected.get("menu_type") or extracted.get("menu_type"),
        "price_level": selected.get("price_level") or extracted.get("price_level"),
    }


def _save_recommendation(
    profile_id: str,
    conversation_id: UUID,
    restaurant: dict,
    conditions: dict,
    reason_text: str,
    reason_source: str,
):
    """추천 결과를 recommendations에 저장한다."""
    result = (
        supabase.table("recommendations")
        .insert(
            {
                "request_id": str(get_current_request_id() or uuid4()),
                "profile_id": str(profile_id),
                "conversation_id": str(conversation_id),
                "restaurant_id": str(restaurant["id"]),
                "conditions": conditions,
                "reason_text": (reason_text or "")[:300] or None,
                "reason_source": reason_source,
                "model_name": GEMINI_MODEL,
                "prompt_version": "prd-baseline-1.0",
            }
        )
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]


def _sse(payload: dict) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False, default=str) + "\n\n"


def _stream_recommendation(
    conversation_id: UUID,
    profile_id: str,
    user_text: str,
    selected: dict,
):
    """
    Gemini로 조건만 추출한 뒤 DB 52개 식당에서 하나를 고른다.
    추천 이유는 DB 사실을 근거로 만든다.
    """

    def event_stream():
        started_at = time.monotonic()
        try:
            extracted = extract_conditions(user_text)
            conditions = _merge_conditions(selected, extracted)
            exclude_ids = _list_recommended_restaurant_ids(conversation_id)
            restaurant = select_matching_restaurant(
                category=conditions["restaurant_category"],
                menu_types=(
                    [conditions["menu_type"]]
                    if conditions["menu_type"]
                    else None
                ),
                price_level=conditions["price_level"],
                exclude_ids=exclude_ids,
            )
            if not restaurant:
                record_search_conditions(conditions)
                text = (
                    "조건에 맞는 식당이 없습니다. "
                    "음식 종류나 태그를 바꿔 다시 검색해 주세요."
                )
                saved = create_message(
                    conversation_id,
                    MessageCreate(role="assistant", content=text),
                )
                yield _sse({"text": text})
                yield _sse(
                    {
                        "done": True,
                        "message_id": str(saved["id"]),
                        "restaurant": None,
                    }
                )
                return

            reason_text, reason_source = generate_reason_from_facts(restaurant)
            saved_rec = _save_recommendation(
                profile_id,
                conversation_id,
                restaurant,
                conditions,
                reason_text,
                reason_source,
            )
            if not saved_rec:
                yield _sse({"error": "추천 결과를 저장하지 못했습니다."})
                return
            record_search_conditions(
                conditions,
                food_label=restaurant.get("category_name"),
            )

            saved = create_message(
                conversation_id,
                MessageCreate(role="assistant", content=reason_text),
            )
            _log_usage(conversation_id, started_at, None)
            yield _sse({"text": reason_text})
            yield _sse(
                {
                    "done": True,
                    "message_id": str(saved["id"]),
                    "recommendation_id": str(saved_rec["id"]),
                    "restaurant": restaurant,
                }
            )
        except HTTPException as e:
            yield _sse({"error": str(e.detail)})
        except Exception:
            yield _sse({"error": "추천 엔진을 사용할 수 없습니다."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )


# =========================================================
# 8. 답변 다시 생성
# =========================================================

@router.post(
    "/{conversation_id}/regenerate"
)
def regenerate(
    payload: RegenerateRequest,
    conversation_id: UUID = Depends(
        require_own_conversation
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    마지막 AI 추천 답변을 삭제하고 같은 조건으로 다음 식당을 고른다.
    """

    messages = list_messages(
        conversation_id
    )

    if (
        not messages
        or messages[-1]["role"]
        != "assistant"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "다시 생성할 "
                "답변이 없습니다."
            ),
        )

    last_user = next(
        (
            message
            for message in reversed(messages)
            if message["role"] == "user"
        ),
        None,
    )
    if not last_user:
        raise HTTPException(
            status_code=400,
            detail="다시 생성할 질문이 없습니다.",
        )

    supabase.table(
        "messages"
    ).delete().eq(
        "id",
        messages[-1]["id"],
    ).execute()

    if r is not None:
        r.delete(
            f"messages:{conversation_id}"
        )

    last_rec = (
        supabase.table("recommendations")
        .select("conditions")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    conditions = {}
    if last_rec.data:
        stored = last_rec.data[0].get("conditions") or {}
        if isinstance(stored, dict):
            conditions = stored

    return _stream_recommendation(
        conversation_id,
        current_user.id,
        last_user["content"],
        {
            "restaurant_category": conditions.get("restaurant_category"),
            "menu_type": conditions.get("menu_type"),
            "price_level": conditions.get("price_level"),
        },
    )


# =========================================================
# 9. 채팅
# =========================================================

@router.post(
    "/{conversation_id}/chat"
)
def chat(
    payload: ChatRequest,
    conversation_id: UUID = Depends(
        require_own_conversation
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    사용자 질문을 저장하고 DB 식당 한 곳을 추천한다.
    """

    create_message(
        conversation_id,
        MessageCreate(
            role="user",
            content=payload.content,
        ),
    )

    return _stream_recommendation(
        conversation_id,
        current_user.id,
        payload.content,
        {
            "restaurant_category": payload.restaurant_category,
            "menu_type": payload.menu_type,
            "price_level": payload.price_level,
        },
    )
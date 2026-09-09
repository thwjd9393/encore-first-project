"""사용자 추천 평가.

POST /recommendations/{recommendation_id}/feedback
본인 추천에 대해 1·2·3 평가를 저장한다.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends

from app.db import supabase
from app.deps import get_current_user
from app.schemas.common import build_error_response, build_success_response
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse
from app.schemas.user import CurrentUser

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def utc_now():
    return datetime.now(timezone.utc)


def get_own_recommendation(recommendation_id: UUID, current_user: CurrentUser):
    result = (
        supabase.table("recommendations")
        .select("id, profile_id, conversation_id, restaurant_id")
        .eq("id", str(recommendation_id))
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    row = rows[0]
    if str(row.get("profile_id")) != str(current_user.id):
        return None
    return row


@router.post("/{recommendation_id}/feedback")
def create_recommendation_feedback(
    recommendation_id: UUID,
    payload: FeedbackCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """추천 평가를 저장하거나, 이미 있으면 값을 바꾼다."""
    try:
        recommendation = get_own_recommendation(recommendation_id, current_user)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    if not recommendation:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "추천 결과를 찾을 수 없습니다.",
        )

    now = utc_now().isoformat()
    try:
        existing = (
            supabase.table("feedback")
            .select("feedback_id, created_at")
            .eq("profile_id", current_user.id)
            .eq("recommendation_id", str(recommendation_id))
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows:
            updated = (
                supabase.table("feedback")
                .update(
                    {
                        "feedback_value": payload.feedback_value,
                        "updated_at": now,
                    }
                )
                .eq("feedback_id", rows[0]["feedback_id"])
                .execute()
            )
            row = (updated.data or rows)[0]
        else:
            inserted = (
                supabase.table("feedback")
                .insert(
                    {
                        "profile_id": current_user.id,
                        "conversation_id": recommendation["conversation_id"],
                        "restaurant_id": recommendation["restaurant_id"],
                        "recommendation_id": str(recommendation_id),
                        "feedback_value": payload.feedback_value,
                    }
                )
                .execute()
            )
            if not inserted.data:
                return build_error_response(
                    503,
                    "DATABASE_UNAVAILABLE",
                    "평가를 저장하지 못했습니다.",
                )
            row = inserted.data[0]
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "평가를 저장하지 못했습니다.",
        )

    return build_success_response(
        FeedbackResponse(
            feedback_id=row["feedback_id"],
            recommendation_id=recommendation_id,
            feedback_value=str(row.get("feedback_value") or payload.feedback_value),
            created_at=row.get("created_at") or now,
            updated_at=row.get("updated_at"),
        ).model_dump(mode="json")
    )

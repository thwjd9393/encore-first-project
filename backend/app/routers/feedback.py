"""관리자 추천 평가 목록.

GET /admin/feedback  평가 목록과 값별 건수.
관리자(profile_type=0)만 호출할 수 있다.
"""

from fastapi import APIRouter, Depends, Query

from app.admin_auth import require_admin

from app.db import supabase
from app.schemas.common import build_error_response, build_success_response
from app.schemas.feedback import AdminFeedbackCounts, AdminFeedbackItem

router = APIRouter(
    tags=["admin-feedback"],
    dependencies=[Depends(require_admin)],
)


def list_tags_by_restaurant_ids(restaurant_ids):
    """평가 목록에 붙일 식당 태그명을 모은다."""
    if not restaurant_ids:
        return {}
    result = (
        supabase.table("restaurant_tag_map")
        .select("restaurant_id, restaurant_tags(name)")
        .in_("restaurant_id", restaurant_ids)
        .execute()
    )
    tags_by_restaurant_id = {restaurant_id: [] for restaurant_id in restaurant_ids}
    for row in result.data or []:
        tag = row.get("restaurant_tags")
        tag_name = tag.get("name") if isinstance(tag, dict) else None
        if tag_name:
            tags_by_restaurant_id.setdefault(row["restaurant_id"], []).append(tag_name)
    return tags_by_restaurant_id


def labels_from_conditions(conditions):
    """추천 조건에서 가격·메뉴 특성 표시값을 꺼낸다."""
    if not isinstance(conditions, dict):
        return []
    labels = []
    price_level = conditions.get("price_level")
    if price_level:
        labels.append(str(price_level))
    menu_type = conditions.get("menu_type")
    if menu_type:
        labels.append(str(menu_type))
    return labels


def recommendation_payload(row):
    payload = row.get("recommendations")
    if isinstance(payload, list):
        return payload[0] if payload else {}
    if isinstance(payload, dict):
        return payload
    return {}


def get_feedback_value_counts():
    """불만족·보통·만족 건수를 센다."""
    counts = {"1": 0, "2": 0, "3": 0}
    result = supabase.table("feedback").select("feedback_value").execute()
    for row in result.data or []:
        value = str(row.get("feedback_value") or "")
        if value in counts:
            counts[value] += 1
    return AdminFeedbackCounts(
        feedback_1=counts["1"],
        feedback_2=counts["2"],
        feedback_3=counts["3"],
    )


def build_admin_feedback_item(row, matched_tags):
    """feedback 행을 관리자 목록 항목으로 바꾼다."""
    restaurant = row.get("restaurants") if isinstance(row.get("restaurants"), dict) else {}
    category = restaurant.get("restaurant_categories")
    category_name = category.get("name") if isinstance(category, dict) else None
    conditions = recommendation_payload(row).get("conditions")
    if not category_name and isinstance(conditions, dict):
        category_name = conditions.get("restaurant_category") or None
    merged_tags = list(matched_tags)
    for label in labels_from_conditions(conditions):
        if label not in merged_tags:
            merged_tags.append(label)
    return AdminFeedbackItem(
        feedback_id=row["feedback_id"],
        profile_id=row["profile_id"],
        conversation_id=row["conversation_id"],
        restaurant_id=row["restaurant_id"],
        restaurant_name=restaurant.get("name"),
        category_name=category_name,
        feedback_value=str(row["feedback_value"]),
        matched_tags=merged_tags,
        created_at=row["created_at"],
        updated_at=row.get("updated_at"),
    ).model_dump(mode="json")


@router.get("/admin/feedback")
def list_admin_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """관리자 추천 평가 목록과 값별 건수를 반환한다."""
    start = (page - 1) * page_size
    end = start + page_size - 1
    try:
        result = (
            supabase.table("feedback")
            .select(
                "feedback_id, profile_id, conversation_id, restaurant_id, "
                "feedback_value, created_at, updated_at, "
                "restaurants(name, restaurant_categories(name)), "
                "recommendations(conditions)",
                count="exact",
            )
            .order("created_at", desc=True)
            .range(start, end)
            .execute()
        )
        counts = get_feedback_value_counts()
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    rows = result.data or []
    restaurant_ids = [row["restaurant_id"] for row in rows]
    try:
        tags_by_restaurant_id = list_tags_by_restaurant_ids(restaurant_ids)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    items = [
        build_admin_feedback_item(
            row,
            tags_by_restaurant_id.get(row["restaurant_id"], []),
        )
        for row in rows
    ]
    return build_success_response(
        {
            "items": items,
            "counts": counts.model_dump(mode="json"),
        },
        page=page,
        page_size=page_size,
        total_count=result.count or 0,
    )

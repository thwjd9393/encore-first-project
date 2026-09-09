"""관리자 검색정보 통계.

GET /admin/search-stats
dashboard_search_stats의 음식·가격·특성 집계를 반환한다.
추천이 실행되면 같은 테이블에 당일 건수를 더한다.
"""

from datetime import date

from fastapi import APIRouter, Depends

from app.admin_auth import require_admin

from app.db import supabase
from app.schemas.common import build_error_response, build_success_response
from app.schemas.search_stats import SearchStatPoint, SearchStatsResponse

router = APIRouter(
    tags=["admin-search-stats"],
    dependencies=[Depends(require_admin)],
)

STAT_TYPE_FOOD = "0"  # 음식 카테고리
STAT_TYPE_PRICE = "1"  # 가격대
STAT_TYPE_FEATURE = "2"  # 상황·메뉴 특성

PRICE_LABELS = {
    "인당가격_하": "하",
    "인당가격_중": "중",
    "인당가격_상": "상",
    "하": "하",
    "중": "중",
    "상": "상",
}

FEATURE_LABELS = {
    "매운거": "매운거",
    "든든한거": "든든한거",
    "국물여부": "국물",
    "국물": "국물",
}


def aggregate_search_stat_points(rows, stat_type):
    """같은 라벨의 건수를 합쳐 차트 점으로 만든다."""
    totals = {}
    for row in rows:
        if str(row.get("stat_type") or "") != stat_type:
            continue
        label = str(row.get("stat_key") or "").strip()
        if not label:
            continue
        totals[label] = totals.get(label, 0) + int(row.get("count") or 0)
    return [
        SearchStatPoint(label=label, value=value)
        for label, value in sorted(totals.items())
        if value > 0
    ]


def conditions_to_stat_entries(conditions, food_label=None):
    """추천 조건을 검색정보 차트 항목으로 바꾼다."""
    entries = []
    if not isinstance(conditions, dict):
        conditions = {}

    category = str(conditions.get("restaurant_category") or "").strip()
    if not category:
        category = str(food_label or "").strip()
    if category:
        entries.append((STAT_TYPE_FOOD, category))

    price = PRICE_LABELS.get(str(conditions.get("price_level") or "").strip())
    if price:
        entries.append((STAT_TYPE_PRICE, price))

    feature = FEATURE_LABELS.get(str(conditions.get("menu_type") or "").strip())
    if feature:
        entries.append((STAT_TYPE_FEATURE, feature))
    return entries


def bump_search_stat(stat_type, stat_key):
    """오늘 날짜의 해당 항목 건수를 1 늘린다."""
    day = date.today().isoformat()
    existing = (
        supabase.table("dashboard_search_stats")
        .select("stat_id, count")
        .eq("stat_date", day)
        .eq("stat_type", stat_type)
        .eq("stat_key", stat_key)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    if rows:
        (
            supabase.table("dashboard_search_stats")
            .update({"count": int(rows[0].get("count") or 0) + 1})
            .eq("stat_id", rows[0]["stat_id"])
            .execute()
        )
        return
    supabase.table("dashboard_search_stats").insert(
        {
            "stat_date": day,
            "stat_type": stat_type,
            "stat_key": stat_key,
            "count": 1,
        }
    ).execute()


def record_search_conditions(conditions, food_label=None):
    """추천에 쓰인 조건을 검색정보 통계에 반영한다."""
    try:
        for stat_type, stat_key in conditions_to_stat_entries(
            conditions,
            food_label=food_label,
        ):
            bump_search_stat(stat_type, stat_key)
    except Exception:
        return


def list_stats_from_recommendations():
    """통계 테이블이 비어 있으면 저장된 추천 조건으로 집계한다."""
    try:
        result = (
            supabase.table("recommendations")
            .select("conditions, restaurants(restaurant_categories(name))")
            .execute()
        )
        rows_data = result.data or []
    except Exception:
        result = (
            supabase.table("recommendations")
            .select("conditions")
            .execute()
        )
        rows_data = result.data or []

    rows = []
    for rec in rows_data:
        restaurant = rec.get("restaurants") or {}
        if not isinstance(restaurant, dict):
            restaurant = {}
        category = restaurant.get("restaurant_categories") or {}
        food_label = category.get("name") if isinstance(category, dict) else None
        for stat_type, stat_key in conditions_to_stat_entries(
            rec.get("conditions") or {},
            food_label=food_label,
        ):
            rows.append(
                {
                    "stat_type": stat_type,
                    "stat_key": stat_key,
                    "count": 1,
                }
            )
    return rows


@router.get("/admin/search-stats")
def list_search_stats():
    """관리자 검색정보 차트용 집계를 반환한다."""
    try:
        result = (
            supabase.table("dashboard_search_stats")
            .select("stat_type, stat_key, count")
            .execute()
        )
        rows = result.data or []
        food = aggregate_search_stat_points(rows, STAT_TYPE_FOOD)
        price = aggregate_search_stat_points(rows, STAT_TYPE_PRICE)
        feature = aggregate_search_stat_points(rows, STAT_TYPE_FEATURE)
        if not food and not price and not feature:
            rows = list_stats_from_recommendations()
            food = aggregate_search_stat_points(rows, STAT_TYPE_FOOD)
            price = aggregate_search_stat_points(rows, STAT_TYPE_PRICE)
            feature = aggregate_search_stat_points(rows, STAT_TYPE_FEATURE)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    payload = SearchStatsResponse(
        food=food,
        price=price,
        feature=feature,
    )
    return build_success_response(payload.model_dump(mode="json"))

"""식당·메뉴·태그 조회와 관리자 비활성화.

GET /restaurant-categories
GET /restaurants
GET /restaurants/search
GET /restaurants/{restaurant_id}
GET /tag-categories
GET /restaurant-tags
GET /restaurant-tags/{category_id}
DELETE /admin/restaurants/{restaurant_id}  관리자만. 식당을 비활성화한다.
"""

import random
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.admin_auth import require_admin
from app.db import supabase
from app.schemas.common import build_error_response, build_success_response
from app.schemas.restaurant import (
    MenuSummary,
    RestaurantCategory,
    RestaurantSummary,
    RestaurantTag,
    TagCategory,
)

router = APIRouter(tags=["restaurants"])


def get_category_name(row):
    """조인된 restaurant_categories에서 카테고리명을 꺼낸다."""
    category = row.get("restaurant_categories")
    if isinstance(category, dict):
        return category.get("name")
    return None


def build_restaurant_item(row, menus, matched_tags):
    """DB 행을 RestaurantSummary JSON으로 바꾼다."""
    return RestaurantSummary(
        id=row["id"],
        name=row["name"],
        address=row.get("address"),
        phone=row.get("phone"),
        description=row.get("description"),
        storage_path=row.get("storage_path"),
        category_id=row.get("category_id"),
        category_name=get_category_name(row),
        kakao_place_id=row.get("kakao_place_id"),
        kakao_place_url=row.get("kakao_place_url"),
        road_address=row.get("road_address"),
        is_active=row.get("is_active", True),
        menus=menus,
        matched_tags=matched_tags,
    ).model_dump(mode="json")


def list_menus_by_restaurant_ids(restaurant_ids):
    """여러 식당의 메뉴를 restaurant_id별로 묶는다."""
    if not restaurant_ids:
        return {}
    result = (
        supabase.table("menus")
        .select("id, restaurant_id, name, price")
        .in_("restaurant_id", restaurant_ids)
        .order("name")
        .execute()
    )
    menus_by_restaurant_id = {restaurant_id: [] for restaurant_id in restaurant_ids}
    for row in result.data or []:
        restaurant_id = row["restaurant_id"]
        menus_by_restaurant_id.setdefault(restaurant_id, []).append(
            MenuSummary(
                id=row["id"],
                name=row["name"],
                price=row["price"],
            )
        )
    return menus_by_restaurant_id


def list_tags_by_restaurant_ids(restaurant_ids):
    """여러 식당의 태그명을 restaurant_id별로 묶는다."""
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


@router.get("/restaurant-categories")
def list_restaurant_categories():
    """음식 카테고리 목록을 반환한다."""
    try:
        result = (
            supabase.table("restaurant_categories")
            .select("id, name")
            .order("name")
            .execute()
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    items = [
        RestaurantCategory(id=row["id"], name=row["name"]).model_dump(mode="json")
        for row in result.data or []
    ]
    return build_success_response({"items": items})


@router.get("/restaurants")
def list_restaurants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """식당 목록을 페이지 단위로 반환한다."""
    start = (page - 1) * page_size
    end = start + page_size - 1
    try:
        result = (
            supabase.table("restaurants")
            .select("*, restaurant_categories(name)", count="exact")
            .order("name")
            .range(start, end)
            .execute()
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    rows = result.data or []
    restaurant_ids = [row["id"] for row in rows]
    try:
        menus_by_restaurant_id = list_menus_by_restaurant_ids(restaurant_ids)
        tags_by_restaurant_id = list_tags_by_restaurant_ids(restaurant_ids)
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    items = [
        build_restaurant_item(
            row,
            menus_by_restaurant_id.get(row["id"], []),
            tags_by_restaurant_id.get(row["id"], []),
        )
        for row in rows
    ]
    return build_success_response(
        {"items": items},
        page=page,
        page_size=page_size,
        total_count=result.count or 0,
    )

def select_matching_restaurant(
    category: str | None = None,
    menu_types: list[str] | None = None,
    price_level: str | None = None,
    exclude_ids: list[str] | None = None,
):
    """
    활성 식당 중에서 조건 점수가 가장 높은 식당 하나를 고른다.

    Gemini가 식당을 만들지 않고, DB에 있는 52개만 사용한다.
    같은 대화에서 이미 추천한 식당은 exclude_ids로 빼 둔다.
    """

    result = (
        supabase.table("restaurants")
        .select("*, restaurant_categories(name)")
        .eq("is_active", True)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None

    restaurant_ids = [row["id"] for row in rows]
    menus_by_restaurant_id = list_menus_by_restaurant_ids(restaurant_ids)
    tags_by_restaurant_id = list_tags_by_restaurant_ids(restaurant_ids)

    def lookup(mapping, restaurant_id):
        return mapping.get(restaurant_id) or mapping.get(str(restaurant_id), [])

    required_tags = []
    if menu_types:
        required_tags.extend(
            tag for tag in menu_types if tag
        )
    if price_level:
        required_tags.append(price_level)

    scored_items = []
    for row in rows:
        restaurant_id = row["id"]
        restaurant_tags = lookup(tags_by_restaurant_id, restaurant_id)
        score = 0
        matched_conditions = []
        restaurant_category = get_category_name(row)
        if category and restaurant_category == category:
            score += 1
            matched_conditions.append(category)
        for tag in required_tags:
            if tag in restaurant_tags:
                score += 1
                matched_conditions.append(tag)

        total_conditions = len(required_tags)
        if category:
            total_conditions += 1

        item = build_restaurant_item(
            row,
            lookup(menus_by_restaurant_id, restaurant_id),
            restaurant_tags,
        )
        item["match_score"] = score
        item["total_conditions"] = total_conditions
        item["matched_conditions"] = matched_conditions
        item["match_rate"] = (
            round(score / total_conditions * 100, 1)
            if total_conditions > 0
            else 0
        )
        scored_items.append(item)

    if category or required_tags:
        filtered = [
            item for item in scored_items if item["match_score"] > 0
        ]
        has_filter_data = any(
            item.get("category_name") or item.get("matched_tags")
            for item in scored_items
        )
        scored_items = filtered if (filtered or has_filter_data) else scored_items
    if not scored_items:
        return None

    excluded = {str(item_id) for item_id in (exclude_ids or [])}

    def item_id(item):
        return str(item.get("id") or "")

    remaining = [
        item for item in scored_items if item_id(item) not in excluded
    ]
    pool = remaining or scored_items
    max_score = max(item["match_score"] for item in pool)
    top_items = [
        item for item in pool if item["match_score"] == max_score
    ]
    return random.choice(top_items)


@router.get("/restaurants/search")
def search_restaurants(
    category: str | None = Query(default=None),
    menu_types: list[str] | None = Query(default=None),
    price_level: str | None = Query(default=None),
):
    """
    사용자가 선택한 조건과 가장 많이 일치하는 식당을 조회한다.

    모든 조건을 만족할 필요는 없다.
    음식문화권과 태그가 일치할 때마다 1점을 부여하고
    점수가 높은 식당부터 반환한다.
    """

    try:
        item = select_matching_restaurant(
            category=category,
            menu_types=menu_types,
            price_level=price_level,
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    return build_success_response({"item": item})


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: UUID):
    """식당 한 곳의 상세·메뉴·태그를 반환한다."""
    try:
        result = (
            supabase.table("restaurants")
            .select("*, restaurant_categories(name)")
            .eq("id", str(restaurant_id))
            .limit(1)
            .execute()
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    rows = result.data or []
    if not rows:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "식당을 찾을 수 없습니다.",
        )

    row = rows[0]
    try:
        menus_by_restaurant_id = list_menus_by_restaurant_ids([row["id"]])
        tags_by_restaurant_id = list_tags_by_restaurant_ids([row["id"]])
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    return build_success_response(
        build_restaurant_item(
            row,
            menus_by_restaurant_id.get(row["id"], []),
            tags_by_restaurant_id.get(row["id"], []),
        )
    )


@router.get("/tag-categories")
def list_tag_categories():
    """가격대·메뉴 특성 등 태그 분류 목록을 반환한다."""
    try:
        result = (
            supabase.table("tag_categories")
            .select("id, code, name")
            .order("name")
            .execute()
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    items = [
        TagCategory(id=row["id"], code=row["code"], name=row["name"]).model_dump(
            mode="json"
        )
        for row in result.data or []
    ]
    return build_success_response({"items": items})


@router.get("/restaurant-tags/{category_id}")
def list_restaurant_tags_by_category(category_id: UUID):
    """선택한 분류에 속한 태그를 반환한다."""
    try:
        result = (
            supabase.table("restaurant_tags")
            .select("id, category_id, name")
            .eq("category_id", str(category_id))
            .order("name")
            .execute()
        )

    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )

    items = [
        RestaurantTag(
            id=row["id"],
            category_id=row["category_id"],
            name=row["name"],
        ).model_dump(mode="json")
        for row in result.data or []
    ]

    return build_success_response({"items": items})


@router.get("/restaurant-tags")
def list_restaurant_tags():
    """전체 식당 태그를 반환한다."""
    try:
        result = (
            supabase.table("restaurant_tags")
            .select("id, category_id, name")
            .order("name")
            .execute()
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    items = [
        RestaurantTag(
            id=row["id"],
            category_id=row["category_id"],
            name=row["name"],
        ).model_dump(mode="json")
        for row in result.data or []
    ]
    return build_success_response({"items": items})


@router.delete("/admin/restaurants/{restaurant_id}")
def delete_admin_restaurant(
    restaurant_id: UUID,
    _admin=Depends(require_admin),
):
    """관리자가 식당을 비활성화한다. 행은 삭제하지 않는다."""
    try:
        result = (
            supabase.table("restaurants")
            .select("id")
            .eq("id", str(restaurant_id))
            .limit(1)
            .execute()
        )
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "데이터베이스에 연결하지 못했습니다.",
        )
    if not result.data:
        return build_error_response(
            404,
            "RESOURCE_NOT_FOUND",
            "식당을 찾을 수 없습니다.",
        )
    try:
        supabase.table("restaurants").update({"is_active": False}).eq(
            "id", str(restaurant_id)
        ).execute()
    except Exception:
        return build_error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "식당을 비활성화하지 못했습니다.",
        )
    return Response(status_code=204)



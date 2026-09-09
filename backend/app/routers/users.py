"""사용자·회원가입 라우터.

POST /auth/signups     이메일 회원 생성. 공개 가입은 일반 사용자(profile_type=1)만.
GET  /users/me         내 프로필 조회
PATCH /users/me        닉네임 수정
GET  /users/me/tags    자주 사용한 태그 상위 5개
GET  /users/me/likes   최근 긍정 평가 식당 3개
GET  /users/me/categories  긍정 평가 카테고리 비율
"""

from datetime import datetime, timezone
import hashlib
import uuid
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from supabase_auth.errors import AuthApiError

from app.cache import cache_delete
from app.db import supabase
from app.deps import get_current_user
from app.schemas.user import (
    CurrentUser,
    ResponseMeta,
    SignUpRequest,
    SignUpResponse,
    SuccessResponse,
    NicknameUpdateRequest,
)

# 마이페이지·프로필 API
router = APIRouter(prefix="/users", tags=["users"])
# 회원가입만 /auth 아래에 둔다. 로그인은 auth.py가 담당한다.
auth_router = APIRouter(prefix="/auth", tags=["auth"])

# 표준 에러 응답 포맷 생성 함수
def create_error_response(status_code: int, code: str, message: str, details: list = None):
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "status": status_code,
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )

def invalidate_user_session_cache(current_user: CurrentUser):
    """닉네임 변경 후 해당 토큰의 세션 캐시를 지운다."""
    cache_delete(
        f"session:{hashlib.sha256(current_user.token.encode()).hexdigest()}"
    )


def collect_condition_labels(conditions):
    """추천 conditions에서 마이페이지에 보여줄 태그명을 모은다."""
    labels = []
    if not isinstance(conditions, dict):
        return labels

    display_names = {
        "인당가격_하": "가성비",
        "인당가격_중": "중간쯤",
        "인당가격_상": "비싼거",
        "국물여부": "국물",
    }
    for key in ("restaurant_category", "menu_type", "price_level"):
        raw = conditions.get(key)
        if not raw:
            continue
        labels.append(display_names.get(str(raw), str(raw)))

    for tag_id in collect_condition_tag_ids(conditions):
        tag_result = (
            supabase.table("restaurant_tags")
            .select("name")
            .eq("id", str(tag_id))
            .limit(1)
            .execute()
        )
        if tag_result.data:
            labels.append(tag_result.data[0]["name"])
    return labels


def is_positive_feedback(value):
    return str(value or "").strip() == "3"


def collect_condition_tag_ids(conditions):
    """추천 conditions JSON에서 태그 ID를 모은다."""
    tag_ids = []
    if not isinstance(conditions, dict):
        return tag_ids

    for key in ("include_tag_ids", "exclude_tag_ids", "tag_ids"):
        values = conditions.get(key) or []
        if isinstance(values, list):
            tag_ids.extend(values)

    price_tag_id = conditions.get("price_range_tag_id")
    if price_tag_id:
        tag_ids.append(price_tag_id)
    return tag_ids


def delete_incomplete_auth_user(user_id):
    """프로필 저장에 실패하면 Auth 사용자를 되돌린다."""
    if not user_id:
        return
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception:
        pass


def raise_signup_auth_error(error):
    """Auth 가입 오류를 409·429·500 표준 에러로 바꾼다."""
    message = str(error).lower()
    if "already" in message or "registered" in message or "exists" in message:
        raise create_error_response(
            409,
            "EMAIL_CONFLICT",
            "이미 등록된 이메일입니다.",
        )
    if "rate limit" in message:
        raise create_error_response(
            429,
            "RATE_LIMITED",
            "잠시 후 다시 시도해주세요.",
        )
    raise create_error_response(
        500,
        "INTERNAL_ERROR",
        "회원가입 처리 중 오류가 발생했습니다.",
    )


@auth_router.post(
    "/signups",
    response_model=SuccessResponse[SignUpResponse],
    status_code=status.HTTP_201_CREATED
)
def create_user(request: SignUpRequest):
    """이메일 회원을 만들고 profiles·user_consents를 함께 저장한다."""
    nickname_check = (
        supabase.table("profiles")
        .select("id")
        .eq("profile_nickname", request.nickname)
        .execute()
    )
    if nickname_check.data:
        raise create_error_response(409, "NICKNAME_CONFLICT", "이미 사용 중인 닉네임입니다.")

    new_user_id = None

    try:
        # 공개 signup은 확인 메일 한도에 걸린다. 서비스 롤로 생성하고 즉시 로그인 가능하게 한다.
        auth_response = supabase.auth.admin.create_user(
            {
                "email": str(request.email),
                "password": request.password,
                "email_confirm": True,
            }
        )
        if not auth_response.user:
            raise create_error_response(409, "EMAIL_CONFLICT", "이미 등록된 이메일입니다.")

        new_user_id = auth_response.user.id
        profile_result = (
            supabase.table("profiles")
            .insert(
                {
                    "id": new_user_id,
                    "profile_nickname": request.nickname,
                    "profile_type": "1",
                    "profile_status": "1",
                }
            )
            .execute()
        )
        if not profile_result.data:
            raise RuntimeError("프로필 저장에 실패했습니다.")

        supabase.table("user_consents").insert(
            [
                {
                    "profile_id": new_user_id,
                    "consent_type": "terms",
                    "consent_version": "terms-v1.0",
                    "is_agreed": request.terms_agreed,
                },
                {
                    "profile_id": new_user_id,
                    "consent_type": "privacy",
                    "consent_version": "privacy-v1.0",
                    "is_agreed": request.privacy_agreed,
                },
            ]
        ).execute()

        return SuccessResponse(
            data=SignUpResponse(
                user_id=new_user_id,
                email=request.email,
                nickname=request.nickname,
                created_at=profile_result.data[0]["profile_created_at"],
            ),
            meta=ResponseMeta(
                request_id=uuid.uuid4(),
                timestamp=datetime.now(timezone.utc),
            ),
        )

    except HTTPException:
        delete_incomplete_auth_user(new_user_id)
        raise
    except AuthApiError as error:
        delete_incomplete_auth_user(new_user_id)
        raise_signup_auth_error(error)
    except Exception:
        delete_incomplete_auth_user(new_user_id)
        raise create_error_response(
            500,
            "INTERNAL_ERROR",
            "회원가입 처리 중 오류가 발생했습니다.",
        )

# 현재 로그인한 사용자 정보 조회하기
@router.get("/me")
def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
):
    """로그인한 사용자의 이메일과 닉네임을 반환한다."""
    # 현재 사용자의 프로필 조회하기
    profile_result = (
        supabase
        .table("profiles")
        .select("profile_nickname")
        .eq("id", current_user.id)
        .single()
        .execute()
    )

    # 프로필이 없는 경우
    if not profile_result.data:
        raise create_error_response(
            404,
            "PROFILE_NOT_FOUND",
            "사용자 프로필을 찾을 수 없습니다.",
        )

    # 마이페이지에 필요한 사용자 정보 반환하기
    return {
        "email": current_user.email,
        "nickname": profile_result.data["profile_nickname"],
    }

# 자주 사용하는 태그 조회하기
@router.get("/me/tags")
def get_my_tags(
    current_user: CurrentUser = Depends(get_current_user),
):
    """저장된 추천 조건에 포함된 태그 사용 횟수 상위 5개를 반환한다."""
    recommendation_result = (
        supabase
        .table("recommendations")
        .select("conditions")
        .eq("profile_id", current_user.id)
        .execute()
    )

    if not recommendation_result.data:
        return {
            "tags": [],
            "message": "아직 사용한 태그가 없습니다."
        }

    tag_counts = {}
    for recommendation in recommendation_result.data:
        for label in collect_condition_labels(recommendation.get("conditions")):
            if not label:
                continue
            tag_counts[label] = tag_counts.get(label, 0) + 1

    if not tag_counts:
        return {
            "tags": [],
            "message": "아직 사용한 태그가 없습니다."
        }

    sorted_tags = sorted(
        tag_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    return {
        "tags": [label for label, _ in sorted_tags[:5]]
    }

# 최근 좋아요 식당 조회하기
@router.get("/me/likes")
def get_my_likes(
    current_user: CurrentUser = Depends(get_current_user),
):
    """feedback_value=3 평가를 최신순으로 서로 다른 식당 3개를 반환한다."""
    # 현재 사용자가 좋아요를 누른 식당을 최근 순으로 조회하기
    feedback_result = (
        supabase
        .table("feedback")
        .select(
            "restaurant_id, feedback_value, created_at, "
            "restaurants(id, name, address, road_address, category_id, "
            "restaurant_categories(name))"
        )
        .eq("profile_id", current_user.id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    restaurants = []
    seen_restaurant_ids = set()
    for row in feedback_result.data or []:
        if not is_positive_feedback(row.get("feedback_value")):
            continue
        restaurant_id = str(row.get("restaurant_id") or "")
        if not restaurant_id or restaurant_id in seen_restaurant_ids:
            continue
        restaurant = row.get("restaurants") or {}
        if not isinstance(restaurant, dict) or not restaurant.get("name"):
            continue
        seen_restaurant_ids.add(restaurant_id)
        restaurants.append(
            {
                "id": restaurant.get("id") or restaurant_id,
                "name": restaurant.get("name"),
                "address": restaurant.get("road_address") or restaurant.get("address"),
            }
        )
        if len(restaurants) >= 3:
            break

    return {
        "restaurants": restaurants
    }

# 선호 음식 카테고리 비율 조회하기
@router.get("/me/categories")
def get_my_categories(
    current_user: CurrentUser = Depends(get_current_user),
):
    """긍정 평가 식당을 음식 카테고리별로 나눈 비율을 반환한다."""
    # 현재 사용자가 좋아요를 누른 식당 조회하기
    feedback_result = (
        supabase
        .table("feedback")
        .select(
            "restaurant_id, feedback_value, "
            "restaurants(category_id, restaurant_categories(name))"
        )
        .eq("profile_id", current_user.id)
        .execute()
    )

    liked_rows = [
        row
        for row in feedback_result.data or []
        if is_positive_feedback(row.get("feedback_value"))
    ]
    if not liked_rows:
        return {
            "categories": []
        }

    category_counts = {}
    for row in liked_rows:
        restaurant = row.get("restaurants") or {}
        if not isinstance(restaurant, dict):
            continue
        category = restaurant.get("restaurant_categories") or {}
        name = category.get("name") if isinstance(category, dict) else None
        if not name:
            continue
        category_counts[name] = category_counts.get(name, 0) + 1

    total_count = sum(category_counts.values())
    if not total_count:
        return {
            "categories": []
        }

    categories = [
        {
            "name": name,
            "percentage": round(count / total_count * 100),
        }
        for name, count in category_counts.items()
    ]
    categories.sort(key=lambda item: item["percentage"], reverse=True)
    return {
        "categories": categories
    }

# 닉네임 수정하기
@router.patch("/me")
def update_my_profile(
    request: NicknameUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """닉네임을 수정한다. 다른 사용자와 중복이면 409."""
    # 변경하려는 닉네임이 이미 사용 중인지 확인하기
    nickname_check = (
        supabase
        .table("profiles")
        .select("id")
        .eq("profile_nickname", request.nickname)
        .execute()
    )

    # 다른 사용자가 같은 닉네임을 사용하고 있으면 수정하지 않기
    if nickname_check.data:
        existing_user_id = str(nickname_check.data[0]["id"])

        if existing_user_id != current_user.id:
            raise create_error_response(
                409,
                "NICKNAME_CONFLICT",
                "이미 사용 중인 닉네임입니다.",
            )

    # 현재 사용자의 닉네임 수정하기
    profile_result = (
        supabase
        .table("profiles")
        .update({
            "profile_nickname": request.nickname,
            "profile_updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", current_user.id)
        .execute()
    )

    # 사용자 프로필을 찾을 수 없는 경우
    if not profile_result.data:
        raise create_error_response(
            404,
            "PROFILE_NOT_FOUND",
            "사용자 프로필을 찾을 수 없습니다.",
        )

    invalidate_user_session_cache(current_user)

    # 수정된 닉네임 반환하기
    return {
        "email": current_user.email,
        "nickname": request.nickname,
    }
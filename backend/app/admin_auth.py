from fastapi import Header

from app.db import supabase
from app.schemas.common import build_error_response

ADMIN_PROFILE_TYPE = "0"
ACTIVE_PROFILE_STATUS = "1"


class AdminAuthError(Exception):
    def __init__(self, response):
        self.response = response


def get_access_token_from_authorization(authorization):
    if not authorization:
        return None
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None
    access_token = token.strip()
    return access_token or None


def get_user_id_from_access_token(access_token):
    try:
        user_response = supabase.auth.get_user(access_token)
    except Exception as exc:
        message = str(exc).lower()
        if "expired" in message:
            return None, "expired"
        return None, "invalid"
    user = getattr(user_response, "user", None)
    user_id = getattr(user, "id", None)
    if not user_id:
        return None, "invalid"
    return str(user_id), None


def get_profile_for_user_id(user_id):
    result = (
        supabase.table("profiles")
        .select("id, profile_type, profile_status")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return rows[0]


def require_admin(authorization: str | None = Header(default=None)):
    access_token = get_access_token_from_authorization(authorization)
    if not access_token:
        raise AdminAuthError(
            build_error_response(
                401,
                "AUTH_REQUIRED",
                "로그인이 필요합니다.",
            )
        )

    user_id, reason = get_user_id_from_access_token(access_token)
    if not user_id:
        code = "TOKEN_EXPIRED" if reason == "expired" else "INVALID_TOKEN"
        raise AdminAuthError(
            build_error_response(
                401,
                code,
                "로그인이 필요합니다.",
            )
        )

    profile = get_profile_for_user_id(user_id)
    if not profile or profile.get("profile_status") != ACTIVE_PROFILE_STATUS:
        raise AdminAuthError(
            build_error_response(
                403,
                "RESOURCE_FORBIDDEN",
                "사용할 수 없는 계정입니다.",
            )
        )
    if profile.get("profile_type") != ADMIN_PROFILE_TYPE:
        raise AdminAuthError(
            build_error_response(
                403,
                "ADMIN_REQUIRED",
                "관리자만 이용할 수 있습니다.",
            )
        )
    return profile

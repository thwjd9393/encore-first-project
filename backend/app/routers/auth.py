"""인증 라우터.

POST /auth/login   이메일 로그인. 성공 시 Access Token과 프로필을 반환한다.
PATCH /auth/password  로그인 사용자의 비밀번호 변경. 성공 후 모든 세션을 종료한다.

공개 회원가입은 users.auth_router의 POST /auth/signups를 사용한다.
"""

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.cache import cache_delete
from app.db import get_anon_client, supabase
from app.deps import get_current_user
from app.schemas.user import CurrentUser


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class LoginRequest(BaseModel):
    """로그인 요청. MVP는 이메일+비밀번호만 받는다."""

    email: EmailStr  # 로그인 ID. 별도 login_id는 쓰지 않는다
    password: str  # 비밀번호. 응답·로그에 남기지 않는다


class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청. 확인 값은 화면에서만 검사한다."""

    current_password: str = Field(min_length=8, max_length=128)  # 현재 비밀번호
    new_password: str = Field(min_length=8, max_length=128)  # 새 비밀번호 8자 이상


def ensure_login_profile(user):
    """로그인 사용자에 profiles 행이 없으면 일반 사용자 프로필을 만든다."""
    profile_result = (
        supabase.table("profiles")
        .select("id, profile_nickname, profile_status, profile_type")
        .eq("id", str(user.id))
        .execute()
    )
    if profile_result.data:
        return profile_result.data[0]

    base_nickname = (user.email or "user").split("@")[0].strip()[:45] or "user"
    nickname = base_nickname
    suffix = 1
    while True:
        exists = (
            supabase.table("profiles")
            .select("id")
            .eq("profile_nickname", nickname)
            .execute()
        )
        if not exists.data:
            break
        suffix += 1
        nickname = f"{base_nickname[:40]}{suffix}"

    profile_result = (
        supabase.table("profiles")
        .insert(
            {
                "id": str(user.id),
                "profile_nickname": nickname,
                "profile_type": "1",
                "profile_status": "1",
            }
        )
        .execute()
    )
    if not profile_result.data:
        raise HTTPException(
            status_code=404,
            detail="사용자 프로필을 찾을 수 없습니다.",
        )
    return profile_result.data[0]


@router.post("/login")
def login(login_info: LoginRequest):
    """이메일 로그인. 관리자(profile_type=0)와 일반 사용자를 구분한다."""
    auth_client = get_anon_client()

    try:
        result = auth_client.auth.sign_in_with_password(
            {
                "email": login_info.email,
                "password": login_info.password,
            }
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if result.user is None or result.session is None:
        raise HTTPException(
            status_code=401,
            detail="로그인에 실패했습니다.",
        )

    profile = ensure_login_profile(result.user)

    if profile["profile_status"] != "1":
        raise HTTPException(
            status_code=403,
            detail="사용할 수 없는 계정입니다.",
        )

    return {
        "access_token": result.session.access_token,
        "token_type": "bearer",
        "user": {
            "id": str(result.user.id),
            "email": result.user.email,
            "nickname": profile["profile_nickname"],
            "profile_type": profile["profile_type"],
        },
    }


@router.patch("/password")
def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """현재 비밀번호를 확인한 뒤 Auth 비밀번호를 바꾸고 세션을 종료한다."""
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=422,
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.",
        )

    auth_client = get_anon_client()
    try:
        auth_client.auth.sign_in_with_password(
            {
                "email": current_user.email,
                "password": payload.current_password,
            }
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )

    try:
        supabase.auth.admin.update_user_by_id(
            current_user.id,
            {"password": payload.new_password},
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="비밀번호 변경 중 오류가 발생했습니다.",
        )

    try:
        supabase.auth.admin.sign_out(current_user.token)
    except Exception:
        pass

    cache_delete(f"session:{hashlib.sha256(current_user.token.encode()).hexdigest()}")

    return {
        "message": "비밀번호가 변경되었습니다. 다시 로그인해 주세요.",
    }
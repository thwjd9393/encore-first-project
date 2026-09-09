"""사용자·인증 요청/응답 스키마.

회원가입, 닉네임 수정, 현재 로그인 사용자 정보를 정의한다.
비밀번호는 요청 검증에만 쓰고 응답·로그에 넣지 않는다.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── 사용자 ────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    """사용자 생성 초안 모델. 실제 가입은 SignUpRequest를 사용한다."""

    email: EmailStr  # 가입 이메일
    username: str = Field(min_length=2, max_length=30)  # 표시 이름(2~30자)


class UserUpdate(BaseModel):
    """사용자 이름만 수정할 때 쓰는 초안 모델."""

    username: str = Field(min_length=2, max_length=30)  # 변경할 이름


class UserOut(BaseModel):
    """사용자 조회 초안 응답. 실제 프로필 조회는 라우터에서 직접 반환한다."""

    id: UUID  # 사용자 ID
    email: str  # 이메일
    username: str  # 표시 이름
    created_at: datetime  # 생성 시각


class SignUpRequest(BaseModel):
    """POST /auth/signups 요청. 이메일 회원 생성."""

    email: EmailStr  # 로그인에 사용할 이메일
    password: str = Field(min_length=8, max_length=128)  # 8자 이상, 조합 조건 없음
    nickname: str = Field(min_length=1, max_length=45)  # 프로필 닉네임
    terms_agreed: Literal[True]  # 이용약관 필수 동의
    privacy_agreed: Literal[True]  # 개인정보 수집·이용 필수 동의

    @field_validator("nickname", mode="before")
    @classmethod
    def strip_nickname(cls, value):
        """닉네임 앞뒤 공백을 제거한다."""
        if isinstance(value, str):
            return value.strip()
        return value


class SignUpResponse(BaseModel):
    """회원가입 완료 후 돌려줄 회원 정보."""

    user_id: UUID  # 생성된 사용자 ID
    email: EmailStr  # 가입 이메일
    nickname: str  # 저장한 닉네임
    created_at: datetime  # 가입 시각


class ResponseMeta(BaseModel):
    """성공 응답에 함께 담을 요청 번호와 시각."""

    request_id: UUID  # 요청 추적 ID
    timestamp: datetime  # 응답 시각


T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """공통 성공 응답. data와 meta를 함께 반환한다."""

    data: T  # 실제 응답 본문
    meta: ResponseMeta  # 요청 메타데이터


class NicknameUpdateRequest(BaseModel):
    """PATCH /users/me 닉네임 수정 요청."""

    nickname: str = Field(min_length=1, max_length=45)  # 공백 제거 후 1~45자

    @field_validator("nickname", mode="before")
    @classmethod
    def strip_nickname(cls, value):
        """닉네임 앞뒤 공백을 제거한다."""
        if isinstance(value, str):
            return value.strip()
        return value


# ── 현재 로그인 사용자 ────────────────────────────────────────────
@dataclass
class CurrentUser:
    """토큰으로 확인한 현재 사용자. get_current_user가 채운다."""

    id: str  # auth.users / profiles.id
    email: str  # 로그인 이메일
    token: str  # Access Token. 세션 캐시 키와 로그아웃에 사용

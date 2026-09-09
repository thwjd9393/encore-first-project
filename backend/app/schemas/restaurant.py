"""식당·메뉴·태그 응답 스키마.

목록·검색·상세·관리자 비활성화에서 공통으로 사용한다.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class MenuSummary(BaseModel):
    """식당에 연결된 메뉴 요약."""

    id: UUID  # 메뉴 ID
    name: str  # 메뉴명
    price: int = Field(ge=0)  # 가격. 원 단위


class TagCategory(BaseModel):
    """태그 분류. 가격대·메뉴 특성 등."""

    id: UUID  # 태그 카테고리 ID
    code: str  # menu_type, price_level 등 코드
    name: str  # 화면 표시명


class RestaurantTag(BaseModel):
    """식당에 붙는 개별 태그."""

    id: UUID  # 태그 ID
    category_id: UUID  # 소속 태그 카테고리
    name: str  # 태그명


class RestaurantSummary(BaseModel):
    """식당 목록·상세 공통 응답."""

    id: UUID  # 식당 ID
    name: str  # 식당명
    address: str | None = None  # 주소
    phone: str | None = None  # 전화번호
    description: str | None = None  # 설명
    storage_path: str | None = None  # 이미지 저장 경로
    category_id: UUID | None = None  # 음식 카테고리 ID
    category_name: str | None = None  # 음식 카테고리명
    kakao_place_id: str | None = None  # 카카오 장소 ID
    kakao_place_url: str | None = None  # 카카오맵 URL
    road_address: str | None = None  # 도로명 주소
    is_active: bool = True  # 운영 여부. False면 관리자가 비활성화
    menus: list[MenuSummary] = Field(default_factory=list)  # 메뉴 목록
    matched_tags: list[str] = Field(default_factory=list)  # 검색에 맞은 태그


class RestaurantCategory(BaseModel):
    """음식 카테고리. 한식·중식·일식·양식·기타."""

    id: UUID  # 카테고리 ID
    name: str  # 카테고리명

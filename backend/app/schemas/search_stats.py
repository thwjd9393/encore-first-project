"""관리자 검색정보 통계 스키마.

dashboard_search_stats 테이블의 음식·가격·특성 집계를 담는다.
stat_type 0=음식 카테고리, 1=가격대, 2=상황 태그.
"""

from pydantic import BaseModel, Field


class SearchStatPoint(BaseModel):
    """검색 통계 한 점."""

    label: str  # 화면에 보여줄 항목명
    value: int = Field(ge=0)  # 건수


class SearchStatsResponse(BaseModel):
    """관리자 검색정보 차트 데이터."""

    food: list[SearchStatPoint] = Field(default_factory=list)  # 음식 카테고리
    price: list[SearchStatPoint] = Field(default_factory=list)  # 가격대
    feature: list[SearchStatPoint] = Field(default_factory=list)  # 메뉴 특성

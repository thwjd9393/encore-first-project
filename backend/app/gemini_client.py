"""이 파일의 목적
Gemini API 키를 가져오고 음식점 추천을 위한 기본 설정을 관리한다.

작성 순서

1. Gemini API 키 가져오기
2. 모델 선택
3. 음식점 추천 BASE_PROMPT 생성
4. restaurant_categories 목록 정의
5. menu_type 태그 목록 정의
6. price_level 태그 목록 정의
7. 시스템 프롬프트 생성
"""

from pathlib import Path
import json
import os

from dotenv import load_dotenv


# =========================================================
# 1. 환경변수 로드
# =========================================================

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_client = None


def get_gemini_client():
    global _client
    if _client is not None:
        return _client
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 없습니다.")
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai 패키지가 설치되어 있지 않습니다.") from exc
    _client = genai.Client(api_key=api_key)
    return _client


# =========================================================
# 2. Gemini 모델
# =========================================================

GEMINI_MODEL = (os.getenv("GEMINI_MODEL_NAME") or "gemini-3.5-flash-lite").strip()


# =========================================================
# 3. 기본 프롬프트
# =========================================================

BASE_PROMPT = (
    "당신은 사용자의 식사 상황과 취향을 분석하는 음식점 추천 도우미입니다. "
    "사용자의 질문을 읽고 음식문화권, 메뉴 특성, 가격 조건을 파악하세요. "
    "사용자가 명확하게 말하지 않은 조건은 임의로 추측하지 마세요. "
    "분석한 조건은 반드시 제공된 카테고리와 태그 안에서만 선택하세요."
)


# =========================================================
# 4. restaurant_categories
#
# DB restaurant_categories 테이블과 동일하게 관리
# =========================================================

RESTAURANT_CATEGORIES = [
    "한식",
    "중식",
    "일식",
    "양식",
    "기타",
]


# =========================================================
# 5. tag_categories - menu_type
#
# DB tag_categories.code = menu_type
# =========================================================

MENU_TYPES = [
    "매운거",
    "든든한거",
    "국물여부",
]


# =========================================================
# 6. tag_categories - price_level
#
# DB tag_categories.code = price_level
# =========================================================

PRICE_LEVELS = [
    "인당가격_하",
    "인당가격_중",
    "인당가격_상",
]


# =========================================================
# 7. 전체 카테고리
#
# 필요하면 코드에서 한 번에 접근할 수 있도록 묶어둔다.
# =========================================================

TAG_CATEGORIES = {
    "menu_type": MENU_TYPES,
    "price_level": PRICE_LEVELS,
}


# =========================================================
# 8. Gemini 시스템 프롬프트 생성
# =========================================================

MENU_TYPE_ALIASES = {
    "매운거": "매운거",
    "매운맛": "매운거",
    "든든한거": "든든한거",
    "든든함": "든든한거",
    "국물": "국물여부",
    "국물여부": "국물여부",
}

PRICE_LEVEL_ALIASES = {
    "인당가격_하": "인당가격_하",
    "가성비": "인당가격_하",
    "저가": "인당가격_하",
    "인당가격_중": "인당가격_중",
    "중간쯤": "인당가격_중",
    "중가": "인당가격_중",
    "인당가격_상": "인당가격_상",
    "비싼거": "인당가격_상",
    "고가": "인당가격_상",
}


def build_system_prompt() -> str:
    """음식점 추천 조건 분석용 시스템 프롬프트를 만든다."""

    return "\n".join(
        [
            BASE_PROMPT,
            "",
            "[선택 가능한 음식문화권]",
            ", ".join(RESTAURANT_CATEGORIES),
            "",
            "[선택 가능한 메뉴 특성]",
            ", ".join(MENU_TYPES),
            "",
            "[선택 가능한 가격대]",
            ", ".join(PRICE_LEVELS),
            "",
            "사용자의 질문에서 해당되는 조건만 선택하세요.",
            "해당 조건이 없다면 임의로 값을 만들지 마세요.",
            "식당 이름·메뉴·가격을 만들지 마세요.",
            "반드시 JSON만 반환하세요.",
        ]
    )


def _normalize_category(value):
    if not value or not isinstance(value, str):
        return None
    name = value.strip()
    if name in RESTAURANT_CATEGORIES:
        return name
    return None


def _normalize_menu_type(value):
    if not value or not isinstance(value, str):
        return None
    return MENU_TYPE_ALIASES.get(value.strip())


def _normalize_price_level(value):
    if not value or not isinstance(value, str):
        return None
    return PRICE_LEVEL_ALIASES.get(value.strip())


def extract_conditions(user_text: str) -> dict:
    """자연어에서 추천 조건만 추출한다. 식당은 고르지 않는다."""

    empty = {
        "restaurant_category": None,
        "menu_type": None,
        "price_level": None,
    }
    text = (user_text or "").strip()
    if not text:
        return empty

    try:
        from google.genai import types

        response = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=(
                "다음 사용자 요청에서 조건만 JSON으로 추출하세요. "
                '형식: {"restaurant_category": string|null, '
                '"menu_type": string|null, "price_level": string|null}. '
                f"요청: {text}"
            ),
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(),
                response_mime_type="application/json",
            ),
        )
        raw = (response.text or "").strip()
        data = json.loads(raw) if raw else {}
    except Exception:
        return empty

    if not isinstance(data, dict):
        return empty

    return {
        "restaurant_category": _normalize_category(
            data.get("restaurant_category")
        ),
        "menu_type": _normalize_menu_type(data.get("menu_type")),
        "price_level": _normalize_price_level(data.get("price_level")),
    }


def generate_reason_from_facts(restaurant: dict) -> tuple[str, str]:
    """DB 사실만으로 추천 이유를 만든다. Gemini 실패 시 고정 문장을 쓴다."""

    fallback = _build_db_reason(restaurant)
    facts = {
        "name": restaurant.get("name"),
        "category_name": restaurant.get("category_name"),
        "address": restaurant.get("address") or restaurant.get("road_address"),
        "matched_tags": restaurant.get("matched_tags") or [],
        "menus": [
            {
                "name": menu.get("name"),
                "price": menu.get("price"),
            }
            for menu in (restaurant.get("menus") or [])[:3]
            if isinstance(menu, dict)
        ],
    }
    try:
        from google.genai import types

        response = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=(
                "아래 JSON 사실만 사용해 한국어 1~3문장, 300자 이내 추천 이유를 쓰세요. "
                "JSON에 없는 메뉴·가격·위치를 만들지 마세요.\n"
                + json.dumps(facts, ensure_ascii=False)
            ),
            config=types.GenerateContentConfig(
                system_instruction=(
                    "당신은 저장된 식당 사실만 설명합니다. "
                    "없는 정보를 추측하지 마세요."
                ),
            ),
        )
        text = (response.text or "").strip()
        if text:
            return text[:300], "gemini"
    except Exception:
        pass
    return fallback, "db_fallback"


def _build_db_reason(restaurant: dict) -> str:
    name = restaurant.get("name") or "이 식당"
    category = restaurant.get("category_name")
    tags = restaurant.get("matched_tags") or []
    menus = restaurant.get("menus") or []
    parts = [f"{name}은(는)"]
    if category:
        parts.append(f"{category} 식당입니다.")
    else:
        parts.append("저장된 식당입니다.")
    if menus:
        menu = menus[0]
        if isinstance(menu, dict) and menu.get("name"):
            menu_line = f"대표 메뉴는 {menu.get('name')}"
            if menu.get("price") is not None:
                menu_line += f"({menu['price']}원)"
            parts.append(menu_line + "입니다.")
    if tags:
        parts.append(f"{', '.join(tags)} 조건과 맞습니다.")
    return " ".join(parts)[:300]
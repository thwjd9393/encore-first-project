from pathlib import Path
import os

from dotenv import load_dotenv
from supabase import Client, create_client
from supabase.client import ClientOptions

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError(
        "backend/.env에 SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 넣으세요."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# 회원가입·로그인 요청에 사용할 새 연결 객체 만들기
def create_auth_client() -> Client:
    return create_client(
        SUPABASE_URL,
        os.environ["SUPABASE_PUBLISHABLE_KEY"],
        options=ClientOptions(
            persist_session=False,
            auto_refresh_token=False,
        ),
    )


def get_anon_client() -> Client:
    return create_auth_client()

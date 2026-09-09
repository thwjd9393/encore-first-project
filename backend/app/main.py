import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.admin_auth import AdminAuthError
from app.middleware.request_log import ApiRequestLogMiddleware
from app.routers import auth, users
from app.routers.admin_logs import router as admin_logs_router
from app.routers.chat import options_router as chat_options_router
from app.routers.chat import router as chat_router
from app.routers.conversations import conversation_router
from app.routers.feedback import router as feedback_router
from app.routers.recommendations import router as recommendations_router
from app.routers.restaurants import router as restaurants_router
from app.routers.search_stats import router as search_stats_router

app = FastAPI(title="PlayEAT", version="0.2.0")


def list_cors_origins():
    origins = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]
    extra = os.getenv("CORS_ALLOW_ORIGINS") or ""
    for item in extra.split(","):
        origin = item.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


@app.exception_handler(AdminAuthError)
async def handle_admin_auth_error(request: Request, exc: AdminAuthError):
    return exc.response

app.add_middleware(ApiRequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(restaurants_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(search_stats_router, prefix="/api/v1")
app.include_router(admin_logs_router, prefix="/api/v1")
app.include_router(users.auth_router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(conversation_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(chat_options_router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}

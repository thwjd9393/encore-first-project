import json
import time
from uuid import UUID, uuid4

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.db import supabase
from app.request_context import current_request_id

SKIP_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}
SKIP_PREFIXES = ("/static", "/assets")
ALLOWED_METHODS = {"GET", "POST", "PATCH", "DELETE"}


def should_skip_logging(path, method):
    if method not in ALLOWED_METHODS:
        return True
    if path in SKIP_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in SKIP_PREFIXES)


def resolve_request_id(header_value):
    if not header_value:
        return uuid4()
    try:
        return UUID(str(header_value).strip())
    except (ValueError, TypeError, AttributeError):
        return uuid4()


def resolve_profile_id(authorization):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    access_token = authorization.split(" ", 1)[1].strip()
    if not access_token:
        return None
    try:
        user_response = supabase.auth.get_user(access_token)
        user = getattr(user_response, "user", None)
        return getattr(user, "id", None)
    except Exception:
        return None


def read_error_code(response):
    if response.status_code < 400:
        return None
    body = getattr(response, "body", None)
    if not body:
        return None
    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        return None
    error_body = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error_body, dict):
        return error_body.get("code")
    return None


def collect_api_request_log(
    request_id,
    profile_id,
    occurred_at,
    http_method,
    endpoint_path,
    status_code,
    response_time_ms,
    error_code,
    client_type,
):
    supabase.table("api_request_logs").insert(
        {
            "request_id": str(request_id),
            "profile_id": str(profile_id) if profile_id else None,
            "occurred_at": occurred_at,
            "http_method": http_method,
            "endpoint_path": endpoint_path,
            "status_code": status_code,
            "response_time_ms": max(0, int(response_time_ms)),
            "error_code": error_code,
            "client_type": client_type,
        }
    ).execute()


class ApiRequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method.upper()
        if should_skip_logging(path, method):
            return await call_next(request)

        request_id = resolve_request_id(request.headers.get("x-request-id"))
        token = current_request_id.set(request_id)
        started = time.perf_counter()
        occurred_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        profile_id = resolve_profile_id(request.headers.get("authorization"))
        client_type = request.headers.get("x-client-type") or "streamlit"

        try:
            try:
                response = await call_next(request)
            except StarletteHTTPException:
                raise
            except Exception:
                try:
                    collect_api_request_log(
                        request_id=request_id,
                        profile_id=profile_id,
                        occurred_at=occurred_at,
                        http_method=method,
                        endpoint_path=path,
                        status_code=500,
                        response_time_ms=(time.perf_counter() - started) * 1000,
                        error_code="INTERNAL_ERROR",
                        client_type=client_type,
                    )
                except Exception:
                    pass
                error_response = JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "status": 500,
                            "code": "INTERNAL_ERROR",
                            "message": "요청을 처리하지 못했습니다.",
                            "details": [],
                            "request_id": str(request_id),
                            "timestamp": occurred_at,
                        }
                    },
                )
                error_response.headers["X-Request-ID"] = str(request_id)
                return error_response

            try:
                collect_api_request_log(
                    request_id=request_id,
                    profile_id=profile_id,
                    occurred_at=occurred_at,
                    http_method=method,
                    endpoint_path=path,
                    status_code=response.status_code,
                    response_time_ms=(time.perf_counter() - started) * 1000,
                    error_code=read_error_code(response),
                    client_type=client_type,
                )
            except Exception:
                pass
            response.headers["X-Request-ID"] = str(request_id)
            return response
        finally:
            current_request_id.reset(token)

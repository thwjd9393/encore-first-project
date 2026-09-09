import json
import os

import httpx

DEFAULT_FASTAPI_BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"
REQUEST_TIMEOUT_SECONDS = 30.0


def get_fastapi_base_url():
    env_url = (os.getenv("FASTAPI_BASE_URL") or "").strip()
    if env_url:
        return env_url.rstrip("/")
    try:
        import streamlit as st

        secret_url = str(st.secrets.get("FASTAPI_BASE_URL") or "").strip()
        if secret_url:
            return secret_url.rstrip("/")
    except Exception:
        pass
    return DEFAULT_FASTAPI_BASE_URL


def build_api_path(path):
    if not path.startswith("/"):
        path = f"/{path}"
    if path.startswith(API_PREFIX):
        return path
    return f"{API_PREFIX}{path}"


def _build_error_body(status_code, payload):
    error_body = None
    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict):
            error_body = payload["error"]
        elif isinstance(payload.get("detail"), dict) and isinstance(
            payload["detail"].get("error"), dict
        ):
            error_body = payload["detail"]["error"]
        elif isinstance(payload.get("detail"), str):
            error_body = {"message": payload["detail"]}

    if error_body:
        return {
            "status": error_body.get("status", status_code),
            "code": error_body.get("code", "UNKNOWN_ERROR"),
            "message": error_body.get("message", "요청을 처리하지 못했습니다."),
            "request_id": error_body.get("request_id"),
        }

    return {
        "status": status_code,
        "code": "UNKNOWN_ERROR",
        "message": "요청을 처리하지 못했습니다.",
        "request_id": None,
    }


def fetch_json(
    method,
    path,
    params=None,
    json_body=None,
    access_token=None,
    idempotency_key=None,
    timeout=None,
):
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    url = f"{get_fastapi_base_url()}{build_api_path(path)}"

    try:
        response = httpx.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=timeout or REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.RequestError:
        return {
            "ok": False,
            "status_code": 0,
            "data": None,
            "error": {
                "status": 0,
                "code": "NETWORK_ERROR",
                "message": "FastAPI 서버에 연결하지 못했습니다.",
                "request_id": None,
            },
        }

    if response.status_code == 204:
        return {
            "ok": True,
            "status_code": 204,
            "data": None,
            "error": None,
        }

    payload = None
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            payload = None

    if response.is_success:
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
        else:
            data = payload
        return {
            "ok": True,
            "status_code": response.status_code,
            "data": data,
            "error": None,
        }

    return {
        "ok": False,
        "status_code": response.status_code,
        "data": None,
        "error": _build_error_body(response.status_code, payload),
    }


def get_json(path, params=None, access_token=None):
    return fetch_json(
        "GET",
        path,
        params=params,
        access_token=access_token,
    )


def post_json(
    path,
    json_body=None,
    access_token=None,
    idempotency_key=None,
    timeout=None,
):
    return fetch_json(
        "POST",
        path,
        json_body=json_body,
        access_token=access_token,
        idempotency_key=idempotency_key,
        timeout=timeout,
    )


def patch_json(path, json_body=None, access_token=None):
    return fetch_json(
        "PATCH",
        path,
        json_body=json_body,
        access_token=access_token,
    )


def delete_json(path, access_token=None):
    return fetch_json(
        "DELETE",
        path,
        access_token=access_token,
    )


def list_resource_items(payload):
    if isinstance(payload, list):
        return payload, len(payload)
    if not isinstance(payload, dict):
        return [], 0

    items = (
        payload.get("items")
        or payload.get("restaurants")
        or payload.get("results")
        or payload.get("logs")
        or []
    )
    total_count = payload.get("total_count", payload.get("total", len(items)))
    return items, total_count


# 채팅 스트리밍
def stream_post(
    path,
    json_body=None,
    access_token=None,
    timeout=None,
):
    headers = {
        "Accept": "text/event-stream",
    }

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    url = f"{get_fastapi_base_url()}{build_api_path(path)}"

    try:
        with httpx.stream(
            "POST",
            url,
            json=json_body,
            headers=headers,
            timeout=timeout or REQUEST_TIMEOUT_SECONDS,
        ) as response:

            response.raise_for_status()

            for line in response.iter_lines():

                if not line:
                    continue

                if not line.startswith("data: "):
                    continue

                raw = line.removeprefix("data: ")

                try:
                    yield json.loads(raw)
                except ValueError:
                    continue

    except httpx.RequestError as error:
        yield {
            "error": f"FastAPI 서버에 연결하지 못했습니다: {error}"
        }

    except httpx.HTTPStatusError as error:
        yield {
            "error": f"요청 실패: {error.response.status_code}"
        }
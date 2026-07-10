import json
import time
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models import ApiKey, UsageLog
from common.config import conf
from common.logger import my_logger


def _chat_completions_url() -> str:
    base = conf.MODEL_BASE_URL.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


async def proxy_chat_completions(
    request: Request,
    body: dict[str, Any],
    api_key: ApiKey,
    db: Session,
) -> Any:
    url = _chat_completions_url()
    headers = {
        "Authorization": f"Bearer {conf.MODEL_API_KEY}",
        "Content-Type": "application/json",
    }
    stream = bool(body.get("stream", False))
    model = str(body.get("model", conf.MODEL_NAME or "unknown"))
    started = time.perf_counter()
    my_logger.info("Proxy chat: tenant=%s model=%s stream=%s", api_key.tenant_id, model, stream)

    async with httpx.AsyncClient(timeout=120.0) as client:
        if stream:
            return await _stream_response(client, url, headers, body, api_key, db, model, started)
        return await _json_response(client, url, headers, body, api_key, db, model, started)


async def _json_response(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    api_key: ApiKey,
    db: Session,
    model: str,
    started: float,
) -> dict[str, Any]:
    try:
        resp = await client.post(url, headers=headers, json=body)
        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = resp.json()
        usage = payload.get("usage") or {}
        _log_usage(
            db,
            api_key,
            model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            latency_ms,
            "success" if resp.is_success else "error",
            None if resp.is_success else resp.text[:500],
        )
        resp.raise_for_status()
        my_logger.info("Chat success: model=%s latency=%sms", model, latency_ms)
        return payload
    except httpx.HTTPStatusError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_usage(db, api_key, model, 0, 0, latency_ms, "error", str(exc)[:500])
        my_logger.error("Upstream HTTP error: model=%s status=%s", model, exc.response.status_code)
        raise
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_usage(db, api_key, model, 0, 0, latency_ms, "error", str(exc)[:500])
        my_logger.exception("Chat proxy failed: model=%s", model)
        raise


async def _stream_response(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    api_key: ApiKey,
    db: Session,
    model: str,
    started: float,
) -> StreamingResponse:
    async def event_generator():
        prompt_tokens = 0
        completion_tokens = 0
        status = "success"
        error_message = None
        try:
            async with client.stream("POST", url, headers=headers, json=body) as resp:
                if resp.is_error:
                    status = "error"
                    error_message = (await resp.aread()).decode()[:500]
                    my_logger.error("Stream upstream error: model=%s", model)
                    yield error_message
                    return
                async for chunk in resp.aiter_bytes():
                    text = chunk.decode(errors="ignore")
                    for line in text.splitlines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            event = json.loads(data)
                            usage = event.get("usage")
                            if usage:
                                prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                                completion_tokens = usage.get("completion_tokens", completion_tokens)
                        except json.JSONDecodeError:
                            pass
                    yield chunk
        except Exception as exc:
            status = "error"
            error_message = str(exc)[:500]
            my_logger.exception("Stream proxy failed: model=%s", model)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            _log_usage(db, api_key, model, prompt_tokens, completion_tokens, latency_ms, status, error_message)
            my_logger.info("Stream finished: model=%s latency=%sms status=%s", model, latency_ms, status)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _log_usage(
    db: Session,
    api_key: ApiKey,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    status: str,
    error_message: str | None,
) -> None:
    db.add(
        UsageLog(
            api_key_id=api_key.id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
    )
    db.commit()

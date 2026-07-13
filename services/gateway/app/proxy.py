import json
import time
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models import ApiKey, UsageLog
from common.logger import my_logger
from common.model_router import (
    RouteDecision,
    UpstreamTarget,
    chat_completions_url,
    get_fallback_target,
    route_request,
)
from common.tracing import log_generation, trace_span


async def proxy_chat_completions(
    request: Request,
    body: dict[str, Any],
    api_key: ApiKey,
    db: Session,
) -> Any:
    decision = route_request(body, tenant_id=api_key.tenant_id)
    body = {**body, "model": decision.model}
    stream = bool(body.get("stream", False))
    started = time.perf_counter()
    my_logger.info(
        "Proxy chat: tenant=%s model=%s provider=%s reason=%s stream=%s",
        api_key.tenant_id,
        decision.model,
        decision.target.provider,
        decision.reason,
        stream,
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        with trace_span(
            "gateway-chat",
            user_id=api_key.tenant_id,
            session_id=str(api_key.id),
            input_data={"model": body.get("model"), "tenant": api_key.tenant_id},
            tags=["gateway"],
        ) as trace:
            try:
                if stream:
                    return await _stream_response(client, body, api_key, db, decision, started, trace)
                return await _json_response(client, body, api_key, db, decision, started, trace)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise
                return await _try_fallback(client, body, api_key, db, decision, started, stream, exc, trace)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                return await _try_fallback(client, body, api_key, db, decision, started, stream, exc, trace)


async def _try_fallback(
    client: httpx.AsyncClient,
    body: dict[str, Any],
    api_key: ApiKey,
    db: Session,
    decision: RouteDecision,
    started: float,
    stream: bool,
    original_exc: Exception,
    trace: Any = None,
) -> Any:
    fallback = get_fallback_target()
    if fallback is None or fallback.model == decision.model:
        raise original_exc

    my_logger.warning("Fallback: %s -> %s", decision.model, fallback.model)
    fb_decision = RouteDecision(model=fallback.model, target=fallback, reason="fallback")
    body = {**body, "model": fallback.model}
    if stream:
        return await _stream_response(client, body, api_key, db, fb_decision, started, trace)
    return await _json_response(client, body, api_key, db, fb_decision, started, trace)


def _headers(target: UpstreamTarget) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {target.api_key}",
        "Content-Type": "application/json",
    }


async def _json_response(
    client: httpx.AsyncClient,
    body: dict[str, Any],
    api_key: ApiKey,
    db: Session,
    decision: RouteDecision,
    started: float,
    trace: Any = None,
) -> dict[str, Any]:
    url = chat_completions_url(decision.target)
    try:
        resp = await client.post(url, headers=_headers(decision.target), json=body)
        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = resp.json()
        usage = payload.get("usage") or {}
        _log_usage(
            db,
            api_key,
            decision.model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            latency_ms,
            "success" if resp.is_success else "error",
            None if resp.is_success else resp.text[:500],
            decision.reason,
        )
        resp.raise_for_status()
        payload.setdefault("x_route_reason", decision.reason)
        payload.setdefault("x_provider", decision.target.provider)
        log_generation(
            trace,
            name="chat",
            model=decision.model,
            input_data=body.get("messages"),
            output_data=payload.get("choices"),
            usage=usage,
            metadata={"provider": decision.target.provider, "reason": decision.reason},
        )
        my_logger.info("Chat success: model=%s provider=%s latency=%sms", decision.model, decision.target.provider, latency_ms)
        return payload
    except httpx.HTTPStatusError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_usage(db, api_key, decision.model, 0, 0, latency_ms, "error", "upstream_http_error", decision.reason)
        raise
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_usage(db, api_key, decision.model, 0, 0, latency_ms, "error", str(exc)[:500], decision.reason)
        my_logger.exception("Chat proxy failed: model=%s", decision.model)
        raise


async def _stream_response(
    client: httpx.AsyncClient,
    body: dict[str, Any],
    api_key: ApiKey,
    db: Session,
    decision: RouteDecision,
    started: float,
    trace: Any = None,
) -> StreamingResponse:
    url = chat_completions_url(decision.target)
    headers = _headers(decision.target)

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
                    my_logger.error("Stream upstream error: model=%s", decision.model)
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
            my_logger.exception("Stream proxy failed: model=%s", decision.model)
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            _log_usage(
                db, api_key, decision.model, prompt_tokens, completion_tokens,
                latency_ms, status, error_message, decision.reason,
            )

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
    route_reason: str = "",
) -> None:
    msg = error_message or ""
    if route_reason and status == "success":
        msg = route_reason
    db.add(
        UsageLog(
            api_key_id=api_key.id,
            tenant_id=api_key.tenant_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=msg[:500] if msg else None,
        )
    )
    db.commit()

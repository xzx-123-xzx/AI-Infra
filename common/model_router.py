"""模型路由：智能选模、本地/API 分流、Fallback。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from common.config import conf
from common.logger import my_logger


@dataclass
class UpstreamTarget:
    base_url: str
    api_key: str
    model: str
    provider: str  # api | local | inference


@dataclass
class RouteDecision:
    model: str
    target: UpstreamTarget
    reason: str


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    total = 0
    for msg in messages or []:
        content = msg.get("content") or ""
        if isinstance(content, str):
            total += max(len(content) // 3, 1)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += max(len(part.get("text", "")) // 3, 1)
    return total


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def is_local_model(model: str) -> bool:
    return model in conf.local_model_set


def resolve_model(body: dict[str, Any]) -> tuple[str, str]:
    """返回 (实际模型名, 路由原因)。"""
    requested = str(body.get("model") or conf.MODEL_NAME or "gpt-4o-mini")

    if requested != "auto":
        if is_local_model(requested):
            return requested, "explicit_local"
        return requested, "explicit"

    if not conf.ROUTING_ENABLED:
        return conf.MODEL_NAME or requested, "auto_disabled"

    messages = body.get("messages") or []
    tokens = estimate_tokens(messages)
    if tokens >= conf.ROUTING_TOKEN_THRESHOLD:
        model = conf.ROUTING_COMPLEX_MODEL or conf.MODEL_NAME
        return model, f"auto_complex_tokens={tokens}"

    model = conf.ROUTING_SIMPLE_MODEL or conf.MODEL_NAME
    return model, f"auto_simple_tokens={tokens}"


def get_upstream(model: str) -> UpstreamTarget:
    if is_local_model(model):
        return UpstreamTarget(
            base_url=conf.INFERENCE_BASE_URL or conf.VLLM_BASE_URL,
            api_key=conf.INFERENCE_API_KEY or "local",
            model=model,
            provider="local",
        )
    return UpstreamTarget(
        base_url=conf.MODEL_BASE_URL,
        api_key=conf.MODEL_API_KEY,
        model=model,
        provider="api",
    )


def get_fallback_target() -> UpstreamTarget | None:
    if not conf.FALLBACK_MODEL:
        return None
    return get_upstream(conf.FALLBACK_MODEL)


def route_request(body: dict[str, Any], tenant_id: str = "default") -> RouteDecision:
    model, reason = resolve_model(body)
    try:
        from app.canary import apply_canary

        model, canary_reason = apply_canary(model, tenant_id)
        if canary_reason.startswith("canary"):
            reason = f"{reason};{canary_reason}"
    except ImportError:
        pass
    target = get_upstream(model)
    my_logger.info("Route decision: model=%s provider=%s reason=%s", model, target.provider, reason)
    return RouteDecision(model=model, target=target, reason=reason)


def chat_completions_url(target: UpstreamTarget) -> str:
    return _chat_url(target.base_url)


def all_available_models() -> list[dict[str, str]]:
    models: list[dict[str, str]] = []
    for name in conf.model_list:
        provider = "local" if is_local_model(name) else "api"
        models.append({"id": name, "provider": provider})
    if conf.ROUTING_ENABLED:
        models.append({"id": "auto", "provider": "router"})
    for name in sorted(conf.local_model_set):
        if not any(m["id"] == name for m in models):
            models.append({"id": name, "provider": "local"})
    return models

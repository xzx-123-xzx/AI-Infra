"""Langfuse 全链路 Trace（未配置时静默 no-op）。"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from common.config import conf
from common.logger import my_logger

_langfuse = None


def _client():
    global _langfuse
    if not conf.langfuse_enabled:
        return None
    if _langfuse is None:
        try:
            from langfuse import Langfuse

            _langfuse = Langfuse(
                public_key=conf.LANGFUSE_PUBLIC_KEY,
                secret_key=conf.LANGFUSE_SECRET_KEY,
                host=conf.LANGFUSE_HOST or None,
            )
        except Exception:
            my_logger.exception("Langfuse init failed")
            return None
    return _langfuse


@contextmanager
def trace_span(
    name: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    input_data: Any = None,
    tags: list[str] | None = None,
) -> Iterator[Any]:
    client = _client()
    if client is None:
        yield None
        return

    trace = client.trace(
        name=name,
        user_id=user_id,
        session_id=session_id,
        metadata=metadata or {},
        input=input_data,
        tags=tags or [],
    )
    try:
        yield trace
    finally:
        try:
            client.flush()
        except Exception:
            pass


def log_generation(
    trace: Any,
    *,
    name: str,
    model: str,
    input_data: Any,
    output_data: Any,
    usage: dict[str, int] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if trace is None:
        return
    try:
        trace.generation(
            name=name,
            model=model,
            input=input_data,
            output=output_data,
            usage=usage,
            metadata=metadata or {},
        )
    except Exception:
        my_logger.exception("Langfuse generation log failed")


def log_retrieval(
    trace: Any,
    *,
    name: str,
    query: str,
    hits: list[dict],
    metadata: dict[str, Any] | None = None,
) -> None:
    if trace is None:
        return
    try:
        trace.span(
            name=name,
            input={"query": query},
            output={"count": len(hits), "hits": hits[:10]},
            metadata=metadata or {},
        )
    except Exception:
        my_logger.exception("Langfuse retrieval log failed")

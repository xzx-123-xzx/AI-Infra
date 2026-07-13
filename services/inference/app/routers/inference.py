import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from common.config import conf
from common.logger import my_logger

router = APIRouter(prefix="/v1", tags=["inference"])


def _vllm_chat_url() -> str:
    base = conf.VLLM_BASE_URL.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {conf.VLLM_API_KEY}",
        "Content-Type": "application/json",
    }


@router.get("/models")
async def list_models():
    base = conf.VLLM_BASE_URL.rstrip("/")
    url = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=_headers())
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"vLLM unreachable: {exc}") from exc


@router.post("/chat/completions")
async def chat_completions(request: Request, body: dict[str, Any]):
    stream = bool(body.get("stream", False))
    model = body.get("model", "unknown")
    started = time.perf_counter()
    my_logger.info("Inference proxy: model=%s stream=%s", model, stream)

    async with httpx.AsyncClient(timeout=300.0) as client:
        if stream:
            return await _stream(client, body)
        try:
            resp = await client.post(_vllm_chat_url(), headers=_headers(), json=body)
            latency = int((time.perf_counter() - started) * 1000)
            my_logger.info("Inference success: model=%s latency=%sms", model, latency)
            if resp.is_error:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except HTTPException:
            raise
        except Exception as exc:
            my_logger.exception("Inference failed: model=%s", model)
            raise HTTPException(status_code=502, detail=str(exc)) from exc


async def _stream(client: httpx.AsyncClient, body: dict[str, Any]) -> StreamingResponse:
    async def gen():
        async with client.stream("POST", _vllm_chat_url(), headers=_headers(), json=body) as resp:
            if resp.is_error:
                yield (await resp.aread()).decode()
                return
            async for chunk in resp.aiter_bytes():
                yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream")

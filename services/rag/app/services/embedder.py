import asyncio

import httpx

from common.config import conf
from common.logger import my_logger


async def _embed_via_api(texts: list[str]) -> list[list[float]]:
    if not conf.MODEL_API_KEY:
        raise ValueError("MODEL_API_KEY is not configured for API embedding")

    headers = {
        "Authorization": f"Bearer {conf.MODEL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": conf.EMBEDDING_MODEL, "input": texts}

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(conf.embedding_url(), headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()["data"]
        data.sort(key=lambda item: item["index"])
        vectors = [item["embedding"] for item in data]
        my_logger.info("API embedded %s texts model=%s", len(texts), conf.EMBEDDING_MODEL)
        return vectors


def _embed_via_bge(texts: list[str]) -> list[list[float]]:
    from common.bge_embedding import encode_dense

    return encode_dense(texts)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    if conf.use_local_embedding:
        return await asyncio.to_thread(_embed_via_bge, texts)
    return await _embed_via_api(texts)

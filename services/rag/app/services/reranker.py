import asyncio

from common.config import conf
from common.logger import my_logger


async def rerank_hits(query: str, hits: list[dict], top_k: int) -> list[dict]:
    if not hits:
        return []
    if not conf.use_local_rerank:
        return hits[:top_k]

    passages = [hit["content"] for hit in hits]
    scores = await asyncio.to_thread(_rerank_sync, query, passages)
    ranked = []
    for hit, score in zip(hits, scores):
        item = dict(hit)
        item["rerank_score"] = score
        ranked.append(item)
    ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    result = ranked[:top_k]
    my_logger.info("Reranked %s -> %s hits", len(hits), len(result))
    return result


def _rerank_sync(query: str, passages: list[str]) -> list[float]:
    from common.bge_reranker import rerank_pairs

    return rerank_pairs(query, passages)

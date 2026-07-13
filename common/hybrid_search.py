"""Reciprocal Rank Fusion (RRF) 混合检索融合。"""

from __future__ import annotations


def rrf_fusion(
    *result_lists: list[dict],
    k: int = 60,
    id_key: str = "chunk_id",
) -> list[dict]:
    """合并多路检索结果，按 RRF 分数降序。"""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for results in result_lists:
        for rank, hit in enumerate(results, start=1):
            chunk_id = str(hit.get(id_key) or "")
            if not chunk_id:
                continue
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            if chunk_id not in items:
                items[chunk_id] = dict(hit)

    merged = []
    for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        row = items[chunk_id]
        row["rrf_score"] = score
        merged.append(row)
    return merged

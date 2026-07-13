"""跨知识库联邦检索与联合问答。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import KnowledgeBase
from app.services.rag_chain import retrieve
from common.hybrid_search import rrf_fusion
from common.logger import my_logger


def verify_kb_access(db: Session, kb_ids: list[int], tenant_id: str) -> list[KnowledgeBase]:
    kbs = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id.in_(kb_ids), KnowledgeBase.status == "active")
        .all()
    )
    if len(kbs) != len(set(kb_ids)):
        found = {kb.id for kb in kbs}
        missing = set(kb_ids) - found
        raise ValueError(f"Knowledge bases not found: {sorted(missing)}")

    denied = [kb.id for kb in kbs if kb.tenant_id != tenant_id]
    if denied:
        raise PermissionError(f"Tenant {tenant_id} cannot access kb_ids: {denied}")
    return kbs


async def federated_retrieve(
    db: Session,
    kb_ids: list[int],
    query: str,
    tenant_id: str,
    top_k: int | None = None,
) -> list[dict]:
    from common.config import conf

    verify_kb_access(db, kb_ids, tenant_id)
    k = top_k or conf.RETRIEVAL_K
    per_kb = max(k, conf.retrieval_candidates)

    all_hits: list[list[dict]] = []
    for kb_id in kb_ids:
        hits = await retrieve(kb_id, query, per_kb)
        for hit in hits:
            hit["kb_id"] = kb_id
        all_hits.append(hits)

    merged = rrf_fusion(*all_hits) if len(all_hits) > 1 else (all_hits[0] if all_hits else [])
    my_logger.info("Federated retrieve: kb_ids=%s hits=%s", kb_ids, len(merged))
    return merged[:k]

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.services.embedder import embed_texts
from app.services.es_store import search_chunks as es_search
from app.services.milvus_store import search_chunks as milvus_search
from app.services.prompt_service import resolve_prompt
from app.services.reranker import rerank_hits
from common.config import conf
from common.hybrid_search import rrf_fusion
from common.llm import my_llm
from common.logger import my_logger
from common.tracing import log_generation, log_retrieval, trace_span


async def retrieve(kb_id: int, query: str, top_k: int | None = None) -> list[dict]:
    k = top_k or conf.RETRIEVAL_K
    vectors = await embed_texts([query])
    vector_hits = milvus_search(kb_id, vectors[0], conf.retrieval_candidates)
    for hit in vector_hits:
        hit["source"] = "vector"

    if conf.HYBRID_SEARCH_ENABLED:
        keyword_hits = es_search(kb_id, query, conf.retrieval_candidates)
        candidates = rrf_fusion(vector_hits, keyword_hits, k=conf.RRF_K)
    else:
        candidates = vector_hits

    return await rerank_hits(query, candidates, k)


async def chat_with_kb(
    kb_id: int,
    query: str,
    top_k: int | None = None,
    *,
    db: Session | None = None,
    prompt_template_id: int | None = None,
    prompt_variables: dict[str, str] | None = None,
    tenant_id: str = "default",
    session_id: str | None = None,
) -> dict:
    with trace_span(
        "rag-chat",
        user_id=tenant_id,
        session_id=session_id or f"kb-{kb_id}",
        input_data={"query": query, "kb_id": kb_id},
        tags=["rag"],
    ) as trace:
        hits = await retrieve(kb_id, query, top_k)
        log_retrieval(
            trace,
            name="retrieve",
            query=query,
            hits=hits,
            metadata={"kb_id": kb_id, "hybrid": conf.HYBRID_SEARCH_ENABLED},
        )

        if db is not None:
            system_prompt, prompt_meta = resolve_prompt(
                db,
                template_id=prompt_template_id,
                tenant_id=tenant_id,
                variables=prompt_variables,
                ab_bucket=session_id or tenant_id,
            )
        else:
            system_prompt = conf.DEFAULT_RAG_SYSTEM_PROMPT
            prompt_meta = {"source": "default"}

        if not hits:
            return {
                "answer": "知识库中未找到相关内容，无法回答该问题。",
                "sources": [],
                "prompt_meta": prompt_meta,
            }

        context_blocks = []
        for idx, hit in enumerate(hits, start=1):
            score = hit.get("rerank_score", hit.get("rrf_score", hit.get("score")))
            context_blocks.append(
                f"[{idx}] doc_id={hit['doc_id']} chunk={hit['chunk_index']} score={score}\n{hit['content']}"
            )
        context = "\n\n".join(context_blocks)
        user_prompt = f"上下文：\n{context}\n\n问题：{query}"

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = my_llm.invoke(messages)
        answer = response.content if hasattr(response, "content") else str(response)

        log_generation(
            trace,
            name="llm",
            model=conf.MODEL_NAME,
            input_data={"system": system_prompt[:500], "user": user_prompt[:2000]},
            output_data=answer,
            metadata={"prompt_meta": prompt_meta, "source_count": len(hits)},
        )
        my_logger.info(
            "RAG chat completed: kb_id=%s sources=%s hybrid=%s prompt=%s",
            kb_id, len(hits), conf.HYBRID_SEARCH_ENABLED, prompt_meta.get("source"),
        )

        return {
            "answer": answer,
            "sources": hits,
            "prompt_meta": prompt_meta,
        }

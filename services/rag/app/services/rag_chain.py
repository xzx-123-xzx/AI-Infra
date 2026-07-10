from langchain_core.messages import HumanMessage, SystemMessage

from app.services.embedder import embed_texts
from app.services.milvus_store import search_chunks
from app.services.reranker import rerank_hits
from common.config import conf
from common.llm import my_llm
from common.logger import my_logger

SYSTEM_PROMPT = """你是企业知识库问答助手。请仅根据提供的上下文回答问题。
如果上下文不足以回答，请明确说明不知道，不要编造。
回答时引用相关事实，保持简洁准确。"""


async def retrieve(kb_id: int, query: str, top_k: int | None = None) -> list[dict]:
    k = top_k or conf.RETRIEVAL_K
    vectors = await embed_texts([query])
    candidates = search_chunks(kb_id, vectors[0], conf.retrieval_candidates)
    return await rerank_hits(query, candidates, k)


async def chat_with_kb(kb_id: int, query: str, top_k: int | None = None) -> dict:
    hits = await retrieve(kb_id, query, top_k)
    if not hits:
        return {
            "answer": "知识库中未找到相关内容，无法回答该问题。",
            "sources": [],
        }

    context_blocks = []
    for idx, hit in enumerate(hits, start=1):
        score = hit.get("rerank_score", hit.get("score"))
        context_blocks.append(
            f"[{idx}] doc_id={hit['doc_id']} chunk={hit['chunk_index']} score={score}\n{hit['content']}"
        )
    context = "\n\n".join(context_blocks)
    user_prompt = f"上下文：\n{context}\n\n问题：{query}"

    response = my_llm.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )
    answer = response.content if hasattr(response, "content") else str(response)
    my_logger.info("RAG chat completed: kb_id=%s sources=%s rerank=%s", kb_id, len(hits), conf.use_local_rerank)

    return {
        "answer": answer,
        "sources": hits,
    }

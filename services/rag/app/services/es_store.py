"""Elasticsearch BM25 关键词检索。"""

from __future__ import annotations

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

from common.config import conf
from common.logger import my_logger

_client: Elasticsearch | None = None


def _index_name() -> str:
    return conf.ES_INDEX_PREFIX or "aiinfra_chunks"


def get_client() -> Elasticsearch:
    global _client
    if _client is None:
        _client = Elasticsearch(conf.es_url, request_timeout=30)
    return _client


def ensure_index() -> None:
    client = get_client()
    name = _index_name()
    if client.indices.exists(index=name):
        return
    client.indices.create(
        index=name,
        settings={"number_of_shards": 1, "number_of_replicas": 0},
        mappings={
            "properties": {
                "chunk_id": {"type": "keyword"},
                "kb_id": {"type": "integer"},
                "doc_id": {"type": "integer"},
                "chunk_index": {"type": "integer"},
                "content": {"type": "text"},
            }
        },
    )
    my_logger.info("Created ES index: %s", name)


def index_chunks(
    kb_id: int,
    doc_id: int,
    chunk_ids: list[str],
    chunks: list[str],
    chunk_indices: list[int] | None = None,
) -> int:
    if not conf.HYBRID_SEARCH_ENABLED:
        return 0
    ensure_index()
    client = get_client()
    name = _index_name()
    indices = chunk_indices if chunk_indices is not None else list(range(len(chunks)))
    ops = []
    for chunk_id, content, idx in zip(chunk_ids, chunks, indices):
        ops.append({"index": {"_index": name, "_id": chunk_id}})
        ops.append(
            {
                "chunk_id": chunk_id,
                "kb_id": kb_id,
                "doc_id": doc_id,
                "chunk_index": idx,
                "content": content,
            }
        )
    if ops:
        client.bulk(operations=ops, refresh="wait_for")
    return len(chunks)


def search_chunks(kb_id: int, query: str, top_k: int) -> list[dict]:
    if not conf.HYBRID_SEARCH_ENABLED:
        return []
    ensure_index()
    client = get_client()
    resp = client.search(
        index=_index_name(),
        query={
            "bool": {
                "must": [{"match": {"content": query}}],
                "filter": [{"term": {"kb_id": kb_id}}],
            }
        },
        size=top_k,
    )
    hits: list[dict] = []
    for hit in resp["hits"]["hits"]:
        src = hit["_source"]
        hits.append(
            {
                "chunk_id": src.get("chunk_id"),
                "doc_id": src.get("doc_id"),
                "chunk_index": src.get("chunk_index"),
                "content": src.get("content"),
                "score": float(hit.get("_score") or 0),
                "source": "bm25",
            }
        )
    return hits


def delete_by_kb(kb_id: int) -> None:
    if not conf.HYBRID_SEARCH_ENABLED:
        return
    try:
        get_client().delete_by_query(
            index=_index_name(),
            query={"term": {"kb_id": kb_id}},
            refresh=True,
        )
    except NotFoundError:
        pass


def delete_by_doc(kb_id: int, doc_id: int) -> None:
    if not conf.HYBRID_SEARCH_ENABLED:
        return
    try:
        get_client().delete_by_query(
            index=_index_name(),
            query={"bool": {"filter": [{"term": {"kb_id": kb_id}}, {"term": {"doc_id": doc_id}}]}},
            refresh=True,
        )
    except NotFoundError:
        pass


def ping() -> bool:
    if not conf.HYBRID_SEARCH_ENABLED:
        return False
    try:
        return bool(get_client().ping())
    except Exception:
        return False

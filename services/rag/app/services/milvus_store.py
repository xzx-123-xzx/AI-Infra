import uuid

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from common.config import conf
from common.logger import my_logger

_collection: Collection | None = None


def _connect() -> None:
    if not connections.has_connection("default"):
        connections.connect(
            alias="default",
            host=conf.MILVUS_HOST,
            port=str(conf.MILVUS_PORT),
        )


def get_collection() -> Collection:
    global _collection
    _connect()
    if _collection is not None:
        return _collection

    name = conf.MILVUS_COLLECTION_NAME or "aiinfra_kb"
    dim = conf.embedding_dimension

    if utility.has_collection(name):
        collection = Collection(name)
        for field in collection.schema.fields:
            if field.name == "embedding":
                existing_dim = field.params.get("dim")
                if existing_dim and int(existing_dim) != dim:
                    raise RuntimeError(
                        f"Milvus collection '{name}' dim={existing_dim}, "
                        f"expected {dim}. Drop collection or align EMBEDDING_DIMENSION / BGE_EMBEDDING_DIMENSION."
                    )
                break
    else:
        fields = [
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="kb_id", dtype=DataType.INT64),
            FieldSchema(name="doc_id", dtype=DataType.INT64),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields, description="AI-Infra knowledge base chunks")
        collection = Collection(name, schema)
        collection.create_index(
            "embedding",
            {"index_type": "AUTOINDEX", "metric_type": "COSINE"},
        )
        my_logger.info("Created Milvus collection: %s dim=%s", name, dim)

    collection.load()
    _collection = collection
    return collection


def insert_chunks(
    kb_id: int,
    doc_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    chunk_ids: list[str] | None = None,
    chunk_indices: list[int] | None = None,
) -> tuple[int, list[str]]:
    collection = get_collection()
    ids = chunk_ids or [uuid.uuid4().hex for _ in chunks]
    indices = chunk_indices if chunk_indices is not None else list(range(len(chunks)))
    collection.insert([
        ids,
        [kb_id] * len(chunks),
        [doc_id] * len(chunks),
        indices,
        chunks,
        embeddings,
    ])
    collection.flush()
    return len(chunks), ids


def delete_chunks_by_ids(chunk_ids: list[str]) -> None:
    if not chunk_ids:
        return
    collection = get_collection()
    quoted = ", ".join(f'"{cid}"' for cid in chunk_ids)
    collection.delete(expr=f"chunk_id in [{quoted}]")
    collection.flush()


def search_chunks(kb_id: int, query_vector: list[float], top_k: int) -> list[dict]:
    collection = get_collection()
    results = collection.search(
        data=[query_vector],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {}},
        limit=top_k,
        expr=f"kb_id == {kb_id}",
        output_fields=["chunk_id", "doc_id", "chunk_index", "content"],
    )
    hits: list[dict] = []
    for hit in results[0]:
        hits.append(
            {
                "chunk_id": hit.entity.get("chunk_id"),
                "doc_id": hit.entity.get("doc_id"),
                "chunk_index": hit.entity.get("chunk_index"),
                "content": hit.entity.get("content"),
                "score": float(hit.distance),
            }
        )
    return hits


def delete_by_kb(kb_id: int) -> None:
    collection = get_collection()
    collection.delete(expr=f"kb_id == {kb_id}")
    collection.flush()
    my_logger.info("Deleted Milvus chunks for kb_id=%s", kb_id)


def delete_by_doc(kb_id: int, doc_id: int) -> None:
    collection = get_collection()
    collection.delete(expr=f"kb_id == {kb_id} and doc_id == {doc_id}")
    collection.flush()
    my_logger.info("Deleted Milvus chunks for kb_id=%s doc_id=%s", kb_id, doc_id)

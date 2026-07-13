from fastapi import APIRouter

from app.database import engine
from app.services.es_store import ping as es_ping
from app.services.milvus_store import get_collection
from common.config import conf
from common.logger import my_logger

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "rag",
        "embedding_backend": "bge" if conf.use_local_embedding else "api",
        "rerank_backend": "bge" if conf.use_local_rerank else "off",
        "embedding_dimension": conf.embedding_dimension,
        "hybrid_search": conf.HYBRID_SEARCH_ENABLED,
        "elasticsearch": es_ping() if conf.HYBRID_SEARCH_ENABLED else None,
        "langfuse": conf.langfuse_enabled,
        "ingestion_async": conf.INGESTION_ASYNC,
        "ocr_backend": conf.OCR_BACKEND,
        "asr_backend": conf.ASR_BACKEND,
    }


@router.get("/ready")
def ready():
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    get_collection()
    if conf.use_local_embedding:
        from common.bge_embedding import get_bge_embedding_model

        get_bge_embedding_model()
    if conf.use_local_rerank:
        from common.bge_reranker import get_bge_reranker

        get_bge_reranker()
    my_logger.info("RAG readiness check passed")
    return {"status": "ready"}

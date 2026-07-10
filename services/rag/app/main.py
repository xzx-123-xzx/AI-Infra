from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import chat, documents, health, knowledge_bases, retrieve
from app.services.milvus_store import get_collection
from common.config import conf
from common.cors import setup_cors
from common.logger import my_logger
from common.metrics import setup_metrics
from common.path_utils import root_dir


def _warmup_local_models() -> None:
    if conf.use_local_embedding:
        from common.bge_embedding import warmup as embed_warmup

        embed_warmup()
        my_logger.info("BGE-M3 warmup done")
    if conf.use_local_rerank:
        from common.bge_reranker import warmup as rerank_warmup

        rerank_warmup()
        my_logger.info("BGE Reranker warmup done")


@asynccontextmanager
async def lifespan(_: FastAPI):
    my_logger.info(
        "RAG service starting: root=%s port=%s embed=%s rerank=%s dim=%s",
        root_dir,
        conf.RAG_PORT,
        "bge" if conf.use_local_embedding else "api",
        "bge" if conf.use_local_rerank else "off",
        conf.embedding_dimension,
    )
    try:
        get_collection()
        my_logger.info("Milvus collection ready")
    except Exception:
        my_logger.exception("Milvus init failed on startup")
    try:
        _warmup_local_models()
    except Exception:
        my_logger.exception("Local model warmup failed")
    yield
    my_logger.info("RAG service stopped")


app = FastAPI(title=conf.RAG_APP_NAME, lifespan=lifespan)
setup_cors(app)
setup_metrics(app)
app.include_router(health.router)
app.include_router(knowledge_bases.router)
app.include_router(documents.router)
app.include_router(retrieve.router)
app.include_router(chat.router)

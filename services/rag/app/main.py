import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import chat, documents, eval, federated, health, knowledge_bases, prompts, retrieve, sync
from app.services.milvus_store import get_collection
from app.worker import ingest_worker_loop, sync_scheduler_loop
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
        "RAG service starting: root=%s port=%s embed=%s async=%s ocr=%s",
        root_dir,
        conf.RAG_PORT,
        "bge" if conf.use_local_embedding else "api",
        conf.INGESTION_ASYNC,
        conf.OCR_BACKEND,
    )
    stop = asyncio.Event()
    worker_task = None
    sync_task = None
    try:
        get_collection()
        my_logger.info("Milvus collection ready")
    except Exception:
        my_logger.exception("Milvus init failed on startup")
    try:
        _warmup_local_models()
    except Exception:
        my_logger.exception("Local model warmup failed")

    if conf.INGESTION_WORKER_ENABLED:
        worker_task = asyncio.create_task(ingest_worker_loop(stop))
        sync_task = asyncio.create_task(sync_scheduler_loop(stop))

    yield

    stop.set()
    if worker_task:
        await worker_task
    if sync_task:
        await sync_task
    my_logger.info("RAG service stopped")


app = FastAPI(title=conf.RAG_APP_NAME, lifespan=lifespan)
setup_cors(app)
setup_metrics(app)
app.include_router(health.router)
app.include_router(knowledge_bases.router)
app.include_router(documents.router)
app.include_router(sync.router)
app.include_router(federated.router)
app.include_router(eval.router)
app.include_router(prompts.router)
app.include_router(retrieve.router)
app.include_router(chat.router)

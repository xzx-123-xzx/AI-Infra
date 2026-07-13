import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import jobs, registry
from app.worker import mlops_worker_loop
from common.config import conf
from common.cors import setup_cors
from common.logger import my_logger
from common.metrics import setup_metrics


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop = asyncio.Event()
    task = None
    if conf.MLOPS_WORKER_ENABLED:
        task = asyncio.create_task(mlops_worker_loop(stop))
    my_logger.info("MLOps service started port=%s", conf.MLOPS_PORT)
    yield
    stop.set()
    if task:
        await task
    my_logger.info("MLOps service stopped")


app = FastAPI(title=conf.MLOPS_APP_NAME, lifespan=lifespan)
setup_cors(app)
setup_metrics(app)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mlops"}


app.include_router(jobs.router)
app.include_router(registry.router)

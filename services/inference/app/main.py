from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.routers import inference
from common.config import conf
from common.cors import setup_cors
from common.logger import my_logger
from common.metrics import setup_metrics


@asynccontextmanager
async def lifespan(_: FastAPI):
    my_logger.info(
        "Inference service starting: vllm=%s port=%s local_models=%s",
        conf.VLLM_BASE_URL,
        conf.INFERENCE_PORT,
        conf.LOCAL_MODELS,
    )
    yield
    my_logger.info("Inference service stopped")


app = FastAPI(title=conf.INFERENCE_APP_NAME, lifespan=lifespan)
setup_cors(app)
setup_metrics(app)


@app.get("/health")
def health():
    return {"status": "ok", "service": "inference", "vllm_base": conf.VLLM_BASE_URL}


@app.get("/ready")
async def ready():
    base = conf.VLLM_BASE_URL.rstrip("/")
    url = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {conf.VLLM_API_KEY}"})
        resp.raise_for_status()
    return {"status": "ready", "vllm": "ok"}


app.include_router(inference.router)

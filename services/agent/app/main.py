from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import agents, workflows
from common.config import conf
from common.cors import setup_cors
from common.logger import my_logger
from common.metrics import setup_metrics


@asynccontextmanager
async def lifespan(_: FastAPI):
    my_logger.info("Agent service starting: port=%s rag=%s", conf.AGENT_PORT, conf.RAG_INTERNAL_URL)
    yield
    my_logger.info("Agent service stopped")


app = FastAPI(title=conf.AGENT_APP_NAME, lifespan=lifespan)
setup_cors(app)
setup_metrics(app)


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


app.include_router(agents.router)
app.include_router(workflows.router)

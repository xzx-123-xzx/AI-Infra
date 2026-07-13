from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import admin, chat, health, tenants
from common.config import conf
from common.cors import setup_cors
from common.logger import my_logger
from common.metrics import setup_metrics
from common.path_utils import root_dir


@asynccontextmanager
async def lifespan(_: FastAPI):
    my_logger.info("Gateway starting: root=%s port=%s", root_dir, conf.GATEWAY_PORT)
    yield
    my_logger.info("Gateway stopped")


app = FastAPI(title=conf.APP_NAME, lifespan=lifespan)
setup_cors(app)
setup_metrics(app)
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(tenants.router)

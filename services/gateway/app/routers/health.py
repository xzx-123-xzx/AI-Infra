from fastapi import APIRouter

from common.config import conf
from common.logger import my_logger
from common.model_router import all_available_models

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "gateway",
        "routing_enabled": conf.ROUTING_ENABLED,
        "local_models": conf.LOCAL_MODELS,
    }


@router.get("/ready")
def ready():
    from app.database import engine
    from app.rate_limit import get_redis

    get_redis().ping()
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    my_logger.info("Readiness check passed")
    return {"status": "ready"}

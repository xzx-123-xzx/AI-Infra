from fastapi import APIRouter

from common.logger import my_logger

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@router.get("/ready")
def ready():
    from app.database import engine
    from app.rate_limit import get_redis

    get_redis().ping()
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    my_logger.info("Readiness check passed")
    return {"status": "ready"}

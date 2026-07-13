import asyncio

from app.database import SessionLocal
from app.services.pipeline import process_job
from common.config import conf
from common.logger import my_logger
from common.mlops_queue import dequeue_job


async def mlops_worker_loop(stop: asyncio.Event) -> None:
    my_logger.info("MLOps worker started")
    while not stop.is_set():
        job = await asyncio.to_thread(dequeue_job, 2)
        if job is None:
            continue
        db = SessionLocal()
        try:
            await process_job(db, int(job["job_id"]))
        finally:
            db.close()

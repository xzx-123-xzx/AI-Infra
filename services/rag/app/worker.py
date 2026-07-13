import asyncio
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import SyncSource
from app.services.incremental import ingest_incremental
from app.services.ingestion import ingest_document
from common.config import conf
from common.ingest_queue import dequeue_ingest
from common.logger import my_logger


async def process_ingest_job(doc_id: int, *, incremental: bool = False) -> None:
    db = SessionLocal()
    try:
        from app.models import Document

        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc is None:
            my_logger.warning("Ingest job skipped: doc_id=%s not found", doc_id)
            return
        if incremental or doc.content_hash:
            await ingest_incremental(db, doc)
        else:
            await ingest_document(db, doc)
    finally:
        db.close()


async def ingest_worker_loop(stop: asyncio.Event) -> None:
    my_logger.info("Ingest worker started (async=%s)", conf.INGESTION_ASYNC)
    while not stop.is_set():
        job = await asyncio.to_thread(dequeue_ingest, 2)
        if job is None:
            continue
        try:
            await process_ingest_job(int(job["doc_id"]), incremental=bool(job.get("incremental")))
        except Exception:
            my_logger.exception("Ingest worker job failed: %s", job)


async def sync_scheduler_loop(stop: asyncio.Event) -> None:
    interval = max(conf.SYNC_WORKER_INTERVAL, 60)
    my_logger.info("Sync scheduler started interval=%ss", interval)
    while not stop.is_set():
        await asyncio.sleep(interval)
        db = SessionLocal()
        try:
            sources = (
                db.query(SyncSource)
                .filter(SyncSource.enabled.is_(True), SyncSource.cron_minutes > 0)
                .all()
            )
            now = datetime.utcnow()
            from app.services.sync_sources import run_sync

            for source in sources:
                due = (
                    source.last_sync_at is None
                    or now - source.last_sync_at >= timedelta(minutes=source.cron_minutes)
                )
                if not due:
                    continue
                try:
                    await run_sync(db, source)
                except Exception as exc:
                    source.last_status = "failed"
                    source.last_error = str(exc)[:1000]
                    db.commit()
                    my_logger.exception("Scheduled sync failed: source_id=%s", source.id)
        finally:
            db.close()

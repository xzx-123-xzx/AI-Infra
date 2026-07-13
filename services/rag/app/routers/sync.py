import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeBase, SyncSource
from app.services.sync_sources import run_sync
from common.security import verify_admin_token

router = APIRouter(prefix="/knowledge-bases/{kb_id}/sync-sources", tags=["sync"])


class SyncSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    source_type: str = Field(pattern="^(confluence|lark)$")
    config: dict
    cron_minutes: int = Field(default=0, ge=0, le=10080)
    enabled: bool = True


class SyncSourceResponse(BaseModel):
    id: int
    kb_id: int
    name: str
    source_type: str
    config: dict
    cron_minutes: int
    enabled: bool
    last_sync_at: str | None = None
    last_status: str | None = None
    last_error: str | None = None

    model_config = {"from_attributes": True}


def _serialize(source: SyncSource) -> dict:
    cfg = json.loads(source.config) if isinstance(source.config, str) else source.config
    return {
        "id": source.id,
        "kb_id": source.kb_id,
        "name": source.name,
        "source_type": source.source_type,
        "config": cfg,
        "cron_minutes": source.cron_minutes,
        "enabled": source.enabled,
        "last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
        "last_status": source.last_status,
        "last_error": source.last_error,
    }


def _get_kb(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.status == "active").first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.post("")
async def create_sync_source(
    kb_id: int,
    payload: SyncSourceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    source = SyncSource(
        kb_id=kb_id,
        name=payload.name,
        source_type=payload.source_type,
        config=json.dumps(payload.config),
        cron_minutes=payload.cron_minutes,
        enabled=payload.enabled,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _serialize(source)


@router.get("")
def list_sync_sources(
    kb_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    rows = db.query(SyncSource).filter(SyncSource.kb_id == kb_id).order_by(SyncSource.id.desc()).all()
    return [_serialize(r) for r in rows]


@router.post("/{source_id}/run")
async def trigger_sync(
    kb_id: int,
    source_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    source = db.query(SyncSource).filter(SyncSource.id == source_id, SyncSource.kb_id == kb_id).first()
    if source is None:
        raise HTTPException(status_code=404, detail="Sync source not found")
    try:
        doc = await run_sync(db, source)
        return {"status": "queued", "document_id": doc.id, "doc_status": doc.status}
    except Exception as exc:
        source.last_status = "failed"
        source.last_error = str(exc)[:1000]
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/{source_id}")
def delete_sync_source(
    kb_id: int,
    source_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    source = db.query(SyncSource).filter(SyncSource.id == source_id, SyncSource.kb_id == kb_id).first()
    if source is None:
        raise HTTPException(status_code=404, detail="Sync source not found")
    db.delete(source)
    db.commit()
    return {"status": "deleted", "id": source_id}

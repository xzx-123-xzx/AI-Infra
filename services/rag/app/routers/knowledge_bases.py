from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeBase
from app.services.ingestion import remove_kb_files
from app.services.milvus_store import delete_by_kb
from common.logger import my_logger
from common.security import verify_admin_token

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


class KBCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(default="default", max_length=64)
    description: str | None = None


class KBResponse(BaseModel):
    id: int
    name: str
    tenant_id: str
    description: str | None
    status: str

    model_config = {"from_attributes": True}


@router.post("", response_model=KBResponse)
def create_kb(
    payload: KBCreateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    kb = KnowledgeBase(name=payload.name, tenant_id=payload.tenant_id, description=payload.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    my_logger.info("Knowledge base created: id=%s tenant=%s", kb.id, kb.tenant_id)
    return kb


@router.get("", response_model=list[KBResponse])
def list_kbs(
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    query = db.query(KnowledgeBase).filter(KnowledgeBase.status == "active")
    if tenant_id:
        query = query.filter(KnowledgeBase.tenant_id == tenant_id)
    return query.order_by(KnowledgeBase.id.desc()).all()


@router.get("/{kb_id}", response_model=KBResponse)
def get_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.status == "active").first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.delete("/{kb_id}")
def delete_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    kb.status = "deleted"
    delete_by_kb(kb_id)
    remove_kb_files(kb_id)
    db.commit()
    my_logger.info("Knowledge base deleted: id=%s", kb_id)
    return {"status": "deleted", "id": kb_id}

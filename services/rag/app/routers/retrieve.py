from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeBase
from app.services.rag_chain import retrieve
from common.config import conf
from common.security import verify_admin_token

router = APIRouter(prefix="/knowledge-bases/{kb_id}", tags=["retrieve"])


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=50)


class RetrieveResponse(BaseModel):
    query: str
    results: list[dict]


def _get_kb(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.status == "active").first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_chunks(
    kb_id: int,
    payload: RetrieveRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    top_k = payload.top_k or conf.RETRIEVAL_K
    results = await retrieve(kb_id, payload.query, top_k)
    return RetrieveResponse(query=payload.query, results=results)

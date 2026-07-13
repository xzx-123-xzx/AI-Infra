from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeBase
from app.services.rag_chain import chat_with_kb
from common.config import conf
from common.security import verify_admin_token

router = APIRouter(prefix="/knowledge-bases/{kb_id}", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=50)
    prompt_template_id: int | None = None
    prompt_variables: dict[str, str] | None = None
    tenant_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    prompt_meta: dict | None = None


def _get_kb(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.status == "active").first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.post("/chat", response_model=ChatResponse)
async def chat(
    kb_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    kb = _get_kb(db, kb_id)
    result = await chat_with_kb(
        kb_id,
        payload.query,
        payload.top_k or conf.RETRIEVAL_K,
        db=db,
        prompt_template_id=payload.prompt_template_id,
        prompt_variables=payload.prompt_variables,
        tenant_id=payload.tenant_id or kb.tenant_id,
        session_id=payload.session_id,
    )
    return ChatResponse(**result)

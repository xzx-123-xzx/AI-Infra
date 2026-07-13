from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.federated import federated_retrieve
from common.config import conf
from common.security import verify_admin_token
from langchain_core.messages import HumanMessage, SystemMessage
from common.llm import my_llm

router = APIRouter(prefix="/federated", tags=["federated"])


class FederatedRetrieveRequest(BaseModel):
    kb_ids: list[int] = Field(min_length=1)
    query: str = Field(min_length=1)
    tenant_id: str = Field(default="default")
    top_k: int | None = Field(default=None, ge=1, le=50)


class FederatedChatRequest(FederatedRetrieveRequest):
    prompt_template_id: int | None = None


@router.post("/retrieve")
async def federated_retrieve_api(
    payload: FederatedRetrieveRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    try:
        hits = await federated_retrieve(
            db, payload.kb_ids, payload.query, payload.tenant_id, payload.top_k
        )
        return {"results": hits}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/chat")
async def federated_chat_api(
    payload: FederatedChatRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    try:
        hits = await federated_retrieve(
            db, payload.kb_ids, payload.query, payload.tenant_id, payload.top_k
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not hits:
        return {"answer": "未找到相关内容", "sources": []}

    context_blocks = []
    for idx, hit in enumerate(hits, 1):
        context_blocks.append(
            f"[{idx}] kb={hit.get('kb_id')} doc={hit['doc_id']}\n{hit['content']}"
        )
    context = "\n\n".join(context_blocks)
    user_prompt = f"上下文：\n{context}\n\n问题：{payload.query}"
    response = my_llm.invoke(
        [SystemMessage(content=conf.DEFAULT_RAG_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )
    answer = response.content if hasattr(response, "content") else str(response)
    return {"answer": answer, "sources": hits}

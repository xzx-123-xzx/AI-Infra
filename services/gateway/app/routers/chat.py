from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import get_api_key
from app.database import get_db
from app.models import ApiKey
from app.proxy import proxy_chat_completions
from app.rate_limit import check_rate_limit

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: dict[str, Any],
    api_key: ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    check_rate_limit(api_key.id, api_key.rate_limit_rpm)
    try:
        return await proxy_chat_completions(request, body, api_key, db)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

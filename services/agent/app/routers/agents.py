from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.runtime import TOOLS, run_agent
from common.security import verify_admin_token

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    kb_id: int | None = None
    tools: list[str] | None = None
    max_steps: int | None = Field(default=None, ge=1, le=20)


class AgentRunResponse(BaseModel):
    answer: str
    steps: list[dict]


@router.get("/tools")
def list_tools(_: None = Depends(verify_admin_token)):
    return {"tools": [{"name": k, **v} for k, v in TOOLS.items()]}


@router.post("/run", response_model=AgentRunResponse)
async def run(payload: AgentRunRequest, _: None = Depends(verify_admin_token)):
    result = await run_agent(
        payload.query,
        kb_id=payload.kb_id,
        tools=payload.tools,
        max_steps=payload.max_steps,
    )
    return AgentRunResponse(**result)

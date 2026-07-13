import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AgentWorkflow
from app.services.workflow import execute_workflow
from common.security import verify_admin_token

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(default="default")
    definition: dict


class WorkflowRunRequest(BaseModel):
    query: str = Field(min_length=1)
    inputs: dict | None = None


@router.post("")
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    wf = AgentWorkflow(
        name=payload.name,
        tenant_id=payload.tenant_id,
        definition=json.dumps(payload.definition),
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return {"id": wf.id, "name": wf.name}


@router.get("")
def list_workflows(
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    q = db.query(AgentWorkflow).filter(AgentWorkflow.status == "active")
    if tenant_id:
        q = q.filter(AgentWorkflow.tenant_id == tenant_id)
    return q.order_by(AgentWorkflow.id.desc()).all()


@router.get("/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    wf = db.query(AgentWorkflow).filter(AgentWorkflow.id == workflow_id).first()
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": wf.id,
        "name": wf.name,
        "tenant_id": wf.tenant_id,
        "definition": json.loads(wf.definition),
    }


@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: int,
    payload: WorkflowRunRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    wf = db.query(AgentWorkflow).filter(AgentWorkflow.id == workflow_id).first()
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    definition = json.loads(wf.definition)
    inputs = {"query": payload.query, **(payload.inputs or {})}
    result = await execute_workflow(definition, inputs)
    return result

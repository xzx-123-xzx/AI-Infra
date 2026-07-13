import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EvalDataset, EvalRun
from app.services.eval_runner import compare_runs, run_eval
from common.security import verify_admin_token

router = APIRouter(prefix="/eval", tags=["eval"])


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1)
    tenant_id: str = Field(default="default")
    items: list[dict] = Field(min_length=1)


class RunCreate(BaseModel):
    dataset_id: int
    name: str = Field(min_length=1)
    config: dict


@router.post("/datasets")
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    ds = EvalDataset(name=payload.name, tenant_id=payload.tenant_id, items=json.dumps(payload.items))
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return {"id": ds.id, "name": ds.name, "item_count": len(payload.items)}


@router.get("/datasets")
def list_datasets(
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    q = db.query(EvalDataset).order_by(EvalDataset.id.desc())
    if tenant_id:
        q = q.filter(EvalDataset.tenant_id == tenant_id)
    rows = q.all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "tenant_id": r.tenant_id,
            "item_count": len(json.loads(r.items)),
        }
        for r in rows
    ]


@router.post("/runs")
async def create_run(
    payload: RunCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    ds = db.query(EvalDataset).filter(EvalDataset.id == payload.dataset_id).first()
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    run = EvalRun(
        dataset_id=payload.dataset_id,
        name=payload.name,
        config=json.dumps(payload.config),
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run = await run_eval(db, run)
    return {
        "id": run.id,
        "status": run.status,
        "metrics": json.loads(run.metrics) if run.metrics else None,
        "error_message": run.error_message,
    }


@router.get("/runs")
def list_runs(dataset_id: int | None = None, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    q = db.query(EvalRun).order_by(EvalRun.id.desc())
    if dataset_id:
        q = q.filter(EvalRun.dataset_id == dataset_id)
    return q.all()


@router.get("/runs/compare")
def compare(
    run_a: int,
    run_b: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    a = db.query(EvalRun).filter(EvalRun.id == run_a).first()
    b = db.query(EvalRun).filter(EvalRun.id == run_b).first()
    if not a or not b:
        raise HTTPException(status_code=404, detail="Run not found")
    return compare_runs(a, b)

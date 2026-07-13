from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FinetuneJob, FinetuneSample
from app.services.pipeline import advance_job, export_jsonl
from common.mlops_queue import enqueue_job
from common.security import verify_admin_token

router = APIRouter(prefix="/jobs", tags=["finetune"])


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(default="default")
    base_model: str = Field(min_length=1)
    config: dict | None = None


class SampleCreate(BaseModel):
    instruction: str | None = None
    input_text: str | None = None
    output_text: str | None = None
    label_status: str = Field(default="approved", pattern="^(pending|approved|rejected)$")


@router.post("")
def create_job(payload: JobCreate, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    import json

    job = FinetuneJob(
        name=payload.name,
        tenant_id=payload.tenant_id,
        base_model=payload.base_model,
        config=json.dumps(payload.config or {}),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("")
def list_jobs(tenant_id: str | None = None, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    q = db.query(FinetuneJob).order_by(FinetuneJob.id.desc())
    if tenant_id:
        q = q.filter(FinetuneJob.tenant_id == tenant_id)
    return q.all()


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    job = db.query(FinetuneJob).filter(FinetuneJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    samples = db.query(FinetuneSample).filter(FinetuneSample.job_id == job_id).all()
    return {"job": job, "samples": samples}


@router.post("/{job_id}/samples")
def add_sample(
    job_id: int,
    payload: SampleCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    job = db.query(FinetuneJob).filter(FinetuneJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    sample = FinetuneSample(job_id=job_id, **payload.model_dump())
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


@router.post("/{job_id}/submit")
def submit_job(job_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    job = db.query(FinetuneJob).filter(FinetuneJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    approved = (
        db.query(FinetuneSample)
        .filter(FinetuneSample.job_id == job_id, FinetuneSample.label_status == "approved")
        .count()
    )
    if approved == 0:
        raise HTTPException(status_code=400, detail="No approved samples")
    export_jsonl(db, job)
    job.stage = "ready"
    job.status = "ready"
    db.commit()
    enqueue_job(job_id)
    return {"status": "queued", "job_id": job_id}


@router.post("/{job_id}/advance")
def advance(job_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    job = db.query(FinetuneJob).filter(FinetuneJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return advance_job(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ModelRegistry
from common.security import verify_admin_token

router = APIRouter(prefix="/registry", tags=["registry"])


class CanaryUpdate(BaseModel):
    canary_weight: int = Field(ge=0, le=100)


@router.get("")
def list_models(
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    q = db.query(ModelRegistry).order_by(ModelRegistry.id.desc())
    if tenant_id:
        q = q.filter(ModelRegistry.tenant_id == tenant_id)
    rows = q.all()
    result = []
    for r in rows:
        result.append(
            {
                "id": r.id,
                "name": r.name,
                "version": r.version,
                "base_model": r.base_model,
                "adapter_path": r.adapter_path,
                "tenant_id": r.tenant_id,
                "status": r.status,
                "canary_weight": r.canary_weight,
                "metrics": json.loads(r.metrics) if r.metrics else None,
            }
        )
    return result


@router.get("/{model_id}")
def get_model(model_id: int, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    r = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return r


@router.put("/{model_id}/canary")
def update_canary(
    model_id: int,
    payload: CanaryUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    r = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Model not found")
    r.canary_weight = payload.canary_weight
    if payload.canary_weight > 0 and r.status == "draft":
        r.status = "canary"
    db.commit()
    return {"id": model_id, "canary_weight": r.canary_weight, "status": r.status}

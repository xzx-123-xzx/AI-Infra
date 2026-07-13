from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tenant, TenantQuota
from app.quota import get_or_create_quota, tenant_usage
from common.security import verify_admin_token

router = APIRouter(prefix="/admin/tenants", tags=["tenants"])


class TenantCreateRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)


class QuotaUpdateRequest(BaseModel):
    monthly_token_limit: int = Field(default=0, ge=0)
    monthly_request_limit: int = Field(default=0, ge=0)
    kb_limit: int = Field(default=0, ge=0)


class TenantResponse(BaseModel):
    id: str
    name: str
    status: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TenantResponse])
def list_tenants(db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    return db.query(Tenant).filter(Tenant.status == "active").order_by(Tenant.id).all()


@router.post("", response_model=TenantResponse)
def create_tenant(
    payload: TenantCreateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    if db.query(Tenant).filter(Tenant.id == payload.id).first():
        raise HTTPException(status_code=409, detail="Tenant already exists")
    tenant = Tenant(id=payload.id, name=payload.name)
    db.add(tenant)
    db.add(TenantQuota(tenant_id=payload.id))
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}/usage")
def get_usage(tenant_id: str, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    if db.query(Tenant).filter(Tenant.id == tenant_id).first() is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_usage(db, tenant_id)


@router.put("/{tenant_id}/quota")
def update_quota(
    tenant_id: str,
    payload: QuotaUpdateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    if db.query(Tenant).filter(Tenant.id == tenant_id).first() is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    quota = get_or_create_quota(db, tenant_id)
    quota.monthly_token_limit = payload.monthly_token_limit
    quota.monthly_request_limit = payload.monthly_request_limit
    quota.kb_limit = payload.kb_limit
    db.commit()
    return {
        "tenant_id": tenant_id,
        "monthly_token_limit": quota.monthly_token_limit,
        "monthly_request_limit": quota.monthly_request_limit,
        "kb_limit": quota.kb_limit,
    }

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Tenant, TenantQuota, UsageLog


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_or_create_quota(db: Session, tenant_id: str) -> TenantQuota:
    quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tenant_id).first()
    if quota:
        return quota
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        tenant = Tenant(id=tenant_id, name=tenant_id)
        db.add(tenant)
    quota = TenantQuota(tenant_id=tenant_id)
    db.add(quota)
    db.commit()
    db.refresh(quota)
    return quota


def tenant_usage(db: Session, tenant_id: str) -> dict:
    start = _month_start()
    row = (
        db.query(
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0),
        )
        .filter(UsageLog.tenant_id == tenant_id, UsageLog.created_at >= start)
        .first()
    )
    requests = int(row[0] or 0)
    tokens = int(row[1] or 0)
    quota = get_or_create_quota(db, tenant_id)
    return {
        "tenant_id": tenant_id,
        "period": start.strftime("%Y-%m"),
        "requests": requests,
        "tokens": tokens,
        "monthly_token_limit": int(quota.monthly_token_limit),
        "monthly_request_limit": quota.monthly_request_limit,
        "token_remaining": max(int(quota.monthly_token_limit) - tokens, 0) if quota.monthly_token_limit else None,
        "request_remaining": max(quota.monthly_request_limit - requests, 0) if quota.monthly_request_limit else None,
    }


def check_tenant_quota(db: Session, tenant_id: str) -> None:
    usage = tenant_usage(db, tenant_id)
    if usage["monthly_request_limit"] and usage["requests"] >= usage["monthly_request_limit"]:
        raise HTTPException(status_code=429, detail="Tenant monthly request quota exceeded")
    if usage["monthly_token_limit"] and usage["tokens"] >= usage["monthly_token_limit"]:
        raise HTTPException(status_code=429, detail="Tenant monthly token quota exceeded")

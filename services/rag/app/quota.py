from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import KnowledgeBase


def check_kb_quota(db: Session, tenant_id: str) -> None:
    row = db.execute(
        text("SELECT kb_limit FROM tenant_quotas WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    ).first()
    kb_limit = int(row[0]) if row and row[0] else 0
    if kb_limit <= 0:
        return
    count = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.tenant_id == tenant_id, KnowledgeBase.status == "active")
        .count()
    )
    if count >= kb_limit:
        raise HTTPException(status_code=429, detail="Tenant knowledge base quota exceeded")

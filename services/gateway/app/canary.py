"""模型注册表灰度路由。"""

from __future__ import annotations

import hashlib

from sqlalchemy import text

from common.logger import my_logger


def apply_canary(model: str, tenant_id: str = "default") -> tuple[str, str]:
    try:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            row = db.execute(
                text(
                    "SELECT name, version, base_model, canary_weight FROM model_registry "
                    "WHERE name=:name AND status IN ('published','canary') "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"name": model},
            ).first()
        finally:
            db.close()
    except Exception:
        return model, "registry_unavailable"

    if not row or int(row[3] or 0) <= 0:
        return model, "no_canary"

    bucket = int(hashlib.md5(tenant_id.encode()).hexdigest(), 16) % 100
    weight = int(row[3])
    if bucket < weight:
        alias = f"{row[0]}-{row[1]}"
        my_logger.info("Canary route: %s -> %s (weight=%s)", model, alias, weight)
        return alias, f"canary_finetuned_{weight}"
    return str(row[2]), f"canary_base_{weight}"

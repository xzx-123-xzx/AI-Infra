"""Prompt 模板加载、版本选择与 A/B 分流。"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.models import PromptTemplate, PromptVersion
from common.config import conf
from common.prompt_utils import extract_variables, render_prompt


def _parse_variables(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _pick_ab_version(versions: list[PromptVersion], bucket_key: str) -> PromptVersion:
    total = sum(max(v.ab_weight, 1) for v in versions)
    digest = int(hashlib.md5(bucket_key.encode()).hexdigest(), 16)
    point = digest % total
    acc = 0
    for version in versions:
        acc += max(version.ab_weight, 1)
        if point < acc:
            return version
    return versions[-1]


def resolve_prompt(
    db: Session,
    *,
    template_id: int | None = None,
    template_name: str | None = None,
    tenant_id: str = "default",
    prompt_type: str = "rag",
    variables: dict[str, str] | None = None,
    ab_bucket: str | None = None,
) -> tuple[str, dict]:
    """返回 (渲染后的 prompt, meta)。"""
    template: PromptTemplate | None = None
    if template_id:
        template = db.query(PromptTemplate).filter(
            PromptTemplate.id == template_id,
            PromptTemplate.status == "active",
        ).first()
    elif template_name:
        template = db.query(PromptTemplate).filter(
            PromptTemplate.name == template_name,
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.prompt_type == prompt_type,
            PromptTemplate.status == "active",
        ).first()

    if template is None:
        content = conf.DEFAULT_RAG_SYSTEM_PROMPT
        return render_prompt(content, variables), {"source": "default"}

    active = (
        db.query(PromptVersion)
        .filter(PromptVersion.template_id == template.id, PromptVersion.is_active.is_(True))
        .order_by(PromptVersion.version.desc())
        .all()
    )
    if not active:
        content = conf.DEFAULT_RAG_SYSTEM_PROMPT
        return render_prompt(content, variables), {"source": "default", "template_id": template.id}

    if template.ab_enabled and len(active) > 1:
        version = _pick_ab_version(active, ab_bucket or tenant_id)
    else:
        version = active[0]

    rendered = render_prompt(version.content, variables)
    meta = {
        "template_id": template.id,
        "version_id": version.id,
        "version": version.version,
        "variant_label": version.variant_label,
        "ab_enabled": template.ab_enabled,
    }
    return rendered, meta


def next_version_no(db: Session, template_id: int) -> int:
    latest = (
        db.query(PromptVersion)
        .filter(PromptVersion.template_id == template_id)
        .order_by(PromptVersion.version.desc())
        .first()
    )
    return (latest.version + 1) if latest else 1


def serialize_version(version: PromptVersion) -> dict:
    return {
        "id": version.id,
        "template_id": version.template_id,
        "version": version.version,
        "content": version.content,
        "variables": _parse_variables(version.variables),
        "variant_label": version.variant_label,
        "ab_weight": version.ab_weight,
        "is_active": version.is_active,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def create_version_record(
    db: Session,
    template: PromptTemplate,
    content: str,
    *,
    variant_label: str | None = None,
    ab_weight: int = 100,
    activate: bool = True,
) -> PromptVersion:
    if activate and not template.ab_enabled:
        db.query(PromptVersion).filter(PromptVersion.template_id == template.id).update(
            {"is_active": False}
        )
    version = PromptVersion(
        template_id=template.id,
        version=next_version_no(db, template.id),
        content=content,
        variables=json.dumps(extract_variables(content)),
        variant_label=variant_label,
        ab_weight=ab_weight,
        is_active=activate,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version

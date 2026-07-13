from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PromptTemplate, PromptVersion
from app.services.prompt_service import create_version_record, serialize_version
from common.security import verify_admin_token

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(default="default", max_length=64)
    prompt_type: str = Field(default="rag", max_length=32)
    description: str | None = None
    content: str = Field(min_length=1)
    variant_label: str | None = None


class PromptTemplateResponse(BaseModel):
    id: int
    name: str
    tenant_id: str
    prompt_type: str
    description: str | None
    status: str
    ab_enabled: bool

    model_config = {"from_attributes": True}


class VersionCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    variant_label: str | None = None
    ab_weight: int = Field(default=100, ge=1, le=1000)
    activate: bool = True


class AbConfigRequest(BaseModel):
    variants: list[dict] = Field(min_length=2, max_length=5)
    # [{"version_id": 1, "weight": 50}, {"version_id": 2, "weight": 50}]


@router.post("", response_model=PromptTemplateResponse)
def create_prompt(
    payload: PromptCreateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    exists = db.query(PromptTemplate).filter(
        PromptTemplate.name == payload.name,
        PromptTemplate.tenant_id == payload.tenant_id,
        PromptTemplate.prompt_type == payload.prompt_type,
        PromptTemplate.status == "active",
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Prompt template already exists")

    template = PromptTemplate(
        name=payload.name,
        tenant_id=payload.tenant_id,
        prompt_type=payload.prompt_type,
        description=payload.description,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    create_version_record(
        db, template, payload.content, variant_label=payload.variant_label or "A", activate=True
    )
    return template


@router.get("", response_model=list[PromptTemplateResponse])
def list_prompts(
    tenant_id: str | None = None,
    prompt_type: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    query = db.query(PromptTemplate).filter(PromptTemplate.status == "active")
    if tenant_id:
        query = query.filter(PromptTemplate.tenant_id == tenant_id)
    if prompt_type:
        query = query.filter(PromptTemplate.prompt_type == prompt_type)
    return query.order_by(PromptTemplate.id.desc()).all()


@router.get("/{template_id}")
def get_prompt(
    template_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    versions = (
        db.query(PromptVersion)
        .filter(PromptVersion.template_id == template_id)
        .order_by(PromptVersion.version.desc())
        .all()
    )
    return {
        "template": PromptTemplateResponse.model_validate(template),
        "versions": [serialize_version(v) for v in versions],
    }


@router.post("/{template_id}/versions")
def add_version(
    template_id: int,
    payload: VersionCreateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    version = create_version_record(
        db,
        template,
        payload.content,
        variant_label=payload.variant_label,
        ab_weight=payload.ab_weight,
        activate=payload.activate and not template.ab_enabled,
    )
    return serialize_version(version)


@router.put("/{template_id}/versions/{version_id}/activate")
def activate_version(
    template_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    version = db.query(PromptVersion).filter(
        PromptVersion.id == version_id,
        PromptVersion.template_id == template_id,
    ).first()
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    if not template.ab_enabled:
        db.query(PromptVersion).filter(PromptVersion.template_id == template_id).update(
            {"is_active": False}
        )
    version.is_active = True
    db.commit()
    return {"status": "activated", "version_id": version_id}


@router.post("/{template_id}/ab")
def configure_ab(
    template_id: int,
    payload: AbConfigRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")

    db.query(PromptVersion).filter(PromptVersion.template_id == template_id).update(
        {"is_active": False, "ab_weight": 0}
    )
    for item in payload.variants:
        version = db.query(PromptVersion).filter(
            PromptVersion.id == int(item["version_id"]),
            PromptVersion.template_id == template_id,
        ).first()
        if version is None:
            raise HTTPException(status_code=404, detail=f"Version {item['version_id']} not found")
        version.is_active = True
        version.ab_weight = int(item.get("weight", 50))

    template.ab_enabled = True
    db.commit()
    return {"status": "ab_enabled", "template_id": template_id}


@router.delete("/{template_id}")
def delete_prompt(
    template_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    template.status = "deleted"
    db.commit()
    return {"status": "deleted", "id": template_id}

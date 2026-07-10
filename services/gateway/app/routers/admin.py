from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import generate_api_key
from app.database import get_db
from app.models import ApiKey
from common.config import conf
from common.logger import my_logger
from common.security import verify_admin_token

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(default="default", max_length=64)
    rate_limit_rpm: int | None = Field(default=None, ge=1, le=10000)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    tenant_id: str
    key_prefix: str
    is_active: bool
    rate_limit_rpm: int


class CreateKeyResponse(ApiKeyResponse):
    api_key: str


@router.get("/models")
def list_models(_: None = Depends(verify_admin_token)):
    return {"data": [{"id": model} for model in conf.model_list]}


@router.get("/keys", response_model=list[ApiKeyResponse])
def list_keys(db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    return db.query(ApiKey).order_by(ApiKey.id.desc()).all()


@router.post("/keys", response_model=CreateKeyResponse)
def create_key(payload: CreateKeyRequest, db: Session = Depends(get_db), _: None = Depends(verify_admin_token)):
    raw_key, key_hash, key_prefix = generate_api_key()
    record = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=payload.name,
        tenant_id=payload.tenant_id,
        rate_limit_rpm=payload.rate_limit_rpm or conf.DEFAULT_RATE_LIMIT_RPM,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    my_logger.info("API key created: name=%s tenant=%s prefix=%s", record.name, record.tenant_id, record.key_prefix)
    return CreateKeyResponse(api_key=raw_key, **ApiKeyResponse.model_validate(record).model_dump())

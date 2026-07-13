from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(64))
    base_model: Mapped[str] = mapped_column(String(128))
    adapter_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    canary_weight: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FinetuneJob(Base):
    __tablename__ = "finetune_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    tenant_id: Mapped[str] = mapped_column(String(64), default="default")
    base_model: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="labeling")
    stage: Mapped[str] = mapped_column(String(32), default="labeling")
    config: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    registry_id: Mapped[int | None] = mapped_column(ForeignKey("model_registry.id"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FinetuneSample(Base):
    __tablename__ = "finetune_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("finetune_jobs.id", ondelete="CASCADE"), index=True)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    label_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, KnowledgeBase
from app.services.ingestion import queue_document, remove_document_file, save_upload_file
from app.services.milvus_store import delete_by_doc
from app.services.es_store import delete_by_doc as es_delete_doc
from common.config import conf
from common.security import verify_admin_token
from common.logger import my_logger

router = APIRouter(prefix="/knowledge-bases/{kb_id}/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    kb_id: int
    filename: str
    file_size: int
    status: str
    chunk_count: int
    progress: int = 0
    content_hash: str | None = None
    error_message: str | None

    model_config = {"from_attributes": True}


def _get_kb(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.status == "active").first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.post("", response_model=DocumentResponse)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    async_ingest: bool | None = Query(default=None, description="异步入库，默认读 INGESTION_ASYNC"),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    safe_name = file.filename
    existing = (
        db.query(Document)
        .filter(Document.kb_id == kb_id, Document.filename == safe_name)
        .first()
    )
    use_async = conf.INGESTION_ASYNC if async_ingest is None else async_ingest
    incremental = existing is not None

    file_path = save_upload_file(kb_id, safe_name, content)
    if existing:
        existing.file_path = file_path
        existing.file_size = len(content)
        existing.status = "queued" if use_async else "pending"
        existing.progress = 0
        existing.error_message = None
        doc = existing
    else:
        doc = Document(
            kb_id=kb_id,
            filename=safe_name,
            file_path=file_path,
            file_size=len(content),
            status="queued" if use_async else "pending",
        )
        db.add(doc)

    db.commit()
    db.refresh(doc)

    if use_async:
        queue_document(doc.id, incremental=incremental)
        my_logger.info("Document queued: doc_id=%s incremental=%s", doc.id, incremental)
    else:
        if incremental:
            from app.services.incremental import ingest_incremental

            doc = await ingest_incremental(db, doc)
        else:
            from app.services.ingestion import ingest_document

            doc = await ingest_document(db, doc)
    return doc


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    kb_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    return db.query(Document).filter(Document.kb_id == kb_id).order_by(Document.id.desc()).all()


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    kb_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/{doc_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    kb_id: int,
    doc_id: int,
    async_ingest: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = "queued" if async_ingest else "pending"
    doc.progress = 0
    db.commit()

    if async_ingest:
        queue_document(doc.id, incremental=True)
    else:
        from app.services.incremental import ingest_incremental

        doc = await ingest_incremental(db, doc)
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}")
def delete_document(
    kb_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_by_doc(kb_id, doc_id)
    es_delete_doc(kb_id, doc_id)
    remove_document_file(doc.file_path)
    db.delete(doc)
    db.commit()
    my_logger.info("Document deleted: kb_id=%s doc_id=%s", kb_id, doc_id)
    return {"status": "deleted", "id": doc_id}

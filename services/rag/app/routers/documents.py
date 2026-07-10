from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, KnowledgeBase
from app.services.ingestion import ingest_document, remove_document_file, save_upload_file
from app.services.milvus_store import delete_by_doc
from common.logger import my_logger
from common.security import verify_admin_token

router = APIRouter(prefix="/knowledge-bases/{kb_id}/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    kb_id: int
    filename: str
    file_size: int
    status: str
    chunk_count: int
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
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
):
    _get_kb(db, kb_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    file_path = save_upload_file(kb_id, file.filename, content)
    doc = Document(
        kb_id=kb_id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

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
    remove_document_file(doc.file_path)
    db.delete(doc)
    db.commit()
    my_logger.info("Document deleted: kb_id=%s doc_id=%s", kb_id, doc_id)
    return {"status": "deleted", "id": doc_id}

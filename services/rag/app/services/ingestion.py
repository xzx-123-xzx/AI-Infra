import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Document, KnowledgeBase
from app.services.chunker import chunk_text
from app.services.embedder import embed_texts
from app.services.milvus_store import delete_by_doc, insert_chunks
from app.services.parser import parse_file
from common.config import conf
from common.logger import my_logger


def kb_dir(kb_id: int) -> Path:
    path = Path(conf.KB_DATA_DIR) / str(kb_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def ingest_document(db: Session, doc: Document) -> Document:
    doc.status = "processing"
    doc.error_message = None
    db.commit()

    try:
        text = parse_file(doc.file_path)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No text extracted from document")

        batch_size = 32
        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vectors = await embed_texts(batch)
            total += insert_chunks(doc.kb_id, doc.id, batch, vectors)

        doc.status = "ready"
        doc.chunk_count = total
        my_logger.info("Document ingested: doc_id=%s chunks=%s", doc.id, total)
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = str(exc)[:1000]
        doc.chunk_count = 0
        delete_by_doc(doc.kb_id, doc.id)
        my_logger.exception("Document ingest failed: doc_id=%s", doc.id)
    finally:
        db.commit()
        db.refresh(doc)
    return doc


def save_upload_file(kb_id: int, filename: str, content: bytes) -> str:
    safe_name = Path(filename).name
    target = kb_dir(kb_id) / safe_name
    target.write_bytes(content)
    return str(target)


def remove_kb_files(kb_id: int) -> None:
    path = Path(conf.KB_DATA_DIR) / str(kb_id)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def remove_document_file(file_path: str) -> None:
    path = Path(file_path)
    if path.exists():
        path.unlink()

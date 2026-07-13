import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.services.chunker import chunk_text
from app.services.embedder import embed_texts
from app.services.es_store import delete_by_doc as es_delete_doc
from app.services.es_store import index_chunks as es_index_chunks
from app.services.milvus_store import delete_by_doc, insert_chunks
from app.services.parser import chunk_hash, content_hash, parse_file
from common.config import conf
from common.ingest_queue import enqueue_ingest
from common.logger import my_logger


def kb_dir(kb_id: int) -> Path:
    path = Path(conf.KB_DATA_DIR) / str(kb_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def queue_document(doc_id: int, *, incremental: bool = False) -> None:
    enqueue_ingest(doc_id, incremental=incremental)


async def ingest_document(db: Session, doc: Document) -> Document:
    doc.status = "processing"
    doc.error_message = None
    doc.progress = 0
    db.commit()

    try:
        text = parse_file(doc.file_path)
        doc.content_hash = content_hash(text)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No text extracted from document")

        delete_by_doc(doc.kb_id, doc.id)
        es_delete_doc(doc.kb_id, doc.id)
        db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc.id).delete()
        db.commit()

        batch_size = 32
        total = len(chunks)
        inserted = 0
        for i in range(0, total, batch_size):
            batch = chunks[i : i + batch_size]
            vectors = await embed_texts(batch)
            chunk_ids = [uuid.uuid4().hex for _ in batch]
            indices = list(range(i, i + len(batch)))
            insert_chunks(doc.kb_id, doc.id, batch, vectors, chunk_ids, chunk_indices=indices)
            es_index_chunks(doc.kb_id, doc.id, chunk_ids, batch, chunk_indices=indices)
            for idx, content, cid in zip(indices, batch, chunk_ids):
                db.add(
                    DocumentChunk(
                        doc_id=doc.id,
                        chunk_index=idx,
                        chunk_hash=chunk_hash(content),
                        chunk_id=cid,
                    )
                )
            inserted += len(batch)
            doc.progress = int(inserted / total * 100)
            db.commit()

        doc.status = "ready"
        doc.chunk_count = total
        doc.progress = 100
        my_logger.info("Document ingested: doc_id=%s chunks=%s", doc.id, total)
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = str(exc)[:1000]
        doc.chunk_count = 0
        doc.progress = 0
        delete_by_doc(doc.kb_id, doc.id)
        es_delete_doc(doc.kb_id, doc.id)
        db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc.id).delete()
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

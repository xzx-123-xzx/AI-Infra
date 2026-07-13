"""增量分块：仅更新变化 chunk。"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import DocumentChunk
from app.services.chunker import chunk_text
from app.services.embedder import embed_texts
from app.services.es_store import delete_by_doc as es_delete_doc
from app.services.es_store import index_chunks as es_index_chunks
from app.services.milvus_store import delete_by_doc, delete_chunks_by_ids, insert_chunks
from app.services.parser import chunk_hash, content_hash, parse_file
from common.logger import my_logger


def _set_progress(db: Session, doc, progress: int) -> None:
    doc.progress = min(max(progress, 0), 100)
    db.commit()


async def ingest_incremental(db: Session, doc) -> "Document":
    from app.models import Document

    doc.status = "processing"
    doc.error_message = None
    doc.progress = 0
    db.commit()

    try:
        text = parse_file(doc.file_path)
        new_hash = content_hash(text)
        prev_hash = doc.content_hash
        if prev_hash == new_hash and doc.chunk_count > 0:
            doc.status = "ready"
            doc.progress = 100
            db.commit()
            return doc

        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No text extracted from document")

        old_rows = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.doc_id == doc.id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        old_map = {row.chunk_index: row for row in old_rows}
        new_meta = [(i, chunk_hash(c), c) for i, c in enumerate(chunks)]

        unchanged = 0
        to_insert: list[tuple[int, str]] = []
        delete_ids: list[str] = []

        for idx, chash, content in new_meta:
            old = old_map.get(idx)
            if old and old.chunk_hash == chash:
                unchanged += 1
                continue
            if old:
                delete_ids.append(old.chunk_id)
                db.delete(old)
            to_insert.append((idx, content))

        for idx in range(len(new_meta), len(old_map)):
            old = old_map.get(idx)
            if old:
                delete_ids.append(old.chunk_id)
                db.delete(old)

        if delete_ids:
            delete_chunks_by_ids(delete_ids)

        total = len(chunks)
        done = unchanged
        _set_progress(db, doc, int(done / total * 80) if total else 0)

        batch_size = 32
        for i in range(0, len(to_insert), batch_size):
            batch = to_insert[i : i + batch_size]
            texts = [item[1] for item in batch]
            vectors = await embed_texts(texts)
            chunk_ids = [uuid.uuid4().hex for _ in batch]
            indexed = [item[0] for item in batch]
            insert_chunks(
                doc.kb_id,
                doc.id,
                texts,
                vectors,
                chunk_ids,
                chunk_indices=indexed,
            )
            es_index_chunks(doc.kb_id, doc.id, chunk_ids, texts, chunk_indices=indexed)
            for (chunk_index, content), cid, chash in zip(batch, chunk_ids, [chunk_hash(t) for t in texts]):
                db.add(
                    DocumentChunk(
                        doc_id=doc.id,
                        chunk_index=chunk_index,
                        chunk_hash=chash,
                        chunk_id=cid,
                    )
                )
            done += len(batch)
            _set_progress(db, doc, int(80 + done / total * 20) if total else 100)

        doc.status = "ready"
        doc.chunk_count = total
        doc.content_hash = new_hash
        doc.progress = 100
        my_logger.info(
            "Incremental ingest: doc_id=%s total=%s unchanged=%s inserted=%s deleted=%s",
            doc.id, total, unchanged, len(to_insert), len(delete_ids),
        )
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = str(exc)[:1000]
        doc.chunk_count = 0
        doc.progress = 0
        delete_by_doc(doc.kb_id, doc.id)
        es_delete_doc(doc.kb_id, doc.id)
        db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc.id).delete()
        my_logger.exception("Incremental ingest failed: doc_id=%s", doc.id)
    finally:
        db.commit()
        db.refresh(doc)
    return doc

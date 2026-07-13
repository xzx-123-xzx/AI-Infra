"""外部数据源同步：Confluence / 飞书文档。"""

from __future__ import annotations

import json
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models import Document, SyncSource
from app.services.ingestion import kb_dir, save_upload_file
from app.services.parser import content_hash
from common.ingest_queue import enqueue_ingest
from common.logger import my_logger


async def fetch_confluence(config: dict) -> tuple[str, str]:
    base_url = config["base_url"].rstrip("/")
    page_id = config["page_id"]
    token = config.get("token") or config.get("api_token", "")
    url = f"{base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,title"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    title = data.get("title", f"confluence-{page_id}")
    html = data.get("body", {}).get("storage", {}).get("value", "")
    text = _strip_html(html)
    return title, text


async def fetch_lark_doc(config: dict) -> tuple[str, str]:
    """飞书云文档：需 config 含 document_id + tenant_access_token。"""
    doc_id = config["document_id"]
    token = config["tenant_access_token"]
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/raw_content"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    if data.get("code") != 0:
        raise ValueError(data.get("msg", "Lark API error"))
    title = config.get("title") or f"lark-{doc_id[:8]}"
    return title, data.get("data", {}).get("content", "")


def _strip_html(html: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", "\n", html)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def run_sync(db: Session, source: SyncSource, *, async_ingest: bool = True) -> Document:
    config = json.loads(source.config) if isinstance(source.config, str) else source.config
    if source.source_type == "confluence":
        title, text = await fetch_confluence(config)
    elif source.source_type == "lark":
        title, text = await fetch_lark_doc(config)
    else:
        raise ValueError(f"Unsupported source_type: {source.source_type}")

    if not text.strip():
        raise ValueError("Empty content from external source")

    filename = f"{source.source_type}-{source.id}-{title[:50]}.md"
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
    file_path = save_upload_file(source.kb_id, safe, text.encode("utf-8"))
    chash = content_hash(text)

    doc = (
        db.query(Document)
        .filter(Document.kb_id == source.kb_id, Document.filename == safe)
        .first()
    )
    if doc is None:
        doc = Document(
            kb_id=source.kb_id,
            filename=safe,
            file_path=file_path,
            file_size=len(text.encode("utf-8")),
            status="queued" if async_ingest else "pending",
            content_hash=chash,
        )
        db.add(doc)
    else:
        doc.file_path = file_path
        doc.file_size = len(text.encode("utf-8"))
        doc.status = "queued" if async_ingest else "pending"
        doc.content_hash = chash
        doc.progress = 0

    source.last_sync_at = datetime.utcnow()
    source.last_status = "success"
    source.last_error = None
    db.commit()
    db.refresh(doc)

    if async_ingest:
        enqueue_ingest(doc.id, incremental=True)
    else:
        from app.services.incremental import ingest_incremental

        await ingest_incremental(db, doc)

    my_logger.info("Sync completed: source_id=%s doc_id=%s", source.id, doc.id)
    return doc

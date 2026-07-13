from pathlib import Path
from typing import Any

from aiinfra._http import HTTPClient


class RagClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        *,
        admin_token: str | None = None,
        timeout: float = 120.0,
    ):
        self._http = HTTPClient(base_url, admin_token=admin_token, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def health(self) -> dict:
        return self._http.get("/health")

    def ready(self) -> dict:
        return self._http.get("/ready")

    def create_knowledge_base(
        self,
        name: str,
        *,
        tenant_id: str = "default",
        description: str | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"name": name, "tenant_id": tenant_id}
        if description:
            payload["description"] = description
        return self._http.post("/knowledge-bases", json=payload)

    def list_knowledge_bases(self, *, tenant_id: str | None = None) -> list[dict]:
        params = {"tenant_id": tenant_id} if tenant_id else None
        return self._http.get("/knowledge-bases", params=params)

    def get_knowledge_base(self, kb_id: int) -> dict:
        return self._http.get(f"/knowledge-bases/{kb_id}")

    def delete_knowledge_base(self, kb_id: int) -> dict:
        return self._http.delete(f"/knowledge-bases/{kb_id}")

    def list_documents(self, kb_id: int) -> list[dict]:
        return self._http.get(f"/knowledge-bases/{kb_id}/documents")

    def upload_document(self, kb_id: int, file_path: str | Path, *, async_ingest: bool | None = None) -> dict:
        path = Path(file_path)
        params = {}
        if async_ingest is not None:
            params["async_ingest"] = str(async_ingest).lower()
        with path.open("rb") as f:
            files = {"file": (path.name, f)}
            resp = self._http._client.post(
                f"/knowledge-bases/{kb_id}/documents",
                files=files,
                params=params or None,
            )
        if resp.is_error:
            from aiinfra._http import AIInfraError

            raise AIInfraError(resp.status_code, resp.text)
        return resp.json()

    def get_document(self, kb_id: int, doc_id: int) -> dict:
        return self._http.get(f"/knowledge-bases/{kb_id}/documents/{doc_id}")

    def reindex_document(self, kb_id: int, doc_id: int, *, async_ingest: bool = True) -> dict:
        return self._http.post(
            f"/knowledge-bases/{kb_id}/documents/{doc_id}/reindex",
            params={"async_ingest": str(async_ingest).lower()},
        )

    def create_sync_source(self, kb_id: int, body: dict) -> dict:
        return self._http.post(f"/knowledge-bases/{kb_id}/sync-sources", json=body)

    def list_sync_sources(self, kb_id: int) -> list[dict]:
        return self._http.get(f"/knowledge-bases/{kb_id}/sync-sources")

    def run_sync(self, kb_id: int, source_id: int) -> dict:
        return self._http.post(f"/knowledge-bases/{kb_id}/sync-sources/{source_id}/run")

    def delete_document(self, kb_id: int, doc_id: int) -> dict:
        return self._http.delete(f"/knowledge-bases/{kb_id}/documents/{doc_id}")

    def retrieve(self, kb_id: int, query: str, *, top_k: int | None = None) -> dict:
        payload: dict[str, Any] = {"query": query}
        if top_k is not None:
            payload["top_k"] = top_k
        return self._http.post(f"/knowledge-bases/{kb_id}/retrieve", json=payload)

    def chat(self, kb_id: int, query: str, *, top_k: int | None = None) -> dict:
        payload: dict[str, Any] = {"query": query}
        if top_k is not None:
            payload["top_k"] = top_k
        return self._http.post(f"/knowledge-bases/{kb_id}/chat", json=payload)

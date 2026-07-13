from typing import Any

from aiinfra._http import HTTPClient


class AgentClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        *,
        admin_token: str | None = None,
        timeout: float = 180.0,
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

    def list_tools(self) -> dict:
        return self._http.get("/agents/tools")

    def run(
        self,
        query: str,
        *,
        kb_id: int | None = None,
        tools: list[str] | None = None,
        max_steps: int | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"query": query}
        if kb_id is not None:
            payload["kb_id"] = kb_id
        if tools is not None:
            payload["tools"] = tools
        if max_steps is not None:
            payload["max_steps"] = max_steps
        return self._http.post("/agents/run", json=payload)

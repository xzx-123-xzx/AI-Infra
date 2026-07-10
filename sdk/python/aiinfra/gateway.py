from typing import Any

from aiinfra._http import HTTPClient


class GatewayClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        *,
        admin_token: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        self._http = HTTPClient(
            base_url,
            admin_token=admin_token,
            api_key=api_key,
            timeout=timeout,
        )

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

    def list_models(self) -> dict:
        return self._http.get("/admin/models")

    def list_api_keys(self) -> list[dict]:
        return self._http.get("/admin/keys")

    def create_api_key(
        self,
        name: str,
        *,
        tenant_id: str = "default",
        rate_limit_rpm: int | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"name": name, "tenant_id": tenant_id}
        if rate_limit_rpm is not None:
            payload["rate_limit_rpm"] = rate_limit_rpm
        return self._http.post("/admin/keys", json=payload)

    def chat_completions(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
        **extra: Any,
    ) -> dict:
        payload = {"model": model, "messages": messages, "stream": stream, **extra}
        return self._http.post("/v1/chat/completions", json=payload)

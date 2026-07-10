# AI-Infra Python SDK

Install:

```bash
pip install -e sdk/python
```

Usage:

```python
from aiinfra import GatewayClient, RagClient

with GatewayClient("http://localhost:8080", admin_token="xxx") as gw:
    key = gw.create_api_key("my-app")
    print(key["api_key"])

with RagClient("http://localhost:8081", admin_token="xxx") as rag:
    kb = rag.create_knowledge_base("docs")
    rag.upload_document(kb["id"], "README.md")
    print(rag.chat(kb["id"], "你好"))
```

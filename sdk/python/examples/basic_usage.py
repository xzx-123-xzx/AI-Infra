"""AI-Infra SDK usage example."""

import os

from aiinfra import GatewayClient, RagClient

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me-admin-token")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")
RAG_URL = os.getenv("RAG_URL", "http://localhost:8081")


def main() -> None:
    with GatewayClient(GATEWAY_URL, admin_token=ADMIN_TOKEN) as gw:
        print("Gateway:", gw.health())
        print("Models:", gw.list_models())

    with RagClient(RAG_URL, admin_token=ADMIN_TOKEN) as rag:
        print("RAG:", rag.health())
        kbs = rag.list_knowledge_bases()
        print("Knowledge bases:", kbs)
        if kbs:
            result = rag.chat(kbs[0]["id"], "这个知识库是关于什么的？")
            print("Chat:", result.get("answer"))


if __name__ == "__main__":
    main()

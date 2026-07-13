"""可视化工作流执行引擎。"""

from __future__ import annotations

import json
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from common.config import conf
from common.llm import my_llm
from common.logger import my_logger


async def _exec_rag(params: dict) -> str:
    kb_id = int(params["kb_id"])
    query = str(params["query"])
    url = f"{conf.RAG_INTERNAL_URL.rstrip('/')}/knowledge-bases/{kb_id}/retrieve"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {conf.ADMIN_TOKEN}", "Content-Type": "application/json"},
            json={"query": query, "top_k": conf.RETRIEVAL_K},
        )
        resp.raise_for_status()
        data = resp.json()
    results = data.get("results") or []
    return "\n".join(h.get("content", "")[:400] for h in results[:5]) or "无检索结果"


async def _exec_llm(params: dict, context: str) -> str:
    prompt = params.get("prompt") or "请根据上下文回答。"
    user = f"上下文：\n{context}\n\n任务：{params.get('query', '')}"
    resp = my_llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user)])
    return resp.content if hasattr(resp, "content") else str(resp)


async def execute_workflow(definition: dict, inputs: dict) -> dict:
    nodes = {n["id"]: n for n in definition.get("nodes", [])}
    edges = definition.get("edges", [])
    adjacency: dict[str, list[str]] = {}
    for e in edges:
        adjacency.setdefault(e["source"], []).append(e["target"])

    start = next((n for n in definition.get("nodes", []) if n.get("type") == "start"), None)
    if start is None:
        raise ValueError("Workflow needs a start node")

    context = inputs.get("query", "")
    steps: list[dict[str, Any]] = []
    current = start["id"]
    visited = 0

    while current and visited < 20:
        visited += 1
        node = nodes.get(current)
        if node is None:
            break
        ntype = node.get("type")
        data = node.get("data") or {}

        if ntype == "start":
            context = inputs.get("query", context)
            steps.append({"node": current, "type": ntype, "output": context[:200]})
        elif ntype == "rag":
            obs = await _exec_rag({**data, "query": data.get("query") or context})
            context = obs
            steps.append({"node": current, "type": ntype, "output": obs[:500]})
        elif ntype == "llm":
            answer = await _exec_llm({**data, "query": context}, context)
            context = answer
            steps.append({"node": current, "type": ntype, "output": answer[:500]})
        elif ntype == "end":
            return {"answer": context, "steps": steps}

        next_ids = adjacency.get(current, [])
        current = next_ids[0] if next_ids else None

    my_logger.info("Workflow executed steps=%s", len(steps))
    return {"answer": context, "steps": steps}

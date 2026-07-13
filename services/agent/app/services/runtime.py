import json
import re
from typing import Any, Callable, Awaitable

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from common.config import conf
from common.llm import my_llm
from common.logger import my_logger

ToolFn = Callable[[dict[str, Any]], Awaitable[str]]

TOOLS: dict[str, dict[str, Any]] = {
    "rag_search": {
        "description": "从知识库检索相关文档片段。input: {kb_id: int, query: str}",
    },
    "http_get": {
        "description": "HTTP GET 请求。input: {url: str}",
    },
}


async def rag_search(params: dict[str, Any]) -> str:
    kb_id = int(params["kb_id"])
    query = str(params["query"])
    url = f"{conf.RAG_INTERNAL_URL.rstrip('/')}/knowledge-bases/{kb_id}/retrieve"
    headers = {"Authorization": f"Bearer {conf.ADMIN_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json={"query": query, "top_k": conf.RETRIEVAL_K})
        resp.raise_for_status()
        data = resp.json()
    results = data.get("results") or []
    if not results:
        return "未检索到相关内容"
    lines = []
    for i, hit in enumerate(results[:5], 1):
        lines.append(f"[{i}] {hit.get('content', '')[:500]}")
    return "\n".join(lines)


async def http_get(params: dict[str, Any]) -> str:
    url = str(params["url"])
    if not url.startswith(("http://", "https://")):
        return "Error: url must start with http:// or https://"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        return resp.text[:2000]


EXECUTORS: dict[str, ToolFn] = {
    "rag_search": rag_search,
    "http_get": http_get,
}


def tools_prompt(enabled: list[str]) -> str:
    lines = ["可用工具："]
    for name in enabled:
        meta = TOOLS.get(name, {})
        lines.append(f"- {name}: {meta.get('description', '')}")
    lines.append(
        '回复格式（JSON）：\n'
        '调用工具: {"action":"<tool_name>","input":{...}}\n'
        '结束: {"final_answer":"<你的回答>"}'
    )
    return "\n".join(lines)


def parse_action(text: str) -> dict[str, Any] | None:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


async def run_agent(
    query: str,
    *,
    kb_id: int | None = None,
    tools: list[str] | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    enabled = tools or (["rag_search"] if kb_id else ["http_get"])
    if kb_id and "rag_search" not in enabled:
        enabled = ["rag_search", *enabled]

    system = (
        "你是 AI-Infra Agent，可使用工具完成任务。\n"
        f"{tools_prompt(enabled)}\n"
        + (f"默认知识库 kb_id={kb_id}。" if kb_id else "")
    )
    messages = [SystemMessage(content=system), HumanMessage(content=query)]
    steps: list[dict[str, Any]] = []
    limit = max_steps or conf.AGENT_MAX_STEPS

    for step in range(limit):
        response = my_llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        my_logger.info("Agent step %s: %s", step + 1, content[:200])

        parsed = parse_action(content)
        if parsed is None:
            steps.append({"step": step + 1, "type": "raw", "content": content})
            return {"answer": content, "steps": steps}

        if parsed.get("final_answer"):
            steps.append({"step": step + 1, "type": "final", "content": parsed["final_answer"]})
            return {"answer": parsed["final_answer"], "steps": steps}

        action = parsed.get("action")
        tool_input = parsed.get("input") or {}
        if kb_id and action == "rag_search" and "kb_id" not in tool_input:
            tool_input["kb_id"] = kb_id

        executor = EXECUTORS.get(action or "")
        if executor is None:
            obs = f"未知工具: {action}"
        else:
            try:
                obs = await executor(tool_input)
            except Exception as exc:
                obs = f"工具执行失败: {exc}"
                my_logger.exception("Tool %s failed", action)

        steps.append({"step": step + 1, "type": "tool", "action": action, "input": tool_input, "observation": obs[:1000]})
        messages.append(HumanMessage(content=f"Observation:\n{obs}\n请继续或给出 final_answer。"))

    return {"answer": "已达到最大步数，未能完成。", "steps": steps}

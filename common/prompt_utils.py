"""Prompt 模板变量替换。"""

from __future__ import annotations

import re

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def extract_variables(content: str) -> list[str]:
    return sorted(set(_VAR_PATTERN.findall(content)))


def render_prompt(content: str, variables: dict[str, str] | None = None) -> str:
    variables = variables or {}

    def repl(match: re.Match) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return _VAR_PATTERN.sub(repl, content)

"""Feedback helpers that convert validation errors into LLM prompts."""
from __future__ import annotations

from typing import Iterable, List

from .shacl_validator import ValidationIssue


def to_messages(issues: Iterable[ValidationIssue]) -> List[str]:
    messages = []
    for issue in issues:
        segment = issue.message or "Constraint violated"
        if issue.result_path:
            segment += f" (path: {issue.result_path})"
        if issue.focus_node:
            segment += f" for node {issue.focus_node}"
        messages.append(segment)
    return messages


__all__ = ["to_messages"]

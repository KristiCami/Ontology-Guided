"""Abstractions over the Large Language Model used in the pipeline."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMClient(ABC):
    """Simple interface that can be backed by OpenAI, Azure or mocks."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Returns the raw model text response for ``prompt``."""


class MockLLMClient(LLMClient):
    """Deterministic mock that emits two-stage answers for demonstration."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if "Repair" in prompt or self.calls > 1:
            payload: Dict[str, Any] = {
                "classes": [
                    {"name": "ATM", "parent": "System"},
                    {"name": "Transaction", "parent": "Action"},
                    {"name": "User", "parent": "Actor"},
                ],
                "object_properties": [
                    {
                        "name": "logs",
                        "domain": "ATM",
                        "range": "Transaction",
                        "description": "ATM logs transactions",
                    },
                    {
                        "name": "performedBy",
                        "domain": "Transaction",
                        "range": "User",
                    },
                ],
                "restrictions": [
                    {
                        "subject": "Transaction",
                        "property": "performedBy",
                        "target": "User",
                        "restriction_type": "SomeValuesFrom",
                    }
                ],
            }
        else:
            payload = {
                "classes": [
                    {"name": "ATM", "parent": "System"},
                    {"name": "Transaction", "parent": "Action"},
                ],
                "object_properties": [
                    {
                        "name": "logs",
                        "domain": "ATM",
                        "range": "Transaction",
                        "description": "ATM logs transactions",
                    }
                ],
                "restrictions": [],
            }
        return json.dumps(payload, indent=2)


__all__ = ["LLMClient", "MockLLMClient"]

"""Utilities to parse the LLM JSON output into ``OntologyDraft`` instances."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from .data_models import (
    DataProperty,
    Individual,
    ObjectProperty,
    OntologyClass,
    OntologyDraft,
    Restriction,
)


class DraftParserError(RuntimeError):
    pass


class DraftParser:
    """Converts the raw JSON string produced by the LLM into data classes."""

    def parse(self, payload: str | Dict[str, Any]) -> OntologyDraft:
        data = json.loads(payload) if isinstance(payload, str) else payload
        try:
            classes = [OntologyClass(**item) for item in data.get("classes", [])]
            object_properties = [ObjectProperty(**item) for item in data.get("object_properties", [])]
            data_properties = [DataProperty(**item) for item in data.get("data_properties", [])]
            restrictions = [Restriction(**item) for item in data.get("restrictions", [])]
            individuals = [Individual(**item) for item in data.get("individuals", [])]
        except TypeError as exc:  # pragma: no cover - defensive guard
            raise DraftParserError(str(exc)) from exc
        return OntologyDraft(
            classes=classes,
            object_properties=object_properties,
            data_properties=data_properties,
            restrictions=restrictions,
            individuals=individuals,
        )


__all__ = ["DraftParser", "DraftParserError"]

"""Typed domain objects used throughout the OG-NSD pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


@dataclass
class Placeholder:
    span: str
    type: str
    start: int
    end: int


@dataclass
class Requirement:
    title: str
    text: str
    boilerplate: dict
    boilerplate_type: str
    placeholders: Sequence[Placeholder]

    @classmethod
    def from_json(cls, obj: dict) -> "Requirement":
        placeholders = [Placeholder(**ph) for ph in obj.get("placeholders", [])]
        return cls(
            title=obj.get("title", ""),
            text=obj.get("text", ""),
            boilerplate=obj.get("boilerplate", {}),
            boilerplate_type=obj.get("boilerplate_type", ""),
            placeholders=placeholders,
        )


@dataclass
class ValidationResult:
    conforms: bool
    text_report: str
    graph_report: str | None = None

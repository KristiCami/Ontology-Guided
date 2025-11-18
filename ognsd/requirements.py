"""Utilities for parsing requirement JSON fragments."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional
import json
import re


@dataclass
class Placeholder:
    """Placeholder span annotated in the dataset."""

    span: str
    type: str
    start: int | None = None
    end: int | None = None


@dataclass
class Requirement:
    """Structured requirement entry."""

    identifier: str
    title: str
    text: str
    boilerplate: Dict[str, Optional[str]]
    boilerplate_type: Optional[str] = None
    placeholders: List[Placeholder] = field(default_factory=list)
    meta: Dict[str, str] | None = None
    axioms: Dict[str, List[str]] | None = None

    def iter_segments(self) -> Iterator[str]:
        for key in ("prefix", "main", "suffix"):
            segment = (self.boilerplate or {}).get(key)
            if segment:
                yield segment
        if self.text:
            yield self.text


PLACEHOLDER_PATTERN = re.compile(r"<([^:>]+):([^>]+)>")


def extract_inline_placeholders(segment: str) -> Iterable[Placeholder]:
    """Parse inline placeholders of the form <Type:Value>."""

    for match in PLACEHOLDER_PATTERN.finditer(segment):
        yield Placeholder(
            span=match.group(2).strip(),
            type=match.group(1).strip(),
            start=match.start(),
            end=match.end(),
        )


def load_json_fragments(path: Path) -> List[dict]:
    """Load newline-separated JSON objects with relaxed formatting."""

    path = Path(path)
    buffer: List[str] = []
    depth = 0
    objects: List[dict] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line and not buffer:
            continue
        buffer.append(raw_line)
        depth += raw_line.count("{") - raw_line.count("}")
        if depth == 0 and buffer:
            fragment = "\n".join(buffer).strip()
            if fragment:
                objects.append(json.loads(fragment))
            buffer.clear()
    if buffer:
        fragment = "\n".join(buffer).strip()
        if fragment:
            objects.append(json.loads(fragment))
    return objects


def load_requirements(path: Path) -> List[Requirement]:
    """Load Requirement objects from a JSON fragments file."""

    records = load_json_fragments(path)
    requirements: List[Requirement] = []
    for idx, record in enumerate(records, start=1):
        placeholders = [Placeholder(**ph) for ph in record.get("placeholders", [])]
        requirements.append(
            Requirement(
                identifier=f"REQ-{idx:03d}",
                title=record.get("title", f"Requirement {idx}"),
                text=record.get("text", ""),
                boilerplate=record.get("boilerplate", {}),
                boilerplate_type=record.get("boilerplate_type"),
                placeholders=placeholders,
                meta=record.get("meta"),
                axioms=record.get("axioms"),
            )
        )
    return requirements


__all__ = [
    "Placeholder",
    "Requirement",
    "extract_inline_placeholders",
    "load_requirements",
]

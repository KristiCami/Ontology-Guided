"""Utility helpers for the OG-NSD project."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Iterator, List

from .structures import Requirement


def load_requirements(path: Path) -> List[Requirement]:
    """Load requirement objects from a JSONL file."""

    data = []
    with path.open("r", encoding="utf-8") as handle:
        buffer = ""
        for line in handle:
            buffer += line
            if line.strip().endswith("}"):
                obj = json.loads(buffer)
                data.append(Requirement.from_json(obj))
                buffer = ""
    return data


def normalize_identifier(value: str) -> str:
    """Convert free text into a Turtle-friendly local name."""

    slug = re.sub(r"[^a-zA-Z0-9]", "_", value.strip())
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_") or "Concept"


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

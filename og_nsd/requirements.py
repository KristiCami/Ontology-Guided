"""Requirement ingestion and preprocessing utilities."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence


@dataclass
class Requirement:
    """Structured representation of a single requirement sentence."""

    identifier: str
    title: str
    text: str
    boilerplate_prefix: str | None
    boilerplate_main: str | None
    boilerplate_suffix: str | None

    @property
    def boilerplate(self) -> str:
        segments = [self.boilerplate_prefix, self.boilerplate_main, self.boilerplate_suffix]
        return " \n".join(seg for seg in segments if seg)


class RequirementLoader:
    """Loads requirement artifacts from JSON/JSONL files."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self, limit: int | None = None) -> List[Requirement]:
        records = list(self._iter_records())
        if limit is not None:
            records = records[:limit]
        return [self._as_requirement(idx, rec) for idx, rec in enumerate(records, start=1)]

    def _iter_records(self) -> Iterator[dict]:
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return iter(())
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                parsed = [parsed]
            return iter(parsed)
        except json.JSONDecodeError:
            # Treat file as JSON Lines.
            def _iter() -> Iterator[dict]:
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("//"):
                        continue
                    yield json.loads(line)

            return _iter()

    def _as_requirement(self, idx: int, record: dict) -> Requirement:
        boilerplate = record.get("boilerplate", {})
        return Requirement(
            identifier=record.get("id") or f"REQ-{idx:03d}",
            title=record.get("title", f"Requirement {idx}"),
            text=record.get("text", "").strip(),
            boilerplate_prefix=boilerplate.get("prefix"),
            boilerplate_main=boilerplate.get("main"),
            boilerplate_suffix=boilerplate.get("suffix"),
        )


def chunk_requirements(requirements: Sequence[Requirement], size: int) -> Iterable[List[Requirement]]:
    """Yield batches of requirements for more efficient prompting."""

    chunk: List[Requirement] = []
    for req in requirements:
        chunk.append(req)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

"""Requirement ingestion and preprocessing utilities."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence


@dataclass
class Requirement:
    """Structured representation of a single requirement sentence."""

    identifier: str
    title: str
    text: str
    axioms: dict | None
    boilerplate_prefix: str | None
    boilerplate_main: str | None
    boilerplate_suffix: str | None
    split: str | None = None

    @property
    def boilerplate(self) -> str:
        segments = [self.boilerplate_prefix, self.boilerplate_main, self.boilerplate_suffix]
        return " \n".join(seg for seg in segments if seg)


class RequirementLoader:
    """Loads requirement artifacts from JSON/JSONL files."""

    def __init__(self, path: Path, dev_ids: set[str] | None = None, test_ids: set[str] | None = None) -> None:
        self.path = path
        self.dev_ids = dev_ids or set()
        self.test_ids = test_ids or set()
        self.unmatched_split_ids: set[str] = set(self.dev_ids) | set(self.test_ids)

    def load(self, limit: int | None = None) -> List[Requirement]:
        records = list(self._iter_records())
        if limit is not None:
            records = records[:limit]
        requirements: List[Requirement] = []
        for idx, rec in enumerate(records, start=1):
            requirement = self._as_requirement(idx, rec)
            requirements.append(requirement)
        return requirements

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
            # Treat file as JSON Lines or multi-line JSON objects separated by
            # blank lines. Lines that only contain commas are ignored to allow
            # slightly malformed pretty-printed JSONL files.
            def _iter() -> Iterator[dict]:
                buffer: list[str] = []

                def flush_buffer() -> dict | None:
                    if not buffer:
                        return None
                    parsed = json.loads("\n".join(buffer))
                    buffer.clear()
                    return parsed

                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("//") or stripped == ",":
                        continue

                    buffer.append(line)
                    try:
                        # Attempt to parse whenever we add a line; successful
                        # parses are yielded immediately so the next object can
                        # start accumulating.
                        parsed = flush_buffer()
                    except json.JSONDecodeError:
                        # Keep accumulating lines until a complete JSON object
                        # can be parsed.
                        continue
                    if parsed is not None:
                        yield parsed

                # Catch any trailing buffered object.
                try:
                    parsed = flush_buffer()
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    raise json.JSONDecodeError(
                        f"Failed to parse requirements from {self.path}", text, exc.pos
                    ) from exc
                if parsed is not None:
                    yield parsed

            return _iter()

    def _as_requirement(self, idx: int, record: dict) -> Requirement:
        identifier = self._determine_identifier(idx, record)
        split = self._resolve_split(identifier)
        boilerplate = record.get("boilerplate", {})
        return Requirement(
            identifier=identifier,
            title=record.get("title", f"Requirement {idx}"),
            text=record.get("text", "").strip(),
            axioms=record.get("axioms"),
            boilerplate_prefix=boilerplate.get("prefix"),
            boilerplate_main=boilerplate.get("main"),
            boilerplate_suffix=boilerplate.get("suffix"),
            split=split,
        )

    def _determine_identifier(self, idx: int, record: dict) -> str:
        for key in ("id", "sentence_id", "identifier"):
            if record.get(key):
                return str(record[key])

        meta_title = record.get("meta", {}).get("title")
        if meta_title:
            return self._normalize_title(str(meta_title))

        if record.get("title"):
            return self._normalize_title(str(record["title"]))

        return f"REQ-{idx:03d}"

    def _normalize_title(self, title: str) -> str:
        match = re.search(r"(?:functional\s+requirement|fr)[\s_-]*(\d+)", title, flags=re.IGNORECASE)
        if match:
            return f"FR-{match.group(1)}"
        return title.strip()

    def _resolve_split(self, identifier: str) -> str | None:
        if identifier in self.dev_ids:
            self.unmatched_split_ids.discard(identifier)
            return "dev"
        if identifier in self.test_ids:
            self.unmatched_split_ids.discard(identifier)
            return "test"
        return None


def load_split_ids(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


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

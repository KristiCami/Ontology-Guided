"""Competency question execution utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rdflib import Graph


@dataclass
class CompetencyQuestionResult:
    query: str
    success: bool
    answer: Optional[bool]
    message: str


class CompetencyQuestionRunner:
    def __init__(self, path: Path) -> None:
        self.path = path
        if not path.exists():
            raise FileNotFoundError(path)
        self.queries = self._load_queries(path)

    def _load_queries(self, path: Path) -> List[str]:
        content = path.read_text(encoding="utf-8")
        buffer: List[str] = []
        queries: List[str] = []
        brace_depth = 0

        def flush_buffer() -> None:
            nonlocal buffer
            query = "\n".join(buffer).strip()
            if query:
                queries.append(query)
            buffer = []

        for line in content.splitlines():
            stripped = line.strip()
            if not buffer and (not stripped or stripped.startswith("#")):
                continue

            buffer.append(line)
            brace_depth += line.count("{") - line.count("}")

            if buffer and brace_depth == 0 and any("ASK" in b.upper() for b in buffer):
                flush_buffer()

        if buffer:
            flush_buffer()

        return [q for q in queries if "ASK" in q.upper()]

    def run(self, graph: Graph) -> List[CompetencyQuestionResult]:
        results: List[CompetencyQuestionResult] = []
        for query in self.queries:
            try:
                answer = bool(graph.query(query).askAnswer)
                results.append(
                    CompetencyQuestionResult(
                        query=query,
                        success=True,
                        answer=answer,
                        message="",
                    )
                )
            except Exception as exc:  # pragma: no cover - rdflib runtime
                results.append(
                    CompetencyQuestionResult(
                        query=query,
                        success=False,
                        answer=None,
                        message=str(exc),
                    )
                )
        return results

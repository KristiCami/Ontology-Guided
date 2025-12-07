"""Competency question execution utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from rdflib import Graph


@dataclass
class CompetencyQuestionResult:
    query: str
    success: bool
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
        for line in content.splitlines():
            if line.strip().startswith("#") and not buffer:
                continue
            buffer.append(line)
            if line.strip().endswith("}"):
                query = "\n".join(buffer).strip()
                if query:
                    queries.append(query)
                buffer = []
        if buffer:
            queries.append("\n".join(buffer).strip())
        return [q for q in queries if "ASK" in q.upper()]

    def run(self, graph: Graph) -> List[CompetencyQuestionResult]:
        results: List[CompetencyQuestionResult] = []
        for query in self.queries:
            try:
                success = bool(graph.query(query).askAnswer)
                results.append(CompetencyQuestionResult(query=query, success=success, message=""))
            except Exception as exc:  # pragma: no cover - rdflib runtime
                results.append(CompetencyQuestionResult(query=query, success=False, message=str(exc)))
        return results

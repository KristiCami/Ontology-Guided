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
        # Split competency questions on blank lines rather than closing braces so
        # nested FILTER / UNION blocks do not prematurely terminate a query.
        blocks = [block.strip() for block in content.split("\n\n") if block.strip()]

        queries: List[str] = []
        for block in blocks:
            # Ignore standalone comment blocks
            lines = [line for line in block.splitlines() if line.strip()]
            if lines and all(line.lstrip().startswith("#") for line in lines):
                continue
            query = "\n".join(lines).strip()
            if query and "ASK" in query.upper():
                queries.append(query)

        return queries

    def run(self, graph: Graph) -> List[CompetencyQuestionResult]:
        results: List[CompetencyQuestionResult] = []
        for query in self.queries:
            try:
                success = bool(graph.query(query).askAnswer)
                results.append(CompetencyQuestionResult(query=query, success=success, message=""))
            except Exception as exc:  # pragma: no cover - rdflib runtime
                results.append(CompetencyQuestionResult(query=query, success=False, message=str(exc)))
        return results

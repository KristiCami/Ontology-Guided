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
        """Load ASK queries from a SPARQL file.

        The legacy parser split queries whenever a line ended with ``}``, which
        broke patterns containing nested braces (for example ``FILTER
        NOT EXISTS`` blocks). We now keep track of brace depth and only finalize
        a query when the braces are balanced and we encounter a blank separator
        line. This is intentionally lightweight – the file is expected to
        contain straightforward ASK queries separated by blank lines.
        """

        content = path.read_text(encoding="utf-8")
        buffer: List[str] = []
        queries: List[str] = []
        depth = 0

        def flush_buffer() -> None:
            nonlocal buffer, queries
            query = "\n".join(buffer).strip()
            if query:
                queries.append(query)
            buffer = []

        for line in content.splitlines():
            stripped = line.strip()

            if not buffer and (stripped.startswith("#") or not stripped):
                # Skip leading comments/blank lines before a query starts
                continue

            buffer.append(line)
            depth += line.count("{") - line.count("}")

            if depth == 0 and not stripped:
                flush_buffer()

        if buffer:
            flush_buffer()

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

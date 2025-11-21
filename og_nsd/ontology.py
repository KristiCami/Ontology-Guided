"""Ontology graph assembly utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional

from rdflib import Graph


@dataclass
class OntologyState:
    graph: Graph
    turtle_snippets: list[str]


class OntologyAssembler:
    def __init__(self, base_ontology_path: Optional[Path] = None) -> None:
        self.base_path = base_ontology_path

    def bootstrap(self) -> OntologyState:
        graph = Graph()
        snippets: list[str] = []
        if self.base_path and self.base_path.exists():
            graph.parse(self.base_path)
            snippets.append(self.base_path.read_text(encoding="utf-8"))
        return OntologyState(graph=graph, turtle_snippets=snippets)

    def add_turtle(self, state: OntologyState, turtle: str) -> None:
        cleaned = _strip_code_fence(turtle)
        try:
            state.graph.parse(data=cleaned, format="turtle")
        except Exception as exc:  # pragma: no cover - requires rdflib parse error
            raise ValueError(f"Failed to parse Turtle from LLM response: {exc}") from exc
        state.turtle_snippets.append(cleaned)

    def serialize(self, state: OntologyState, path: Path) -> None:
        path.write_text(state.graph.serialize(format="turtle"), encoding="utf-8")


_CODE_FENCE_RE = re.compile(r"```(?:turtle)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def _strip_code_fence(turtle: str) -> str:
    """Remove Markdown code fences often returned by LLMs."""

    match = _CODE_FENCE_RE.search(turtle)
    if match:
        return match.group(1).strip()
    return turtle.strip()

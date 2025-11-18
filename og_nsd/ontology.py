"""Ontology graph assembly utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
        state.graph.parse(data=turtle, format="turtle")
        state.turtle_snippets.append(turtle)

    def serialize(self, state: OntologyState, path: Path) -> None:
        path.write_text(state.graph.serialize(format="turtle"), encoding="utf-8")

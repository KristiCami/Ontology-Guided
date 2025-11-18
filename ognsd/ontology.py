"""Lightweight TTL generation utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set

PREFIXES = {
    "atm": "http://lod.csd.auth.gr/atm/atm.ttl#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
}


@dataclass
class RequirementNode:
    identifier: str
    title: str
    text: str
    boilerplate_type: str | None
    roles: Dict[str, Set[str]] = field(default_factory=dict)

    def add_role(self, role: str, value: str) -> None:
        self.roles.setdefault(role, set()).add(value)


class OntologyBuilder:
    """In-memory representation of the drafted ontology."""

    def __init__(self, bootstrap_files: Iterable[Path] | None = None) -> None:
        self.bootstrap_segments: List[str] = []
        for path in bootstrap_files or []:
            self.bootstrap_segments.append(Path(path).read_text(encoding="utf-8"))
        self.classes: Set[str] = set()
        self.requirements: Dict[str, RequirementNode] = {}

    def register_class(self, label: str) -> None:
        self.classes.add(label)

    def register_requirement(self, req_id: str, title: str, text: str, boilerplate_type: str | None) -> RequirementNode:
        node = self.requirements.get(req_id)
        if not node:
            node = RequirementNode(req_id, title, text, boilerplate_type)
            self.requirements[req_id] = node
        return node

    @staticmethod
    def _prefixes_block() -> List[str]:
        return [f"@prefix {p}: <{iri}> ." for p, iri in PREFIXES.items()]

    def _render_requirement(self, node: RequirementNode) -> str:
        lines = [f"atm:{node.identifier} a atm:BasicRequirement ;"]
        lines.append(f"  rdfs:label \"{node.title}\" ;")
        if node.text:
            text = node.text.replace("\"", "'")
            lines.append(f"  atm:requirementText \"{text}\" ;")
        if node.boilerplate_type:
            lines.append(f"  atm:boilerplateType \"{node.boilerplate_type}\" ;")
        for role, values in sorted(node.roles.items()):
            joined = ", ".join(f"atm:{v}" for v in sorted(values))
            lines.append(f"  atm:{role} {joined} ;")
        if lines[-1].endswith(";"):
            lines[-1] = lines[-1][:-1] + "."
        else:
            lines.append(".")
        return "\n".join(lines)

    def to_turtle(self) -> str:
        blocks: List[str] = []
        blocks.extend(self.bootstrap_segments)
        blocks.append("\n".join(self._prefixes_block()))
        for cls in sorted(self.classes):
            blocks.append(f"atm:{cls} a owl:Class .")
        for node in self.requirements.values():
            blocks.append(self._render_requirement(node))
        return "\n\n".join(blocks)


__all__ = ["OntologyBuilder", "RequirementNode"]

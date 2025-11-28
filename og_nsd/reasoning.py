"""Optional DL reasoning helpers."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rdflib import Graph

try:  # pragma: no cover - optional heavy dependency
    from owlready2 import get_ontology, sync_reasoner_pellet
except Exception:  # pragma: no cover
    get_ontology = None  # type: ignore
    sync_reasoner_pellet = None  # type: ignore


@dataclass
class ReasonerReport:
    enabled: bool
    consistent: Optional[bool]
    unsatisfiable_classes: List[str]
    notes: str


class OwlreadyReasoner:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled and get_ontology is not None

    def run(self, graph: Graph) -> ReasonerReport:
        if not self.enabled or get_ontology is None:
            return ReasonerReport(False, None, [], "Reasoner disabled or owlready2 unavailable.")
        tmp_dir = Path(tempfile.gettempdir())
        tmp_path = tmp_dir / "og_nsd_reasoner.owl"
        tmp_path.write_text(graph.serialize(format="pretty-xml"), encoding="utf-8")

        # Owlready2 and Pellet expect forward-slash paths. On Windows, passing
        # a raw filesystem path with backslashes results in invalid escape
        # sequences (e.g., "\\s") that Pellet cannot parse. Using
        # ``Path.as_posix`` normalizes the path to a portable forward-slash
        # string without introducing ``file://`` prefixes that some Owlready2
        # versions mishandle on Windows.
        onto = get_ontology(tmp_path.as_posix()).load()
        notes = []
        consistent = None
        if sync_reasoner_pellet is None:
            notes.append("Pellet not available; skipped reasoning.")
            unsat = []
        else:
            with onto:
                sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True)
            unsat = [
                cls.name
                for cls in onto.classes()
                if any(str(eq) == "Nothing" for eq in cls.equivalent_to)
            ]
            consistent = True
        return ReasonerReport(True, consistent, unsat, " ".join(notes))

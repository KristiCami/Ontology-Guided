"""Optional DL reasoning helpers."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional

from rdflib import Graph, Literal
from rdflib.namespace import XSD

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


@dataclass
class ReasonerResult:
    """Bundle of the reasoner diagnostics and the expanded graph."""

    report: ReasonerReport
    expanded_graph: Graph


class OwlreadyReasoner:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled and get_ontology is not None

    def run(self, graph: Graph) -> ReasonerResult:
        """Run Pellet reasoning and return the expanded graph.

        The expanded graph is always populated: when reasoning is disabled or
        owlready2 is missing we return a defensive copy of the input graph so
        downstream SHACL validation still receives a graph object.
        """

        base_graph = Graph()
        base_graph.parse(data=graph.serialize(format="turtle"))

        # Owlready/Pellet will choke on invalid xsd:decimal lexical forms. Detect
        # and coerce any such literals to plain strings so reasoning can
        # continue rather than failing with an XML parse error (e.g., when a
        # literal like "amount" is incorrectly typed as xsd:decimal).
        invalid_decimals: list[tuple] = []
        for subject, predicate, obj in list(base_graph):
            if isinstance(obj, Literal) and obj.datatype == XSD.decimal:
                try:
                    Decimal(str(obj))
                except (InvalidOperation, ValueError):
                    base_graph.remove((subject, predicate, obj))
                    base_graph.add((subject, predicate, Literal(str(obj))))
                    invalid_decimals.append((subject, predicate, obj))
        notes = []
        if invalid_decimals:
            notes.append(
                f"Coerced {len(invalid_decimals)} invalid xsd:decimal literals to plain strings before reasoning."
            )

        if not self.enabled or get_ontology is None:
            message = "Reasoner disabled or owlready2 unavailable."
            if notes:
                message = " ".join(notes + [message])
            report = ReasonerReport(False, None, [], message)
            return ReasonerResult(report=report, expanded_graph=base_graph)

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
        consistent = None
        if sync_reasoner_pellet is None:
            notes.append("Pellet not available; skipped reasoning.")
            unsat = []
            expanded_graph = base_graph
        else:
            with onto:
                sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True)
            unsat = [
                cls.name
                for cls in onto.classes()
                if any(str(eq) == "Nothing" for eq in cls.equivalent_to)
            ]
            consistent = True
            expanded_graph = onto.world.as_rdflib_graph()

        report = ReasonerReport(True, consistent, unsat, " ".join(notes))
        return ReasonerResult(report=report, expanded_graph=expanded_graph)

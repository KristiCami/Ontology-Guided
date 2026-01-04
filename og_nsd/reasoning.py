"""Optional DL reasoning helpers."""
from __future__ import annotations

import tempfile
from decimal import Decimal
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from isodate import parse_datetime
from rdflib import Graph, Literal, OWL, RDF
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
    backend: Optional[str] = None


@dataclass
class ReasonerResult:
    """Bundle of the reasoner diagnostics and the expanded graph."""

    report: ReasonerReport
    expanded_graph: Graph


class OwlreadyReasoner:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled and get_ontology is not None
        self.backend = "pellet" if self.enabled and sync_reasoner_pellet is not None else None

    def run(self, graph: Graph) -> ReasonerResult:
        """Run Pellet reasoning and return the expanded graph.

        The expanded graph is always populated: when reasoning is disabled or
        owlready2 is missing we return a defensive copy of the input graph so
        downstream SHACL validation still receives a graph object.
        """

        base_graph, coerced_literals = _sanitize_numeric_literals(graph)
        notes: List[str] = []
        if coerced_literals:
            notes.append(
                f"Coerced {coerced_literals} invalid literal(s) or datatype-property values to xsd:string for reasoning."
            )

        if not self.enabled or get_ontology is None:
            notes.append("Reasoner disabled or owlready2 unavailable.")
            report = ReasonerReport(False, None, [], " ".join(notes), backend=None)
            return ReasonerResult(report=report, expanded_graph=base_graph)

        tmp_dir = Path(tempfile.gettempdir())
        tmp_path = tmp_dir / "og_nsd_reasoner.owl"
        tmp_path.write_text(base_graph.serialize(format="pretty-xml"), encoding="utf-8")

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

        report = ReasonerReport(True, consistent, unsat, " ".join(notes), backend=self.backend)
        return ReasonerResult(report=report, expanded_graph=expanded_graph)


def _sanitize_numeric_literals(graph: Graph) -> Tuple[Graph, int]:
    """Repair malformed literals and datatype-property objects prior to reasoning.

    LLM outputs occasionally annotate text tokens (e.g., "amount" or "timestamp")
    with numeric or datetime datatypes, or provide resources where a datatype
    property expects a literal. Owlready2 and Pellet reject such content when
    serializing/reading RDF/XML, so we defensively coerce these cases to plain
    strings before invoking the reasoner.
    """

    numeric_types = {
        XSD.decimal,
        XSD.double,
        XSD.float,
        XSD.integer,
        XSD.int,
        XSD.long,
        XSD.short,
    }
    datetime_types = {XSD.dateTime}

    datatype_properties = set(graph.subjects(RDF.type, OWL.DatatypeProperty))

    sanitized = Graph()
    for prefix, uri in graph.namespace_manager.namespaces():
        sanitized.bind(prefix, uri)

    fixes = 0
    for triple in graph:
        subject, predicate, obj = triple
        if isinstance(obj, Literal):
            coerced, changed = _coerce_literal(obj, numeric_types, datetime_types)
            if changed:
                fixes += 1
            sanitized.add((subject, predicate, coerced))
            continue

        if predicate in datatype_properties:
            sanitized.add((subject, predicate, Literal(str(obj))))
            fixes += 1
            continue

        sanitized.add(triple)

    return sanitized, fixes


def _is_valid_numeric_literal(literal: Literal) -> bool:
    if literal.datatype in {XSD.float, XSD.double}:
        parser = float
    elif literal.datatype in {XSD.integer, XSD.int, XSD.long, XSD.short}:
        parser = int
    else:
        parser = Decimal

    try:
        parser(str(literal))
    except Exception:
        return False
    return True


def _is_valid_datetime_literal(literal: Literal) -> bool:
    try:
        parse_datetime(str(literal))
    except Exception:
        return False
    return True


def _coerce_literal(
    literal: Literal, numeric_types: set, datetime_types: set
) -> Tuple[Literal, bool]:
    if literal.datatype in numeric_types:
        if _is_valid_numeric_literal(literal):
            return literal, False
        return Literal(str(literal)), True

    if literal.datatype in datetime_types:
        if _is_valid_datetime_literal(literal):
            return literal, False
        return Literal(str(literal)), True

    return literal, False

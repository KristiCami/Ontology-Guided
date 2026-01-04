"""Optional DL reasoning helpers."""
from __future__ import annotations

import tempfile
from decimal import Decimal
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from isodate import parse_datetime
from rdflib import Graph, Literal, OWL, RDF, RDFS
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
        base_graph, stripped_restrictions = _strip_invalid_restrictions(base_graph)
        base_graph, declared_classes = _declare_missing_classes(base_graph)
        notes: List[str] = []
        if coerced_literals:
            notes.append(
                f"Coerced {coerced_literals} invalid literal(s) or datatype-property values to xsd:string for reasoning."
            )
        if stripped_restrictions:
            notes.append(f"Removed {stripped_restrictions} invalid restriction(s) before reasoning.")
        if declared_classes:
            notes.append(f"Declared {declared_classes} missing owl:Class resource(s) for class-level axioms.")

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
            try:
                with onto:
                    sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True)
                unsat = [
                    cls.name
                    for cls in onto.classes()
                    if any(str(eq) == "Nothing" for eq in cls.equivalent_to)
                ]
                consistent = True
                expanded_graph = onto.world.as_rdflib_graph()
            except Exception as exc:  # pragma: no cover - exercised via mocks in tests
                notes.append(f"Pellet failed: {exc}")
                report = ReasonerReport(
                    True,
                    consistent,
                    [],
                    " ".join(notes),
                    backend=self.backend,
                )
                return ReasonerResult(report=report, expanded_graph=base_graph)

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


def _declare_missing_classes(graph: Graph) -> Tuple[Graph, int]:
    """Ensure subjects/objects that participate in class-level axioms are typed as classes.

    Pellet can raise ordering errors when subclass/equivalence relations reference
    resources that are never declared as ``owl:Class``. We defensively add class
    declarations for any resource that appears in common TBox positions.
    """

    classish_predicates = {
        RDFS.subClassOf,
        OWL.equivalentClass,
        OWL.disjointWith,
    }

    declared_classes = set(graph.subjects(RDF.type, OWL.Class))
    additions: list[tuple] = []

    for s, p, o in graph:
        if p in classish_predicates:
            if not isinstance(s, Literal) and s not in declared_classes:
                additions.append((s, RDF.type, OWL.Class))
                declared_classes.add(s)
            if not isinstance(o, Literal) and o not in declared_classes:
                additions.append((o, RDF.type, OWL.Class))
                declared_classes.add(o)

    if not additions:
        return graph, 0

    enriched = Graph()
    for prefix, uri in graph.namespace_manager.namespaces():
        enriched.bind(prefix, uri)
    for triple in graph:
        enriched.add(triple)
    for triple in additions:
        enriched.add(triple)
    return enriched, len(additions)


def _strip_invalid_restrictions(graph: Graph) -> Tuple[Graph, int]:
    """Remove malformed OWL restrictions that Pellet cannot handle.

    Some LLM outputs create ``owl:Restriction`` nodes that combine
    ``owl:onProperty`` with unsupported constructs such as ``owl:complementOf``,
    or omit a filler/cardinality. Pellet treats these as fatal errors, so we
    defensively drop the offending blank nodes (and any triples that reference
    them) before invoking the reasoner.
    """

    valid_fillers = {
        OWL.someValuesFrom,
        OWL.allValuesFrom,
        OWL.hasValue,
        OWL.minCardinality,
        OWL.maxCardinality,
        OWL.cardinality,
        OWL.qualifiedCardinality,
        OWL.minQualifiedCardinality,
        OWL.maxQualifiedCardinality,
    }

    invalid_nodes: set = set()
    for restriction in graph.subjects(RDF.type, OWL.Restriction):
        on_props = list(graph.objects(restriction, OWL.onProperty))
        filler_terms = {filler: list(graph.objects(restriction, filler)) for filler in valid_fillers}
        has_filler = any(values for values in filler_terms.values())
        has_complement = any(graph.objects(restriction, OWL.complementOf))

        # SomeValues/AllValues/Min/Max/... fillers must be resources, not literals.
        has_literal_filler = any(
            any(isinstance(value, Literal) for value in values)
            for predicate, values in filler_terms.items()
            if predicate != OWL.hasValue  # hasValue can legitimately point to a literal
        )

        if len(on_props) != 1 or not has_filler or has_complement or has_literal_filler:
            invalid_nodes.add(restriction)

    if not invalid_nodes:
        return graph, 0

    filtered = Graph()
    for prefix, uri in graph.namespace_manager.namespaces():
        filtered.bind(prefix, uri)

    removed = 0
    for triple in graph:
        if triple[0] in invalid_nodes or triple[2] in invalid_nodes:
            removed += 1
            continue
        filtered.add(triple)

    return filtered, removed


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

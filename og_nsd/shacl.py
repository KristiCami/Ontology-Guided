"""SHACL validation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from pathlib import Path
from typing import List, Optional

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SH, XSD

try:
    from pyshacl import validate
    _PYSHACL_IMPORT_ERROR: Optional[Exception] = None
except ImportError as exc:  # pragma: no cover
    validate = None  # type: ignore
    _PYSHACL_IMPORT_ERROR = exc


@dataclass
class ShaclReport:
    conforms: bool
    text_report: str
    report_graph_ttl: Optional[str]
    results: List["ShaclResult"]


@dataclass
class ShaclResult:
    """Structured representation of a single SHACL validation result."""

    focus_node: Optional[str]
    path: Optional[str]
    message: Optional[str]
    severity: Optional[str]
    source_shape: Optional[str]
    constraint_component: Optional[str]
    value: Optional[str]


class ShaclValidator:
    def __init__(self, shapes_path: Path) -> None:
        if not shapes_path.exists():
            raise FileNotFoundError(f"SHACL shapes file not found: {shapes_path}")
        self.shapes_path = shapes_path
        self.shapes_graph = Graph().parse(shapes_path)

    def validate(self, data_graph: Graph) -> ShaclReport:
        if validate is None:
            reason = (
                "pyshacl import failed"
                f" ({_PYSHACL_IMPORT_ERROR}); install dependencies via 'pip install -r requirements.txt'"
            )
            return ShaclReport(False, reason, None, [])

        invalid_decimals = self._find_invalid_decimal_literals(data_graph)
        if invalid_decimals:
            message_lines = ["Invalid xsd:decimal literals detected before SHACL validation:"]
            for subject, predicate, literal_value in invalid_decimals:
                message_lines.append(
                    f"- {subject} {predicate} literal=\"{literal_value}\""
                )
            message = "\n".join(message_lines)
            return ShaclReport(False, message, None, [])
        conforms, report_graph, text_report = validate(
            data_graph,
            shacl_graph=self.shapes_graph,
            inference="rdfs",
            advanced=True,
            serialize_report_graph=False,
        )
        report_graph_ttl: Optional[str] = None
        parsed_results: List[ShaclResult] = []
        if isinstance(report_graph, bytes):
            report_graph_ttl = report_graph.decode("utf-8")
        elif isinstance(report_graph, str):
            report_graph_ttl = report_graph
        elif report_graph:
            report_graph_ttl = report_graph.serialize(format="turtle")
            parsed_results = self._extract_results(report_graph)
        return ShaclReport(bool(conforms), str(text_report), report_graph_ttl, parsed_results)

    def _find_invalid_decimal_literals(self, data_graph: Graph) -> list[tuple[str, str, str]]:
        """Return any literals with datatype xsd:decimal that cannot be parsed.

        PySHACL's OWL-RL inference raises a runtime error when encountering an
        invalid xsd:decimal lexical form. Detecting these upfront lets the
        pipeline return a structured report instead of crashing.
        """

        invalid_literals: list[tuple[str, str, str]] = []
        for subject, predicate, obj in data_graph:
            if isinstance(obj, Literal) and obj.datatype == XSD.decimal:
                lexical_value = str(obj)
                try:
                    Decimal(lexical_value)
                except (InvalidOperation, ValueError):
                    invalid_literals.append((str(subject), str(predicate), lexical_value))
        return invalid_literals

    def _extract_results(self, report_graph: Graph) -> List[ShaclResult]:
        results: List[ShaclResult] = []
        for result_node in report_graph.subjects(RDF.type, SH.ValidationResult):
            def _maybe(pred: str) -> Optional[str]:
                node = report_graph.value(result_node, SH[pred])
                return str(node) if node else None

            results.append(
                ShaclResult(
                    focus_node=_maybe("focusNode"),
                    path=_maybe("resultPath"),
                    message=_maybe("resultMessage"),
                    severity=_maybe("resultSeverity"),
                    source_shape=_maybe("sourceShape"),
                    constraint_component=_maybe("sourceConstraintComponent"),
                    value=_maybe("value"),
                )
            )
        return results


def summarize_shacl_report(report: ShaclReport) -> dict:
    """Aggregate SHACL results into a compact severity summary."""

    hard = 0
    soft = 0
    for result in report.results:
        severity_value = (result.severity or "").lower()
        if "violation" in severity_value:
            hard += 1
        else:
            soft += 1
    total = len(report.results)
    return {
        "total": total,
        "violations": {
            "hard": hard,
            "soft": soft,
        },
    }


def generate_minimal_target_instances(
    shapes_graph: Graph, base_namespace: str, *, instance_prefix: str = "Seed"
) -> Graph:
    """Generate placeholder individuals for each ``sh:targetClass``.

    For every ``sh:NodeShape`` with a ``sh:targetClass``, the returned graph contains
    one instance of that class plus placeholder values that satisfy ``sh:minCount``
    constraints for properties declaring ``sh:datatype`` or ``sh:class``. This is
    intended to prime drafts with minimally conforming focus nodes before the first
    validation pass.
    """

    seeds = Graph()
    for prefix, uri in shapes_graph.namespace_manager.namespaces():
        seeds.bind(prefix, uri)

    base = Namespace(_normalize_namespace(base_namespace))
    class_counts: dict[URIRef, int] = {}

    for node_shape in shapes_graph.subjects(RDF.type, SH.NodeShape):
        target_class = shapes_graph.value(node_shape, SH.targetClass)
        if not isinstance(target_class, URIRef):
            continue

        focus_instance = _build_instance_uri(base, target_class, instance_prefix, class_counts)
        seeds.add((focus_instance, RDF.type, target_class))

        for prop_shape in shapes_graph.objects(node_shape, SH.property):
            min_count_raw = shapes_graph.value(prop_shape, SH.minCount)
            if min_count_raw is None:
                continue
            try:
                min_count = int(min_count_raw)
            except (TypeError, ValueError):
                continue
            if min_count <= 0:
                continue

            path = shapes_graph.value(prop_shape, SH.path)
            if path is None:
                continue
            datatype = shapes_graph.value(prop_shape, SH.datatype)
            class_constraint = shapes_graph.value(prop_shape, SH.class)

            for occurrence in range(min_count):
                if isinstance(path, BNode):
                    inverse_predicate = shapes_graph.value(path, SH.inversePath)
                    if not isinstance(inverse_predicate, URIRef):
                        continue
                    target = _target_for_class_constraint(
                        seeds, base, class_constraint, instance_prefix, class_counts
                    )
                    seeds.add((target, inverse_predicate, focus_instance))
                    continue

                if datatype:
                    literal_value = _placeholder_literal(datatype, occurrence)
                    seeds.add((focus_instance, path, literal_value))
                else:
                    target = _target_for_class_constraint(
                        seeds, base, class_constraint, instance_prefix, class_counts
                    )
                    seeds.add((focus_instance, path, target))

    return seeds


def _normalize_namespace(base_namespace: str) -> str:
    if base_namespace.endswith(("#", "/")):
        return base_namespace
    return f"{base_namespace}#"


_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]")


def _build_instance_uri(
    namespace: Namespace, target_class: URIRef, prefix: str, counts: dict[URIRef, int]
) -> URIRef:
    counts[target_class] = counts.get(target_class, 0) + 1
    local = _NON_ALNUM_RE.sub("", _local_name(target_class)) or "Instance"
    suffix = counts[target_class]
    return namespace[f"{prefix}{local}{'' if suffix == 1 else '_' + str(suffix)}"]


def _target_for_class_constraint(
    graph: Graph,
    namespace: Namespace,
    class_constraint: Optional[URIRef],
    prefix: str,
    counts: dict[URIRef, int],
):
    if isinstance(class_constraint, URIRef):
        target = _build_instance_uri(namespace, class_constraint, prefix, counts)
        graph.add((target, RDF.type, class_constraint))
        return target
    return BNode()


def _local_name(term: URIRef) -> str:
    text = str(term)
    if "#" in text:
        return text.rsplit("#", 1)[1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def _placeholder_literal(datatype: URIRef, occurrence: int) -> Literal:
    if datatype == XSD.string:
        return Literal(f"placeholder_{occurrence + 1}", datatype=datatype)
    if datatype == XSD.decimal:
        return Literal("0", datatype=datatype)
    if datatype == XSD.integer:
        return Literal(0, datatype=datatype)
    if datatype == XSD.boolean:
        return Literal(False, datatype=datatype)
    if datatype == XSD.dateTime:
        return Literal(datetime.now(timezone.utc).isoformat(), datatype=datatype)
    return Literal(f"value_{occurrence + 1}", datatype=datatype)

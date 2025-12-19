"""SHACL validation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional

from rdflib import Graph, Literal
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
    shape_path: Optional[str]
    message: Optional[str]
    severity: Optional[str]
    source_shape: Optional[str]
    property_shape: Optional[str]
    target_class: Optional[str]
    constraint_component: Optional[str]
    value: Optional[str]
    class_constraint: Optional[str]
    datatype_constraint: Optional[str]
    min_count: Optional[int]


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

            source_shape_node = report_graph.value(result_node, SH.sourceShape)
            result_path_node = report_graph.value(result_node, SH.resultPath)

            property_shape_node = None
            shape_path_node = None
            class_constraint_node = None
            datatype_constraint_node = None
            min_count_value: Optional[int] = None
            target_class_node = None

            if source_shape_node is not None:
                property_shapes = list(self.shapes_graph.objects(source_shape_node, SH.property))
                if property_shapes:
                    for prop_shape in property_shapes:
                        prop_path = self.shapes_graph.value(prop_shape, SH.path)
                        if result_path_node is None or prop_path == result_path_node:
                            property_shape_node = prop_shape
                            shape_path_node = prop_path
                            break
                    if property_shape_node is None:
                        property_shape_node = property_shapes[0]
                        shape_path_node = self.shapes_graph.value(property_shape_node, SH.path)
                if property_shape_node is None:
                    property_shape_node = source_shape_node
                    shape_path_node = self.shapes_graph.value(property_shape_node, SH.path)

                class_constraint_node = self.shapes_graph.value(property_shape_node, SH["class"])
                datatype_constraint_node = self.shapes_graph.value(property_shape_node, SH.datatype)
                min_count_literal = self.shapes_graph.value(property_shape_node, SH.minCount)
                if isinstance(min_count_literal, Literal):
                    try:
                        min_count_value = int(min_count_literal)
                    except (ValueError, TypeError):
                        min_count_value = None

                target_class_node = self.shapes_graph.value(source_shape_node, SH.targetClass)
                if target_class_node is None and property_shape_node is not None:
                    for node_shape in self.shapes_graph.subjects(SH.property, property_shape_node):
                        target_class_node = self.shapes_graph.value(node_shape, SH.targetClass)
                        if target_class_node is not None:
                            break

            results.append(
                ShaclResult(
                    focus_node=_maybe("focusNode"),
                    path=_maybe("resultPath"),
                    shape_path=str(shape_path_node) if shape_path_node else None,
                    message=_maybe("resultMessage"),
                    severity=_maybe("resultSeverity"),
                    source_shape=_maybe("sourceShape"),
                    property_shape=str(property_shape_node) if property_shape_node else None,
                    target_class=str(target_class_node) if target_class_node else None,
                    constraint_component=_maybe("sourceConstraintComponent"),
                    value=_maybe("value"),
                    class_constraint=str(class_constraint_node) if class_constraint_node else None,
                    datatype_constraint=str(datatype_constraint_node) if datatype_constraint_node else None,
                    min_count=min_count_value,
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

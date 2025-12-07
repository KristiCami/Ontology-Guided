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
            serialize_report_graph=True,
        )
        report_graph_ttl: Optional[str] = None
        parsed_results: List[ShaclResult] = []
        if isinstance(report_graph, bytes):
            report_graph_ttl = report_graph.decode("utf-8")
        elif isinstance(report_graph, str):
            report_graph_ttl = report_graph
        elif report_graph:
            report_graph_ttl = report_graph.serialize(format="turtle")

        if report_graph_ttl and not parsed_results:
            try:
                parsed_graph = Graph().parse(data=report_graph_ttl, format="turtle")
                parsed_results = self._extract_results(parsed_graph)
            except Exception:  # pragma: no cover - rdflib parse error
                parsed_results = []
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
    classified: list[dict] = []
    for result in report.results:
        category = classify_shacl_result(result)
        classified.append({"category": category, "result": result.__dict__})
        if category == "hard":
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
        "classified_results": classified,
    }


def classify_shacl_result(result: ShaclResult) -> str:
    """Label a SHACL result as ``hard`` or ``soft`` based on severity and component."""

    severity_value = (result.severity or "").lower()
    if "warning" in severity_value or "info" in severity_value:
        return "soft"

    component_fragment = (result.constraint_component or "").split("#")[-1].lower()
    hard_components = {
        "mincountconstraintcomponent",
        "datatypeconstraintcomponent",
        "classconstraintcomponent",
        "nodekindconstraintcomponent",
    }
    if component_fragment in hard_components:
        return "hard"
    return "soft"

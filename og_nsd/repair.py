"""Utilities for the E4 iterative repair loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from rdflib import BNode, Graph, URIRef
from rdflib.namespace import SH

from .metrics import compute_exact_metrics_from_graphs, compute_semantic_metrics
from .shacl import ShaclReport, summarize_shacl_report


@dataclass
class Patch:
    action: str
    subject: str
    predicate: str
    object: str
    message: str | None = None
    source_shape: str | None = None
    severity: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _node_from_identifier(identifier: str) -> URIRef | BNode:
    if identifier.startswith("http"):
        return URIRef(identifier)
    return BNode(identifier)


def _shape_expected_value(report_graph: Graph, shape_node: URIRef | BNode) -> str | None:
    expected = report_graph.value(shape_node, SH["class"])
    if expected is None:
        expected = report_graph.value(shape_node, SH["datatype"])
    if expected is None:
        expected = report_graph.value(shape_node, SH["nodeKind"])
    return str(expected) if expected else None


def _shape_path(report_graph: Graph, shape_node: URIRef | BNode) -> tuple[str | None, bool]:
    path_node = report_graph.value(shape_node, SH["path"])
    if path_node is None:
        return None, False
    inverse_path = report_graph.value(path_node, SH["inversePath"])
    if inverse_path is not None:
        return str(inverse_path), True
    return str(path_node), False


def shacl_report_to_patches(report: ShaclReport) -> List[Patch]:
    """Translate hard SHACL violations into a JSON-friendly patch plan."""

    report_graph = None
    if report.report_graph_ttl:
        report_graph = Graph()
        report_graph.parse(data=report.report_graph_ttl, format="turtle")

    patches: List[Patch] = []
    for result in report.results:
        severity = (result.severity or "").lower()
        if "violation" not in severity:
            continue
        constraint_component = result.constraint_component or ""
        if "MaxCountConstraintComponent" in constraint_component:
            continue

        predicate = result.path
        path_is_inverse = result.path_is_inverse
        expected_value = None
        if report_graph is not None and result.source_shape:
            shape_node = _node_from_identifier(result.source_shape)
            expected_value = _shape_expected_value(report_graph, shape_node)
            if predicate is None:
                predicate, path_is_inverse = _shape_path(report_graph, shape_node)

        predicate = predicate or "rdfs:comment"
        expected_value = expected_value or result.value or "xsd:string"

        subject = result.focus_node or "atm:UnknownFocus"
        obj = expected_value
        if path_is_inverse:
            subject = expected_value or "atm:UnknownSubject"
            obj = result.focus_node or "atm:UnknownFocus"

        patches.append(
            Patch(
                action="addProperty",
                subject=subject,
                predicate=predicate,
                object=obj,
                message=result.message,
                source_shape=result.source_shape,
                severity=result.severity,
            )
        )
    return patches


def save_patch_plan(patches: Sequence[Patch], path: Path) -> None:
    path.write_text(json.dumps([patch.to_dict() for patch in patches], indent=2), encoding="utf-8")


def save_shacl_report(report: ShaclReport, path: Path) -> None:
    if report.report_graph_ttl:
        path.write_text(report.report_graph_ttl, encoding="utf-8")
    else:
        path.write_text(report.text_report, encoding="utf-8")


def compute_cq_pass_rate(results: Iterable) -> float:
    items = list(results)
    total = len(items)
    if total == 0:
        return 0.0
    passed = sum(1 for item in items if getattr(item, "success", False))
    return passed / total


def final_metrics(pred_graph: Graph, gold_graph: Graph) -> dict:
    exact = compute_exact_metrics_from_graphs(pred_graph, gold_graph)
    semantic = compute_semantic_metrics(pred_graph, gold_graph)
    return {"exact": exact, "semantic": semantic}


def should_stop(
    *,
    iteration: int,
    max_iterations: int,
    patches: Sequence[Patch],
    previous_patches: Sequence[Patch] | None,
    shacl_report: ShaclReport,
    cq_pass_rate: float,
    cq_threshold: float,
) -> bool:
    summary = summarize_shacl_report(shacl_report)
    hard = summary["violations"]["hard"]
    if hard == 0:
        return True
    if not patches:
        return True
    if previous_patches is not None and [p.to_dict() for p in previous_patches] == [p.to_dict() for p in patches]:
        return True
    if cq_pass_rate >= cq_threshold:
        return True
    if iteration >= max_iterations:
        return True
    return False

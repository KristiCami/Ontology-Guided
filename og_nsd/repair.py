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


def shacl_report_to_patches(report: ShaclReport, shapes_graph: Graph | None = None) -> List[Patch]:
    """Translate hard SHACL violations into a JSON-friendly patch plan."""

    patches: List[Patch] = []
    seen: set[tuple[str, str, str]] = set()

    for result in report.results:
        severity = (result.severity or "").lower()
        if "violation" not in severity:
            continue

        subject = _compact_node(result.focus_node, shapes_graph) or "atm:UnknownFocus"
        predicate = _compact_node(result.path, shapes_graph)
        obj = _compact_node(result.value, shapes_graph)

        if shapes_graph is not None and result.source_shape:
            shape_node = _as_graph_node(result.source_shape, shapes_graph)
            if shape_node is not None:
                predicate, obj, subject = _derive_patch_terms(
                    shapes_graph=shapes_graph,
                    shape_node=shape_node,
                    fallback_subject=subject,
                    fallback_predicate=predicate,
                    fallback_object=obj,
                )

        predicate = predicate or "rdfs:comment"
        obj = obj or "xsd:string"

        key = (subject, predicate, obj)
        if key in seen:
            continue
        seen.add(key)

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


def _as_graph_node(value: str, shapes_graph: Graph) -> BNode | URIRef | None:
    if not value:
        return None
    if value.startswith("http"):
        return URIRef(value)
    try:
        expanded = shapes_graph.namespace_manager.expand_curie(value)
        return URIRef(expanded)
    except Exception:
        return BNode(value)


def _compact_node(value: str | None, shapes_graph: Graph | None) -> str | None:
    if not value:
        return None
    if shapes_graph is None:
        return value
    try:
        return shapes_graph.namespace_manager.normalizeUri(URIRef(value))
    except Exception:
        return value


def _derive_patch_terms(
    *,
    shapes_graph: Graph,
    shape_node: BNode | URIRef,
    fallback_subject: str,
    fallback_predicate: str | None,
    fallback_object: str | None,
) -> tuple[str | None, str | None, str]:
    predicate: str | None = fallback_predicate
    obj: str | None = fallback_object
    subject = fallback_subject

    path_node = shapes_graph.value(shape_node, SH.path)
    if path_node:
        inverse_node = shapes_graph.value(path_node, SH.inversePath)
        if inverse_node:
            predicate = _compact_node(str(inverse_node), shapes_graph)
            expected_class = shapes_graph.value(shape_node, SH["class"])
            if expected_class:
                subject = _compact_node(str(expected_class), shapes_graph) or subject
            if fallback_subject:
                obj = fallback_subject
        else:
            predicate = _compact_node(str(path_node), shapes_graph)

    expected_datatype = shapes_graph.value(shape_node, SH.datatype)
    expected_class = shapes_graph.value(shape_node, SH["class"])
    if expected_datatype:
        obj = _compact_node(str(expected_datatype), shapes_graph)
    elif expected_class:
        obj = _compact_node(str(expected_class), shapes_graph)

    return predicate, obj, subject


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

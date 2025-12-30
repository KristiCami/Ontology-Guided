"""Utilities for the E4 iterative repair loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from rdflib import Graph

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


@dataclass
class StopDecision:
    stop: bool
    reason: str


def shacl_report_to_patches(report: ShaclReport) -> List[Patch]:
    """Translate hard SHACL violations into a JSON-friendly patch plan."""

    patches: List[Patch] = []
    seen: set[tuple[str, str, str]] = set()
    for result in report.results:
        severity = (result.severity or "").lower()
        if "violation" not in severity:
            continue
        key = (
            result.focus_node or "atm:UnknownFocus",
            result.path or "rdfs:comment",
            result.value or "xsd:string",
        )
        if key in seen:
            continue
        seen.add(key)
        patches.append(
            Patch(
                action="addProperty",
                subject=key[0],
                predicate=key[1],
                object=key[2],
                message=result.message,
                source_shape=result.source_shape,
                severity=result.severity,
            )
        )
    return sorted(patches, key=lambda p: (p.subject, p.predicate, p.object))


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
    shacl_report: Optional[ShaclReport],
    cq_pass_rate: float,
    cq_threshold: float,
) -> StopDecision:
    summary = summarize_shacl_report(shacl_report) if shacl_report else {"violations": {"hard": 0}}
    hard = summary["violations"]["hard"]
    if hard == 0:
        return StopDecision(True, "no_hard_violations")
    if not patches:
        return StopDecision(True, "no_patches_available")
    if previous_patches is not None and [p.to_dict() for p in previous_patches] == [p.to_dict() for p in patches]:
        return StopDecision(True, "patches_unchanged")
    if cq_pass_rate >= cq_threshold:
        return StopDecision(True, "cq_threshold_met")
    if iteration >= max_iterations:
        return StopDecision(True, "max_iterations_reached")
    return StopDecision(False, "continue")

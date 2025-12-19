"""Utilities for the E4 iterative repair loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

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


def shacl_report_to_patches(report: ShaclReport) -> List[Patch]:
    """Translate hard SHACL violations into a JSON-friendly patch plan."""

    patches: List[Patch] = []
    for result in report.results:
        severity = (result.severity or "").lower()
        if "violation" not in severity:
            continue
        patches.append(
            Patch(
                action="addProperty",
                subject=result.focus_node or "atm:UnknownFocus",
                predicate=result.path or "rdfs:comment",
                object=result.value or "xsd:string",
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
    shacl_report: ShaclReport,
    cq_pass_rate: float,
    cq_threshold: float,
    hard_history: Sequence[int],
    delta: int = 1,
    stagnation_limit: int = 0,
) -> tuple[bool, str | None]:
    summary = summarize_shacl_report(shacl_report)
    hard = summary["violations"]["hard"]
    if hard == 0:
        return True, "hard_zero"
    if not patches:
        return True, "no_patches"
    if stagnation_limit > 0 and len(hard_history) >= stagnation_limit + 1:
        stagnated = True
        for idx in range(-stagnation_limit, 0):
            hard_prev = hard_history[idx - 1]
            hard_current = hard_history[idx]
            if hard_prev - hard_current >= delta:
                stagnated = False
                break
        if stagnated:
            return True, "stagnation"
    if cq_pass_rate >= cq_threshold:
        return True, "cq_threshold"
    if iteration >= max_iterations:
        return True, "kmax"
    return False, None

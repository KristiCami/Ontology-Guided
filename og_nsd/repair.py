"""Utilities for the E4 iterative repair loop."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, TYPE_CHECKING

from rdflib import Graph

from .metrics import compute_exact_metrics_from_graphs, compute_semantic_metrics
from .shacl import ShaclReport, summarize_shacl_report

if TYPE_CHECKING:  # pragma: no cover - import guard for type checkers
    from .queries import CompetencyQuestionResult


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


def shacl_report_to_patches(report: ShaclReport, include_soft_if_no_hard: bool = False) -> List[Patch]:
    """Translate SHACL violations into a JSON-friendly patch plan.

    By default, only ``Violation`` severities are converted to patches. When
    ``include_soft_if_no_hard`` is true and no hard violations are present,
    soft/warning results are also converted so the repair loop can progress.
    """

    patches: List[Patch] = []
    seen: set[tuple[str, str, str]] = set()
    severities = [(result.severity or "").lower() for result in report.results]
    has_hard_violations = any("violation" in level for level in severities)

    for result in report.results:
        severity = (result.severity or "").lower()
        if "violation" not in severity and not (include_soft_if_no_hard and not has_hard_violations):
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
    normalized = []
    for patch in patches:
        normalized.append(patch.to_dict() if hasattr(patch, "to_dict") else patch)
    path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")


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


_DOMAIN_RANGE_PATTERN = re.compile(
    r"(atm:[A-Za-z0-9_]+)\s+rdfs:domain\s+(atm:[A-Za-z0-9_]+)\s*;\s*rdfs:range\s+([A-Za-z0-9_:]+)",
    re.IGNORECASE,
)
_SUBCLASS_PATTERN = re.compile(
    r"(atm:[A-Za-z0-9_]+)\s+rdfs:subClassOf[+*]?\s+(atm:[A-Za-z0-9_]+)",
    re.IGNORECASE,
)
_ATM_TOKEN_PATTERN = re.compile(r"atm:[A-Za-z0-9_]+")


def cq_results_to_patches(cq_results: Sequence["CompetencyQuestionResult"]) -> List[Patch]:
    """Convert failed CQ checks into patch candidates.

    The heuristic looks for common domain/range or subclass patterns within the
    ASK queries. When none are found, it falls back to using the first two ATM
    tokens as a subclass assertion. This keeps the repair loop moving even when
    SHACL cannot propose edits (e.g., due to missing focus nodes).
    """

    patches: List[Patch] = []
    seen: set[tuple[str, str, str]] = set()

    for result in cq_results:
        if result.success:
            continue

        query = result.query or ""
        domain_range_matches = list(_DOMAIN_RANGE_PATTERN.finditer(query))
        subclass_matches = list(_SUBCLASS_PATTERN.finditer(query))
        patch_added = False

        for match in domain_range_matches:
            predicate, subject, obj = match.group(1), match.group(2), match.group(3)
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
                    message="Generated from failed competency question",
                    severity="CQ",
                )
            )
            patch_added = True

        if not patch_added:
            for match in subclass_matches:
                subject, obj = match.group(1), match.group(2)
                key = (subject, "rdfs:subClassOf", obj)
                if key in seen:
                    continue
                seen.add(key)
                patches.append(
                    Patch(
                        action="addSubclass",
                        subject=subject,
                        predicate="rdfs:subClassOf",
                        object=obj,
                        message="Generated from failed competency question (subclass expectation)",
                        severity="CQ",
                    )
                )
                patch_added = True
                break

        if not patch_added:
            tokens = _ATM_TOKEN_PATTERN.findall(query)
            if len(tokens) >= 2:
                key = (tokens[0], "rdfs:subClassOf", tokens[1])
                if key not in seen:
                    seen.add(key)
                    patches.append(
                        Patch(
                            action="addSubclass",
                            subject=tokens[0],
                            predicate="rdfs:subClassOf",
                            object=tokens[1],
                            message="Fallback CQ-derived subclass patch",
                            severity="CQ",
                        )
                    )

    return sorted(patches, key=lambda p: (p.subject, p.predicate, p.object))


def should_stop(
    *,
    iteration: int,
    max_iterations: int,
    patches: Sequence[Patch],
    previous_patches: Sequence[Patch] | None,
    shacl_report: Optional[ShaclReport],
    cq_pass_rate: float,
    cq_threshold: float,
    stop_policy: str = "default",
) -> StopDecision:
    """Decide whether the iterative repair loop should stop.

    stop_policy controls how aggressively the loop stops:
    - default: original behaviour, stop immediately when hard violations are zero.
    - hard_and_cq: require both zero hard violations AND CQ pass rate >= threshold to stop.
    - ignore_no_hard: do not stop on zero hard violations; rely on patches/CQ/max-iterations.
    - max_only: ignore SHACL/CQ signals and stop only when iteration >= max_iterations.
    """

    summary = summarize_shacl_report(shacl_report) if shacl_report else {"violations": {"hard": 0}}
    hard = summary["violations"]["hard"]

    if stop_policy == "max_only":
        if iteration >= max_iterations:
            return StopDecision(True, "max_iterations_reached")
        return StopDecision(False, "continue")

    if stop_policy == "hard_and_cq":
        if hard == 0 and cq_pass_rate >= cq_threshold:
            return StopDecision(True, "no_hard_violations_and_cq_threshold_met")
    elif stop_policy == "default":
        if hard == 0:
            return StopDecision(True, "no_hard_violations")
    elif stop_policy == "ignore_no_hard":
        pass
    else:
        raise ValueError(f"Unsupported stop_policy '{stop_policy}'.")

    if not patches:
        return StopDecision(True, "no_patches_available")
    if previous_patches is not None and [p.to_dict() for p in previous_patches] == [p.to_dict() for p in patches]:
        return StopDecision(True, "patches_unchanged")
    if cq_pass_rate >= cq_threshold:
        return StopDecision(True, "cq_threshold_met")
    if iteration >= max_iterations:
        return StopDecision(True, "max_iterations_reached")
    return StopDecision(False, "continue")

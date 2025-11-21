#!/usr/bin/env python3
"""Utility to compute experiment metrics for README tables.

Given a generated ontology, a gold ontology, and (optionally) a JSON
report from the pipeline, this script emits precision/recall/F1 scores
as well as SHACL compliance summaries formatted as Markdown table rows.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from rdflib import BNode, Graph
from rdflib.namespace import OWL, RDF, RDFS


AxiomSet = Set[str] | Set[Tuple[str, str]]


@dataclass
class AxiomMetrics:
    name: str
    gold: int
    predicted: int
    overlap: int
    precision: float
    recall: float
    f1: float


@dataclass
class OverallMetrics:
    categories: List[AxiomMetrics]
    overall_precision: float
    overall_recall: float
    overall_f1: float


@dataclass
class ShaclSummary:
    violations_pre: int
    violations_post: int
    iterations: int
    conforms: bool
    first_conforming_iteration: Optional[int]
    unsat_pre: Optional[int]
    unsat_post: Optional[int]


def _safe_ratio(num: float, den: float) -> float:
    return num / den if den else 0.0


def _as_str(value) -> str:
    return str(value)


def _filter_nodes(nodes: Iterable) -> Set[str]:
    return {_as_str(node) for node in nodes if not isinstance(node, BNode)}


def extract_axiom_sets(graph: Graph) -> Dict[str, AxiomSet]:
    """Extract a handful of axiom categories from a graph for scoring."""

    classes = _filter_nodes(graph.subjects(RDF.type, OWL.Class)) | _filter_nodes(
        graph.subjects(RDF.type, RDFS.Class)
    )
    object_props = _filter_nodes(graph.subjects(RDF.type, OWL.ObjectProperty))
    datatype_props = _filter_nodes(graph.subjects(RDF.type, OWL.DatatypeProperty))
    subclass = {
        (_as_str(sub), _as_str(super_))
        for sub, super_ in graph.subject_objects(RDFS.subClassOf)
        if not isinstance(sub, BNode) and not isinstance(super_, BNode)
    }
    domains = {
        (_as_str(prop), _as_str(domain))
        for prop, domain in graph.subject_objects(RDFS.domain)
        if not isinstance(prop, BNode) and not isinstance(domain, BNode)
    }
    ranges = {
        (_as_str(prop), _as_str(range_))
        for prop, range_ in graph.subject_objects(RDFS.range)
        if not isinstance(prop, BNode) and not isinstance(range_, BNode)
    }

    return {
        "Classes": classes,
        "SubClassOf": subclass,
        "Domain": domains,
        "Range": ranges,
        "ObjectProperty": object_props,
        "DatatypeProperty": datatype_props,
    }


def compute_metrics(gold: Graph, predicted: Graph) -> OverallMetrics:
    gold_axioms = extract_axiom_sets(gold)
    predicted_axioms = extract_axiom_sets(predicted)

    categories: List[AxiomMetrics] = []
    total_gold = 0
    total_pred = 0
    total_overlap = 0

    for name, gold_set in gold_axioms.items():
        pred_set = predicted_axioms.get(name, set())
        overlap = len(gold_set & pred_set)
        precision = _safe_ratio(overlap, len(pred_set))
        recall = _safe_ratio(overlap, len(gold_set))
        f1 = _safe_ratio(2 * precision * recall, precision + recall) if precision or recall else 0.0

        categories.append(
            AxiomMetrics(
                name=name,
                gold=len(gold_set),
                predicted=len(pred_set),
                overlap=overlap,
                precision=precision,
                recall=recall,
                f1=f1,
            )
        )

        total_gold += len(gold_set)
        total_pred += len(pred_set)
        total_overlap += overlap

    overall_precision = _safe_ratio(total_overlap, total_pred)
    overall_recall = _safe_ratio(total_overlap, total_gold)
    overall_f1 = _safe_ratio(2 * overall_precision * overall_recall, overall_precision + overall_recall) if (
        overall_precision or overall_recall
    ) else 0.0

    return OverallMetrics(categories, overall_precision, overall_recall, overall_f1)


def load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path)
    return graph


def summarise_shacl(report_path: Path) -> Optional[ShaclSummary]:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    iterations = data.get("iterations") or []
    if not iterations:
        return None

    def violation_count(iteration: dict) -> int:
        shacl_results = iteration.get("shacl", {}).get("results") or []
        return len(shacl_results)

    def unsat_count(iteration: dict) -> Optional[int]:
        reasoner = iteration.get("reasoner") or {}
        unsat = reasoner.get("unsatisfiable_classes")
        if unsat is None:
            return None
        return len(unsat)

    violations_pre = violation_count(iterations[0])
    violations_post = violation_count(iterations[-1])
    unsat_pre = unsat_count(iterations[0])
    unsat_post = unsat_count(iterations[-1])
    conforms = bool(iterations[-1].get("shacl", {}).get("conforms"))
    first_conforming_iteration = None
    for iter_report in iterations:
        if iter_report.get("shacl", {}).get("conforms"):
            first_conforming_iteration = iter_report.get("iteration")
            break

    return ShaclSummary(
        violations_pre=violations_pre,
        violations_post=violations_post,
        iterations=len(iterations),
        conforms=conforms,
        first_conforming_iteration=first_conforming_iteration,
        unsat_pre=unsat_pre,
        unsat_post=unsat_post,
    )


def format_row(label: str, metrics: OverallMetrics) -> str:
    return "| {label} | {p:.2f} | {r:.2f} | {f1:.2f} |".format(
        label=label,
        p=metrics.overall_precision,
        r=metrics.overall_recall,
        f1=metrics.overall_f1,
    )


def format_shacl_row(label: str, summary: ShaclSummary) -> str:
    conforms_label = "Yes" if summary.conforms else "No"
    return "| {label} | {pre} | {post} | {iters} | {conf} |".format(
        label=label,
        pre=summary.violations_pre,
        post=summary.violations_post,
        iters=summary.iterations,
        conf=conforms_label,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute OG-NSD evaluation metrics")
    parser.add_argument("--generated", type=Path, required=True, help="Generated ontology (TTL)")
    parser.add_argument("--gold", type=Path, required=True, help="Gold ontology (TTL)")
    parser.add_argument("--report", type=Path, help="JSON report from run_pipeline")
    parser.add_argument("--label", default="Run", help="Label to use in README tables")
    args = parser.parse_args()

    gold_graph = load_graph(args.gold)
    predicted_graph = load_graph(args.generated)
    metrics = compute_metrics(gold_graph, predicted_graph)

    print("Overall extraction quality (paste into the README table):")
    print(format_row(args.label, metrics))
    print()
    print("Per-category metrics:")
    print("| Axiom type | Gold | Predicted | Overlap | Precision | Recall | F1 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for cat in metrics.categories:
        print(
            "| {name} | {gold} | {pred} | {overlap} | {p:.2f} | {r:.2f} | {f1:.2f} |".format(
                name=cat.name,
                gold=cat.gold,
                pred=cat.predicted,
                overlap=cat.overlap,
                p=cat.precision,
                r=cat.recall,
                f1=cat.f1,
            )
        )

    if args.report and args.report.exists():
        shacl_summary = summarise_shacl(args.report)
        if shacl_summary:
            print()
            print("SHACL / repair loop summary (paste into Table II):")
            print(format_shacl_row(args.label, shacl_summary))
            if shacl_summary.first_conforming_iteration is not None:
                print(f"First conforming iteration: {shacl_summary.first_conforming_iteration}")
            if shacl_summary.unsat_pre is not None or shacl_summary.unsat_post is not None:
                print(
                    f"Unsatisfiable classes (pre→post): {shacl_summary.unsat_pre} → {shacl_summary.unsat_post}"
                )


if __name__ == "__main__":
    main()

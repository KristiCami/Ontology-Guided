"""Evaluation helpers for generating experiment tables."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Set, Tuple

from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS


@dataclass
class MetricTriple:
    precision: float
    recall: float
    f1: float


@dataclass
class ExtractionMetrics:
    per_type: Dict[str, MetricTriple]
    macro: MetricTriple
    micro: MetricTriple


@dataclass
class ShaclSummary:
    violations_start: int
    violations_end: int
    iterations: int
    conforms: bool


def _load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path)
    return graph


def _axiom_sets(graph: Graph) -> Dict[str, Set[Tuple[str, ...]]]:
    classes = {str(s) for s in graph.subjects(RDF.type, OWL.Class)}
    subclasses = {(str(s), str(o)) for s, o in graph.subject_objects(RDFS.subClassOf)}
    obj_props = {str(s) for s in graph.subjects(RDF.type, OWL.ObjectProperty)}
    dt_props = {str(s) for s in graph.subjects(RDF.type, OWL.DatatypeProperty)}
    domains = {(str(s), str(o)) for s, o in graph.subject_objects(RDFS.domain)}
    ranges = {(str(s), str(o)) for s, o in graph.subject_objects(RDFS.range)}
    return {
        "classes": {(iri,) for iri in classes},
        "subclass": subclasses,
        "object_property": {(iri,) for iri in obj_props},
        "datatype_property": {(iri,) for iri in dt_props},
        "domain": domains,
        "range": ranges,
    }


def _prf1(gold: Iterable[Tuple[str, ...]], pred: Iterable[Tuple[str, ...]]) -> MetricTriple:
    gold_set = set(gold)
    pred_set = set(pred)
    overlap = gold_set & pred_set
    precision = len(overlap) / len(pred_set) if pred_set else 0.0
    recall = len(overlap) / len(gold_set) if gold_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return MetricTriple(precision, recall, f1)


def compute_extraction_metrics(gold_path: Path, generated_path: Path) -> ExtractionMetrics:
    gold_graph = _load_graph(gold_path)
    pred_graph = _load_graph(generated_path)

    gold_sets = _axiom_sets(gold_graph)
    pred_sets = _axiom_sets(pred_graph)

    per_type: Dict[str, MetricTriple] = {}
    for key in gold_sets:
        per_type[key] = _prf1(gold_sets[key], pred_sets.get(key, set()))

    macro_precision = sum(m.precision for m in per_type.values()) / len(per_type)
    macro_recall = sum(m.recall for m in per_type.values()) / len(per_type)
    macro_f1 = sum(m.f1 for m in per_type.values()) / len(per_type)
    macro = MetricTriple(macro_precision, macro_recall, macro_f1)

    gold_union = set().union(*gold_sets.values())
    pred_union = set().union(*pred_sets.values())
    micro = _prf1(gold_union, pred_union)

    return ExtractionMetrics(per_type=per_type, macro=macro, micro=micro)


def summarize_shacl_iterations(report_path: Path) -> ShaclSummary:
    import json

    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    iterations = data.get("iterations", [])
    if not iterations:
        raise ValueError("Report does not contain iteration data; rerun pipeline with --report set")

    def _count(results: object) -> int:
        if not results:
            return 0
        if isinstance(results, list):
            return len(results)
        return 0

    first = iterations[0]
    final = iterations[-1]
    start_count = _count(first.get("shacl", {}).get("results"))
    end_count = _count(final.get("shacl", {}).get("results"))
    iterations_run = int(final.get("iteration", len(iterations) - 1)) + 1
    conforms = bool(final.get("shacl", {}).get("conforms", False))
    return ShaclSummary(start_count, end_count, iterations_run, conforms)


def format_markdown_row(label: str, metrics: MetricTriple) -> str:
    return f"| {label} | {metrics.precision:.2f} | {metrics.recall:.2f} | {metrics.f1:.2f} |"


def format_shacl_row(label: str, summary: ShaclSummary) -> str:
    status = "✅" if summary.conforms else "⚠️"
    return (
        f"| {label} | {summary.violations_start} | {summary.violations_end} | "
        f"{summary.iterations} | {status} |"
    )

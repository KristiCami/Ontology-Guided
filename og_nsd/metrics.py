"""Lightweight evaluation helpers for ATM experiments."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, Tuple

from rdflib import Graph, term

try:  # Optional but recommended: materialise entailments for semantic metrics
    from rdflib.extras.infixowl import DeductiveClosure, OWLRL_Semantics
except Exception:  # pragma: no cover - fallback if owlrl is missing at runtime
    DeductiveClosure = None
    OWLRL_Semantics = None

Triple = Tuple[term.Node, term.Node, term.Node]


def _load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format=_guess_format(path))
    return graph


def _guess_format(path: Path) -> str | None:
    """Best-effort format guess based on file suffix."""
    suffix = path.suffix.lower()
    if suffix in {".ttl", ".n3"}:
        return "turtle"
    if suffix in {".owl", ".rdf", ".xml"}:
        return "xml"
    if suffix == ".nt":
        return "nt"
    if suffix in {".nq", ".nquads"}:
        return "nquads"
    return None


def _triple_set(graph: Graph) -> Set[Triple]:
    return set(graph.triples((None, None, None)))


def _normalized_triple_set(graph: Graph) -> Set[Tuple[str, str, str]]:
    def _norm(value: term.Node) -> str:
        return (
            str(value)
            .lower()
            .replace("_", "")
            .replace("-", "")
            .replace(" ", "")
        )

    return {(_norm(s), _norm(p), _norm(o)) for s, p, o in _triple_set(graph)}


def _materialize_closure(graph: Graph) -> Graph:
    """Return a graph materialised under OWL 2 RL semantics if possible.

    Falls back to the input graph when the optional owlrl dependency is unavailable.
    """
    if DeductiveClosure is None or OWLRL_Semantics is None:
        return graph
    working_copy = Graph()
    for prefix, ns in graph.namespace_manager.namespaces():
        working_copy.bind(prefix, ns)
    working_copy += graph
    DeductiveClosure(OWLRL_Semantics).expand(working_copy)
    return working_copy


def compute_exact_metrics(pred_path: Path, gold_path: Path) -> Dict[str, float]:
    pred_graph = _load_graph(pred_path)
    gold_graph = _load_graph(gold_path)
    return compute_exact_metrics_from_graphs(pred_graph, gold_graph)


def compute_exact_metrics_from_graphs(pred_graph: Graph, gold_graph: Graph) -> Dict[str, float]:
    pred_triples = _triple_set(pred_graph)
    gold_triples = _triple_set(gold_graph)
    overlap = pred_triples.intersection(gold_triples)
    precision = len(overlap) / len(pred_triples) if pred_triples else 0.0
    recall = len(overlap) / len(gold_triples) if gold_triples else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "pred_triples": len(pred_triples),
        "gold_triples": len(gold_triples),
        "overlap_triples": len(overlap),
    }


def compute_semantic_metrics(pred_graph: Graph, gold_graph: Graph) -> Dict[str, float]:
    exact = compute_exact_metrics_from_graphs(pred_graph, gold_graph)

    pred_materialized = _materialize_closure(pred_graph)
    gold_materialized = _materialize_closure(gold_graph)

    pred_triples = _normalized_triple_set(pred_materialized)
    gold_triples = _normalized_triple_set(gold_materialized)
    overlap = pred_triples.intersection(gold_triples)

    precision = len(overlap) / len(pred_triples) if pred_triples else 0.0
    recall = len(overlap) / len(gold_triples) if gold_triples else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    precision = max(precision, exact["precision"])
    recall = max(recall, exact["recall"])
    f1 = max(f1, exact["f1"])

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "pred_triples": len(pred_triples),
        "gold_triples": len(gold_triples),
        "overlap_triples": len(overlap),
    }

"""Utility to compute axiom-level precision, recall and F1 between RDF graphs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, Tuple

from rdflib import Graph, OWL
from rdflib.namespace import RDF, RDFS

# Type alias for sets of axioms represented as hashable tuples or nodes
AxiomSet = Set

# Mapping axiom type names to callables extracting corresponding sets from a graph
AXIOM_EXTRACTORS = {
    "Classes": lambda g: set(g.subjects(RDF.type, OWL.Class)),
    "ObjectProperty": lambda g: set(g.subjects(RDF.type, OWL.ObjectProperty)),
    "DatatypeProperty": lambda g: set(g.subjects(RDF.type, OWL.DatatypeProperty)),
    "SubClassOf": lambda g: set(g.subject_objects(RDFS.subClassOf)),
    "Domain": lambda g: set(g.subject_objects(RDFS.domain)),
    "Range": lambda g: set(g.subject_objects(RDFS.range)),
}


def _metrics(pred: AxiomSet, gold: AxiomSet) -> Dict[str, float]:
    tp = len(pred & gold)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "predicted": len(pred),
        "gold": len(gold),
    }


def evaluate_axioms(
    pred_graph: Graph, gold_graph: Graph, micro: bool = False
) -> Dict[str, Dict[str, float]]:
    """Compute axiom-level metrics grouped by axiom type."""
    per_type: Dict[str, Dict[str, float]] = {}
    macro_f1_total = 0.0
    total_tp = total_pred = total_gold = 0

    for axiom_type, extractor in AXIOM_EXTRACTORS.items():
        pred_set = extractor(pred_graph)
        gold_set = extractor(gold_graph)
        m = _metrics(pred_set, gold_set)
        per_type[axiom_type] = {
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
        }
        macro_f1_total += m["f1"]
        if micro:
            total_tp += m["tp"]
            total_pred += m["predicted"]
            total_gold += m["gold"]

    results: Dict[str, Dict[str, float]] = {
        "per_type": per_type,
        "macro_f1": macro_f1_total / len(AXIOM_EXTRACTORS) if AXIOM_EXTRACTORS else 0.0,
    }

    if micro:
        micro_precision = total_tp / total_pred if total_pred else 0.0
        micro_recall = total_tp / total_gold if total_gold else 0.0
        micro_f1 = (
            2 * micro_precision * micro_recall / (micro_precision + micro_recall)
            if (micro_precision + micro_recall) > 0
            else 0.0
        )
        results.update(
            {
                "micro_precision": micro_precision,
                "micro_recall": micro_recall,
                "micro_f1": micro_f1,
            }
        )

    return results


__all__ = ["evaluate_axioms", "AXIOM_EXTRACTORS"]

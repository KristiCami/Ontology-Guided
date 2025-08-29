"""Utility to compute axiom-level precision, recall and F1 between RDF graphs.

Two matching strategies are provided:

* ``syntactic`` (default): exact IRI comparison after normalising any
  ``rdfs:label`` values to IRIs.
* ``semantic``: expands both graphs using OWL RL reasoning before comparison
  to account for entailed axioms.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, Set, Tuple, Union

from rdflib import Graph, OWL
from rdflib.namespace import RDF, RDFS
from rdflib.term import Node, URIRef

try:  # OWL RL reasoning for semantic matching
    from owlrl import DeductiveClosure, OWLRL_Semantics
except Exception:  # pragma: no cover - owlrl is optional at runtime
    DeductiveClosure = None
    OWLRL_Semantics = None

# Type alias for sets of axioms represented as hashable tuples or nodes
NormalizedAxiom = Union[str, Tuple[str, str]]
AxiomSet = Set[NormalizedAxiom]

# Mapping axiom type names to callables extracting corresponding sets from a graph
AXIOM_EXTRACTORS = {
    "Classes": lambda g: set(g.subjects(RDF.type, OWL.Class)),
    "ObjectProperty": lambda g: set(g.subjects(RDF.type, OWL.ObjectProperty)),
    "DatatypeProperty": lambda g: set(g.subjects(RDF.type, OWL.DatatypeProperty)),
    "SubClassOf": lambda g: set(g.subject_objects(RDFS.subClassOf)),
    "Domain": lambda g: set(g.subject_objects(RDFS.domain)),
    "Range": lambda g: set(g.subject_objects(RDFS.range)),
}


def _label_to_iri(label: str) -> str:
    """Normalise a label into an IRI fragment.

    This mirrors the behaviour of many ontology generation pipelines that
    convert labels to IRIs by lowercasing and replacing non-alphanumeric
    characters with ``_``.
    """

    return re.sub(r"[^a-zA-Z0-9]+", "_", label.strip()).strip("_").lower()


def _normalise_term(term: Node, graph: Graph) -> str:
    """Normalise a node to a comparable string value."""

    if isinstance(term, URIRef):
        return str(term)
    label = next(graph.objects(term, RDFS.label), None)
    if label:
        return _label_to_iri(str(label))
    return str(term)


def _normalise_axioms(axioms: Iterable, graph: Graph) -> AxiomSet:
    """Return a set of normalised axioms for comparison."""

    normalised: AxiomSet = set()
    for ax in axioms:
        if isinstance(ax, tuple):
            normalised.add(tuple(_normalise_term(t, graph) for t in ax))
        else:
            normalised.add(_normalise_term(ax, graph))
    return normalised


def _semantic_closure(graph: Graph) -> Graph:
    """Expand ``graph`` using OWL RL reasoning if available."""

    if DeductiveClosure is None:  # pragma: no cover - optional dependency
        return graph
    closure = Graph()
    closure += graph
    DeductiveClosure(OWLRL_Semantics).expand(closure)
    return closure


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
    pred_graph: Graph,
    gold_graph: Graph,
    micro: bool = False,
    match_mode: str = "syntactic",
) -> Dict[str, Dict[str, float]]:
    """Compute axiom-level metrics grouped by axiom type.

    Parameters
    ----------
    pred_graph, gold_graph:
        Graphs to compare.
    micro:
        Whether to compute micro-averaged metrics in addition to macro.
    match_mode:
        ``"syntactic"`` (default) performs exact IRI comparison after label
        normalisation. ``"semantic"`` expands both graphs with an OWL RL
        reasoner before comparison to account for entailed axioms.
    """

    if match_mode == "semantic":
        pred_graph = _semantic_closure(pred_graph)
        gold_graph = _semantic_closure(gold_graph)

    per_type: Dict[str, Dict[str, float]] = {}
    macro_f1_total = 0.0
    total_tp = total_pred = total_gold = 0

    for axiom_type, extractor in AXIOM_EXTRACTORS.items():
        pred_set = _normalise_axioms(extractor(pred_graph), pred_graph)
        gold_set = _normalise_axioms(extractor(gold_graph), gold_graph)
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

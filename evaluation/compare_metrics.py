"""CLI to evaluate ontology generation against a gold standard.

Example
-------
python -m evaluation.compare_metrics \
    evaluation/atm_requirements.jsonl gold/atm_gold.ttl
"""

import argparse
import json
from pathlib import Path
from rdflib import Graph
from typing import Iterable, Optional, Union, Mapping, Tuple

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.main import run_pipeline, load_dev_examples
from evaluation.axiom_metrics import evaluate_axioms


def filter_by_ids(
    graph: Graph,
    ids: Iterable[str],
    provenance: Mapping[Tuple[str, str, str], str],
) -> Graph:
    """Return a subgraph keeping only triples with provenance in ``ids``.

    Parameters
    ----------
    graph: Graph
        RDF graph containing axioms to be filtered.
    ids: Iterable[str]
        Allowed ``sentence_id`` values.
    provenance: Mapping[Tuple[str, str, str], str]
        Mapping from triples to their originating ``sentence_id``.

    Returns
    -------
    Graph
        A new graph containing only triples whose provenance ``sentence_id``
        is present in ``ids``.
    """

    id_set = {str(i) for i in ids}
    filtered = Graph()
    for triple in graph:
        key = tuple(str(term) for term in triple)
        sid = provenance.get(key)
        if sid in id_set:
            filtered.add(triple)
    for prefix, namespace in graph.namespaces():
        filtered.bind(prefix, namespace)
    return filtered


def compare_metrics(
    requirements_path: str,
    gold_path: str,
    shapes_path: str = "shapes.ttl",
    base_iri: str = "http://lod.csd.auth.gr/atm/atm.ttl#",
    keywords: Optional[Union[Iterable[str], None]] = None,
    micro: bool = False,
    output_path: str = "results/axiom_metrics.json",
    match_mode: str = "syntactic",
    equiv_as_subclass: bool = False,
    test_ids: Optional[Iterable[str]] = None,
    examples: Optional[list[dict[str, str]]] = None,
    dev_sentence_ids: Optional[Iterable[str]] = None,
) -> dict:
    """Run the pipeline on requirements and compare against a gold TTL file.

    Parameters
    ----------
    requirements_path: str
        Path to requirements JSONL file.
    gold_path: str
        Path to gold standard TTL file containing expected triples.
    shapes_path: str
        Path to SHACL shapes file.
    base_iri: str
        Base IRI for the generated ontology.
    equiv_as_subclass: bool
        If ``True`` treat ``owl:equivalentClass`` axioms as two ``SubClassOf``
        axioms. Otherwise they are evaluated separately under an
        ``EquivalentClasses`` bucket.

    Returns
    -------
    dict
        Dictionary with ``precision``, ``recall`` and ``f1`` values.
    """
    result = run_pipeline(
        [requirements_path],
        shapes_path,
        base_iri,
        spacy_model="en",
        inference="none",
        keywords=keywords,
        allowed_ids=test_ids,
        examples=examples,
        dev_sentence_ids=dev_sentence_ids,
    )
    predicted_ttl = result["combined_ttl"]

    pred_graph = Graph()
    pred_graph.parse(predicted_ttl, format="turtle")

    gold_graph = Graph()
    gold_graph.parse(gold_path, format="turtle")

    text_to_id: dict[str, str] = {}
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    text_to_id[data.get("text", "")] = str(data.get("sentence_id"))

    prov_pred: dict[Tuple[str, str, str], str] = {}
    for meta in result.get("provenance", {}).values():
        triple = tuple(meta.get("triple", ()))
        sid = text_to_id.get(meta.get("requirement", ""))
        if sid:
            prov_pred[tuple(str(t) for t in triple)] = sid

    prov_gold: dict[Tuple[str, str, str], str] = {}
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                sid = str(rec.get("sentence_id"))
                axioms = rec.get("axioms", {})
                ttl_parts: list[str] = []
                for key in ("tbox", "abox"):
                    part = axioms.get(key)
                    if part:
                        ttl_parts.extend(part)
                if ttl_parts:
                    g = Graph()
                    g.parse(data="\n".join(ttl_parts), format="turtle")
                    for triple in g:
                        prov_gold[tuple(str(t) for t in triple)] = sid

    if test_ids is not None:
        pred_graph = filter_by_ids(pred_graph, test_ids, prov_pred)
        gold_graph = filter_by_ids(gold_graph, test_ids, prov_gold)

    pred_triples = set(pred_graph)
    gold_triples = set(gold_graph)
    intersection = pred_triples & gold_triples

    precision = len(intersection) / len(pred_triples) if pred_triples else 0.0
    recall = len(intersection) / len(gold_triples) if gold_triples else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    axiom_metrics = evaluate_axioms(
        pred_graph,
        gold_graph,
        micro=micro,
        match_mode=match_mode,
        equiv_as_subclass=equiv_as_subclass,
    )

    # Include triple-level metrics for backward compatibility
    axiom_metrics.update(
        {"precision": precision, "recall": recall, "f1": f1}
    )

    # Save metrics to a file for convenience
    out_path = Path(output_path)
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(axiom_metrics, f, indent=2)

    return axiom_metrics


def main():
    parser = argparse.ArgumentParser(description="Compare generated OWL with gold standard")
    parser.add_argument("requirements", help="Path to requirements JSONL file")
    parser.add_argument("gold", help="Path to gold standard TTL file")
    parser.add_argument("--shapes", default="shapes.ttl", help="Path to SHACL shapes file")
    parser.add_argument(
        "--base-iri",
        default="http://lod.csd.auth.gr/atm/atm.ttl#",
        help="Base IRI for the generated ontology",
    )
    parser.add_argument(
        "--keywords",
        default=None,
        help="Comma-separated keywords for sentence filtering",
    )
    parser.add_argument(
        "--micro",
        action="store_true",
        help="Compute micro-averaged precision/recall/F1",
    )
    parser.add_argument(
        "--match-mode",
        choices=["syntactic", "semantic"],
        default="syntactic",
        help="Axiom matching mode (default: syntactic)",
    )
    parser.add_argument(
        "--equiv-as-subclass",
        action="store_true",
        help="Score owl:equivalentClass axioms as two SubClassOf axioms",
    )
    parser.add_argument(
        "--out",
        default="results/axiom_metrics.json",
        help="Path to save computed metrics",
    )
    parser.add_argument(
        "--split",
        default=None,
        help="Path to file with sentence_ids to evaluate",
    )
    parser.add_argument(
        "--dev",
        default=None,
        help="Path to file with sentence_ids for dev examples",
    )
    args = parser.parse_args()

    keywords = (
        [k.strip() for k in args.keywords.split(",") if k.strip()]
        if args.keywords
        else None
    )
    test_ids = None
    if args.split:
        with open(args.split, "r", encoding="utf-8") as f:
            test_ids = [line.strip() for line in f if line.strip()]

    examples = None
    dev_ids = None
    if args.dev:
        examples, dev_ids = load_dev_examples(args.requirements, args.dev)
        if test_ids is not None:
            overlap = set(test_ids) & set(dev_ids)
            if overlap:
                raise RuntimeError(
                    "Dev and test splits overlap: " + ", ".join(sorted(overlap))
                )

    metrics = compare_metrics(
        args.requirements,
        args.gold,
        args.shapes,
        args.base_iri,
        keywords=keywords,
        micro=args.micro,
        output_path=args.out,
        match_mode=args.match_mode,
        equiv_as_subclass=args.equiv_as_subclass,
        test_ids=test_ids,
        examples=examples,
        dev_sentence_ids=dev_ids,
    )

    for axiom, vals in metrics.get("per_type", {}).items():
        print(
            f"{axiom}: P={vals['precision']:.3f} "
            f"R={vals['recall']:.3f} F1={vals['f1']:.3f}"
        )
    print(f"Macro-F1: {metrics.get('macro_f1', 0.0):.3f}")
    if args.micro:
        print(f"Micro-F1: {metrics.get('micro_f1', 0.0):.3f}")

    # also print triple-level metrics
    print(f"Overall Precision: {metrics['precision']:.3f}")
    print(f"Overall Recall: {metrics['recall']:.3f}")
    print(f"Overall F1: {metrics['f1']:.3f}")


if __name__ == "__main__":
    main()

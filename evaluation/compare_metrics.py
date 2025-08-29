"""CLI to evaluate ontology generation against a gold standard.

Example
-------
python -m evaluation.compare_metrics \
    evaluation/atm_requirements.jsonl evaluation/atm_gold.ttl
"""

import argparse
from pathlib import Path
from rdflib import Graph
from typing import Iterable, Optional, Union

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.main import run_pipeline


def compare_metrics(
    requirements_path: str,
    gold_path: str,
    shapes_path: str = "shapes.ttl",
    base_iri: str = "http://lod.csd.auth.gr/atm/atm.ttl#",
    keywords: Optional[Union[Iterable[str], None]] = None,
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
    )
    predicted_ttl = result["combined_ttl"]

    pred_graph = Graph()
    pred_graph.parse(predicted_ttl, format="turtle")

    gold_graph = Graph()
    gold_graph.parse(gold_path, format="turtle")

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

    metrics = {"precision": precision, "recall": recall, "f1": f1}

    # Save metrics to a file for convenience
    Path("results").mkdir(exist_ok=True)
    with open("results/metrics.txt", "w", encoding="utf-8") as f:
        f.write(f"precision: {precision}\nrecall: {recall}\nf1: {f1}\n")

    return metrics


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
    args = parser.parse_args()

    keywords = (
        [k.strip() for k in args.keywords.split(",") if k.strip()]
        if args.keywords
        else None
    )
    metrics = compare_metrics(
        args.requirements, args.gold, args.shapes, args.base_iri, keywords=keywords
    )
    print(f"Precision: {metrics['precision']:.3f}")
    print(f"Recall: {metrics['recall']:.3f}")
    print(f"F1: {metrics['f1']:.3f}")


if __name__ == "__main__":
    main()

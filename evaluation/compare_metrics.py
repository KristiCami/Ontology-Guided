import argparse
from pathlib import Path
from rdflib import Graph

from scripts.main import run_pipeline


def compare_metrics(requirements_path: str, gold_path: str, shapes_path: str = "shapes.ttl") -> dict:
    """Run the pipeline on requirements and compare against a gold TTL file.

    Parameters
    ----------
    requirements_path: str
        Path to requirements text file.
    gold_path: str
        Path to gold standard TTL file containing expected triples.
    shapes_path: str
        Path to SHACL shapes file.

    Returns
    -------
    dict
        Dictionary with ``precision`` and ``recall`` values.
    """
    result = run_pipeline(
        [requirements_path],
        shapes_path,
        "http://example.com/atm#",
        spacy_model="en",
        inference="none",
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

    metrics = {"precision": precision, "recall": recall}

    # Save metrics to a file for convenience
    Path("results").mkdir(exist_ok=True)
    with open("results/metrics.txt", "w", encoding="utf-8") as f:
        f.write(f"precision: {precision}\nrecall: {recall}\n")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Compare generated OWL with gold standard")
    parser.add_argument("requirements", help="Path to requirements text file")
    parser.add_argument("gold", help="Path to gold standard TTL file")
    parser.add_argument("--shapes", default="shapes.ttl", help="Path to SHACL shapes file")
    args = parser.parse_args()

    metrics = compare_metrics(args.requirements, args.gold, args.shapes)
    print(f"Precision: {metrics['precision']:.3f}")
    print(f"Recall: {metrics['recall']:.3f}")


if __name__ == "__main__":
    main()

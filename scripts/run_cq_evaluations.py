"""Command-line helper to run competency-question evaluations.

This script allows users to compare multiple ontologies against the same
SPARQL query file and persist the aggregated results to disk.  It is a thin
wrapper around :func:`evaluation.competency_questions.evaluate_cqs` that keeps
all evaluation logic in one place while providing a reproducible CLI entry
point.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.competency_questions import evaluate_cqs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate SPARQL competency questions against one or more ontologies "
            "and store the aggregated results in a JSON file."
        )
    )
    parser.add_argument(
        "--queries",
        required=True,
        type=Path,
        help="Path to a SPARQL .rq/.sparql file or JSON file with ASK queries.",
    )
    parser.add_argument(
        "--ontology",
        dest="ontologies",
        action="append",
        metavar="LABEL=PATH",
        required=True,
        help=(
            "Ontology to evaluate, provided as LABEL=PATH.  May be repeated to "
            "compare several ontologies in one run."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Where to write the evaluation report (JSON).",
    )
    parser.add_argument(
        "--no-inference",
        dest="inference",
        action="store_false",
        help="Disable OWL RL reasoning before executing the queries.",
    )
    return parser.parse_args()


def _parse_ontology_argument(raw: str) -> Dict[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError(
            "Each --ontology value must be provided as LABEL=PATH."
        )
    label, path = raw.split("=", 1)
    label = label.strip()
    if not label:
        raise argparse.ArgumentTypeError("Ontology label cannot be empty.")
    ontology_path = Path(path).expanduser().resolve()
    if not ontology_path.exists():
        raise argparse.ArgumentTypeError(
            f"Ontology file '{ontology_path}' does not exist."
        )
    return {label: ontology_path}


def main() -> None:
    args = parse_args()

    reports = {}
    for raw in args.ontologies:
        mapping = _parse_ontology_argument(raw)
        label, path = next(iter(mapping.items()))
        reports[label] = evaluate_cqs(path, args.queries, inference=args.inference)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)

    for label, metrics in reports.items():
        passed = metrics["passed"]
        total = metrics["total"]
        rate = metrics["pass_rate"]
        print(f"{label}: {passed}/{total} passed ({rate:.2%})")
    print(f"Results saved to {args.output}")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()

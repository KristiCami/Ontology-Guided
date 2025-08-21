#!/usr/bin/env python3
"""Batch evaluation script for ontology generation pipeline.

This script executes the pipeline for multiple datasets and settings and
summarises the results in CSV and Markdown tables.  It is intended to
reproduce the evaluation tables (Tables 1–4) of the associated paper.

Example
-------
python -m evaluation.run_benchmark \
    --pairs "evaluation/atm_requirements.txt:evaluation/atm_gold.ttl" \
    --repeats 1

The default run evaluates the ATM dataset under all four combinations of the
``use_terms`` and ``validate`` flags and writes ``table_<N>.csv`` and
``table_<N>.md`` files into the ``evaluation`` directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from rdflib import Graph

from scripts.main import run_pipeline


Pair = Tuple[str, str, str]


def parse_pair(text: str) -> Pair:
    """Parse a ``requirements:gold[:shapes]`` triple."""
    parts = text.split(":")
    if len(parts) == 2:
        req, gold = parts
        shapes = "shapes.ttl"
    elif len(parts) == 3:
        req, gold, shapes = parts
    else:  # pragma: no cover - argument validation
        raise ValueError("Expected requirements:gold[:shapes]")
    return req, gold, shapes


def compute_metrics(predicted_ttl: str, gold_path: str) -> Dict[str, float]:
    """Return precision, recall and F1 between predicted and gold graphs."""
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
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_once(
    requirements: str, gold: str, shapes: str, base_iri: str, **settings: Any
) -> Tuple[Dict[str, float], Dict[str, Any], Any]:
    """Run the pipeline once and compute evaluation metrics."""
    result = run_pipeline([requirements], shapes, base_iri, **settings)
    metrics = compute_metrics(result["combined_ttl"], gold)
    violation_stats = result.get("violation_stats", {}) or {}
    shacl_conforms = result.get("shacl_conforms")
    return metrics, violation_stats, shacl_conforms


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], headers: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(",".join(str(row.get(h, "")) for h in headers) + "\n")


def write_markdown(path: Path, rows: Sequence[Dict[str, Any]], headers: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for row in rows:
            f.write("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |\n")


def run_evaluations(
    pairs: Iterable[Pair],
    settings_list: Sequence[Dict[str, Any]],
    repeats: int,
    base_iri: str,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, setting in enumerate(settings_list, start=1):
        name = setting.get("name", f"table_{idx}")
        pipeline_opts = {k: v for k, v in setting.items() if k not in {"name"}}
        table_rows: List[Dict[str, Any]] = []

        for req, gold, shapes in pairs:
            metrics_list: List[Dict[str, float]] = []
            violations_list: List[Dict[str, Any]] = []
            conforms_list: List[Any] = []

            for _ in range(repeats):
                metrics, violations, conforms = evaluate_once(
                    req, gold, shapes, base_iri, **pipeline_opts
                )
                metrics_list.append(metrics)
                violations_list.append(violations)
                conforms_list.append(conforms)

            def avg(key: str) -> float:
                vals = [v.get(key) for v in violations_list if key in v]
                return mean(vals) if vals else 0.0

            row = {
                "requirements": Path(req).name,
                "precision": mean(m["precision"] for m in metrics_list),
                "recall": mean(m["recall"] for m in metrics_list),
                "f1": mean(m["f1"] for m in metrics_list),
                "initial_violations": avg("initial_count"),
                "final_violations": avg("final_count"),
                "iterations": avg("iterations"),
                "shacl_conforms_rate": (
                    sum(1 for c in conforms_list if c) / len(conforms_list)
                    if conforms_list
                    else 0.0
                ),
                "runs": repeats,
            }
            table_rows.append(row)

        headers = [
            "requirements",
            "precision",
            "recall",
            "f1",
            "initial_violations",
            "final_violations",
            "iterations",
            "shacl_conforms_rate",
            "runs",
        ]
        write_csv(output_dir / f"{name}.csv", table_rows, headers)
        write_markdown(output_dir / f"{name}.md", table_rows, headers)


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(description="Run batch evaluations")
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["evaluation/atm_requirements.txt:evaluation/atm_gold.ttl"],
        help="List of requirements:gold[:shapes] triples",
    )
    parser.add_argument(
        "--settings",
        type=str,
        default=None,
        help="JSON list with setting dictionaries",
    )
    parser.add_argument("--repeats", type=int, default=1, help="Number of runs per configuration")
    parser.add_argument(
        "--base-iri",
        default="http://example.com/atm#",
        help="Base IRI for generated ontologies",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation",
        help="Directory where result tables will be written",
    )
    args = parser.parse_args()

    pairs = [parse_pair(p) for p in args.pairs]

    if args.settings:
        settings_list = json.loads(args.settings)
    else:
        settings_list = [
            {"name": "table1", "use_terms": True, "validate": True},
            {"name": "table2", "use_terms": False, "validate": True},
            {"name": "table3", "use_terms": True, "validate": False},
            {"name": "table4", "use_terms": False, "validate": False},
        ]

    run_evaluations(pairs, settings_list, args.repeats, args.base_iri, Path(args.output_dir))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

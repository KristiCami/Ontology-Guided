#!/usr/bin/env python3
"""Batch evaluation script for ontology generation pipeline.

This script executes the pipeline for multiple datasets and settings and
summarises the results in CSV and Markdown tables.  It is intended to
reproduce the evaluation tables (Tables 1–4) of the associated paper. Few-
shot examples from the dev split are loaded automatically.

Example
-------
python -m evaluation.run_benchmark \
    --pairs "evaluation/atm_requirements.jsonl:gold/atm_gold.ttl" \
    --cqs evaluation/atm_cqs.rq \
    --base-iri http://lod.csd.auth.gr/atm/atm.ttl# \
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
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Optional, Union

from rdflib import Graph
from rdflib.term import URIRef

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ontology_guided.project_paths import DEFAULT_SHAPES_PATH
from scripts.main import run_pipeline, load_dev_examples
from .competency_questions import evaluate_cqs
from .repair_efficiency import aggregate_repair_efficiency
from .compare_metrics import filter_by_ids
from ontology_guided import exemplar_selector
from ontology_guided.validator import SHACLValidator
from ontology_guided.reasoner import run_reasoner

DEV_REQUIREMENTS_PATH = os.path.join(PROJECT_ROOT, "evaluation", "atm_requirements.jsonl")
DEV_SPLIT_PATH = os.path.join(PROJECT_ROOT, "splits", "dev.txt")
DEV_EXAMPLES, DEV_SENTENCE_IDS = load_dev_examples(DEV_REQUIREMENTS_PATH, DEV_SPLIT_PATH)


Pair = Tuple[str, str, str]


def parse_pair(text: str) -> Pair:
    """Parse a ``requirements:gold[:shapes]`` triple."""
    parts = text.split(":")
    if len(parts) == 2:
        req, gold = parts
        shapes = str(DEFAULT_SHAPES_PATH)
    elif len(parts) == 3:
        req, gold, shapes = parts
    else:  # pragma: no cover - argument validation
        raise ValueError("Expected requirements:gold[:shapes]")
    return req, gold, shapes


def _normalized_triples(graph: Graph) -> set[Tuple[str, str, str]]:
    """Return triples with URIs normalised via the graph's namespace manager."""
    nm = graph.namespace_manager

    def norm(term):
        if isinstance(term, URIRef):
            return nm.normalizeUri(term)
        return term.n3(nm)

    return {tuple(norm(term) for term in triple) for triple in graph}


def compute_metrics(
    predicted_ttl: str, gold_path: str, normalize_base: bool = False
) -> Dict[str, float]:
    """Return precision, recall and F1 between predicted and gold graphs."""
    pred_graph = Graph()
    pred_graph.parse(predicted_ttl, format="turtle")
    gold_graph = Graph()
    gold_graph.parse(gold_path, format="turtle")

    if normalize_base:
        pred_triples = _normalized_triples(pred_graph)
        gold_triples = _normalized_triples(gold_graph)
    else:
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
    requirements: str,
    gold: str,
    shapes: str,
    base_iri: str,
    ontologies: Optional[Union[Sequence[str], None]] = None,
    normalize_base: bool = False,
    keywords: Optional[Union[Iterable[str], None]] = None,
    cq_path: Optional[str] = None,
    test_ids: Optional[Iterable[str]] = None,
    dev_sentence_ids: Optional[Iterable[str]] = None,
    **settings: Any,
) -> Tuple[Dict[str, float], Dict[str, Any], Any, Optional[float]]:
    """Run the pipeline once and compute evaluation metrics."""
    result = run_pipeline(
        [requirements],
        shapes,
        base_iri,
        ontologies=ontologies,
        keywords=keywords,
        allowed_ids=test_ids,
        dev_sentence_ids=dev_sentence_ids,
        retrieval_method=getattr(exemplar_selector, "RETRIEVAL_METHOD", "tfidf_cosine"),
        **settings,
    )

    pred_graph = Graph()
    if result.get("combined_ttl") and os.path.exists(result["combined_ttl"]):
        pred_graph.parse(result["combined_ttl"], format="turtle")
    gold_graph = Graph()
    if gold and os.path.exists(gold):
        gold_graph.parse(gold, format="turtle")

    text_to_id: Dict[str, str] = {}
    if os.path.exists(requirements):
        with open(requirements, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    text_to_id[data["text"]] = str(data.get("sentence_id"))

    prov_pred: Dict[Tuple[str, str, str], str] = {}
    for meta in result.get("provenance", {}).values():
        triple = tuple(meta.get("triple", ()))
        sid = text_to_id.get(meta.get("requirement", ""))
        if sid:
            prov_pred[triple] = sid

    prov_gold: Dict[Tuple[str, str, str], str] = {}
    if os.path.exists(requirements):
        with open(requirements, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                sid = str(rec.get("sentence_id"))
                axioms = rec.get("axioms", {})
                ttl_parts: List[str] = []
                for key in ("tbox", "abox"):
                    part = axioms.get(key)
                    if part:
                        ttl_parts.extend(part)
                if ttl_parts:
                    g = Graph()
                    g.parse(data="\n".join(ttl_parts), format="turtle")
                    for triple in g:
                        prov_gold[tuple(str(t) for t in triple)] = sid

    if test_ids is None:
        filtered_pred = pred_graph
        filtered_gold = gold_graph
    else:
        filtered_pred = filter_by_ids(pred_graph, test_ids, prov_pred)
        filtered_gold = filter_by_ids(gold_graph, test_ids, prov_gold)

    pred_graph = filtered_pred
    gold_graph = filtered_gold

    pred_path = "results/combined_test.ttl"
    gold_filtered_path = "results/gold_test.ttl"
    pred_graph.serialize(pred_path, format="turtle")
    gold_graph.serialize(gold_filtered_path, format="turtle")

    metrics = compute_metrics(pred_path, gold_filtered_path, normalize_base=normalize_base)

    shacl_conforms = None
    summary: Dict[str, Any] = {"total": 0, "bySeverity": {}}
    is_consistent = None
    unsat_classes: List[str] = []
    if settings.get("reason", False):
        pred_graph.serialize("results/combined_test.owl", format="xml")
        try:
            _, is_consistent, unsat_classes = run_reasoner("results/combined_test.owl")
        except Exception:
            is_consistent = None
            unsat_classes = []
    if settings.get("validate", False):
        validator = SHACLValidator(
            pred_path, shapes, inference=settings.get("inference", "rdfs")
        )
        shacl_conforms, _, summary = validator.run_validation()

    violation_stats = {
        "pre_count": summary.get("total", 0),
        "post_count": summary.get("total", 0),
        "iterations": 0,
        "first_conforms_iteration": 0 if shacl_conforms else None,
        "per_iteration": [
            {
                "iteration": 0,
                "total": summary.get("total", 0),
                "bySeverity": summary.get("bySeverity", {}),
                "is_consistent": is_consistent,
                "unsat_count": len(unsat_classes),
                "prompt_count": 0,
                "prompt_success_rate": 0.0,
            }
        ],
        "reduction": 0.0,
        "unsat_initial": len(unsat_classes),
        "unsat_final": len(unsat_classes),
        "consistency_transitions": [],
        "prompt_count": 0,
        "prompt_success_rate": 0.0,
    }

    cq_rate = None
    if cq_path:
        cq_res = evaluate_cqs(pred_path, cq_path)
        cq_rate = cq_res["pass_rate"]
    return metrics, violation_stats, shacl_conforms, cq_rate


def write_csv(
    path: Path, rows: Sequence[Dict[str, Any]], headers: Sequence[str]
) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(",".join(str(row.get(h, "")) for h in headers) + "\n")


def write_markdown(
    path: Path, rows: Sequence[Dict[str, Any]], headers: Sequence[str]
) -> None:
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
    normalize_base: bool = False,
    keywords: Optional[Union[Iterable[str], None]] = None,
    cq_paths: Optional[Sequence[Optional[str]]] = None,
    split_paths: Optional[Sequence[Optional[str]]] = None,
    dev_sentence_ids: Optional[Iterable[str]] = None,
    skip_filter: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, setting in enumerate(settings_list, start=1):
        name = setting.get("name", f"table_{idx}")
        pipeline_opts = {k: v for k, v in setting.items() if k not in {"name"}}
        table_rows: List[Dict[str, Any]] = []

        for dataset_idx, (req, gold, shapes) in enumerate(pairs):
            cq_path = (
                cq_paths[dataset_idx]
                if cq_paths and dataset_idx < len(cq_paths)
                else None
            )
            test_ids = None
            if not skip_filter:
                if split_paths and dataset_idx < len(split_paths) and split_paths[dataset_idx]:
                    with open(split_paths[dataset_idx], "r", encoding="utf-8") as f:
                        test_ids = [line.strip() for line in f if line.strip()]
                    if dev_sentence_ids is not None:
                        overlap = set(test_ids) & set(dev_sentence_ids)
                        if overlap:
                            raise ValueError(
                                f"Test IDs overlap with dev IDs: {sorted(overlap)}"
                            )
            metrics_list: List[Dict[str, float]] = []
            violations_list: List[Dict[str, Any]] = []
            conforms_list: List[Any] = []
            cq_list: List[float] = []

            for _ in range(repeats):
                metrics, violations, conforms, cq_rate = evaluate_once(
                    req,
                    gold,
                    shapes,
                    base_iri,
                    normalize_base=normalize_base,
                    keywords=keywords,
                    cq_path=cq_path,
                    test_ids=test_ids,
                    dev_sentence_ids=dev_sentence_ids,
                    **pipeline_opts,
                )
                metrics_list.append(metrics)
                violations_list.append(violations)
                conforms_list.append(conforms)
                if cq_rate is not None:
                    cq_list.append(cq_rate)

            def avg(key: str) -> float:
                vals = [v.get(key) for v in violations_list if key in v]
                return mean(vals) if vals else 0.0

            efficiency = aggregate_repair_efficiency(violations_list)

            row = {
                "requirements": Path(req).name,
                "precision": mean(m["precision"] for m in metrics_list),
                "recall": mean(m["recall"] for m in metrics_list),
                "f1": mean(m["f1"] for m in metrics_list),
                "initial_violations": avg("pre_count"),
                "final_violations": avg("post_count"),
                "iterations": efficiency.mean_iterations,
                "iter_1": efficiency.distribution.get("1", 0),
                "iter_2": efficiency.distribution.get("2", 0),
                "iter_3": efficiency.distribution.get("3", 0),
                "iter_gt3": efficiency.distribution.get(">3", 0),
                "prompts_per_iteration": (
                    efficiency.avg_prompts_per_iteration
                    if efficiency.avg_prompts_per_iteration is not None
                    else 0.0
                ),
                "prompt_success_rate": (
                    efficiency.success_rate_per_prompt
                    if efficiency.success_rate_per_prompt is not None
                    else 0.0
                ),
                "shacl_conforms_rate": (
                    sum(1 for c in conforms_list if c) / len(conforms_list)
                    if conforms_list
                    else 0.0
                ),
                "runs": repeats,
                "cq_pass_rate": mean(cq_list) if cq_list else 0.0,
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
            "iter_1",
            "iter_2",
            "iter_3",
            "iter_gt3",
            "prompts_per_iteration",
            "prompt_success_rate",
            "shacl_conforms_rate",
            "runs",
            "cq_pass_rate",
        ]
        write_csv(output_dir / f"{name}.csv", table_rows, headers)
        write_markdown(output_dir / f"{name}.md", table_rows, headers)


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(description="Run batch evaluations")
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["evaluation/atm_requirements.jsonl:gold/atm_gold.ttl"],
        help="List of requirements:gold[:shapes] triples",
    )
    parser.add_argument(
        "--settings",
        type=str,
        default=None,
        help="JSON list with setting dictionaries",
    )
    parser.add_argument(
        "--settings-file",
        type=str,
        default=None,
        help="Path to JSON file with setting dictionaries",
    )
    parser.add_argument(
        "--repeats", type=int, default=1, help="Number of runs per configuration"
    )
    parser.add_argument(
        "--base-iri",
        default="http://lod.csd.auth.gr/atm/atm.ttl#",
        help="Base IRI for generated ontologies",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation",
        help="Directory where result tables will be written",
    )
    parser.add_argument(
        "--ontologies",
        nargs="*",
        default=None,
        help="List of ontology TTL files to include in each run",
    )
    parser.add_argument(
        "--ontology-dir",
        default=None,
        help="Directory from which all .ttl ontologies will be loaded",
    )
    parser.add_argument(
        "--normalize-base",
        action="store_true",
        help="Normalize base IRIs before comparing graphs",
    )
    parser.add_argument(
        "--backend",
        default="cache",
        choices=["cache", "openai", "llama"],
        help="LLM backend to use when running the pipeline",
    )
    parser.add_argument(
        "--keywords",
        default=None,
        help="Comma-separated keywords for sentence filtering",
    )
    parser.add_argument(
        "--cqs",
        nargs="*",
        default=None,
        help="List of files with SPARQL ASK competency questions, one per dataset",
    )
    parser.add_argument(
        "--splits",
        nargs="*",
        default=["splits/test.txt"],
        help="List of files with sentence_id lists, one per dataset",
    )
    parser.add_argument(
        "--skip-filter",
        action="store_true",
        help="Do not filter triples by sentence IDs (use full graphs)",
    )
    parser.add_argument(
        "--use-retrieval",
        action="store_true",
        help="Select few-shot examples via retrieval from a dev pool",
    )
    parser.add_argument(
        "--dev-pool",
        default=None,
        help="JSON file with dev examples used for retrieval",
    )
    parser.add_argument(
        "--retrieve-k",
        type=int,
        default=3,
        help="Number of exemplars to retrieve for each sentence",
    )
    parser.add_argument(
        "--prompt-log",
        default=None,
        help="Where to log IDs of retrieved exemplars",
    )
    args = parser.parse_args()

    pairs = [parse_pair(p) for p in args.pairs]

    if args.settings_file:
        settings_list = json.load(open(args.settings_file))
    elif args.settings:
        try:
            settings_list = json.loads(args.settings)
        except json.JSONDecodeError as exc:
            raise argparse.ArgumentTypeError(
                "Invalid JSON for --settings. JSON must be valid; "
                "for complex configurations, use --settings-file."
            ) from exc
    else:
        settings_list = [
            {"name": "table1", "use_terms": True, "validate": True},
            {"name": "table2", "use_terms": False, "validate": True},
            {"name": "table3", "use_terms": True, "validate": False},
            {"name": "table4", "use_terms": False, "validate": False},
        ]

    ontology_list = list(args.ontologies or [])
    if args.ontology_dir:
        dir_path = Path(args.ontology_dir)
        ontology_list.extend(str(p) for p in sorted(dir_path.glob("*.ttl")))
    if not ontology_list:
        ontology_list = [
            "gold/atm_gold.ttl",
            "ontologies/lexical.ttl",
            "ontologies/lexical_atm.ttl",
        ]
    for setting in settings_list:
        setting.setdefault("ontologies", ontology_list)
        setting.setdefault("examples", DEV_EXAMPLES)
        setting.setdefault("backend", args.backend)
        if args.use_retrieval:
            setting.setdefault("use_retrieval", True)
        if args.dev_pool:
            setting.setdefault("dev_pool", args.dev_pool)
        elif args.use_retrieval:
            setting.setdefault("dev_pool", DEV_EXAMPLES)
        if args.retrieve_k is not None:
            setting.setdefault("retrieve_k", args.retrieve_k)
        if args.prompt_log is not None:
            setting.setdefault("prompt_log", args.prompt_log)

    keywords = (
        [k.strip() for k in args.keywords.split(",") if k.strip()]
        if args.keywords
        else None
    )
    if args.cqs is not None and len(args.cqs) != len(pairs):
        raise ValueError("--cqs requires the same number of paths as --pairs")
    if args.splits is not None and len(args.splits) != len(pairs):
        raise ValueError("--splits requires the same number of paths as --pairs")

    run_evaluations(
        pairs,
        settings_list,
        args.repeats,
        args.base_iri,
        Path(args.output_dir),
        normalize_base=args.normalize_base,
        keywords=keywords,
        cq_paths=args.cqs,
        split_paths=args.splits,
        dev_sentence_ids=DEV_SENTENCE_IDS,
        skip_filter=args.skip_filter,
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

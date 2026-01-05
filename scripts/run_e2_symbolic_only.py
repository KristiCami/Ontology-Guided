#!/usr/bin/env python3
"""Run the E2 symbolic-only baseline (heuristic rules + SHACL/Reasoner)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rdflib import Graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from og_nsd import OntologyDraftingPipeline, PipelineConfig  # noqa: E402
from og_nsd.metrics import compute_exact_metrics, compute_semantic_metrics  # noqa: E402
from og_nsd.queries import CompetencyQuestionRunner  # noqa: E402
from og_nsd.shacl import summarize_shacl_report  # noqa: E402


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the E2 symbolic-only experiment")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/atm_e2_symbolic_only.json")
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    output_root = PROJECT_ROOT / cfg.get("output_root", "runs/E2_symbolic_only")
    ensure_dir(output_root)

    temperature = cfg.get("temperature", 0.7)
    pipeline_config = PipelineConfig(
        requirements_path=PROJECT_ROOT / cfg["requirements_path"],
        shapes_path=PROJECT_ROOT / cfg["shapes_path"],
        base_ontology_path=None,
        competency_questions_path=PROJECT_ROOT / cfg.get("competency_questions")
        if cfg.get("competency_questions")
        else None,
        output_path=output_root / "pred.ttl",
        report_path=output_root / "run_report.json",
        llm_mode=cfg.get("llm_mode", "openai"),
        llm_temperature=temperature,
        max_requirements=cfg.get("max_requirements", 20),
        reasoning_enabled=cfg.get("reasoning", True),
        max_iterations=cfg.get("iterations", 0),
        use_ontology_context=False,
        base_namespace=cfg.get("base_namespace", "http://lod.csd.auth.gr/atm/atm.ttl#"),
    )

    pipeline = OntologyDraftingPipeline(pipeline_config)
    pipeline.run()

    asserted_graph = pipeline.state_graph or Graph().parse(pipeline_config.output_path)
    data_graph = pipeline.reasoned_graph or asserted_graph

    if pipeline.last_shacl_report:
        summary_path = output_root / "validation_summary.json"
        summary_path.write_text(
            json.dumps(summarize_shacl_report(pipeline.last_shacl_report), indent=2),
            encoding="utf-8",
        )

    if pipeline.last_reasoner_report:
        reasoning_payload = {
            "unsat_classes": pipeline.last_reasoner_report.unsatisfiable_classes,
            "total_unsat": len(pipeline.last_reasoner_report.unsatisfiable_classes),
            "notes": pipeline.last_reasoner_report.notes,
        }
        (output_root / "reasoning_report.json").write_text(
            json.dumps(reasoning_payload, indent=2), encoding="utf-8"
        )

    gold_path = PROJECT_ROOT / cfg.get("gold_path", cfg.get("ontology_path", "gold/atm_gold.ttl"))
    (output_root / "metrics_exact.json").write_text(
        json.dumps(compute_exact_metrics(pipeline_config.output_path, gold_path), indent=2),
        encoding="utf-8",
    )
    (output_root / "metrics_semantic.json").write_text(
        json.dumps(compute_semantic_metrics(data_graph, Graph().parse(gold_path)), indent=2),
        encoding="utf-8",
    )

    if pipeline_config.competency_questions_path:
        cq_runner = CompetencyQuestionRunner(pipeline_config.competency_questions_path)
        cq_results = cq_runner.run(data_graph)
        passed = sum(1 for result in cq_results if result.success)
        total = len(cq_results)
        cq_payload = {
            "pass_rate": (passed / total) if total else 0.0,
            "passed": passed,
            "total": total,
            "results": [
                {"query": result.query, "success": result.success, "message": result.message}
                for result in cq_results
            ],
        }
        (output_root / "cq_results.json").write_text(json.dumps(cq_payload, indent=2), encoding="utf-8")

    print("E2 run complete. Key outputs written under", output_root)


if __name__ == "__main__":
    main()

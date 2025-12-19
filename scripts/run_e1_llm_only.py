#!/usr/bin/env python3
"""Run the E1 LLM-only baseline (no SHACL/Reasoner, no repair loop)."""
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


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the E1 LLM-only experiment")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/atm_e1_llm_only.json")
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    output_root = PROJECT_ROOT / cfg.get("output_root", "runs/E1_llm_only")
    ensure_dir(output_root)

    pipeline_config = PipelineConfig(
        requirements_path=PROJECT_ROOT / cfg["requirements_path"],
        shapes_path=None,
        base_ontology_path=None,
        competency_questions_path=PROJECT_ROOT / cfg.get("competency_questions")
        if cfg.get("competency_questions")
        else None,
        output_path=output_root / "pred.ttl",
        report_path=output_root / "run_report.json",
        llm_mode=cfg.get("llm_mode", "heuristic"),
        max_requirements=cfg.get("max_requirements", 20),
        reasoning_enabled=False,
        max_iterations=0,
        draft_only=True,
        use_ontology_context=cfg.get("use_ontology_context", False),
        grounding_ontology_path=PROJECT_ROOT / cfg["ontology_path"] if cfg.get("ontology_path") else None,
        base_namespace=cfg.get("base_namespace", "http://lod.csd.auth.gr/atm/atm.ttl#"),
    )

    pipeline = OntologyDraftingPipeline(pipeline_config)
    pipeline.run()

    pred_graph = Graph().parse(pipeline_config.output_path)
    gold_path = PROJECT_ROOT / cfg.get("ontology_path", "gold/atm_gold.ttl")

    (output_root / "metrics_exact.json").write_text(
        json.dumps(compute_exact_metrics(pipeline_config.output_path, gold_path), indent=2),
        encoding="utf-8",
    )
    (output_root / "metrics_semantic.json").write_text(
        json.dumps(compute_semantic_metrics(pred_graph, Graph().parse(gold_path)), indent=2),
        encoding="utf-8",
    )

    if pipeline_config.competency_questions_path:
        cq_runner = CompetencyQuestionRunner(pipeline_config.competency_questions_path)
        cq_results = cq_runner.run(pred_graph)
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

    print("E1 run complete. Key outputs written under", output_root)


if __name__ == "__main__":
    main()

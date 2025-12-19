"""Run the E4 iterative repair loop as described in the protocol."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from pathlib import Path

from rdflib import Graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from og_nsd import OntologyAssembler, load_schema_context  # noqa: E402
from og_nsd.llm import HeuristicLLM, OpenAILLM  # noqa: E402
from og_nsd.reasoning import OwlreadyReasoner  # noqa: E402
from og_nsd.repair import (  # noqa: E402
    final_metrics,
    save_patch_plan,
    save_shacl_report,
    shacl_report_to_patches,
    should_stop,
)
from og_nsd.requirements import RequirementLoader, chunk_requirements  # noqa: E402
from og_nsd.shacl import ShaclValidator, summarize_shacl_report  # noqa: E402
from og_nsd.queries import CompetencyQuestionRunner  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the E4 iterative repair experiment")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/atm_ontology_aware.json")
    parser.add_argument("--cq-threshold", type=float, default=0.8)
    parser.add_argument("--kmax", type=int, default=3)
    return parser.parse_args()


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def select_llm(cfg: dict, base_namespace: str):
    mode = cfg.get("llm_mode", "heuristic")
    temperature = cfg.get("temperature", 0.2)
    if mode == "openai":
        try:
            return OpenAILLM(temperature=temperature)
        except RuntimeError:
            return HeuristicLLM(base_namespace)
    return HeuristicLLM(base_namespace)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    base_ns = cfg.get("base_namespace", "http://lod.csd.auth.gr/atm/atm.ttl#")
    output_root = PROJECT_ROOT / cfg.get("output_root", "runs/E4_full")
    ensure_dir(output_root)

    requirement_loader = RequirementLoader(PROJECT_ROOT / cfg["requirements_path"])
    requirements = requirement_loader.load(cfg.get("max_requirements", 20))
    schema_context = load_schema_context(PROJECT_ROOT / cfg["ontology_path"], base_ns)

    assembler = OntologyAssembler(default_prefixes=schema_context.prefixes)
    validator = ShaclValidator(PROJECT_ROOT / cfg["shapes_path"])
    reasoner = OwlreadyReasoner(enabled=cfg.get("reasoning", True))
    cq_runner = None
    if cfg.get("competency_questions"):
        cq_runner = CompetencyQuestionRunner(PROJECT_ROOT / cfg["competency_questions"])

    llm = select_llm(cfg, base_ns)

    state = assembler.bootstrap()
    iter_dir = output_root / "iter0"
    ensure_dir(iter_dir)

    draft_log = []
    for batch in chunk_requirements(requirements, size=5):
        response = llm.generate_axioms(batch, schema_context=schema_context)
        assembler.add_turtle(state, response.turtle)
        draft_log.append(
            {
                "requirements": [
                    {
                        "identifier": req.identifier,
                        "title": req.title,
                        "text": req.text,
                        "boilerplate": req.boilerplate,
                    }
                    for req in batch
                ],
                "turtle": response.turtle,
                "reasoning_notes": response.reasoning_notes,
            }
        )

    assembler.serialize(state, iter_dir / "pred.ttl")
    (iter_dir / "llm_draft_log.json").write_text(json.dumps(draft_log, indent=2), encoding="utf-8")

    repair_log: dict = {}
    previous_patches = None
    previous_hard = None
    current_iter = 0
    cq_pass_rate = 0.0

    while True:
        reasoning_result = reasoner.run(state.graph)
        (iter_dir / "reasoner_report.json").write_text(
            json.dumps(asdict(reasoning_result.report), indent=2), encoding="utf-8"
        )
        shacl_report = validator.validate(reasoning_result.expanded_graph)
        summary = summarize_shacl_report(shacl_report)
        repair_log[f"iter{current_iter}"] = summary["violations"]

        cq_results = cq_runner.run(reasoning_result.expanded_graph) if cq_runner else []
        cq_pass_rate = (sum(1 for res in cq_results if res.success) / len(cq_results)) if cq_results else 0.0

        save_shacl_report(shacl_report, iter_dir / "shacl_report.ttl")
        patches = shacl_report_to_patches(shacl_report)
        save_patch_plan(patches, iter_dir / "patches.json")

        if should_stop(
            iteration=current_iter,
            max_iterations=args.kmax,
            patches=patches,
            previous_patches=previous_patches,
            previous_hard=previous_hard,
            shacl_report=shacl_report,
            cq_pass_rate=cq_pass_rate,
            cq_threshold=args.cq_threshold,
        ):
            break

        previous_patches = patches
        previous_hard = summary["violations"]["hard"]
        next_iter = current_iter + 1
        next_dir = output_root / f"iter{next_iter}"
        ensure_dir(next_dir)

        context_ttl = state.graph.serialize(format="turtle")
        patch_response = llm.apply_patches([p.to_dict() for p in patches], context_ttl)
        (iter_dir / "patch_application.json").write_text(
            json.dumps(
                {"patches": [p.to_dict() for p in patches], "reasoning_notes": patch_response.reasoning_notes},
                indent=2,
            ),
            encoding="utf-8",
        )
        state = assembler.bootstrap()
        assembler.add_turtle(state, patch_response.turtle)
        assembler.serialize(state, next_dir / "pred.ttl")

        iter_dir = next_dir
        current_iter = next_iter

    final_dir = output_root / "final"
    ensure_dir(final_dir)
    assembler.serialize(state, final_dir / "pred.ttl")

    gold_path = PROJECT_ROOT / cfg["ontology_path"]
    gold_graph = Graph().parse(gold_path)
    metrics_payload = final_metrics(state.graph, gold_graph)
    (final_dir / "metrics_exact.json").write_text(json.dumps(metrics_payload["exact"], indent=2), encoding="utf-8")
    (final_dir / "metrics_semantic.json").write_text(json.dumps(metrics_payload["semantic"], indent=2), encoding="utf-8")

    validation_summary_path = final_dir / "validation_summary.json"
    validation_summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if cq_runner:
        cq_payload = {
            "pass_rate": cq_pass_rate,
            "results": [
                {"query": result.query, "success": result.success, "message": result.message}
                for result in cq_results
            ],
        }
        (final_dir / "cq_results.json").write_text(json.dumps(cq_payload, indent=2), encoding="utf-8")

    (output_root / "repair_log.json").write_text(json.dumps(repair_log, indent=2), encoding="utf-8")

    print("E4 run complete. Outputs written to", output_root)


if __name__ == "__main__":
    main()

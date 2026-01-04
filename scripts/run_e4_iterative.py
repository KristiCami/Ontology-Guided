"""Run the E4 iterative repair loop as described in the protocol."""

from __future__ import annotations

import argparse
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
    StopDecision,
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
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/atm_e4_iterative.json")
    parser.add_argument("--cq-threshold", type=float, default=0.8)
    parser.add_argument(
        "--stop-policies",
        type=str,
        default=None,
        help=(
            "Comma-separated list of stop policies to sweep. "
            "Supported: default,hard_and_cq,ignore_no_hard,max_only. "
            "Defaults to config stop_policies (or stop_policy) when omitted."
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Override output root (defaults to config). When multiple stop policies are provided, each run is stored in a subfolder.",
    )
    parser.add_argument(
        "--kmax",
        type=int,
        default=None,  # kept for backwards compatibility; validated later.
        help="Deprecated; iterations are controlled via config. Do not set.",
    )
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


def _count_patch_types(patches):
    counts = {}
    for patch in patches:
        action = patch.action if hasattr(patch, "action") else patch.get("action")
        if action is None:
            continue
        counts[action] = counts.get(action, 0) + 1
    return counts


def _normalize_stop_policies(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        items = raw.split(",")
    else:
        items = raw
    return [str(item).strip() for item in items if str(item).strip()]


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    base_ns = cfg.get("base_namespace", "http://lod.csd.auth.gr/atm/atm.ttl#")

    cli_stop_policies = _normalize_stop_policies(args.stop_policies)
    config_stop_policies = _normalize_stop_policies(cfg.get("stop_policies") or cfg.get("stop_policy"))
    stop_policies = cli_stop_policies or config_stop_policies or ["hard_and_cq"]

    output_root_base = PROJECT_ROOT / cfg.get("output_root", "runs/E4_full")
    if args.output_root:
        output_root_base = args.output_root
    ensure_dir(output_root_base)

    iterations_cfg = cfg.get("iterations")
    if iterations_cfg is None:
        raise ValueError("Config must define 'iterations' as the single source of truth for loop count.")
    if iterations_cfg <= 0:
        raise ValueError("Config field 'iterations' must be a positive integer.")
    if args.kmax is not None:
        raise ValueError("--kmax is deprecated; configure iterations exclusively via the config file.")

    prompt_mode = cfg.get("prompt_mode", "ontology_aware")
    valid_modes = {"ontology_aware", "baseline"}
    if prompt_mode not in valid_modes:
        raise ValueError(f"Unsupported prompt_mode '{prompt_mode}'. Choose from {sorted(valid_modes)}.")

    requirement_loader = RequirementLoader(PROJECT_ROOT / cfg["requirements_path"])
    requirements = requirement_loader.load(cfg.get("max_requirements", 20))

    ontology_context_path = None
    if cfg.get("use_ontology_context", True) and prompt_mode != "baseline":
        ontology_context_path = cfg.get("ontology_context_path") or cfg.get("ontology_path")
        if ontology_context_path is None:
            raise ValueError("use_ontology_context=true requires ontology_context_path or ontology_path in config.")

    gold_path = PROJECT_ROOT / (cfg.get("gold_path") or cfg["ontology_path"])
    if ontology_context_path:
        context_resolved = (PROJECT_ROOT / ontology_context_path).resolve()
        gold_resolved = gold_path.resolve()
        if context_resolved == gold_resolved:
            raise ValueError(
                "ontology_context_path must differ from gold_path to avoid schema leakage between grounding and gold."
            )

    schema_context = load_schema_context(PROJECT_ROOT / ontology_context_path, base_ns) if ontology_context_path else None

    assembler = OntologyAssembler(default_prefixes=schema_context.prefixes if schema_context else None)
    validator = ShaclValidator(PROJECT_ROOT / cfg["shapes_path"]) if cfg.get("validation", True) else None
    reasoner = OwlreadyReasoner(enabled=cfg.get("reasoning", True))
    cq_runner = None
    if cfg.get("competency_questions"):
        cq_runner = CompetencyQuestionRunner(PROJECT_ROOT / cfg["competency_questions"])

    llm = select_llm(cfg, base_ns)

    def run_single(policy: str, output_root: Path) -> None:
        state = assembler.bootstrap()
        iter_dir = output_root / "iter0"
        ensure_dir(iter_dir)

        chunk_size = cfg.get("requirements_chunk_size", 5)
        for batch in chunk_requirements(requirements, size=chunk_size):
            response = llm.generate_axioms(batch, schema_context=schema_context)
            try:
                assembler.add_turtle(state, response.turtle)
            except ValueError as exc:
                (iter_dir / "llm_error.txt").write_text(
                    "Draft generation failed to parse LLM Turtle.\n"
                    f"Reason: {exc}\n\nRaw turtle:\n{response.turtle}",
                    encoding="utf-8",
                )
                repair_log: dict = {
                    "config": {
                        "path": str(args.config),
                        "iterations": iterations_cfg,
                        "requirements_chunk_size": cfg.get("requirements_chunk_size", 5),
                        "use_ontology_context": bool(ontology_context_path),
                        "ontology_context_path": str(ontology_context_path) if ontology_context_path else None,
                        "gold_path": str(gold_path),
                        "prompt_mode": prompt_mode,
                        "validation": cfg.get("validation", True),
                        "reasoning": cfg.get("reasoning", True),
                        "stop_policy": policy,
                    },
                    "iterations": {},
                    "stop": {"iteration": 0, "reason": "draft_parse_error", "error": str(exc)},
                }
                (output_root / "repair_log.json").write_text(json.dumps(repair_log, indent=2), encoding="utf-8")
                print(f"[{policy}] Aborted at draft due to Turtle parse error. See {iter_dir / 'llm_error.txt'}")
                return

        assembler.serialize(state, iter_dir / "pred.ttl")

        repair_log: dict = {
            "config": {
                "path": str(args.config),
                "iterations": iterations_cfg,
                "requirements_chunk_size": cfg.get("requirements_chunk_size", 5),
                "use_ontology_context": bool(ontology_context_path),
                "ontology_context_path": str(ontology_context_path) if ontology_context_path else None,
                "gold_path": str(gold_path),
                "prompt_mode": prompt_mode,
                "validation": cfg.get("validation", True),
                "reasoning": cfg.get("reasoning", True),
                "stop_policy": policy,
            },
            "iterations": {},
        }
        previous_patches = None
        current_iter = 0
        cq_pass_rate = 0.0

        while True:
            reasoning_result = reasoner.run(state.graph)
            if cfg.get("validation", True):
                if validator is None:
                    raise RuntimeError("Validation enabled but SHACL validator is not configured.")
                shacl_report = validator.validate(reasoning_result.expanded_graph)
                summary = summarize_shacl_report(shacl_report)
                save_shacl_report(shacl_report, iter_dir / "shacl_report.ttl")
                patches = shacl_report_to_patches(shacl_report)
                save_patch_plan(patches, iter_dir / "patches.json")
            else:
                shacl_report = None
                summary = {"total": 0, "violations": {"hard": 0, "soft": 0}}
                patches = []

            cq_results = cq_runner.run(reasoning_result.expanded_graph) if cq_runner else []
            cq_pass_rate = (sum(1 for res in cq_results if res.success) / len(cq_results)) if cq_results else 0.0

            cq_payload = {
                "pass_rate": cq_pass_rate,
                "results": [
                    {"query": result.query, "success": result.success, "message": result.message}
                    for result in cq_results
                ],
            }
            (iter_dir / "cq_results.json").write_text(json.dumps(cq_payload, indent=2), encoding="utf-8")

            if not cfg.get("validation", True):
                stop_decision = StopDecision(True, "validation_disabled")
            else:
                stop_decision = should_stop(
                    iteration=current_iter,
                    max_iterations=iterations_cfg,
                    patches=patches,
                    previous_patches=previous_patches,
                    shacl_report=shacl_report,
                    cq_pass_rate=cq_pass_rate,
                    cq_threshold=args.cq_threshold,
                    stop_policy=policy,
                )

            repair_log["iterations"][f"iter{current_iter}"] = {
                "shacl": summary,
                "cq": {
                    "pass_rate": cq_pass_rate,
                    "failed": len([r for r in cq_results if not r.success]),
                    "failed_queries": [r.query for r in cq_results if not r.success] if cq_results else [],
                },
                "patches": {
                    "count": len(patches),
                    "types": {k: v for k, v in _count_patch_types(patches).items() if v > 0},
                },
                "reasoning": {
                    "enabled": reasoning_result.report.enabled,
                    "consistent": reasoning_result.report.consistent,
                    "unsat_classes": len(reasoning_result.report.unsatisfiable_classes),
                    "notes": reasoning_result.report.notes,
                    "backend": reasoning_result.report.backend,
                    "triples_before_reasoning": len(state.graph),
                    "triples_after_reasoning": len(reasoning_result.expanded_graph),
                },
                "stop_decision": stop_decision.reason,
            }

            if stop_decision.stop:
                break

            previous_patches = patches
            next_iter = current_iter + 1
            next_dir = output_root / f"iter{next_iter}"
            ensure_dir(next_dir)

            context_ttl = state.graph.serialize(format="turtle")
            patch_response = llm.apply_patches([p.to_dict() for p in patches], context_ttl)

            next_state = assembler.bootstrap()
            assembler.add_turtle(next_state, context_ttl)
            try:
                assembler.add_turtle(next_state, patch_response.turtle)
            except ValueError as exc:
                (next_dir / "llm_error.txt").write_text(
                    "Patch application failed to parse LLM Turtle.\n"
                    f"Reason: {exc}\n\nRaw turtle:\n{patch_response.turtle}",
                    encoding="utf-8",
                )
                repair_log["iterations"][f"iter{next_iter}"] = {
                    "shacl": {"total": 0, "violations": {"hard": 0, "soft": 0}},
                    "cq": {"pass_rate": 0.0, "failed": 0, "failed_queries": []},
                    "patches": {"count": 0, "types": {}},
                    "reasoning": {"enabled": False, "consistent": False, "unsat_classes": 0, "notes": "parse_error"},
                    "stop_decision": "patch_parse_error",
                }
                repair_log["stop"] = {"iteration": next_iter, "reason": "patch_parse_error", "error": str(exc)}
                (output_root / "repair_log.json").write_text(json.dumps(repair_log, indent=2), encoding="utf-8")
                print(f"[{policy}] Aborted at iter{next_iter} due to Turtle parse error. See {next_dir / 'llm_error.txt'}")
                return
            state = next_state
            assembler.serialize(state, next_dir / "pred.ttl")

            iter_dir = next_dir
            current_iter = next_iter

        repair_log["stop"] = {"iteration": current_iter, "reason": stop_decision.reason}

        final_dir = output_root / "final"
        ensure_dir(final_dir)
        assembler.serialize(state, final_dir / "pred.ttl")

        gold_graph = Graph().parse(gold_path)
        metrics_payload = final_metrics(reasoning_result.expanded_graph, gold_graph)
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

        print(f"[{policy}] E4 run complete. Outputs written to {output_root}")

    for policy in stop_policies:
        policy_output_root = output_root_base
        if len(stop_policies) > 1:
            policy_output_root = output_root_base / policy
        ensure_dir(policy_output_root)
        run_single(policy, policy_output_root)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Command-line entry point for the OG-NSD pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root (containing the ``og_nsd`` package) is on ``sys.path``
# so the script can be executed directly without an editable install.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from og_nsd import OntologyDraftingPipeline, PipelineConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the OG-NSD ontology drafting pipeline")
    parser.add_argument("--requirements", type=Path, required=True, help="Path to JSON/JSONL requirements file")
    parser.add_argument("--shapes", type=Path, required=True, help="Path to SHACL shapes file")
    parser.add_argument("--output", type=Path, required=True, help="Where to write the generated ontology (TTL)")
    parser.add_argument("--base", type=Path, help="Optional bootstrap ontology for grounding")
    parser.add_argument("--cqs", type=Path, help="Optional SPARQL ASK queries for competency evaluation")
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    parser.add_argument("--llm-mode", choices=["heuristic", "openai"], default="heuristic")
    parser.add_argument(
        "--use-ontology-context",
        action="store_true",
        help="Enable ontology-aware prompting by extracting schema from the gold ontology",
    )
    parser.add_argument(
        "--context-ontology",
        type=Path,
        help="Optional path to an ontology used solely for schema extraction (defaults to --base)",
    )
    parser.add_argument("--max-reqs", type=int, default=20, help="Maximum number of requirements to process")
    parser.add_argument("--reasoning", action="store_true", help="Enable owlready2 reasoning (requires Pellet)")
    parser.add_argument("--iterations", type=int, default=2, help="Maximum repair iterations")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM sampling temperature")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PipelineConfig(
        requirements_path=args.requirements,
        shapes_path=args.shapes,
        base_ontology_path=args.base,
        competency_questions_path=args.cqs,
        output_path=args.output,
        report_path=args.report,
        llm_mode=args.llm_mode,
        use_ontology_context=args.use_ontology_context,
        ontology_context_path=args.context_ontology,
        max_requirements=args.max_reqs,
        reasoning_enabled=args.reasoning,
        max_iterations=args.iterations,
        llm_temperature=args.temperature,
    )
    pipeline = OntologyDraftingPipeline(config)
    report = pipeline.run()
    print("Pipeline complete. Summary:")
    for key, value in report.items():
        print(f"- {key}: {value if not isinstance(value, dict) else ''}")


if __name__ == "__main__":
    main()

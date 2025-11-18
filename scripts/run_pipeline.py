#!/usr/bin/env python3
"""Command-line entry point for the OG-NSD pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path

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
    parser.add_argument("--max-reqs", type=int, default=20, help="Maximum number of requirements to process")
    parser.add_argument("--reasoning", action="store_true", help="Enable owlready2 reasoning (requires Pellet)")
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
        max_requirements=args.max_reqs,
        reasoning_enabled=args.reasoning,
    )
    pipeline = OntologyDraftingPipeline(config)
    report = pipeline.run()
    print("Pipeline complete. Summary:")
    for key, value in report.items():
        print(f"- {key}: {value if not isinstance(value, dict) else ''}")


if __name__ == "__main__":
    main()

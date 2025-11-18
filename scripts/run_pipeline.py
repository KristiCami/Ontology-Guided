"""Command-line entry-point for the OG-NSD pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path

from og_nsd.config import LLMConfig, PipelineConfig, ValidationConfig
from og_nsd.pipeline import OntologyDraftingPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the OG-NSD pipeline")
    parser.add_argument(
        "requirements",
        type=Path,
        help="Path to the JSONL file that stores annotated requirements.",
    )
    parser.add_argument(
        "--shapes",
        type=Path,
        default=Path("gold/shapes_atm.ttl"),
        help="Path to the SHACL shapes file used for validation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts"),
        help="Directory where the ontology and reports will be saved.",
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="http://example.com/atm#",
        help="Base namespace used when emitting Turtle prefixes.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=2,
        help="Maximum number of repair iterations per requirement.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="template",
        help="LLM backend to use (template or OpenAI model name).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for OpenAI models.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = OntologyDraftingPipeline(
        pipeline_config=PipelineConfig(
            namespace=args.namespace,
            output_dir=args.output,
            iterations=args.iterations,
        ),
        llm_config=LLMConfig(
            model=args.model,
            temperature=args.temperature,
        ),
        validation_config=ValidationConfig(shacl_shapes=args.shapes),
    )
    output_path = pipeline.run(args.requirements)
    print(f"Ontology written to {output_path}")


if __name__ == "__main__":
    main()

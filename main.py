"""Executable example of the ontology drafting pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path

from ontology_pipeline.llm_interface import MockLLMClient
from ontology_pipeline.pipeline import OntologyDraftingPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ontology drafting demo pipeline")
    parser.add_argument("requirement_file", type=Path, help="Path to the requirement text file")
    parser.add_argument(
        "--shacl",
        type=Path,
        default=Path("shacl/atm_shapes.ttl"),
        help="SHACL shapes file used for validation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    requirement_text = args.requirement_file.read_text().strip()
    pipeline = OntologyDraftingPipeline(llm_client=MockLLMClient(), shacl_graph_path=args.shacl)
    result = pipeline.run(requirement_text)

    print(f"Requirement: {result.requirement}")
    print(f"Iterations: {result.iterations}")
    print(f"SHACL conforms: {result.validation.conforms}")
    if result.validation.issues:
        print("Issues detected:")
        for issue in result.validation.issues:
            print(f"- {issue.message} [{issue.result_path}] {issue.focus_node}")

    print("\nGenerated graph (Turtle):")
    print(result.graph.serialize(format="turtle"))


if __name__ == "__main__":
    main()

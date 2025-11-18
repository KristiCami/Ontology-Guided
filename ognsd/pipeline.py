"""Command-line entry point for the OG-NSD pipeline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from .drafters import draft_all
from .ontology import OntologyBuilder
from .requirements import load_requirements
from .validator import OntologyValidator


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ontology-guided drafting pipeline")
    parser.add_argument("--requirements", type=Path, required=True, help="Path to requirements JSON fragments")
    parser.add_argument("--output", type=Path, required=True, help="Destination TTL file for the drafted ontology")
    parser.add_argument("--shapes", type=Path, default=None, help="Optional SHACL shapes for validation")
    parser.add_argument("--cqs", type=Path, default=None, help="Optional SPARQL ASK competency questions")
    parser.add_argument("--bootstrap", type=Path, nargs="*", default=None, help="Optional ontologies to append before drafting")
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON report destination")
    return parser.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> dict:
    requirements = load_requirements(args.requirements)
    builder = OntologyBuilder(bootstrap_files=args.bootstrap)
    builder, stats = draft_all(builder, requirements)

    output_text = builder.to_turtle()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output_text, encoding="utf-8")

    validator = OntologyValidator(builder, shapes_path=args.shapes, cq_path=args.cqs)
    shacl = validator.run_shacl()
    cq = validator.run_competency_questions()
    reasoning = validator.run_reasoner()

    report = {
        "drafting": {
            "requirements": stats.requirements,
            "classes": stats.classes,
            "relations": stats.relations,
        },
        "output": str(args.output),
        "shacl": {
            "conforms": shacl.conforms,
            "violations": shacl.violations,
        },
        "competency_questions": {
            "total": cq.total,
            "passed": cq.passed,
            "failed": cq.failed_descriptions,
        },
        "reasoning": {
            "inferred_relations": reasoning.inferred_relations,
            "total_relations": reasoning.total_relations,
        },
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main(argv: List[str] | None = None) -> None:
    args = _parse_args(argv)
    report = run_pipeline(args)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()

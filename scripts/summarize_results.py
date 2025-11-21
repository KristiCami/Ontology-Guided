#!/usr/bin/env python3
"""Produce markdown table rows for extraction and SHACL metrics."""
from __future__ import annotations

import argparse
from pathlib import Path

# Ensure project root is on path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from og_nsd.evaluation import (  # pylint: disable=wrong-import-position
    compute_extraction_metrics,
    format_markdown_row,
    format_shacl_row,
    summarize_shacl_iterations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize OG-NSD experiment outputs")
    parser.add_argument("--generated", type=Path, required=True, help="Generated ontology (TTL) from a run")
    parser.add_argument("--gold", type=Path, required=True, help="Gold ontology (TTL) to compare against")
    parser.add_argument("--report", type=Path, required=True, help="JSON report emitted by scripts/run_pipeline.py")
    parser.add_argument("--label", required=True, help="Label to use in markdown rows (e.g., 'Ours (full)')")
    parser.add_argument(
        "--section",
        choices=["both", "extraction", "shacl"],
        default="both",
        help="Which table rows to emit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.section in {"both", "extraction"}:
        extraction = compute_extraction_metrics(args.gold, args.generated)
        print("Extraction quality (micro-average) → paste into Table I:")
        print(format_markdown_row(args.label, extraction.micro))
        print()
        print("Per-type details:")
        for key, metrics in extraction.per_type.items():
            print(f"- {key}: P={metrics.precision:.2f}, R={metrics.recall:.2f}, F1={metrics.f1:.2f}")
        print(f"Macro-average: P={extraction.macro.precision:.2f}, "
              f"R={extraction.macro.recall:.2f}, F1={extraction.macro.f1:.2f}")

    if args.section in {"both", "shacl"}:
        summary = summarize_shacl_iterations(args.report)
        print("\nSHACL compliance → paste into Table II:")
        print(format_shacl_row(args.label, summary))


if __name__ == "__main__":
    main()

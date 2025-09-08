"""Example usage of :func:`aggregate_repair_efficiency`.

This script loads sample repair statistics from ``evaluation/repair_samples``
and prints the distribution of iterations to first conformance together with
the mean iteration count.  It is intended as a minimal demonstration of how
repair efficiency metrics can be aggregated across multiple cases.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys

# Ensure project root is on ``sys.path`` when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.repair_efficiency import aggregate_repair_efficiency


def main() -> None:
    base = Path(__file__).resolve().parent / "repair_samples"
    stats = []
    for path in sorted(base.glob("*.json")):
        with path.open("r", encoding="utf8") as fh:
            stats.append(json.load(fh))
    efficiency = aggregate_repair_efficiency(stats)
    print(f"Distribution: {efficiency.distribution}")
    print(f"Mean iterations: {efficiency.mean_iterations:.2f}")


if __name__ == "__main__":
    main()

"""Utilities to analyze repair loop efficiency.

This module provides helpers for aggregating statistics collected from the
ontology repair loop. Each item in the ``violation_stats`` list represents the
per–case statistics returned by :mod:`ontology_guided.repair_loop`.

The core function :func:`aggregate_repair_efficiency` derives a number of
aggregated metrics:

* iterations to first conformance
* mean number of iterations across cases
* distribution of first-conformance iterations (1, 2, 3, and >3)
* optional metrics about prompt usage, if present in the input data

The module can also be executed as ``python -m evaluation.repair_efficiency`` to
collect one or more JSON files containing per-case statistics and print the
aggregated metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

Distribution = Dict[str, int]


@dataclass
class RepairEfficiency:
    """Container for aggregated repair metrics."""

    case_count: int
    mean_iterations: float
    mean_first_conformance: Optional[float]
    distribution: Distribution
    avg_prompts_per_iteration: Optional[float] = None
    success_rate_per_prompt: Optional[float] = None

    def asdict(self) -> Dict[str, Any]:
        """Return a dictionary representation useful for JSON serialisation."""
        data = {
            "case_count": self.case_count,
            "mean_iterations": self.mean_iterations,
            "mean_first_conformance": self.mean_first_conformance,
            "distribution": self.distribution,
        }
        if self.avg_prompts_per_iteration is not None:
            data["avg_prompts_per_iteration"] = self.avg_prompts_per_iteration
        if self.success_rate_per_prompt is not None:
            data["success_rate_per_prompt"] = self.success_rate_per_prompt
        return data


def _bucket_first_conformance(first: Optional[int]) -> str:
    """Return the distribution bucket label for ``first`` iteration."""
    if first is None or first > 3:
        return ">3"
    if first <= 1:
        return "1"
    return str(first)


def aggregate_repair_efficiency(violation_stats: Iterable[Dict[str, Any]]) -> RepairEfficiency:
    """Aggregate repair efficiency metrics from ``violation_stats``.

    Parameters
    ----------
    violation_stats:
        Iterable of dictionaries, one for each evaluated case. Each dictionary
        should at least contain ``iterations`` and ``first_conforms_iteration``
        keys. Additional prompt-related keys are optional and used when
        available.

    Returns
    -------
    RepairEfficiency
        An object holding aggregated metrics.
    """

    iterations: List[int] = []
    firsts: List[int] = []
    distribution: Distribution = {"1": 0, "2": 0, "3": 0, ">3": 0}
    prompts_per_iteration: List[float] = []
    prompt_success_rates: List[float] = []

    for stats in violation_stats:
        iter_count = int(stats.get("iterations", 0))
        iterations.append(iter_count)

        first = stats.get("first_conforms_iteration")
        if isinstance(first, int):
            firsts.append(first)
        bucket = _bucket_first_conformance(first if isinstance(first, int) else None)
        distribution[bucket] += 1

        # Optional prompt metrics
        total_prompts: Optional[int] = None
        total_success: Optional[int] = None

        if isinstance(stats.get("prompt_count"), int):
            total_prompts = stats["prompt_count"]
        elif isinstance(stats.get("total_prompts"), int):
            total_prompts = stats["total_prompts"]

        if isinstance(stats.get("prompt_successes"), int):
            total_success = stats["prompt_successes"]
        elif isinstance(stats.get("successful_prompts"), int):
            total_success = stats["successful_prompts"]

        per_iter = stats.get("per_iteration")
        if isinstance(per_iter, list):
            prompt_counts: List[int] = []
            success_counts: List[int] = []
            for entry in per_iter:
                if not isinstance(entry, dict):
                    continue
                pc = entry.get("prompt_count") or entry.get("prompts")
                if isinstance(pc, int):
                    prompt_counts.append(pc)
                sc = entry.get("prompt_successes") or entry.get("successful_prompts")
                if isinstance(sc, int):
                    success_counts.append(sc)
            if prompt_counts:
                total_prompts = sum(prompt_counts)
            if success_counts:
                total_success = sum(success_counts)

        if total_prompts is not None and iter_count > 0:
            prompts_per_iteration.append(total_prompts / iter_count)
        if total_prompts:
            if total_success is not None:
                prompt_success_rates.append(total_success / total_prompts)

    mean_iterations = mean(iterations) if iterations else 0.0
    mean_first = mean(firsts) if firsts else None

    avg_prompts = mean(prompts_per_iteration) if prompts_per_iteration else None
    success_rate = mean(prompt_success_rates) if prompt_success_rates else None

    return RepairEfficiency(
        case_count=len(iterations),
        mean_iterations=mean_iterations,
        mean_first_conformance=mean_first,
        distribution=distribution,
        avg_prompts_per_iteration=avg_prompts,
        success_rate_per_prompt=success_rate,
    )


def _load_violation_stats(path: Path) -> Dict[str, Any]:
    """Load violation statistics from ``path``.

    The JSON file may either contain the raw statistics dictionary or an object
    with a ``violation_stats`` field.
    """

    with path.open("r", encoding="utf8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "violation_stats" in data:
        stats = data["violation_stats"]
        if not isinstance(stats, dict):
            raise ValueError(f"'violation_stats' in {path} is not a dict")
        return stats
    if not isinstance(data, dict):
        raise ValueError(f"JSON root of {path} must be a dict")
    return data


def main(argv: Optional[List[str]] = None) -> int:
    """Command line entry point."""

    parser = argparse.ArgumentParser(description="Aggregate repair efficiency metrics")
    parser.add_argument("stats", nargs="+", type=Path, help="JSON files with per-case stats")
    parser.add_argument("--json", action="store_true", help="output metrics as JSON")
    args = parser.parse_args(argv)

    stats = [_load_violation_stats(p) for p in args.stats]
    efficiency = aggregate_repair_efficiency(stats)

    if args.json:
        print(json.dumps(efficiency.asdict(), indent=2, sort_keys=True))
    else:
        data = efficiency.asdict()
        for key, value in data.items():
            print(f"{key}: {value}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

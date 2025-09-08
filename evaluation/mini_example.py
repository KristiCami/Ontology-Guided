
from pathlib import Path
import sys

# Ensure project root is on sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rdflib import Graph
from evaluation.axiom_metrics import evaluate_axioms
from evaluation.competency_questions import evaluate_cqs
from ontology_guided.validator import SHACLValidator
from ontology_guided.reasoner import run_reasoner, ReasonerError
from evaluation.repair_efficiency import aggregate_repair_efficiency


def main() -> None:
    base = Path(__file__).resolve().parent
    gold_path = base / "mini_gold.ttl"
    gold_graph = Graph()
    gold_graph.parse(gold_path, format="turtle")
    shapes_path = base / "mini_shapes.ttl"
    cq_path = base / "mini_cqs.rq"

    # store violation counts and per-iteration stats
    violation_counts = []
    per_iter_stats = []

    # iterate through predicted files in order
    for idx in range(3):
        pred_path = base / f"mini_pred_iter{idx}.ttl"
        pred_graph = Graph()
        pred_graph.parse(pred_path, format="turtle")

        # run SHACL validation and record violations
        validator = SHACLValidator(str(pred_path), str(shapes_path))
        conforms, _, summary = validator.run_validation()
        violations = summary.get("total", 0)
        violation_counts.append(violations)
        per_iter_stats.append({"iteration": idx, "total": violations})

        try:
            _, is_consistent, unsat_classes = run_reasoner(str(pred_path))
        except Exception as exc:
            is_consistent = False
            unsat_classes = []
            print(f"  Reasoner error: {exc}")

        metrics = evaluate_axioms(pred_graph, gold_graph)
        subclass = metrics["per_type"].get("SubClassOf", {})
        range_metrics = metrics["per_type"].get("Range", {})
        cq_results = evaluate_cqs(pred_path, cq_path)

        print(f"Iteration {idx}")
        print(
            "  SubClassOf: "
            f"P={subclass.get('precision', 0.0):.3f} "
            f"R={subclass.get('recall', 0.0):.3f} "
            f"F1={subclass.get('f1', 0.0):.3f}"
        )
        print(
            "  Range:      "
            f"P={range_metrics.get('precision', 0.0):.3f} "
            f"R={range_metrics.get('recall', 0.0):.3f} "
            f"F1={range_metrics.get('f1', 0.0):.3f}"
        )
        print(f"  Violations: {violations} (conforms={conforms})")
        print(f"  Consistent: {is_consistent}")
        if unsat_classes:
            print("  Unsatisfiable classes:")
            for cls in unsat_classes:
                print(f"    - {cls}")
        else:
            print("  Unsatisfiable classes: none")
        print(
            f"  CQs: {cq_results['passed']}/{cq_results['total']} "
            f"({cq_results['pass_rate'] * 100:.1f}%) passed"
        )

    # report violation reduction across iterations
    print("\nViolation counts (pre -> post repair):")
    first_conform = None
    for idx in range(len(violation_counts) - 1):
        pre = violation_counts[idx]
        post = violation_counts[idx + 1]
        print(f"Iteration {idx}: {pre} -> {post}")
        if post == 0 and first_conform is None:
            first_conform = idx + 1

    if first_conform is not None:
        print(f"Conformance achieved at iteration {first_conform}")
    else:
        # check final iteration in case loop above didn't capture
        if violation_counts and violation_counts[-1] == 0:
            first_conform = len(violation_counts) - 1
            print(f"Conformance achieved at iteration {first_conform}")
        else:
            print("Conformance not achieved")

    # aggregate repair efficiency metrics
    violation_stats = {
        "iterations": len(violation_counts),
        "first_conforms_iteration": first_conform,
        "per_iteration": per_iter_stats,
    }
    efficiency = aggregate_repair_efficiency([violation_stats])
    print("\nAggregated repair efficiency:")
    print(f"  Distribution: {efficiency.distribution}")
    print(f"  Average iterations: {efficiency.mean_iterations:.2f}")


if __name__ == "__main__":
    main()

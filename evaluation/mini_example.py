from pathlib import Path
import sys

# Ensure project root is on sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rdflib import Graph
from evaluation.axiom_metrics import evaluate_axioms
from ontology_guided.validator import SHACLValidator


def main() -> None:
    base = Path(__file__).resolve().parent
    gold_path = base / "mini_gold.ttl"
    gold_graph = Graph()
    gold_graph.parse(gold_path, format="turtle")
    shapes_path = base / "mini_shapes.ttl"

    # store violation counts for each iteration
    violation_counts = []

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

        metrics = evaluate_axioms(pred_graph, gold_graph)
        subclass = metrics["per_type"].get("SubClassOf", {})
        range_metrics = metrics["per_type"].get("Range", {})

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
            print(f"Conformance achieved at iteration {len(violation_counts) - 1}")
        else:
            print("Conformance not achieved")


if __name__ == "__main__":
    main()

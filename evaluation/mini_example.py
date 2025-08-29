from pathlib import Path
import sys

# Ensure project root is on sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rdflib import Graph
from evaluation.axiom_metrics import evaluate_axioms


def main() -> None:
    base = Path(__file__).resolve().parent
    gold_path = base / "mini_gold.ttl"
    gold_graph = Graph()
    gold_graph.parse(gold_path, format="turtle")

    # iterate through predicted files in order
    for idx in range(3):
        pred_path = base / f"mini_pred_iter{idx}.ttl"
        pred_graph = Graph()
        pred_graph.parse(pred_path, format="turtle")

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


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
import sys

# Ensure project root is on sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rdflib import Graph, Namespace, RDFS
from evaluation.axiom_metrics import evaluate_axioms


def main() -> None:
    ex = Namespace("http://example.com/")

    gold = Graph()
    gold.add((ex.hasPet, RDFS.domain, ex.Person))
    gold.add((ex.drives, RDFS.domain, ex.Person))
    gold.add((ex.hasPet, RDFS.range, ex.Animal))
    gold.add((ex.drives, RDFS.range, ex.Vehicle))

    pred = Graph()
    pred.add((ex.hasPet, RDFS.domain, ex.Person))
    pred.add((ex.owns, RDFS.domain, ex.Company))
    pred.add((ex.hasPet, RDFS.range, ex.Animal))
    pred.add((ex.drives, RDFS.range, ex.Person))

    metrics = evaluate_axioms(pred, gold)
    domain = metrics["per_type"]["Domain"]
    range_ = metrics["per_type"]["Range"]
    print(
        "Domain P={:.2f} R={:.2f} F1={:.2f}".format(
            domain["precision"], domain["recall"], domain["f1"]
        )
    )
    print(
        "Range  P={:.2f} R={:.2f} F1={:.2f}".format(
            range_["precision"], range_["recall"], range_["f1"]
        )
    )


if __name__ == "__main__":
    main()

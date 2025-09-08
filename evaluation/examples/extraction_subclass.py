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
    gold.add((ex.Cat, RDFS.subClassOf, ex.Animal))
    gold.add((ex.Dog, RDFS.subClassOf, ex.Animal))
    gold.add((ex.Wolf, RDFS.subClassOf, ex.Animal))
    gold.add((ex.Car, RDFS.subClassOf, ex.Vehicle))
    gold.add((ex.Bicycle, RDFS.subClassOf, ex.Vehicle))

    pred = Graph()
    pred.add((ex.Cat, RDFS.subClassOf, ex.Animal))
    pred.add((ex.Dog, RDFS.subClassOf, ex.Animal))
    pred.add((ex.Car, RDFS.subClassOf, ex.Vehicle))
    pred.add((ex.Wolf, RDFS.subClassOf, ex.Mammal))
    pred.add((ex.Boat, RDFS.subClassOf, ex.Vehicle))

    metrics = evaluate_axioms(pred, gold)
    m = metrics["per_type"]["SubClassOf"]
    print(f"P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}")


if __name__ == "__main__":
    main()

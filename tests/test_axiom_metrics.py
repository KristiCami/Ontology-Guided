import pytest
from rdflib import Graph

from evaluation.axiom_metrics import evaluate_axioms


def _graph_with_equiv() -> Graph:
    g = Graph()
    g.parse(
        data=(
            "@prefix : <http://example.com/> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            ":A owl:equivalentClass :B ."
        ),
        format="turtle",
    )
    return g


def test_equivalent_classes_bucket():
    g_pred = _graph_with_equiv()
    g_gold = _graph_with_equiv()
    metrics = evaluate_axioms(g_pred, g_gold)
    eq = metrics["per_type"]["EquivalentClasses"]
    assert eq["precision"] == pytest.approx(1.0)
    assert eq["recall"] == pytest.approx(1.0)
    # SubClassOf should have no entries
    assert metrics["per_type"]["SubClassOf"]["precision"] == pytest.approx(0.0)


def test_equivalent_classes_as_subclass():
    g_pred = _graph_with_equiv()
    g_gold = _graph_with_equiv()
    metrics = evaluate_axioms(g_pred, g_gold, equiv_as_subclass=True)
    assert "EquivalentClasses" not in metrics["per_type"]
    sub = metrics["per_type"]["SubClassOf"]
    assert sub["precision"] == pytest.approx(1.0)
    assert sub["recall"] == pytest.approx(1.0)


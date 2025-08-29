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


def test_domain_and_range_metrics():
    g_pred = Graph()
    g_pred.parse(
        data=(
            "@prefix : <http://example.com/> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            ":p a owl:ObjectProperty ;\n"
            "    rdfs:domain :A ;\n"
            "    rdfs:range :B ."
        ),
        format="turtle",
    )

    g_gold = Graph()
    g_gold.parse(
        data=(
            "@prefix : <http://example.com/> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            ":p a owl:ObjectProperty ;\n"
            "    rdfs:domain :A ;\n"
            "    rdfs:range :C ."
        ),
        format="turtle",
    )

    metrics = evaluate_axioms(g_pred, g_gold)
    dom = metrics["per_type"]["Domain"]
    rng = metrics["per_type"]["Range"]

    assert dom["precision"] == pytest.approx(1.0)
    assert dom["recall"] == pytest.approx(1.0)
    assert rng["precision"] == pytest.approx(0.0)
    assert rng["recall"] == pytest.approx(0.0)

    # macro-F1 should include Domain and Range axiom types
    expected_macro = (1 + 1) / 7  # two types with F1=1 out of seven
    assert metrics["macro_f1"] == pytest.approx(expected_macro)


def test_all_axiom_type_metrics():
    """Ensure every axiom type is scored correctly."""
    pred_ttl = (
        "@prefix : <http://example.com/> .\n"
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        ":A a owl:Class .\n"
        ":C a owl:Class .\n"
        ":p1 a owl:ObjectProperty ;\n"
        "    rdfs:domain :A ;\n"
        "    rdfs:range :B .\n"
        ":d1 a owl:DatatypeProperty .\n"
        ":A rdfs:subClassOf :B .\n"
        ":B owl:equivalentClass :C .\n"
    )
    gold_ttl = (
        "@prefix : <http://example.com/> .\n"
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        ":A a owl:Class .\n"
        ":B a owl:Class .\n"
        ":p1 a owl:ObjectProperty ;\n"
        "    rdfs:domain :A ;\n"
        "    rdfs:range :C .\n"
        ":p2 a owl:ObjectProperty ;\n"
        "    rdfs:domain :B ;\n"
        "    rdfs:range :C .\n"
        ":d2 a owl:DatatypeProperty .\n"
        ":A rdfs:subClassOf :B .\n"
        ":C rdfs:subClassOf :A .\n"
        ":B owl:equivalentClass :C .\n"
        ":A owl:equivalentClass :C .\n"
    )
    g_pred = Graph()
    g_pred.parse(data=pred_ttl, format="turtle")
    g_gold = Graph()
    g_gold.parse(data=gold_ttl, format="turtle")

    metrics = evaluate_axioms(g_pred, g_gold, micro=True)

    expected = {
        "Classes": {"precision": 0.5, "recall": 0.5, "f1": 0.5},
        "ObjectProperty": {"precision": 1.0, "recall": 0.5, "f1": 2 / 3},
        "DatatypeProperty": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        "SubClassOf": {"precision": 1.0, "recall": 0.5, "f1": 2 / 3},
        "Domain": {"precision": 1.0, "recall": 0.5, "f1": 2 / 3},
        "Range": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        "EquivalentClasses": {"precision": 1.0, "recall": 0.5, "f1": 2 / 3},
    }

    for axiom_type, vals in expected.items():
        result = metrics["per_type"][axiom_type]
        assert result["precision"] == pytest.approx(vals["precision"])
        assert result["recall"] == pytest.approx(vals["recall"])
        assert result["f1"] == pytest.approx(vals["f1"])

    macro = sum(v["f1"] for v in expected.values()) / len(expected)
    assert metrics["macro_f1"] == pytest.approx(macro)
    assert metrics["micro_precision"] == pytest.approx(5 / 8)
    assert metrics["micro_recall"] == pytest.approx(5 / 13)
    micro_f1 = (2 * (5 / 8) * (5 / 13)) / ((5 / 8) + (5 / 13))
    assert metrics["micro_f1"] == pytest.approx(micro_f1)


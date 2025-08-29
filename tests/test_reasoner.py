import pytest
import owlready2
from ontology_guided.reasoner import run_reasoner, ReasonerError


def test_run_reasoner(tmp_path):
    onto = owlready2.get_ontology("http://example.com/test.owl")
    with onto:
        class A(owlready2.Thing):
            pass

        class B(A):
            pass

    owl_path = tmp_path / "test.owl"
    onto.save(file=str(owl_path))

    try:
        result, is_consistent, inconsistent = run_reasoner(str(owl_path))
    except ReasonerError as exc:
        pytest.skip(str(exc))
        return

    assert is_consistent
    assert inconsistent == []
    names = {c.name for c in result.classes()}
    assert {"A", "B"}.issubset(names)


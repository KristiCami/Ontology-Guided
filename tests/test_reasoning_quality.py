import pytest
import owlready2
from ontology_guided.reasoner import run_reasoner, ReasonerError
from ontology_guided.repair_loop import RepairLoop
import ontology_guided.repair_loop as repair_loop
from ontology_guided.llm_interface import LLMInterface


def test_reasoning_quality(monkeypatch, tmp_path):
    onto = owlready2.get_ontology("http://example.com/test.owl")
    with onto:
        class Customer(owlready2.Thing):
            pass
        class VIPCustomer(Customer):
            pass
        class NonCustomer(owlready2.Thing):
            pass
    NonCustomer.is_a.append(owlready2.Not(Customer))
    VIPCustomer.is_a.append(NonCustomer)

    owl_path = tmp_path / "orig.owl"
    onto.save(file=str(owl_path))

    try:
        _, is_consistent, unsat = run_reasoner(str(owl_path))
    except ReasonerError as exc:
        pytest.skip(str(exc))
    unsat = [u for u in unsat if not u.endswith("owl#Nothing")]
    assert is_consistent
    assert unsat == ["http://example.com/test.owl#VIPCustomer"]

    VIPCustomer.is_a.remove(NonCustomer)
    if owlready2.Nothing in VIPCustomer.equivalent_to:
        VIPCustomer.equivalent_to.remove(owlready2.Nothing)
    fixed_path = tmp_path / "fixed.owl"
    onto.save(file=str(fixed_path))
    _, is_consistent2, unsat2 = run_reasoner(str(fixed_path))
    unsat2 = [u for u in unsat2 if not u.endswith("owl#Nothing")]
    assert is_consistent2
    assert unsat2 == []

    ttl_data = """
    @prefix ex: <http://example.com/test#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    ex:Customer a owl:Class .
    ex:VIPCustomer a owl:Class ; rdfs:subClassOf ex:Customer .
    ex:NonCustomer a owl:Class ; rdfs:subClassOf [ a owl:Class ; owl:complementOf ex:Customer ] .
    ex:VIPCustomer rdfs:subClassOf ex:NonCustomer .
    """
    data_path = tmp_path / "data.ttl"
    shapes_path = tmp_path / "shapes.ttl"
    data_path.write_text(ttl_data, encoding="utf-8")
    shapes_path.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class FakeValidator:
        calls = 0
        def __init__(self, data_path, shapes_path, inference="rdfs"):
            pass
        def run_validation(self):
            FakeValidator.calls += 1
            if FakeValidator.calls == 1:
                return False, [], {"total": 1}
            else:
                return True, [], {"total": 0}
    monkeypatch.setattr(repair_loop, "SHACLValidator", FakeValidator)

    offending = (
        "http://example.com/test#VIPCustomer "
        "http://www.w3.org/2000/01/rdf-schema#subClassOf "
        "http://example.com/test#NonCustomer"
    )
    monkeypatch.setattr(
        repair_loop,
        "synthesize_repair_prompts",
        lambda violations, graph, available_terms, inconsistent, max_triples=50: [
            {
                "prompt": "SYSTEM:\nLOCAL CONTEXT (Turtle):\n\nVIOLATION (canonicalized): v\nSUGGEST PATCH (Turtle only):",
                "offending_axioms": [offending],
                "terms": [],
            }
        ],
    )
    monkeypatch.setattr(
        LLMInterface,
        "generate_owl",
        lambda self, sentences, prompt_template, available_terms=None, base=None, prefix=None: [""],
    )

    calls = {"n": 0}
    def fake_run_reasoner(path):
        calls["n"] += 1
        if calls["n"] == 1:
            return None, True, ["http://example.com/test#VIPCustomer"]
        else:
            return None, True, []
    monkeypatch.setattr(repair_loop, "run_reasoner", fake_run_reasoner)

    repairer = RepairLoop(str(data_path), str(shapes_path), api_key="dummy")
    _, _, _, stats = repairer.run()

    assert stats["per_iteration"][0]["is_consistent"] is True
    assert stats["per_iteration"][0]["unsat_count"] == 1
    assert stats["per_iteration"][1]["is_consistent"] is True
    assert stats["per_iteration"][1]["unsat_count"] == 0

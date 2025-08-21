import ontology_guided.repair_loop as repair_loop
from ontology_guided.repair_loop import RepairLoop
from ontology_guided.llm_interface import LLMInterface
from rdflib import Graph, URIRef


def test_repair_loop_validates_twice(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    data_path = tmp_path / "combined.ttl"
    data_path.write_text("""@prefix atm: <http://example.com/atm#> .\natm:alice a atm:User .""", encoding="utf-8")
    shapes_path = tmp_path / "shapes.ttl"
    shapes_path.write_text("", encoding="utf-8")

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return ["atm:bob a atm:User ."]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    class FakeValidator:
        instances = []
        runs = []

        def __init__(self, data_path, shapes_path, inference="rdfs"):
            self.data_path = data_path
            self.shapes_path = shapes_path
            self.inference = inference
            FakeValidator.instances.append(self)

        def run_validation(self):
            FakeValidator.runs.append(self.data_path)
            if len(FakeValidator.runs) == 1:
                return False, [
                    {
                        "focusNode": "x",
                        "resultPath": "p",
                        "message": "error",
                        "sourceShape": "ex:Shape",
                        "sourceConstraintComponent": "sh:MinCountConstraintComponent",
                        "expected": "1",
                        "value": "0",
                    }
                ]
            return True, []

    monkeypatch.setattr(repair_loop, "SHACLValidator", FakeValidator)

    repairer = RepairLoop(str(data_path), str(shapes_path), api_key="dummy")
    ttl_path, report_path, violations, stats = repairer.run()

    assert len(FakeValidator.runs) == 2
    assert FakeValidator.runs[1].endswith("results/repaired_1.ttl")
    assert ttl_path and ttl_path.endswith("results/repaired_1.ttl")
    assert report_path.endswith("results/report_1.txt")
    assert violations == []
    assert stats == {"initial_count": 1, "final_count": 0, "iterations": 1}

    report0 = tmp_path / "results" / "report_0.txt"
    content = report0.read_text(encoding="utf-8").strip()
    assert (
        content
        == "Shape=ex:Shape, Constraint=sh:MinCountConstraintComponent, Path=p, "
        "Expected=1, Observed=0"
    )


def test_synthesize_repair_prompts_uses_new_template(monkeypatch):
    graph_data = """
        @prefix ex: <http://example.com/> .
        ex:a a ex:A ;
             ex:p ex:b .
    """
    graph = Graph().parse(data=graph_data, format="turtle")

    violations = [
        {
            "focusNode": "http://example.com/a",
            "resultPath": "http://example.com/p",
            "sourceShape": "ex:Shape",
            "sourceConstraintComponent": "sh:MinCountConstraintComponent",
            "expected": "1",
            "value": "0",
        }
    ]
    available_terms = {"classes": [], "properties": []}

    monkeypatch.setattr(
        repair_loop,
        "map_to_ontology_terms",
        lambda available_terms, ctx: (
            ["http://example.com/A"], ["http://example.com/p"]
        ),
    )

    prompts = repair_loop.synthesize_repair_prompts(
        violations, graph, available_terms
    )

    assert len(prompts) == 1
    prompt = prompts[0]
    assert "Use vocabulary: http://example.com/A" in prompt
    assert "http://example.com/p" in prompt
    assert "Terms:" not in prompt


def test_local_context_filters_by_path():
    data = """
        @prefix ex: <http://example.com/> .
        ex:a ex:p ex:b .
        ex:b ex:p ex:c .
        ex:b ex:q ex:d .
    """
    graph = Graph().parse(data=data, format="turtle")

    ctx = repair_loop.local_context(graph, "http://example.com/a", "http://example.com/p")
    ctx_graph = Graph().parse(data=ctx, format="turtle")

    assert (
        URIRef("http://example.com/a"),
        URIRef("http://example.com/p"),
        URIRef("http://example.com/b"),
    ) in ctx_graph
    assert (
        URIRef("http://example.com/b"),
        URIRef("http://example.com/p"),
        URIRef("http://example.com/c"),
    ) in ctx_graph
    assert (
        URIRef("http://example.com/b"),
        URIRef("http://example.com/q"),
        URIRef("http://example.com/d"),
    ) not in ctx_graph

    ctx_all = repair_loop.local_context(graph, "http://example.com/a", None)
    ctx_all_graph = Graph().parse(data=ctx_all, format="turtle")
    assert (
        URIRef("http://example.com/b"),
        URIRef("http://example.com/q"),
        URIRef("http://example.com/d"),
    ) in ctx_all_graph


def test_local_context_handles_inverse_path():
    data = """
        @prefix ex: <http://example.com/> .
        ex:b ex:p ex:a .
        ex:c ex:p ex:b .
        ex:d ex:p ex:c .
    """
    graph = Graph().parse(data=data, format="turtle")

    path = {"inversePath": "http://example.com/p"}
    ctx = repair_loop.local_context(graph, "http://example.com/a", path)
    ctx_graph = Graph().parse(data=ctx, format="turtle")

    assert (
        URIRef("http://example.com/b"),
        URIRef("http://example.com/p"),
        URIRef("http://example.com/a"),
    ) in ctx_graph
    assert (
        URIRef("http://example.com/c"),
        URIRef("http://example.com/p"),
        URIRef("http://example.com/b"),
    ) in ctx_graph
    assert (
        URIRef("http://example.com/d"),
        URIRef("http://example.com/p"),
        URIRef("http://example.com/c"),
    ) not in ctx_graph


def test_local_context_handles_sequence_path():
    data = """
        @prefix ex: <http://example.com/> .
        ex:a ex:p ex:b .
        ex:b ex:q ex:c .
        ex:b ex:r ex:d .
    """
    graph = Graph().parse(data=data, format="turtle")

    path = ["http://example.com/p", "http://example.com/q"]
    ctx = repair_loop.local_context(graph, "http://example.com/a", path)
    ctx_graph = Graph().parse(data=ctx, format="turtle")

    assert (
        URIRef("http://example.com/a"),
        URIRef("http://example.com/p"),
        URIRef("http://example.com/b"),
    ) in ctx_graph
    assert (
        URIRef("http://example.com/b"),
        URIRef("http://example.com/q"),
        URIRef("http://example.com/c"),
    ) in ctx_graph
    assert (
        URIRef("http://example.com/b"),
        URIRef("http://example.com/r"),
        URIRef("http://example.com/d"),
    ) not in ctx_graph

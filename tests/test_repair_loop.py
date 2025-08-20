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
    ttl_path, report_path, violations = repairer.run()

    assert len(FakeValidator.runs) == 2
    assert FakeValidator.runs[1].endswith("results/repaired_1.ttl")
    assert ttl_path and ttl_path.endswith("results/repaired_1.ttl")
    assert report_path.endswith("results/report_1.txt")
    assert violations == []

    report0 = tmp_path / "results" / "report_0.txt"
    content = report0.read_text(encoding="utf-8").strip()
    assert (
        content
        == "Shape=ex:Shape, Constraint=sh:MinCountConstraintComponent, Path=p, "
        "Expected=1, Observed=0"
    )


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

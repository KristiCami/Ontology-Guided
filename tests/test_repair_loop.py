import ontology_guided.repair_loop as repair_loop
from ontology_guided.repair_loop import RepairLoop
import json
from ontology_guided.llm_interface import LLMInterface
from rdflib import Graph, URIRef


def test_repair_loop_validates_twice(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    data_path = tmp_path / "combined.ttl"
    data_path.write_text(
        """@prefix atm: <http://example.com/atm#> .
atm:alice atm:knows atm:bob .""",
        encoding="utf-8",
    )
    shapes_path = tmp_path / "shapes.ttl"
    shapes_path.write_text("", encoding="utf-8")

    def fake_generate_owl(
        self,
        sentences,
        prompt_template,
        available_terms=None,
        base=None,
        prefix=None,
    ):
        return [
            "<http://example.com/atm#alice> <http://example.com/atm#friend> <http://example.com/atm#bob> ."
        ]

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
                        "focusNode": "http://example.com/atm#alice",
                        "resultPath": "http://example.com/atm#knows",
                        "message": "error",
                        "sourceShape": "ex:Shape",
                        "sourceConstraintComponent": "sh:MinCountConstraintComponent",
                        "expected": "1",
                        "value": "http://example.com/atm#bob",
                    }
                ]
            return True, []

    monkeypatch.setattr(repair_loop, "SHACLValidator", FakeValidator)
    monkeypatch.setattr(repair_loop, "run_reasoner", lambda path: (None, []))

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
        == "Shape=ex:Shape, Constraint=sh:MinCountConstraintComponent, Path=http://example.com/atm#knows, Expected=1, Observed=http://example.com/atm#bob"
    )

    final_graph = Graph().parse(ttl_path, format="turtle")
    assert (
        URIRef("http://example.com/atm#alice"),
        URIRef("http://example.com/atm#knows"),
        URIRef("http://example.com/atm#bob"),
    ) not in final_graph
    assert (
        URIRef("http://example.com/atm#alice"),
        URIRef("http://example.com/atm#friend"),
        URIRef("http://example.com/atm#bob"),
    ) in final_graph


def test_synthesize_repair_prompts_returns_structured_json(monkeypatch):
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
            "value": "http://example.com/b",
        }
    ]
    available_terms = {
        "classes": [],
        "properties": [],
        "domain_range_hints": {
            "http://example.com/p": {
                "domain": ["http://example.com/A"],
                "range": ["http://example.com/B"],
            }
        },
        "synonyms": {"http://example.com/alias": "http://example.com/A"},
    }

    monkeypatch.setattr(
        repair_loop,
        "map_to_ontology_terms",
        lambda available_terms, ctx: (
            ["http://example.com/A"], ["http://example.com/p"]
        ),
    )

    prompts = repair_loop.synthesize_repair_prompts(
        violations, graph, available_terms, ["http://example.com/BadClass"]
    )

    assert len(prompts) == 1
    prompt = json.loads(prompts[0])
    assert prompt["violation"].startswith("Shape=ex:Shape")
    assert prompt["offending_axioms"] == [
        "http://example.com/a http://example.com/p http://example.com/b"
    ]
    assert "http://example.com/p" in prompt["terms"]
    assert prompt["domain_range_hints"]["http://example.com/p"]["domain"] == [
        "http://example.com/A"
    ]
    assert prompt["synonyms"]["http://example.com/alias"] == "http://example.com/A"
    assert prompt["reasoner_inconsistencies"] == [
        "http://example.com/BadClass"
    ]


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


def test_local_context_trims_to_max_triples():
    data = "@prefix ex: <http://example.com/> .\n" + "\n".join(
        f"ex:a ex:p ex:o{i} ." for i in range(60)
    )
    graph = Graph().parse(data=data, format="turtle")
    orig = list(
        graph.triples(
            (URIRef("http://example.com/a"), URIRef("http://example.com/p"), None)
        )
    )
    assert len(orig) == 60

    ctx = repair_loop.local_context(
        graph, "http://example.com/a", "http://example.com/p", max_triples=10
    )
    ctx_graph = Graph().parse(data=ctx, format="turtle")
    assert len(ctx_graph) == 10

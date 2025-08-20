import pathlib

import scripts.main as main
from scripts.main import run_pipeline
from ontology_guided.llm_interface import LLMInterface


def test_run_pipeline_custom_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return ["@prefix atm: <http://example.com/atm#> .\natm:dummy a atm:Unused ."]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    root = pathlib.Path(__file__).resolve().parent.parent
    inputs = [str(root / "demo.txt")]
    shapes = str(root / "shapes.ttl")

    result = run_pipeline(
        inputs,
        shapes,
        "http://example.com/atm#",
        spacy_model="en",
        inference="none",
    )
    assert result["shacl_conforms"] is True
    assert result["failed_snippets"] == []
    assert any(
        "The ATM must log" in entry["requirement"]
        for entry in result["provenance"].values()
    )


def test_run_pipeline_collects_failed_snippets(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return ["invalid turtle"]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    root = pathlib.Path(__file__).resolve().parent.parent
    inputs = [str(root / "demo.txt")]
    shapes = str(root / "shapes.ttl")

    result = run_pipeline(
        inputs,
        shapes,
        "http://example.com/atm#",
        spacy_model="en",
        inference="none",
    )

    assert result["failed_snippets"] == [
        {
            "sentence": "The ATM must log all user transactions after card insertion.",
            "snippet": "invalid turtle",
        }
    ]
    assert result["provenance"] == {}


def test_run_pipeline_ontology_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return ["@prefix atm: <http://example.com/atm#> .\natm:dummy a atm:Unused ."]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    onto_dir = tmp_path / "ontos"
    onto_dir.mkdir()
    ttl_file = onto_dir / "extra.ttl"
    ttl_file.write_text("@prefix : <http://example.com/> .")

    captured = {}

    class FakeBuilder:
        def __init__(self, base_iri, ontology_files=None):
            captured["files"] = list(ontology_files or [])
            self.triple_provenance = {}

        def get_available_terms(self):
            return {"classes": [], "properties": [], "domain_range_hints": {}, "synonyms": {}}

        def parse_turtle(self, *args, **kwargs):
            return []

        def add_provenance(self, requirement, triples):
            pass

        def save(self, path, fmt):
            pathlib.Path(path).write_text("")

    monkeypatch.setattr(main, "OntologyBuilder", FakeBuilder)

    root = pathlib.Path(__file__).resolve().parent.parent
    inputs = [str(root / "demo.txt")]
    shapes = str(root / "shapes.ttl")

    run_pipeline(
        inputs,
        shapes,
        "http://example.com/atm#",
        ontology_dir=str(onto_dir),
        spacy_model="en",
        inference="none",
    )

    assert str(ttl_file) in captured["files"]


def test_run_pipeline_passes_repair_options(monkeypatch, tmp_path):
    """Ensure kmax, reason and inference are forwarded to RepairLoop."""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return ["@prefix atm: <http://example.com/atm#> .\natm:dummy a atm:Unused ."]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    class FakeValidator:
        def __init__(self, data_path, shapes_path, inference="rdfs"):
            self.inference = inference

        def run_validation(self):
            return False, "report"

    monkeypatch.setattr(main, "SHACLValidator", FakeValidator)

    captured = {}

    class FakeRepairLoop:
        def __init__(self, data_path, shapes_path, api_key, *, kmax=5, base_iri=None):
            captured["kmax"] = kmax
            captured["base_iri"] = base_iri

        def run(self, reason=False, inference="rdfs"):
            captured["reason"] = reason
            captured["inference"] = inference
            return ("fixed.ttl", "final_report.txt", ["v1"])

    monkeypatch.setattr(main, "RepairLoop", FakeRepairLoop)

    root = pathlib.Path(__file__).resolve().parent.parent
    inputs = [str(root / "demo.txt")]
    shapes = str(root / "shapes.ttl")

    result = run_pipeline(
        inputs,
        shapes,
        "http://example.com/atm#",
        repair=True,
        reason=True,
        inference="owlrl",
        kmax=7,
        spacy_model="en",
    )

    assert captured == {
        "kmax": 7,
        "reason": True,
        "inference": "owlrl",
        "base_iri": "http://example.com/atm#",
    }
    assert result["repaired_ttl"] == "fixed.ttl"
    assert result["repaired_report"]["path"] == "final_report.txt"
    assert result["repaired_report"]["violations"] == ["v1"]


def test_run_pipeline_skips_repaired_ttl_when_none(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return ["@prefix atm: <http://example.com/atm#> .\natm:dummy a atm:Unused ."]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    class FakeValidator:
        def __init__(self, data_path, shapes_path, inference="rdfs"):
            pass

        def run_validation(self):
            return False, "report"

    monkeypatch.setattr(main, "SHACLValidator", FakeValidator)

    class FakeRepairLoop:
        def __init__(self, data_path, shapes_path, api_key, *, kmax=5, base_iri=None):
            pass

        def run(self, reason=False, inference="rdfs"):
            return (None, "final_report.txt", [])

    monkeypatch.setattr(main, "RepairLoop", FakeRepairLoop)

    root = pathlib.Path(__file__).resolve().parent.parent
    inputs = [str(root / "demo.txt")]
    shapes = str(root / "shapes.ttl")

    result = run_pipeline(
        inputs,
        shapes,
        "http://example.com/atm#",
        repair=True,
        spacy_model="en",
        inference="none",
    )

    assert "repaired_ttl" not in result
    assert result["repaired_report"]["path"] == "final_report.txt"
    assert result["repaired_report"]["violations"] == []


def test_run_pipeline_runs_reasoner(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return ["@prefix atm: <http://example.com/atm#> .\natm:dummy a atm:Unused ."]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    called = {}

    def fake_run_reasoner(path):
        called["path"] = path
        return None, []

    import ontology_guided.reasoner as reasoner

    monkeypatch.setattr(reasoner, "run_reasoner", fake_run_reasoner)

    root = pathlib.Path(__file__).resolve().parent.parent
    inputs = [str(root / "demo.txt")]
    shapes = str(root / "shapes.ttl")

    result = run_pipeline(
        inputs,
        shapes,
        "http://example.com/atm#",
        reason=True,
        spacy_model="en",
        inference="none",
    )

    assert called["path"].endswith("combined.owl")
    assert result["reasoning_log"] == "Reasoner completed successfully"
    assert result["inconsistent_classes"]["iris"] == []
    assert pathlib.Path(result["inconsistent_classes"]["path"]).exists()

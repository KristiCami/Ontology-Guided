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
            return []

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

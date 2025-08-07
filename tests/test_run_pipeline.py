import pathlib

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

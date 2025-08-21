import pathlib

from scripts.main import run_pipeline
from ontology_guided.llm_interface import LLMInterface


def test_pipeline_switches_to_healthcare(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return [
            "@prefix hc: <http://example.com/healthcare#> .\n"
            "hc:obs1 a hc:Observation ;\n"
            "    hc:performedBy hc:doc1 ;\n"
            "    hc:onPatient hc:pat1 .\n"
            "hc:doc1 a hc:Doctor .\n"
            "hc:pat1 a hc:Patient ."
        ]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    root = pathlib.Path(__file__).resolve().parent.parent
    inputs = [str(root / "evaluation" / "healthcare_requirements.txt")]
    shapes = str(root / "evaluation" / "healthcare_shapes.ttl")
    ontology = str(root / "ontologies" / "healthcare.ttl")

    result = run_pipeline(
        inputs,
        shapes,
        "http://example.com/healthcare#",
        ontologies=[ontology],
        spacy_model="en",
        inference="none",
    )

    assert result["shacl_conforms"] is True
    assert result["failed_snippets"] == []
    assert any(
        "patient observation" in entry["requirement"].lower()
        for entry in result["provenance"].values()
    )

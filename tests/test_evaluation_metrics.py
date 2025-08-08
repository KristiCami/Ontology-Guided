import pathlib

from evaluation.compare_metrics import compare_metrics
from ontology_guided.llm_interface import LLMInterface


def test_compare_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        return [
            "@prefix atm: <http://example.com/atm#> .\natm:CorrectPINTransaction atm:hasOutcome atm:CashDispensed .",
            "@prefix atm: <http://example.com/atm#> .\natm:ThreeFailedPinAttempt atm:hasOutcome atm:CardRetained .",
        ]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    root = pathlib.Path(__file__).resolve().parent.parent
    requirements = root / "evaluation" / "atm_requirements.txt"
    gold = root / "evaluation" / "atm_gold.ttl"
    shapes = root / "shapes.ttl"

    metrics = compare_metrics(str(requirements), str(gold), str(shapes))
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0

import pathlib
import pytest

from evaluation.compare_metrics import compare_metrics
from ontology_guided.llm_interface import LLMInterface


def test_compare_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(self, sentences, prompt_template, available_terms=None):
        snippet = (
            "<http://lod.csd.auth.gr/atm/atm.ttl> "
            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
            "<http://www.w3.org/2002/07/owl#Ontology> .\n"
            "<http://lod.csd.auth.gr/atm/atm.ttl#accepts> "
            "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
            "<http://www.w3.org/2002/07/owl#ObjectProperty> ."
        )
        return [snippet for _ in sentences]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    root = pathlib.Path(__file__).resolve().parent.parent
    requirements = root / "evaluation" / "atm_requirements.txt"
    gold = root / "evaluation" / "atm_gold.ttl"
    shapes = root / "shapes.ttl"

    metrics = compare_metrics(str(requirements), str(gold), str(shapes))
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(0.001310615989515072)

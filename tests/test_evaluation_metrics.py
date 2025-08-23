import pathlib
import pytest

from evaluation.compare_metrics import compare_metrics
from ontology_guided.llm_interface import LLMInterface
from evaluation.run_benchmark import compute_metrics


def test_compare_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.chdir(tmp_path)

    def fake_generate_owl(
        self,
        sentences,
        prompt_template,
        available_terms=None,
        base=None,
        prefix=None,
    ):
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


def test_compute_metrics_normalize_base(tmp_path):
    pred = tmp_path / "pred.ttl"
    pred.write_text(
        "@prefix : <http://example.org/a#> .\n" \
        ":x :p :y .\n",
        encoding="utf-8",
    )
    gold = tmp_path / "gold.ttl"
    gold.write_text(
        "@prefix : <http://other.org/b#> .\n" \
        ":x :p :y .\n",
        encoding="utf-8",
    )

    no_norm = compute_metrics(str(pred), str(gold))
    assert no_norm["precision"] == 0.0
    assert no_norm["recall"] == 0.0

    with_norm = compute_metrics(str(pred), str(gold), normalize_base=True)
    assert with_norm["precision"] == 1.0
    assert with_norm["recall"] == 1.0

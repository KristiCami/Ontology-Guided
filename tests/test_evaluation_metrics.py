import pathlib
import pytest
from rdflib import Graph, OWL
from rdflib.namespace import RDF

from evaluation.compare_metrics import compare_metrics
from ontology_guided.llm_interface import LLMInterface
from evaluation.run_benchmark import compute_metrics
from ontology_guided.data_loader import DataLoader


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

    def multiline_jsonl_loader(self, file_path, allowed_ids=None):
        import json

        buffer = ""
        depth = 0
        id_set = {str(i) for i in allowed_ids} if allowed_ids is not None else None
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                buffer += line
                depth += line.count("{") - line.count("}")
                if depth == 0:
                    rec = json.loads(buffer)
                    sid = str(rec.get("sentence_id"))
                    if id_set is None or sid in id_set:
                        yield {"text": rec.get("text", ""), "sentence_id": sid}
                    buffer = ""

    monkeypatch.setattr(DataLoader, "load_jsonl_file", multiline_jsonl_loader)

    root = pathlib.Path(__file__).resolve().parent.parent
    requirements = root / "evaluation" / "atm_requirements.jsonl"
    gold = root / "evaluation" / "atm_gold.ttl"
    shapes = root / "shapes.ttl"

    metrics = compare_metrics(str(requirements), str(gold), str(shapes))

    # overall precision/recall should reflect triple level metrics
    assert metrics["precision"] == pytest.approx(1.0)

    gold_graph = Graph()
    gold_graph.parse(str(gold), format="turtle")
    obj_props = set(gold_graph.subjects(RDF.type, OWL.ObjectProperty))
    expected_recall = 1 / len(obj_props)
    assert metrics["per_type"]["ObjectProperty"]["precision"] == pytest.approx(1.0)
    assert metrics["per_type"]["ObjectProperty"]["recall"] == pytest.approx(expected_recall)


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

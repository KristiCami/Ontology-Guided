import pathlib
import json
import pytest
from rdflib import Graph, OWL
from rdflib.namespace import RDF

from evaluation.compare_metrics import compare_metrics
from ontology_guided.llm_interface import LLMInterface
from evaluation.run_benchmark import compute_metrics
from ontology_guided.data_loader import DataLoader
from scripts.main import load_dev_examples


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
            "<http://lod.csd.auth.gr/atm/atm.ttl#operatedBy> "
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
    gold = root / "gold" / "atm_gold.ttl"
    shapes = root / "gold" / "shapes_atm.ttl"

    metrics = compare_metrics(str(requirements), str(gold), str(shapes))

    # overall precision is diluted by categories without matches but remains > 0
    assert metrics["precision"] == pytest.approx(0.5)

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


def test_compare_metrics_with_split_and_dev(monkeypatch, tmp_path):
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
            "<http://lod.csd.auth.gr/atm/atm.ttl#A> "
            "<http://lod.csd.auth.gr/atm/atm.ttl#p> "
            "<http://lod.csd.auth.gr/atm/atm.ttl#B> ."
        )
        return [snippet for _ in sentences]

    monkeypatch.setattr(LLMInterface, "generate_owl", fake_generate_owl)

    def multiline_jsonl_loader(self, file_path, allowed_ids=None):
        import json

        id_set = {str(i) for i in allowed_ids} if allowed_ids is not None else None
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                sid = str(rec.get("sentence_id"))
                if id_set is None or sid in id_set:
                    yield {"text": rec.get("text", ""), "sentence_id": sid}

    monkeypatch.setattr(DataLoader, "load_jsonl_file", multiline_jsonl_loader)

    req = tmp_path / "req.jsonl"
    records = [
        {
            "sentence_id": "1",
            "text": "First",
            "axioms": {
                "tbox": [
                    "<http://lod.csd.auth.gr/atm/atm.ttl#A> <http://lod.csd.auth.gr/atm/atm.ttl#p> <http://lod.csd.auth.gr/atm/atm.ttl#B> ."
                ]
            },
        },
        {
            "sentence_id": "2",
            "text": "Second",
            "axioms": {
                "tbox": [
                    "<http://lod.csd.auth.gr/atm/atm.ttl#C> <http://lod.csd.auth.gr/atm/atm.ttl#p> <http://lod.csd.auth.gr/atm/atm.ttl#D> ."
                ]
            },
        },
    ]
    req.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    gold = tmp_path / "gold.ttl"
    gold.write_text(
        "<http://lod.csd.auth.gr/atm/atm.ttl#A> <http://lod.csd.auth.gr/atm/atm.ttl#p> <http://lod.csd.auth.gr/atm/atm.ttl#B> .\n"
        "<http://lod.csd.auth.gr/atm/atm.ttl#C> <http://lod.csd.auth.gr/atm/atm.ttl#p> <http://lod.csd.auth.gr/atm/atm.ttl#D> .\n",
        encoding="utf-8",
    )

    shapes = pathlib.Path(__file__).resolve().parent.parent / "shapes.ttl"

    dev_split = tmp_path / "dev.txt"
    dev_split.write_text("2\n", encoding="utf-8")

    examples, dev_ids = load_dev_examples(str(req), str(dev_split))

    metrics = compare_metrics(
        str(req),
        str(gold),
        str(shapes),
        test_ids=["1"],
        examples=examples,
        dev_sentence_ids=dev_ids,
    )

    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(1.0)

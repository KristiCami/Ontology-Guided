import sys
from pathlib import Path

import evaluation.run_benchmark as rb


def _run_cli(monkeypatch, tmp_path, extra_args):
    captured = {"ontologies": [], "cqs": []}

    def fake_run_pipeline(inputs, shapes, base_iri, *, ontologies=None, **kwargs):
        captured["ontologies"] = list(ontologies or [])
        return {"combined_ttl": "", "violation_stats": {}, "shacl_conforms": True}

    def fake_evaluate_cqs(ttl, cq_path):
        captured["cqs"].append(cq_path)
        return {"pass_rate": 0.0}

    monkeypatch.setattr(rb, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(rb, "compute_metrics", lambda *a, **k: {"precision": 0, "recall": 0, "f1": 0})
    monkeypatch.setattr(rb, "evaluate_cqs", fake_evaluate_cqs)

    argv = [
        "run_benchmark.py",
        "--pairs",
        "req:gold:shapes",
        "--settings",
        '[{"name": "t"}]',
        "--repeats",
        "1",
        "--output-dir",
        str(tmp_path),
    ] + extra_args
    monkeypatch.setattr(sys, "argv", argv)
    rb.main()
    return captured


def test_cli_accepts_ontologies(monkeypatch, tmp_path):
    a = tmp_path / "a.ttl"
    a.write_text("")
    b = tmp_path / "b.ttl"
    b.write_text("")

    result = _run_cli(monkeypatch, tmp_path, ["--ontologies", str(a), str(b)])
    assert result["ontologies"] == [str(a), str(b)]


def test_cli_accepts_ontology_dir(monkeypatch, tmp_path):
    d = tmp_path / "dir"
    d.mkdir()
    x = d / "x.ttl"
    x.write_text("")
    y = d / "y.ttl"
    y.write_text("")
    (d / "ignore.txt").write_text("no")

    result = _run_cli(monkeypatch, tmp_path, ["--ontology-dir", str(d)])
    assert set(result["ontologies"]) == {str(x), str(y)}


def test_cli_accepts_cqs(monkeypatch, tmp_path):
    cq = tmp_path / "c.rq"
    cq.write_text("")
    result = _run_cli(monkeypatch, tmp_path, ["--cqs", str(cq)])
    assert result["cqs"] == [str(cq)]

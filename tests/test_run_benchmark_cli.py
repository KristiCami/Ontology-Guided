import sys
from pathlib import Path

import pytest

import evaluation.run_benchmark as rb


def _run_cli(monkeypatch, tmp_path, extra_args):
    captured = {
        "ontologies": [],
        "cqs": [],
        "allowed_ids": None,
        "dev_ids": None,
        "retrieval": {},
    }

    def fake_run_pipeline(
        inputs,
        shapes,
        base_iri,
        *,
        ontologies=None,
        allowed_ids=None,
        dev_sentence_ids=None,
        **kwargs,
    ):
        captured["ontologies"] = list(ontologies or [])
        captured["allowed_ids"] = list(allowed_ids or [])
        captured["dev_ids"] = list(dev_sentence_ids or [])
        captured["retrieval"] = {
            "use_retrieval": kwargs.get("use_retrieval"),
            "dev_pool": kwargs.get("dev_pool"),
            "retrieve_k": kwargs.get("retrieve_k"),
            "retrieval_method": kwargs.get("retrieval_method"),
            "prompt_log": kwargs.get("prompt_log"),
        }
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


def test_cli_filters_test_sentences(monkeypatch, tmp_path):
    split = tmp_path / "s.txt"
    split.write_text("100\n101\n")
    result = _run_cli(monkeypatch, tmp_path, ["--splits", str(split)])
    assert result["allowed_ids"] == ["100", "101"]
    dev_ids = set(result["dev_ids"])
    assert dev_ids
    assert not dev_ids.intersection(result["allowed_ids"])


def test_cli_accepts_retrieval(monkeypatch, tmp_path):
    pool = tmp_path / "pool.json"
    pool.write_text("[]")
    log = tmp_path / "log.json"
    result = _run_cli(
        monkeypatch,
        tmp_path,
        [
            "--use-retrieval",
            "--dev-pool",
            str(pool),
            "--retrieve-k",
            "4",
            "--prompt-log",
            str(log),
        ],
    )
    assert result["retrieval"]["use_retrieval"] is True
    assert result["retrieval"]["dev_pool"] == str(pool)
    assert result["retrieval"]["retrieve_k"] == 4
    assert result["retrieval"]["retrieval_method"] == "tfidf_cosine"
    assert result["retrieval"]["prompt_log"] == str(log)


def test_cli_rejects_overlap(monkeypatch, tmp_path):
    split = tmp_path / "s.txt"
    split.write_text(rb.DEV_SENTENCE_IDS[0] + "\n")
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
        "--splits",
        str(split),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError):
        rb.main()

"""Tests for experiment evaluation helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from og_nsd.evaluation import (
    MetricTriple,
    compute_extraction_metrics,
    format_markdown_row,
    format_shacl_row,
    summarize_shacl_iterations,
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_compute_extraction_metrics(tmp_path: Path) -> None:
    gold = _write(
        tmp_path / "gold.ttl",
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .

        ex:A a owl:Class .
        ex:B a owl:Class .
        ex:A rdfs:subClassOf ex:B .
        ex:p a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:B .
        ex:q a owl:DatatypeProperty ; rdfs:domain ex:A ; rdfs:range rdfs:Literal .
        """,
    )
    generated = _write(
        tmp_path / "pred.ttl",
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .

        ex:A a owl:Class .
        ex:C a owl:Class .
        ex:A rdfs:subClassOf ex:B .
        ex:p a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:C .
        """,
    )

    metrics = compute_extraction_metrics(gold, generated)

    assert metrics.per_type["classes"] == MetricTriple(precision=0.5, recall=0.5, f1=0.5)
    assert metrics.per_type["subclass"].f1 == 1.0
    assert metrics.per_type["object_property"].precision == 1.0
    assert metrics.micro.precision == pytest.approx(4 / 6)
    assert metrics.micro.recall == pytest.approx(4 / 9)
    assert metrics.micro.f1 == pytest.approx(2 * (4 / 6) * (4 / 9) / ((4 / 6) + (4 / 9)))


def test_shacl_summary_and_formatting(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    sample = {
        "iterations": [
            {"iteration": 0, "shacl": {"conforms": False, "results": [1, 2]}},
            {"iteration": 1, "shacl": {"conforms": True, "results": []}},
        ]
    }
    report_path.write_text(json.dumps(sample), encoding="utf-8")

    summary = summarize_shacl_iterations(report_path)
    assert summary.violations_start == 2
    assert summary.violations_end == 0
    assert summary.iterations == 2
    assert summary.conforms is True

    assert format_shacl_row("RunA", summary) == "| RunA | 2 | 0 | 2 | ✅ |"
    assert format_markdown_row("RunA", MetricTriple(0.4, 0.5, 0.44)) == "| RunA | 0.40 | 0.50 | 0.44 |"

from pathlib import Path

from og_nsd.queries import CompetencyQuestionRunner


def test_load_queries_handles_nested_braces(tmp_path: Path):
    cq_file = tmp_path / "cq.rq"
    cq_file.write_text(
        """# Comment line\n"
        "PREFIX ex: <http://example.com/>\n"
        "ASK {\n"
        "  FILTER NOT EXISTS {\n"
        "    VALUES ?cls { ex:Foo }\n"
        "    FILTER NOT EXISTS { ?cls a ex:Bar . }\n"
        "  }\n"
        "}\n"
        "\n"
        "PREFIX ex: <http://example.com/>\n"
        "ASK { ex:Foo a ex:Bar }\n"
        """,
        encoding="utf-8",
    )

    runner = CompetencyQuestionRunner(cq_file)

    assert len(runner.queries) == 2
    assert "FILTER NOT EXISTS" in runner.queries[0]
    assert runner.queries[0].count("ASK") == 1
    assert runner.queries[0].rstrip().endswith("}")
    assert runner.queries[1].rstrip().endswith("}")

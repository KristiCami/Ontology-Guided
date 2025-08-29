import textwrap
import pytest

from evaluation.competency_questions import evaluate_cqs


def test_evaluate_cqs_pass_rate(tmp_path):
    ttl = textwrap.dedent(
        """
        @prefix : <http://example.org/> .
        :Alice a :Person .
        """
    ).strip()
    onto_path = tmp_path / "onto.ttl"
    onto_path.write_text(ttl, encoding="utf-8")

    queries = textwrap.dedent(
        """
        PREFIX : <http://example.org/>
        ASK { :Alice a :Person . }

        PREFIX : <http://example.org/>
        ASK { :Bob a :Person . }
        """
    ).strip()
    cq_path = tmp_path / "cqs.rq"
    cq_path.write_text(queries, encoding="utf-8")

    results = evaluate_cqs(onto_path, cq_path, inference=False)
    assert results["passed"] == 1
    assert results["total"] == 2
    assert results["pass_rate"] == pytest.approx(0.5)

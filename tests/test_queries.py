"""Tests for competency question execution and reporting."""

import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, RDF

from og_nsd.queries import CompetencyQuestionRunner


class CompetencyQuestionRunnerTests(unittest.TestCase):
    def _write_queries(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".rq")
        handle.write(content)
        handle.flush()
        handle.close()
        return Path(handle.name)

    def test_records_boolean_answers_separately_from_success(self) -> None:
        path = self._write_queries(
            "\n".join(
                [
                    "ASK { ?a a <http://example.org/Thing> }",
                    "",
                    "ASK { ?a a <http://example.org/Missing> }",
                ]
            )
        )

        graph = Graph()
        ex = Namespace("http://example.org/")
        graph.add((ex.a, RDF.type, ex.Thing))

        results = CompetencyQuestionRunner(path).run(graph)

        self.assertEqual(2, len(results))
        self.assertTrue(results[0].success)
        self.assertTrue(results[0].answer)
        self.assertEqual("", results[0].message)
        self.assertTrue(results[1].success)
        self.assertFalse(results[1].answer)
        self.assertEqual("", results[1].message)

    def test_sets_answer_none_when_query_fails(self) -> None:
        path = self._write_queries("ASK { INVALID }")

        results = CompetencyQuestionRunner(path).run(Graph())

        self.assertEqual(1, len(results))
        self.assertFalse(results[0].success)
        self.assertIsNone(results[0].answer)
        self.assertTrue(results[0].message)


if __name__ == "__main__":
    unittest.main()

"""Tests for competency question parsing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rdflib import Graph

from og_nsd.queries import CompetencyQuestionRunner


class CompetencyQuestionRunnerTests(unittest.TestCase):
    def test_handles_nested_braces_without_truncation(self) -> None:
        content = """
# Example queries
PREFIX atm: <http://lod.csd.auth.gr/atm/atm.ttl#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
ASK {
  FILTER NOT EXISTS {
    VALUES ?cls { atm:ATM atm:Bank }
  }
}

PREFIX atm: <http://lod.csd.auth.gr/atm/atm.ttl#>
ASK {
  atm:ATM a owl:Class .
}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "cqs.rq"
            path.write_text(content)

            runner = CompetencyQuestionRunner(path)

            self.assertEqual(2, len(runner.queries))

            # Queries should remain parseable despite nested braces in the first one
            for query in runner.queries:
                Graph().query(query)


if __name__ == "__main__":
    unittest.main()

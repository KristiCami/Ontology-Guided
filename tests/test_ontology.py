"""Unit tests for ontology assembly helpers."""

import unittest

from rdflib import Graph

from og_nsd.ontology import _ensure_standard_prefixes


class EnsureStandardPrefixesTests(unittest.TestCase):
    def test_adds_missing_standard_prefixes(self) -> None:
        turtle = "@prefix atm: <http://example.org/atm#> .\n\natm:ATM a owl:Class ."

        enriched = _ensure_standard_prefixes(turtle)

        self.assertIn("@prefix owl:", enriched)
        # Parsing should succeed now that owl: is declared
        Graph().parse(data=enriched, format="turtle")

    def test_retains_existing_prefixes(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n\n"
            "atm:ATM a owl:Class ."
        )

        enriched = _ensure_standard_prefixes(turtle)

        # Should not duplicate known prefixes
        self.assertEqual(1, enriched.count("@prefix owl:"))
        Graph().parse(data=enriched, format="turtle")


if __name__ == "__main__":
    unittest.main()

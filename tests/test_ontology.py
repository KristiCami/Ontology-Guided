"""Unit tests for ontology assembly helpers."""

import unittest

from rdflib import Graph

from og_nsd.ontology import _ensure_standard_prefixes, _sanitize_turtle


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

    def test_additional_prefixes_added_when_missing(self) -> None:
        turtle = "atm:ATM a owl:Class ."

        enriched = _ensure_standard_prefixes(
            turtle, additional_prefixes={"atm": "http://example.org/atm#"}
        )

        self.assertIn("@prefix atm: <http://example.org/atm#> .", enriched)
        Graph().parse(data=enriched, format="turtle")


class SanitizeTurtleTests(unittest.TestCase):
    def test_comments_lines_starting_with_not(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n"
            "\n"
            "atm:ATM a owl:Class .\n"
            "NOT atm:CashCard atm:in atm:ATM .\n"
            "atm:CashCard a owl:Class ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn("# NOT atm:CashCard", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_strips_control_characters(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n"
            "\n"
            "atm:ATM a owl:Class .\n"
            "atm:ATM atm:requires [ atm:has atm:CardNumber ; atm:from \x08atm:CashCard ] ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertNotIn("\x08", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_removes_quoted_prefixes(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n"
            "\n"
            "atm:ATM a owl:Class .\n"
            "atm:ATM atm:requires [ atm:has atm:CardNumber ; atm:from 'atm:CashCard ] ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn("atm:from atm:CashCard", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_unwraps_byte_string_reprs(self) -> None:
        turtle = (
            "b'@prefix atm: <http://example.org/atm#> .\\n"
            "\\natm:ATM a owl:Class .\\n'"
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertNotIn("b'@prefix", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_quotes_bare_decimals(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n\n"
            "atm:Transaction atm:requestedAmount 100.00^^xsd:decimal ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn('"100.00"^^xsd:decimal', sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_removes_bytes_prefix_before_qname(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n\n"
            "atm:Response atm:rejectedWithErrorMessage '^b'atm:ErrorMessage ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn("atm:rejectedWithErrorMessage atm:ErrorMessage", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_preserves_spacing_when_bytes_fragments_are_embedded(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n\n"
            "atm:ATM atm:hasValidity atm:Invalid .\n"
            "atm:BankComputer atm:sendsMessage '^b'atm:ATM ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn("atm:BankComputer atm:sendsMessage atm:ATM", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_removes_trailing_bytes_fragment(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n\n"
            "atm:Response atm:hasErrorMessage \"Error\"^^xsd:string'^b' .\n"
            "atm:Response a atm:ResponseType ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertNotIn("'^b'", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")


if __name__ == "__main__":
    unittest.main()

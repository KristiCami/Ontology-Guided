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

    def test_comments_inline_logic_tokens(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n"
            "\n"
            "atm:ATM a owl:Class .\n"
            "atm:ATM atm:runningOutOfMoney ;\n"
            "    atm:ATM NOT atm:set atm:display .\n"
            "atm:ATM atm:has atm:CashDispenser ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn("#     atm:ATM NOT atm:set atm:display .", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_comments_conditional_blocks(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n"
            "\n"
            "atm:ATM a owl:Class .\n"
            "IF atm:ATM atm:runningOutOfMoney ;\n"
            "    atm:ATM atm:blocks atm:CashWithdrawal .\n"
            "THEN atm:ATM atm:has atm:Notice .\n"
            "atm:ATM atm:dispenses atm:Cash ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn("# IF atm:ATM atm:runningOutOfMoney ;", sanitized)
        self.assertIn("# THEN atm:ATM atm:has atm:Notice .", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")


if __name__ == "__main__":
    unittest.main()

"""Unit tests for ontology assembly helpers."""

import unittest

from rdflib import Graph, Literal, URIRef, OWL, RDF
from rdflib.namespace import XSD

from og_nsd.ontology import _ensure_standard_prefixes, _sanitize_turtle
from og_nsd.reasoning import OwlreadyReasoner, _sanitize_numeric_literals


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

    def test_removes_infix_bytes_token(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n\n"
            "atm:logsSerialNumber a owl:DatatypeProperty .\n"
            "atm:logsSerialNumber'^b' a atm:Transaction ; atm:serialNumber atm:CashCard ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn(
            "atm:logsSerialNumber a atm:Transaction ; atm:serialNumber atm:CashCard",
            sanitized,
        )
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")

    def test_removes_variable_prefix_on_qname(self) -> None:
        turtle = (
            "@prefix atm: <http://example.org/atm#> .\n\n"
            "atm:Transaction atm:requestedAmount ?atm:amount ."
        )

        sanitized = _sanitize_turtle(turtle)

        self.assertIn("atm:requestedAmount atm:amount", sanitized)
        Graph().parse(data=_ensure_standard_prefixes(sanitized), format="turtle")


class SanitizeNumericLiteralsTests(unittest.TestCase):
    def test_coerces_invalid_decimal_literals(self) -> None:
        graph = Graph()
        subject = URIRef("http://example.org/txn")
        predicate = URIRef("http://example.org/requestedAmount")
        graph.add((subject, predicate, Literal("amount", datatype=XSD.decimal)))

        sanitized, fixes = _sanitize_numeric_literals(graph)

        self.assertEqual(1, fixes)
        coerced = next(sanitized.objects(subject, predicate))
        self.assertIsNone(coerced.datatype)
        self.assertEqual("amount", str(coerced))

    def test_reasoner_uses_sanitized_graph_when_disabled(self) -> None:
        graph = Graph()
        subject = URIRef("http://example.org/txn")
        predicate = URIRef("http://example.org/requestedAmount")
        graph.add((subject, predicate, Literal("t", datatype=XSD.decimal)))

        reasoner = OwlreadyReasoner(enabled=False)
        result = reasoner.run(graph)

        coerced = next(result.expanded_graph.objects(subject, predicate))
        self.assertIsNone(coerced.datatype)
        self.assertEqual("t", str(coerced))
        self.assertIn("Coerced 1 invalid literal", result.report.notes)

    def test_coerces_invalid_datetime_literals(self) -> None:
        graph = Graph()
        subject = URIRef("http://example.org/txn")
        predicate = URIRef("http://example.org/timestamp")
        graph.add((subject, predicate, Literal("timestamp", datatype=XSD.dateTime)))

        sanitized, fixes = _sanitize_numeric_literals(graph)

        self.assertEqual(1, fixes)
        coerced = next(sanitized.objects(subject, predicate))
        self.assertIsNone(coerced.datatype)
        self.assertEqual("timestamp", str(coerced))

    def test_coerces_resource_objects_on_datatype_properties(self) -> None:
        graph = Graph()
        subject = URIRef("http://example.org/card")
        predicate = URIRef("http://example.org/serialNumber")
        object_resource = URIRef("http://example.org/CashCard")
        graph.add((predicate, RDF.type, OWL.DatatypeProperty))
        graph.add((subject, predicate, object_resource))

        sanitized, fixes = _sanitize_numeric_literals(graph)

        self.assertEqual(1, fixes)
        coerced = next(sanitized.objects(subject, predicate))
        self.assertIsNone(coerced.datatype)
        self.assertEqual(str(object_resource), str(coerced))


if __name__ == "__main__":
    unittest.main()

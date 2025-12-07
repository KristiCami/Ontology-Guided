"""SHACL validation regression tests."""

from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF

from og_nsd.shacl import ShaclReport, ShaclValidator


def test_shacl_validator_supports_prefixed_sparql_constraints():
    """Ensure SPARQL constraints with prefixes are evaluated without errors."""

    graph = Graph()
    atm = Namespace("http://lod.csd.auth.gr/atm/atm.ttl#")

    card = atm["Card1"]
    duplicate = atm["Card2"]

    graph.add((card, RDF.type, atm.CashCard))
    graph.add((card, atm.bankCode, Literal("123")))
    graph.add((card, atm.serialNumber, Literal("A1")))

    graph.add((duplicate, RDF.type, atm.CashCard))
    graph.add((duplicate, atm.bankCode, Literal("123")))
    graph.add((duplicate, atm.serialNumber, Literal("A1")))

    validator = ShaclValidator(Path("gold/shapes_atm.ttl"))
    report = validator.validate(graph)

    assert isinstance(report, ShaclReport)
    assert not report.conforms
    assert "Unknown namespace prefix" not in report.text_report

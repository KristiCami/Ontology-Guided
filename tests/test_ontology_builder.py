from ontology_builder import OntologyBuilder
from rdflib import URIRef
from rdflib.namespace import RDF, OWL


def test_parse_turtle_basic():
    builder = OntologyBuilder("http://example.com/atm#")
    snippet = "atm:ATM a owl:Class ."
    builder.parse_turtle(snippet)
    triple = (URIRef("http://example.com/atm#ATM"), RDF.type, OWL.Class)
    assert triple in builder.graph
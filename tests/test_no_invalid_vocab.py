from rdflib import Graph, BNode
from rdflib.namespace import RDF, OWL

from ontology_guided.ontology_builder import OntologyBuilder


def test_no_invalid_vocab(tmp_path):
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = (
        "@prefix ex: <http://example.com/> .\n"
        "ex:A a owl:Class .\n"
        "ex:B a owl:Class .\n"
        "ex:prop a owl:ObjectProperty ;\n"
        "    rdf:domain ex:A ;\n"
        "    rdf:range ex:B .\n"
        "ex:C rdfs:subClassOf [ a owl:Restriction ] .\n"
        "ex:D rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ex:prop ; owl:someValuesFrom ex:A ] .\n"
    )
    ob.parse_turtle(ttl)
    out = tmp_path / "out.ttl"
    ob.save(out, fmt="turtle")

    text = out.read_text(encoding="utf-8")
    assert "rdf:domain" not in text
    assert "rdf:range" not in text

    g = Graph().parse(out, format="turtle")
    invalid = [
        s
        for s in g.subjects(RDF.type, OWL.Restriction)
        if isinstance(s, BNode) and g.value(s, OWL.onProperty) is None
    ]
    assert not invalid

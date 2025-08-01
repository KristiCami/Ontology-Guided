from ontology_builder import OntologyBuilder


def test_parse_turtle_with_prefix():
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = """@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."""
    # Should not raise an exception
    ob.parse_turtle(ttl)
    assert len(ob.graph) == 1
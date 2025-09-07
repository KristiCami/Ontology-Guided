from rdflib import Graph, Namespace, RDF, RDFS, OWL

from ontology_guided.ontology_builder import OntologyBuilder


def test_named_restriction_cleanup(tmp_path):
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = (
        '@prefix ex: <http://example.com/> .\n'
        'ex:A a owl:Class, owl:Restriction ;\n'
        '  owl:onProperty ex:prop ;\n'
        '  owl:someValuesFrom ex:B .\n'
    )
    ob.parse_turtle(ttl)
    out = tmp_path / 'combined.ttl'
    ob.save(out, fmt='turtle')

    g = Graph()
    g.parse(out)

    ex = Namespace('http://example.com/')
    ex_a = ex.A
    ex_prop = ex.prop
    ex_b = ex.B

    assert (ex_a, RDF.type, OWL.Restriction) not in g

    subclass_nodes = list(g.objects(ex_a, RDFS.subClassOf))
    assert subclass_nodes
    assert any(
        (bn, RDF.type, OWL.Restriction) in g
        and (bn, OWL.onProperty, ex_prop) in g
        and (bn, OWL.someValuesFrom, ex_b) in g
        for bn in subclass_nodes
    )

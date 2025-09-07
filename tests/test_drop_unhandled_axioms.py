import logging

from ontology_guided.ontology_builder import OntologyBuilder


def test_drop_unhandled_axioms(tmp_path):
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = (
        "@prefix ex: <http://example.com/> .\n"
        "ex:A a owl:Class .\n"
        "[] a owl:Axiom ; rdfs:label \"orphan\" .\n"
    )
    logger = logging.getLogger(__name__)
    triples = ob.parse_turtle(ttl, logger=logger)
    # Only the ex:A declaration should remain
    assert len(triples) == 1
    out = tmp_path / 'out.ttl'
    ob.save(out, fmt='turtle')
    content = out.read_text(encoding='utf-8')
    assert 'owl:Axiom' not in content
    assert 'orphan' not in content

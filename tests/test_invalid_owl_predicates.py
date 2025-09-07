import logging
from rdflib import Namespace
from rdflib.namespace import OWL

from ontology_guided.ontology_builder import OntologyBuilder


def test_invalid_owl_predicates_filtered(tmp_path, caplog):
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = (
        "@prefix ex: <http://example.com/> .\n"
        "ex:A owl:datatype ex:B .\n"
    )
    logger = logging.getLogger(__name__)
    with caplog.at_level(logging.WARNING):
        triples = ob.parse_turtle(ttl, logger=logger)
    # Triple should be discarded entirely
    assert not triples

    out = tmp_path / "out.ttl"
    ob.save(out, fmt="turtle")
    text = out.read_text(encoding="utf-8")
    assert "owl:datatype" not in text

    ex = Namespace("http://example.com/")
    owl_datatype = Namespace(str(OWL))["datatype"]
    assert (ex.A, owl_datatype, ex.B) not in ob.graph
    assert "owl#datatype" in caplog.text

import logging

import pytest

from ontology_guided.ontology_builder import OntologyBuilder, InvalidTurtleError


def test_parse_turtle_with_prefix():
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = """@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."""
    logger = logging.getLogger(__name__)
    triples = ob.parse_turtle(ttl, logger=logger)
    ob.add_provenance("req", triples)
    assert len(ob.graph) == 1
    assert ob.triple_provenance


def test_parse_turtle_bad_syntax():
    ob = OntologyBuilder('http://example.com/atm#')
    bad_ttl = "invalid ttl"
    logger = logging.getLogger(__name__)
    with pytest.raises(InvalidTurtleError):
        ob.parse_turtle(bad_ttl, logger=logger, snippet_index=1)


def test_import_external_ontology(tmp_path):
    ext = tmp_path / "ext.ttl"
    ext.write_text(
        """@prefix ex: <http://example.com/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
ex:ClassA a owl:Class .
""",
        encoding="utf-8",
    )
    ob = OntologyBuilder('http://example.com/atm#', ontology_files=[str(ext)])
    classes, _ = ob.get_available_terms()
    assert "ex:ClassA" in classes
    assert "@prefix ex:" in ob.header

import logging
from pathlib import Path

import pytest

from ontology_guided.ontology_builder import OntologyBuilder, InvalidTurtleError
from rdflib import Namespace
from rdflib.namespace import RDF, OWL


def test_parse_turtle_with_prefix():
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = """@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."""
    logger = logging.getLogger(__name__)
    initial_len = len(ob.graph)
    triples = ob.parse_turtle(ttl, logger=logger)
    ob.add_provenance("req", triples)
    assert len(ob.graph) == initial_len + 1
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
    terms = ob.get_available_terms()
    assert "ex:ClassA" in terms["classes"]


def test_domain_range_and_synonyms(tmp_path):
    ext = tmp_path / "ext.ttl"
    ext.write_text(
        """@prefix ex: <http://example.com/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex:A a owl:Class .
ex:B a owl:Class .
ex:prop a owl:ObjectProperty ;
    rdfs:domain ex:A ;
    rdfs:range ex:B .
""",
        encoding="utf-8",
    )
    lex = Path(__file__).resolve().parent.parent / "ontologies" / "lexical.ttl"
    ob = OntologyBuilder(
        'http://example.com/atm#',
        ontology_files=[str(ext), str(lex)],
    )
    terms = ob.get_available_terms()
    assert terms["domain_range_hints"]["ex:prop"] == {
        "domain": ["ex:A"],
        "range": ["ex:B"],
    }
    assert any(
        k.split(":")[-1] == "quick" and v.split(":")[-1] == "fast"
        for k, v in terms["synonyms"].items()
    )


def test_custom_lexical_namespace(tmp_path):
    lex = tmp_path / "lex.ttl"
    lex.write_text(
        """@prefix foo: <http://example.com/foo#> .\n"""
        "foo:a foo:synonym foo:b .\n",
        encoding="utf-8",
    )
    ob = OntologyBuilder(
        'http://example.com/atm#',
        ontology_files=[str(lex)],
        lexical_namespace="http://example.com/foo#",
    )
    terms = ob.get_available_terms()
    assert terms["synonyms"]["foo:a"] == "foo:b"


def test_strict_terms_filters_unknown(tmp_path, caplog):
    ext = tmp_path / "ext.ttl"
    ext.write_text(
        """@prefix ex: <http://example.com/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
ex:A a owl:Class .
ex:knownProp a owl:ObjectProperty .
""",
        encoding="utf-8",
    )
    ob = OntologyBuilder('http://example.com/atm#', ontology_files=[str(ext)])
    ttl = (
        "@prefix ex: <http://example.com/> .\n"
        "ex:x ex:knownProp ex:A .\n"
        "ex:x ex:unknownProp ex:A .\n"
        "ex:x a ex:A .\n"
        "ex:x a ex:UnknownClass .\n"
    )
    logger = logging.getLogger(__name__)
    with caplog.at_level(logging.WARNING):
        triples = ob.parse_turtle(ttl, logger=logger, strict_terms=True)
    assert len(triples) == 2
    assert not any("unknownProp" in str(p) for _, p, _ in triples)
    assert not any("UnknownClass" in str(o) for _, _, o in triples)
    assert "unknownProp" in caplog.text
    assert "UnknownClass" in caplog.text


def test_parse_turtle_applies_synonym():
    lex = Path(__file__).resolve().parent.parent / "ontologies" / "lexical.ttl"
    ob = OntologyBuilder('http://example.com/atm#', ontology_files=[str(lex)])
    ttl = "ex:quick lex:antonym ex:quick ."
    logger = logging.getLogger(__name__)
    triples = ob.parse_turtle(ttl, logger=logger)
    nm = ob.graph.namespace_manager
    ex_fast = nm.expand_curie("ex:fast")
    ex_quick = nm.expand_curie("ex:quick")
    lex_antonym = nm.expand_curie("lex:antonym")
    assert (ex_fast, lex_antonym, ex_fast) in ob.graph
    assert (ex_quick, lex_antonym, ex_quick) not in ob.graph
    assert triples == [(ex_fast, lex_antonym, ex_fast)]


def test_conflicting_types_are_removed():
    ob = OntologyBuilder('http://example.com/atm#')
    ttl = """@prefix ex: <http://example.com/> .\nex:Foo a owl:Class, owl:DatatypeProperty ."""
    ob.parse_turtle(ttl)
    ex = Namespace("http://example.com/")
    ex_foo = ex.Foo
    assert (ex_foo, RDF.type, OWL.Class) in ob.graph
    assert (ex_foo, RDF.type, OWL.DatatypeProperty) not in ob.graph


def test_conflicting_types_across_snippets():
    """Later declarations should clean up earlier conflicting ones."""
    ob = OntologyBuilder('http://example.com/atm#')
    ttl1 = "@prefix ex: <http://example.com/> .\nex:Bar a owl:DatatypeProperty ."
    ttl2 = "@prefix ex: <http://example.com/> .\nex:Bar a owl:Class ."
    ob.parse_turtle(ttl1)
    ob.parse_turtle(ttl2)
    ex = Namespace("http://example.com/")
    ex_bar = ex.Bar
    assert (ex_bar, RDF.type, OWL.Class) in ob.graph
    assert (ex_bar, RDF.type, OWL.DatatypeProperty) not in ob.graph


def test_save_includes_base_and_ontology(tmp_path):
    ob = OntologyBuilder('http://example.com/atm#')
    out = tmp_path / 'out.ttl'
    ob.save(out, fmt='turtle')
    content = out.read_text(encoding='utf-8')
    assert content.startswith(
        '@prefix : <http://example.com/atm#> .\n@prefix owl: <http://www.w3.org/2002/07/owl#> .'
    )
    assert '<http://example.com/atm> rdf:type owl:Ontology .' in content

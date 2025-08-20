from pathlib import Path
from ontology_guided.validator import SHACLValidator


def _write_temp(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_validation_conforming(tmp_path):
    data = """@prefix atm: <http://example.com/atm#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

atm:alice a atm:User ;
    atm:owns atm:acc123 .
atm:acc123 a atm:Account ;
    atm:balance "100.0"^^xsd:decimal .
atm:atm1 a atm:ATM ;
    atm:location "Center"^^xsd:string ;
    atm:logs atm:tx1 .
atm:tx1 a atm:Transaction ;
    atm:actor atm:alice ;
    atm:target atm:acc123 ;
    atm:amount "10.0"^^xsd:decimal .

atm:cash a atm:Item .
atm:act1 a atm:Action ;
    atm:actor atm:alice ;
    atm:object atm:cash .

atm:insert1 a atm:CardInsertion ;
    atm:after atm:tx1 .
"""
    data_path = _write_temp(tmp_path, "valid.ttl", data)
    shapes_path = Path(__file__).resolve().parent.parent / "shapes.ttl"
    validator = SHACLValidator(data_path, str(shapes_path))
    conforms, results = validator.run_validation()
    assert conforms
    assert results == []


def test_validation_non_conforming(tmp_path):
    data = """@prefix atm: <http://example.com/atm#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

atm:alice a atm:User ;
    atm:owns atm:acc123 .
atm:acc123 a atm:Account ;
    atm:balance "100.0"^^xsd:decimal .
atm:cash a atm:Item .
atm:act1 a atm:Action ;
    atm:actor atm:alice ;
    atm:object atm:cash .
atm:atm1 a atm:ATM ;
    atm:location "Center"^^xsd:string ;
    atm:logs atm:act1 .
"""
    data_path = _write_temp(tmp_path, "invalid.ttl", data)
    shapes_path = Path(__file__).resolve().parent.parent / "shapes.ttl"
    validator = SHACLValidator(data_path, str(shapes_path))
    conforms, results = validator.run_validation()
    assert not conforms
    assert isinstance(results, list)
    assert all(
        {
            "focusNode",
            "resultPath",
            "message",
            "sourceShape",
            "resultSeverity",
            "sourceConstraintComponent",
            "expected",
            "value",
        }
        <= r.keys()
        for r in results
    )


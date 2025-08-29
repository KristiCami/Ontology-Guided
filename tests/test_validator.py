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
    conforms, results, summary = validator.run_validation()
    assert conforms
    assert results == []
    assert summary == {"total": 0, "bySeverity": {}, "byShapePath": {}}


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
    conforms, results, summary = validator.run_validation()
    assert not conforms
    assert isinstance(results, list)
    assert summary["total"] == len(results)
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
    assert summary["bySeverity"]["http://www.w3.org/ns/shacl#Violation"] == len(results)
    path_key = "http://example.com/atm#logs"
    assert any(
        counts.get(path_key) == len(results)
        for counts in summary["byShapePath"].values()
    )


def test_summary_counts_multiple_violations(tmp_path):
    data = """@prefix atm: <http://example.com/atm#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

atm:alice a atm:User ;
    atm:owns atm:acc1 .
atm:acc1 a atm:Account ;
    atm:balance "100"^^xsd:decimal .

atm:tx1 a atm:Transaction ;
    atm:target atm:acc1 ;
    atm:amount "50"^^xsd:decimal .
atm:tx2 a atm:Transaction ;
    atm:actor atm:alice ;
    atm:target atm:acc1 .

atm:act1 a atm:Action ;
    atm:actor atm:alice .
"""
    data_path = _write_temp(tmp_path, "multi_invalid.ttl", data)
    shapes_path = Path(__file__).resolve().parent.parent / "shapes.ttl"
    validator = SHACLValidator(data_path, str(shapes_path))
    conforms, results, summary = validator.run_validation()
    assert not conforms
    assert summary["total"] == 3
    sev_key = "http://www.w3.org/ns/shacl#Violation"
    assert summary["bySeverity"].get(sev_key) == 3
    actor_count = sum(
        d.get("http://example.com/atm#actor", 0)
        for d in summary["byShapePath"].values()
    )
    amount_count = sum(
        d.get("http://example.com/atm#amount", 0)
        for d in summary["byShapePath"].values()
    )
    object_count = sum(
        d.get("http://example.com/atm#object", 0)
        for d in summary["byShapePath"].values()
    )
    assert actor_count == 1
    assert amount_count == 1
    assert object_count == 1


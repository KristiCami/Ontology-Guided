from pathlib import Path
from ontology_guided.validator import SHACLValidator


def _write_temp(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_validation_conforming(tmp_path):
    data = """@prefix atm: <http://example.com/atm#> .

atm:alice a atm:User .
atm:acc123 a atm:Account .
atm:tx1 a atm:Transaction ;
    atm:actor atm:alice ;
    atm:target atm:acc123 .

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
    conforms, _, _ = validator.run_validation()
    assert conforms


def test_validation_non_conforming(tmp_path):
    data = """@prefix atm: <http://example.com/atm#> .

atm:device1 a atm:Device .
atm:acc123 a atm:Account .
atm:tx2 a atm:Transaction ;
    atm:actor atm:device1 ;
    atm:target atm:acc123 .
"""
    data_path = _write_temp(tmp_path, "invalid.ttl", data)
    shapes_path = Path(__file__).resolve().parent.parent / "shapes.ttl"
    validator = SHACLValidator(data_path, str(shapes_path))
    conforms, _, _ = validator.run_validation()
    assert not conforms


from validator import SHACLValidator


def test_run_validation(tmp_path):
    shapes = """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix atm: <http://example.com/atm#> .

atm:ActionShape a sh:NodeShape ;
    sh:targetClass atm:Action ;
    sh:property [
        sh:path atm:actor ;
        sh:minCount 1 ;
    ] .
"""
    valid = """@prefix atm: <http://example.com/atm#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

atm:act1 a atm:Action ;
    atm:actor atm:ATM .
"""
    invalid = """@prefix atm: <http://example.com/atm#> .
atm:act2 a atm:Action .
"""
    shapes_file = tmp_path / "shapes.ttl"
    data_file = tmp_path / "data.ttl"
    shapes_file.write_text(shapes, encoding="utf-8")
    data_file.write_text(valid, encoding="utf-8")
    validator = SHACLValidator(str(data_file), str(shapes_file))
    conforms, _, _ = validator.run_validation()
    assert conforms
    data_file.write_text(invalid, encoding="utf-8")
    validator = SHACLValidator(str(data_file), str(shapes_file))
    conforms, _, _ = validator.run_validation()
    assert not conforms
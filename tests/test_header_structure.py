from ontology_guided.ontology_builder import OntologyBuilder


def test_header_and_ontology_elements(tmp_path):
    ob = OntologyBuilder('http://lod.csd.auth.gr/atm/atm.ttl#')
    results_dir = tmp_path / 'results'
    results_dir.mkdir()
    ttl_file = results_dir / 'combined.ttl'
    owl_file = results_dir / 'combined.owl'
    ob.save(ttl_file, fmt='turtle')
    ob.save(owl_file, fmt='xml')

    ttl_lines = ttl_file.read_text(encoding='utf-8').splitlines()
    expected_header = [
        '@prefix : <http://lod.csd.auth.gr/atm/atm.ttl#> .',
        '@prefix owl: <http://www.w3.org/2002/07/owl#> .',
        '@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .',
        '@prefix xml: <http://www.w3.org/XML/1998/namespace> .',
        '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .',
        '@prefix xsp: <http://www.owl-ontologies.com/2005/08/07/xsp.owl#> .',
        '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .',
        '@prefix swrl: <http://www.w3.org/2003/11/swrl#> .',
        '@prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .',
        '@prefix protege: <http://protege.stanford.edu/plugins/owl/protege#> .',
        '@base <http://lod.csd.auth.gr/atm/atm.ttl#> .',
        '',
        '<http://lod.csd.auth.gr/atm/atm.ttl> rdf:type owl:Ontology .',
    ]
    assert ttl_lines[: len(expected_header)] == expected_header

    non_prefix = [line for line in ttl_lines if line and not line.startswith('@')]
    assert non_prefix[0] == '<http://lod.csd.auth.gr/atm/atm.ttl> rdf:type owl:Ontology .'

    import xml.etree.ElementTree as ET
    root = ET.fromstring(owl_file.read_text(encoding='utf-8'))
    first_child = next(iter(root))
    assert first_child.tag.endswith('Ontology')

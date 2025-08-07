import logging

from rdflib import Graph
from rdflib.namespace import RDF, RDFS, OWL, XSD


class OntologyBuilder:
    """Μετατρέπει τμήματα Turtle σε ενιαία οντολογία."""

    def __init__(self, base_iri: str, ontology_files=None):
        if not base_iri.endswith("#"):
            base_iri += "#"
        self.base_iri = base_iri
        self.graph = Graph()
        self.graph.bind("atm", self.base_iri)
        if ontology_files:
            for path in ontology_files:
                self.graph.parse(path)
        self._build_header()
        self._extract_available_terms()

    def _build_header(self):
        prefixes = {
            "atm": self.base_iri,
            "rdf": str(RDF),
            "rdfs": str(RDFS),
            "owl": str(OWL),
            "xsd": str(XSD),
        }
        for prefix, uri in self.graph.namespaces():
            if prefix and prefix not in prefixes:
                prefixes[prefix] = str(uri)
        self.header = "".join(
            f"@prefix {p}: <{u}> .\n" for p, u in prefixes.items()
        )

    def _extract_available_terms(self):
        nm = self.graph.namespace_manager
        classes = [
            nm.normalizeUri(c)
            for c in self.graph.subjects(RDF.type, OWL.Class)
        ]
        props = []
        for t in (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty):
            props.extend(nm.normalizeUri(p) for p in self.graph.subjects(RDF.type, t))
        self.available_classes = sorted(set(classes))
        self.available_properties = sorted(set(props))

    def get_available_terms(self):
        return self.available_classes, self.available_properties

    def parse_turtle(self, turtle_str: str, logger: logging.Logger | None = None):
        lines = [line for line in turtle_str.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        data = self.header + "\n" + cleaned
        if logger:
            logger.debug("=== Turtle input to rdflib.parse ===")
            logger.debug(data)
            logger.debug("=== End of Turtle ===")
        self.graph.parse(data=data, format="turtle")
        self._extract_available_terms()

    def save(self, file_path: str, fmt: str = "turtle"):
        """Αποθηκεύει την οντολογία σε αρχείο."""
        self.graph.serialize(destination=file_path, format=fmt)


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.DEBUG)
    BASE_IRI = "http://example.com/atm#"
    os.makedirs("results", exist_ok=True)
    with open("results/llm_output.ttl", "r", encoding="utf-8") as f:
        ttl = f.read()
    ob = OntologyBuilder(BASE_IRI)
    logger = logging.getLogger(__name__)
    ob.parse_turtle(ttl, logger=logger)
    ob.save("results/combined.ttl", fmt="turtle")
    ob.save("results/combined.owl", fmt="xml")
    print("Saved results/combined.ttl and results/combined.owl")

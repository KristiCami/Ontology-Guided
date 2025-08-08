import logging
from typing import Optional

from rdflib import Graph
from rdflib.namespace import RDF, RDFS, OWL, XSD
from rdflib.plugins.parsers.notation3 import BadSyntax


class InvalidTurtleError(ValueError):
    """Raised when Turtle parsing fails."""
    pass


class OntologyBuilder:
    """Μετατρέπει τμήματα Turtle σε ενιαία οντολογία."""

    def __init__(self, base_iri: str, prefix: Optional[str] = None, ontology_files=None):
        if not base_iri.endswith("#"):
            base_iri += "#"
        self.base_iri = base_iri
        self.prefix = prefix or base_iri.rstrip("#").split("/")[-1]
        self.graph = Graph()
        self.graph.bind(self.prefix, self.base_iri)
        if ontology_files:
            for path in ontology_files:
                self.graph.parse(path)
        self._build_header()
        self._extract_available_terms()

    def _build_header(self):
        prefixes = {
            self.prefix: self.base_iri,
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

    def parse_turtle(
        self,
        turtle_str: str,
        logger: Optional[logging.Logger] = None,
        requirement: Optional[str] = None,
        snippet_index: Optional[int] = None,
    ):
        lines = [line for line in turtle_str.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        data = self.header + "\n" + cleaned
        if logger:
            logger.debug("=== Turtle input to rdflib.parse ===")
            logger.debug(data)
            logger.debug("=== End of Turtle ===")
        try:
            self.graph.parse(data=data, format="turtle")
        except BadSyntax as exc:
            if logger:
                idx = f" snippet_index={snippet_index}" if snippet_index is not None else ""
                req = f" requirement={requirement!r}" if requirement is not None else ""
                logger.exception(
                    "Failed to parse Turtle%s%s. Snippet:\n%s",
                    idx,
                    req,
                    data,
                )
            raise InvalidTurtleError("Invalid Turtle input") from exc
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

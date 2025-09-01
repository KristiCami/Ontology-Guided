import logging
from typing import Optional

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, Namespace
from rdflib.plugins.parsers.notation3 import BadSyntax


class InvalidTurtleError(ValueError):
    """Raised when Turtle parsing fails."""
    pass


class OntologyBuilder:
    """Μετατρέπει τμήματα Turtle σε ενιαία οντολογία."""

    def __init__(
        self,
        base_iri: str,
        prefix: Optional[str] = None,
        ontology_files=None,
        lexical_namespace: str = "http://example.com/lexical#",
    ):
        if not base_iri.endswith("#"):
            base_iri += "#"
        self.base_iri = base_iri
        self.prefix = prefix or base_iri.rstrip("#").split("/")[-1]
        self.lexical_namespace = lexical_namespace
        self.graph = Graph()
        self.graph.bind(self.prefix, self.base_iri)
        ontology_iri = URIRef(self.base_iri.rstrip("#"))
        self.graph.add((ontology_iri, RDF.type, OWL.Ontology))
        if ontology_files:
            for path in ontology_files:
                self.graph.parse(path)
        self._build_header()
        self._extract_available_terms()
        self.triple_provenance: dict[str, dict] = {}
        self._triple_counter = 0

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
        header_lines = [f"@base <{self.base_iri}> .\n"]
        header_lines += [f"@prefix {p}: <{u}> .\n" for p, u in prefixes.items()]
        self.header = "".join(header_lines)

    def _extract_available_terms(self):
        nm = self.graph.namespace_manager
        classes = [
            nm.normalizeUri(c)
            for c in self.graph.subjects(RDF.type, OWL.Class)
        ]

        prop_uris = []
        for t in (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty):
            for p in self.graph.subjects(RDF.type, t):
                prop_uris.append(p)

        props = [nm.normalizeUri(p) for p in prop_uris]
        self.available_classes = sorted(set(classes))
        self.available_properties = sorted(set(props))

        # Build domain/range hints for properties
        hints: dict[str, dict[str, list[str]]] = {}
        for p in prop_uris:
            key = nm.normalizeUri(p)
            domains = [nm.normalizeUri(o) for o in self.graph.objects(p, RDFS.domain)]
            ranges = [nm.normalizeUri(o) for o in self.graph.objects(p, RDFS.range)]
            if domains or ranges:
                entry: dict[str, list[str]] = {}
                if domains:
                    entry["domain"] = domains
                if ranges:
                    entry["range"] = ranges
                hints[key] = entry
        self.domain_range_hints = hints

        # Extract synonym mappings from lexical ontology if present
        syn_map: dict[str, str] = {}
        if self.lexical_namespace:
            LEX = Namespace(self.lexical_namespace)
            for s, o in self.graph.subject_objects(LEX.synonym):
                syn_map[nm.normalizeUri(s)] = nm.normalizeUri(o)
        self.synonym_map = syn_map

    def get_available_terms(self):
        return {
            "classes": self.available_classes,
            "properties": self.available_properties,
            "domain_range_hints": self.domain_range_hints,
            "synonyms": self.synonym_map,
        }

    def parse_turtle(
        self,
        turtle_str: str,
        logger: Optional[logging.Logger] = None,
        requirement: Optional[str] = None,
        snippet_index: Optional[int] = None,
        strict_terms: bool = False,
    ):
        lines = [line for line in turtle_str.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        data = self.header + "\n" + cleaned
        if logger:
            logger.debug("=== Turtle input to rdflib.parse ===")
            logger.debug(data)
            logger.debug("=== End of Turtle ===")
        try:
            temp_graph = Graph()
            temp_graph.parse(data=data, format="turtle")
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
        triples = list(temp_graph.triples((None, None, None)))
        if strict_terms:
            nm = self.graph.namespace_manager
            props = set(self.available_properties)
            classes = set(self.available_classes)
            synonyms = self.synonym_map
            kept_triples = []
            log = logger or logging.getLogger(__name__)
            for s, p, o in triples:
                p_norm = nm.normalizeUri(p)
                keep = False
                if p_norm in props:
                    keep = True
                elif p in (RDF.type, RDFS.subClassOf, OWL.equivalentClass):
                    o_norm = nm.normalizeUri(o)
                    if (
                        o_norm in classes
                        or o_norm in synonyms
                        or synonyms.get(o_norm) in classes
                    ):
                        keep = True
                if keep:
                    kept_triples.append((s, p, o))
                else:
                    log.warning(
                        "Discarded triple due to unknown terms: %s %s %s",
                        s.n3(nm),
                        p.n3(nm),
                        o.n3(nm),
                    )
            triples = kept_triples
        nm = self.graph.namespace_manager
        syn_map = self.synonym_map
        canonical_triples = []
        for s, p, o in triples:
            if isinstance(s, URIRef):
                s_norm = nm.normalizeUri(s)
                if s_norm in syn_map:
                    s = nm.expand_curie(syn_map[s_norm])
            if isinstance(o, URIRef):
                o_norm = nm.normalizeUri(o)
                if o_norm in syn_map:
                    o = nm.expand_curie(syn_map[o_norm])
            self.graph.add((s, p, o))
            canonical_triples.append((s, p, o))
        self._extract_available_terms()
        return canonical_triples

    def add_provenance(self, requirement: str, triples):
        """Map generated triples to the originating requirement."""
        triple_ids = []
        for s, p, o in triples:
            self._triple_counter += 1
            tid = f"t{self._triple_counter}"
            self.triple_provenance[tid] = {
                "requirement": requirement,
                "triple": (str(s), str(p), str(o)),
            }
            triple_ids.append(tid)
        return triple_ids

    def save(self, file_path: str, fmt: str = "turtle"):
        """Αποθηκεύει την οντολογία σε αρχείο."""
        self.graph.serialize(destination=file_path, format=fmt, base=self.base_iri)


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

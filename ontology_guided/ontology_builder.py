import logging
from typing import Optional

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, Namespace
from rdflib.plugins.parsers.notation3 import BadSyntax
from xml.etree import ElementTree as ET


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
        # default prefix is empty so that output uses ':'
        self.prefix = prefix if prefix is not None else ""
        self.lexical_namespace = lexical_namespace
        self.graph = Graph()
        self.graph.bind(self.prefix, self.base_iri)
        # bind common prefixes for consistent header generation
        self.graph.bind("owl", OWL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("xml", Namespace("http://www.w3.org/XML/1998/namespace"))
        self.graph.bind("xsd", XSD)
        self.graph.bind("xsp", Namespace("http://www.owl-ontologies.com/2005/08/07/xsp.owl#"))
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("swrl", Namespace("http://www.w3.org/2003/11/swrl#"))
        self.graph.bind("swrlb", Namespace("http://www.w3.org/2003/11/swrlb#"))
        self.graph.bind("protege", Namespace("http://protege.stanford.edu/plugins/owl/protege#"))
        initial_ns = {p for p, _ in self.graph.namespaces()}

        ontology_iri = URIRef(self.base_iri.rstrip("#"))
        self.graph.add((ontology_iri, RDF.type, OWL.Ontology))
        if ontology_files:
            for path in ontology_files:
                self.graph.parse(path)
        extra = []
        for p, u in self.graph.namespaces():
            if p and p not in initial_ns:
                extra.append((p, str(u)))
        self.extra_prefixes = extra
        self._build_header()
        self._extract_available_terms()
        self.triple_provenance: dict[str, dict] = {}
        self._triple_counter = 0

    def _build_header(self):
        ordered = [
            (self.prefix, self.base_iri),
            ("owl", str(OWL)),
            ("rdf", str(RDF)),
            ("xml", "http://www.w3.org/XML/1998/namespace"),
            ("xsd", str(XSD)),
            ("xsp", "http://www.owl-ontologies.com/2005/08/07/xsp.owl#"),
            ("rdfs", str(RDFS)),
            ("swrl", "http://www.w3.org/2003/11/swrl#"),
            ("swrlb", "http://www.w3.org/2003/11/swrlb#"),
            ("protege", "http://protege.stanford.edu/plugins/owl/protege#"),
        ]
        lines = [f"@prefix {p}: <{u}> .\n" for p, u in ordered + self.extra_prefixes]
        lines.append(f"@base <{self.base_iri}> .\n\n")
        self.header = "".join(lines)

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
        ontology_iri = URIRef(self.base_iri.rstrip("#"))
        if fmt == "turtle":
            temp = Graph()
            for pfx, uri in self.graph.namespaces():
                temp.bind(pfx, uri)
            for s, p, o in self.graph.triples((None, None, None)):
                if (s, p, o) != (ontology_iri, RDF.type, OWL.Ontology):
                    temp.add((s, p, o))
            body = temp.serialize(format="turtle")
            body_lines = [
                line
                for line in body.splitlines()
                if line and not line.startswith("@prefix") and not line.startswith("@base")
            ]
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write(self.header)
                fh.write(f"<{ontology_iri}> rdf:type owl:Ontology .\n")
                for line in body_lines:
                    fh.write(line + "\n")
        elif fmt == "xml":
            xml_graph = Graph()
            for triple in self.graph.triples((None, None, None)):
                xml_graph.add(triple)
            xml_data = xml_graph.serialize(format="pretty-xml", xml_base=self.base_iri)
            root = ET.fromstring(xml_data)
            ontology_elem = None
            others = []
            for child in list(root):
                if child.tag.endswith("Ontology"):
                    ontology_elem = child
                else:
                    others.append(child)
            if ontology_elem is not None:
                root[:] = [ontology_elem] + others
            xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            with open(file_path, "wb") as fh:
                fh.write(xml_bytes)
        else:
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

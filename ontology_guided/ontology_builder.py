import logging
from collections import defaultdict
from typing import Optional

import re

from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, Namespace
from rdflib.plugins.parsers.notation3 import BadSyntax
from xml.etree import ElementTree as ET


# Common OWL predicates that are permitted in generated snippets. Any triple
# using an ``owl:`` predicate not present in this set will be discarded to avoid
# introducing malformed vocabulary into the ontology.
ALLOWED_OWL_PREDICATES = {
    OWL.onProperty,
    OWL.someValuesFrom,
    OWL.allValuesFrom,
    OWL.hasValue,
    OWL.cardinality,
    OWL.minCardinality,
    OWL.maxCardinality,
    OWL.equivalentClass,
    OWL.equivalentProperty,
    OWL.disjointWith,
    OWL.intersectionOf,
    OWL.unionOf,
    OWL.complementOf,
    OWL.sameAs,
    OWL.differentFrom,
    OWL.inverseOf,
}


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
        # bind common prefixes for consistent header generation
        self.standard_prefixes = [
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
        for p, u in self.standard_prefixes:
            self.graph.bind(p, Namespace(u))
        # capture the allowed prefixes so later saves avoid leaking extra ones
        self.allowed_prefixes = {p for p, _ in self.graph.namespaces()}

        ontology_iri = URIRef(self.base_iri.rstrip("#"))
        self.graph.add((ontology_iri, RDF.type, OWL.Ontology))
        # build the header before parsing external ontologies so only standard
        # prefixes appear in the output header
        self._build_header()

        if ontology_files:
            for path in ontology_files:
                self.graph.parse(path)
        self._extract_available_terms()
        self.triple_provenance: dict[str, dict] = {}
        self._triple_counter = 0

    def _build_header(self):
        # store prefix and base lines separately so save() can control ordering
        self.prefix_lines = [
            f"@prefix {p}: <{u}> .\n" for p, u in self.standard_prefixes
        ]

        self.base_line = f"@base <{self.base_iri}> .\n"
        # header is used when parsing snippets and expects a blank line after @base
        self.header = "".join(self.prefix_lines + [self.base_line, "\n"])

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

    def _remove_conflicting_types(self, triples):
        """Filter out rdf:type triples that declare incompatible types.

        LLM generated snippets occasionally assign both class and property
        types to the same resource (e.g. `ex:Foo a owl:Class, owl:DatatypeProperty`).
        Such declarations cause Protégé to fail when loading the ontology. This
        helper keeps a single, sensible type:

        * If an entity is declared as a class or individual, property types are
          dropped.
        * If an entity is declared as both object and datatype property, the
          datatype property declaration is removed.
        """
        type_map: dict = defaultdict(set)
        # collect existing type assertions from the graph so that conflicts
        # can be detected across multiple snippets
        for s, o in self.graph.subject_objects(RDF.type):
            type_map[s].add(o)
        for s, p, o in triples:
            if p == RDF.type:
                type_map[s].add(o)

        cleaned = []
        for s, p, o in triples:
            if p == RDF.type:
                types = type_map[s]
                # classes or individuals take precedence over property types
                if (
                    OWL.Class in types
                    or RDFS.Class in types
                    or OWL.NamedIndividual in types
                ) and (
                    o in (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty)
                ):
                    continue
                # prefer object properties when both are present
                if (
                    OWL.ObjectProperty in types
                    and OWL.DatatypeProperty in types
                    and o == OWL.DatatypeProperty
                ):
                    continue
            cleaned.append((s, p, o))

        # remove conflicting property type declarations already stored in the graph
        for s, types in type_map.items():
            if (
                OWL.Class in types
                or RDFS.Class in types
                or OWL.NamedIndividual in types
            ):
                for t in (
                    OWL.ObjectProperty,
                    OWL.DatatypeProperty,
                    OWL.AnnotationProperty,
                ):
                    self.graph.remove((s, RDF.type, t))
            elif OWL.ObjectProperty in types and OWL.DatatypeProperty in types:
                self.graph.remove((s, RDF.type, OWL.DatatypeProperty))

        return cleaned

    def _filter_invalid_iris(self, triples):
        """Drop triples containing IRIs that are not absolute.

        LLM generated snippets sometimes use placeholders such as
        ``<Actor:Customer>`` which are parsed by rdflib but later cause
        OWL editors like Protégé to fail when loading the ontology.
        These IRIs lack a valid scheme (e.g. ``http`` or ``https``).
        To keep the resulting file robust we simply discard any triple
        where a subject, predicate or object IRI does not start with an
        absolute HTTP(S) scheme.
        """

        def is_valid(term):
            if isinstance(term, URIRef):
                return str(term).startswith(("http://", "https://"))
            return True

        return [t for t in triples if all(is_valid(part) for part in t)]

    def _filter_invalid_owl_predicates(self, triples, logger=None):
        """Remove triples using unsupported predicates from the OWL namespace.

        Generated snippets occasionally invent predicates within the OWL
        namespace, such as ``owl:datatype``. These are not part of the OWL
        vocabulary and can cause downstream tools to reject the ontology. This
        helper discards any triple whose predicate is in the OWL namespace but
        not explicitly whitelisted in ``ALLOWED_OWL_PREDICATES``.
        """

        log = logger or logging.getLogger(__name__)
        cleaned = []
        for s, p, o in triples:
            if isinstance(p, URIRef) and str(p).startswith(str(OWL)):
                if p not in ALLOWED_OWL_PREDICATES:
                    log.warning(
                        "Dropping triple with unsupported OWL predicate: %s %s %s",
                        s,
                        p,
                        o,
                    )
                    continue
            cleaned.append((s, p, o))
        return cleaned

    def _drop_empty_restrictions(self, triples, logger=None):
        """Remove anonymous Restriction nodes lacking owl:onProperty.

        Some generated snippets include blank nodes declared as
        ``rdf:type owl:Restriction`` but omit the required
        ``owl:onProperty`` triple. These fragments are incomplete and are
        discarded entirely to keep the ontology consistent.
        """

        log = logger or logging.getLogger(__name__)
        bnodes = set()
        for s, p, o in triples:
            if isinstance(s, BNode) and p == RDF.type and o == OWL.Restriction:
                bnodes.add(s)
        for s, p, o in triples:
            if s in bnodes and p == OWL.onProperty:
                bnodes.remove(s)
        if not bnodes:
            return triples
        for bn in bnodes:
            log.warning(
                "Dropping anonymous owl:Restriction without owl:onProperty: %s",
                bn,
            )
        return [t for t in triples if all(part not in bnodes for part in t)]

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

        extra_prefix = []
        for p, u in self.graph.namespaces():
            if p and p not in self.allowed_prefixes:
                extra_prefix.append(f"@prefix {p}: <{u}> .\n")
        parse_header = self.header + "".join(extra_prefix)
        data = parse_header + "\n" + cleaned

        # Fix common prefix mistakes before parsing so rdflib succeeds
        corrections = {
            "rdf:domain": "rdfs:domain",
            "rdf:range": "rdfs:range",
            "rdf:label": "rdfs:label",
        }
        log = logger or logging.getLogger(__name__)
        for wrong, right in corrections.items():
            data, count = re.subn(rf"\b{wrong}\b", right, data)
            if count:
                log.warning("Corrected %s -> %s (%d)", wrong, right, count)

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
        # filter out unsupported owl:* predicates before further processing
        triples = self._filter_invalid_owl_predicates(triples, logger)
        # remove conflicting rdf:type declarations that confuse OWL editors
        triples = self._remove_conflicting_types(triples)
        # and drop any triples that use non-absolute IRIs
        triples = self._filter_invalid_iris(triples)
        # drop anonymous restrictions missing owl:onProperty
        triples = self._drop_empty_restrictions(triples, logger)
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
            for p, u in self.standard_prefixes:
                temp.bind(p, Namespace(u))

            ignore = [self.lexical_namespace]
            if self.lexical_namespace.endswith("#"):
                ignore.append(self.lexical_namespace.rsplit("#", 1)[0] + "/example#")

            def in_ignore(term):
                return isinstance(term, URIRef) and any(str(term).startswith(ns) for ns in ignore)

            for s, p, o in self.graph.triples((None, None, None)):
                if (s, p, o) == (ontology_iri, RDF.type, OWL.Ontology):
                    continue
                if in_ignore(s) or in_ignore(p) or in_ignore(o):
                    continue
                temp.add((s, p, o))

            body = temp.serialize(format="turtle")
            body = re.sub(r"(?<=\s)a(?=\s)", "rdf:type", body)
            body_lines = [
                line
                for line in body.splitlines()
                if line and not line.startswith("@prefix") and not line.startswith("@base")
            ]
            with open(file_path, "w", encoding="utf-8") as fh:
                for line in self.prefix_lines:
                    fh.write(line)
                fh.write(self.base_line)
                fh.write("\n")
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

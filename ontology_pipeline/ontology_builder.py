"""Builds RDFlib graphs from ``OntologyDraft`` definitions."""
from __future__ import annotations

from typing import Dict

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, URIRef

from .data_models import OntologyDraft
from .namespaces import BASE, LO, RBO


class OntologyBuilder:
    """Converts the structured output from the LLM into an OWL/RDF graph."""

    def __init__(self, base_namespace: Namespace = BASE) -> None:
        self.ns = base_namespace

    def build_graph(self, draft: OntologyDraft) -> Graph:
        graph = Graph()
        graph.bind("atm", self.ns)
        graph.bind("rbo", RBO)
        graph.bind("lo", LO)

        for cls in draft.classes:
            cls_uri = self._uri(cls.name)
            graph.add((cls_uri, RDF.type, RDFS.Class))
            if cls.parent:
                graph.add((cls_uri, RDFS.subClassOf, self._uri(cls.parent)))
            if cls.description:
                graph.add((cls_uri, RDFS.comment, Literal(cls.description)))

        for prop in draft.object_properties:
            prop_uri = self._uri(prop.name)
            graph.add((prop_uri, RDF.type, RDF.Property))
            if prop.domain:
                graph.add((prop_uri, RDFS.domain, self._uri(prop.domain)))
            if prop.range:
                graph.add((prop_uri, RDFS.range, self._uri(prop.range)))
            for characteristic in prop.characteristics:
                graph.add((prop_uri, self._characteristic_predicate(characteristic), Literal(True)))
            if prop.description:
                graph.add((prop_uri, RDFS.comment, Literal(prop.description)))

        for prop in draft.data_properties:
            prop_uri = self._uri(prop.name)
            graph.add((prop_uri, RDF.type, RDF.Property))
            if prop.domain:
                graph.add((prop_uri, RDFS.domain, self._uri(prop.domain)))
            if prop.range:
                graph.add((prop_uri, RDFS.range, Literal(prop.range)))

        for restriction in draft.restrictions:
            blank = BNode()
            graph.add((self._uri(restriction.subject), RDFS.subClassOf, blank))
            graph.add((blank, RDF.type, URIRef("http://www.w3.org/2002/07/owl#Restriction")))
            graph.add((blank, URIRef("http://www.w3.org/2002/07/owl#onProperty"), self._uri(restriction.property)))
            if restriction.restriction_type == "SomeValuesFrom":
                graph.add(
                    (
                        blank,
                        URIRef("http://www.w3.org/2002/07/owl#someValuesFrom"),
                        self._uri(restriction.target),
                    )
                )
            elif restriction.restriction_type == "AllValuesFrom":
                graph.add(
                    (
                        blank,
                        URIRef("http://www.w3.org/2002/07/owl#allValuesFrom"),
                        self._uri(restriction.target),
                    )
                )
            elif restriction.restriction_type.endswith("Cardinality") and restriction.cardinality is not None:
                predicate = URIRef(f"http://www.w3.org/2002/07/owl#{restriction.restriction_type}")
                graph.add((blank, predicate, Literal(restriction.cardinality)))

        for individual in draft.individuals:
            individual_uri = self._uri(individual.name)
            graph.add((individual_uri, RDF.type, self._uri(individual.class_name)))
            for prop_name, value in individual.properties.items():
                graph.add((individual_uri, self._uri(prop_name), self._uri(value)))

        return graph

    def _uri(self, name: str) -> URIRef:
        return URIRef(f"{self.ns}{name}")

    def _characteristic_predicate(self, name: str) -> URIRef:
        predicate = name.lower()
        mapping: Dict[str, str] = {
            "functional": "http://www.w3.org/2002/07/owl#FunctionalProperty",
            "inversefunctional": "http://www.w3.org/2002/07/owl#InverseFunctionalProperty",
            "transitive": "http://www.w3.org/2002/07/owl#TransitiveProperty",
        }
        iri = mapping.get(predicate, "http://example.org/characteristic#Unknown")
        return URIRef(iri)


__all__ = ["OntologyBuilder"]

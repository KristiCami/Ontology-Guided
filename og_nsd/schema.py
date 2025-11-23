"""Ontology schema extraction utilities for ontology-aware prompting."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from rdflib import Graph, OWL, RDF, RDFS, URIRef


@dataclass
class OntologyContext:
    """Structured vocabulary extracted from a gold ontology.

    The context intentionally excludes full axioms. It only contains the
    allowed vocabulary and typing constraints (domain/range) so the LLM can be
    guided without copying the gold solution.
    """

    classes: List[str]
    object_properties: Dict[str, Dict[str, str]]
    datatype_properties: Dict[str, Dict[str, str]]
    labels: Dict[str, str]
    prefixes: Dict[str, str]

    def as_prompt_section(self) -> str:
        """Render the context as a compact prompt section."""

        lines: List[str] = []
        if self.prefixes:
            lines.append("Prefixes:")
            for prefix, uri in sorted(self.prefixes.items()):
                lines.append(f"- {prefix}: <{uri}>")
            lines.append("")

        if self.classes:
            classes = ", ".join(sorted(self.classes))
            lines.append(f"Valid classes: {classes}")

        if self.object_properties:
            lines.append("Valid object properties (domain → range):")
            for name, meta in sorted(self.object_properties.items()):
                domain = meta.get("domain", "unspecified")
                range_ = meta.get("range", "unspecified")
                lines.append(f"- {name}: {domain} → {range_}")

        if self.datatype_properties:
            lines.append("Valid datatype properties (domain → datatype range):")
            for name, meta in sorted(self.datatype_properties.items()):
                domain = meta.get("domain", "unspecified")
                range_ = meta.get("range", "unspecified")
                lines.append(f"- {name}: {domain} → {range_}")

        if self.labels:
            lines.append("Labels/comments:")
            for name, label in sorted(self.labels.items()):
                lines.append(f"- {name}: {label}")

        return "\n".join(lines).strip()


def extract_ontology_context(path: Path, base_namespace: Optional[str] = None) -> OntologyContext:
    """Extract vocabulary-only schema context from a gold ontology."""

    graph = Graph()
    graph.parse(path)

    prefixes = {prefix: str(uri) for prefix, uri in graph.namespaces()}
    if base_namespace:
        prefixes.setdefault("atm", base_namespace)

    classes = sorted({_local_name(graph, cls) for cls in graph.subjects(RDF.type, OWL.Class)})

    object_properties: Dict[str, Dict[str, str]] = {}
    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        prop_name = _local_name(graph, prop)
        object_properties[prop_name] = {
            "domain": _local_name(graph, _first(graph.objects(prop, RDFS.domain))),
            "range": _local_name(graph, _first(graph.objects(prop, RDFS.range))),
        }

    datatype_properties: Dict[str, Dict[str, str]] = {}
    for prop in graph.subjects(RDF.type, OWL.DatatypeProperty):
        prop_name = _local_name(graph, prop)
        datatype_properties[prop_name] = {
            "domain": _local_name(graph, _first(graph.objects(prop, RDFS.domain))),
            "range": _local_name(graph, _first(graph.objects(prop, RDFS.range))),
        }

    labels: Dict[str, str] = {}
    for subject, label in graph.subject_objects(RDFS.label):
        labels[_local_name(graph, subject)] = str(label)

    return OntologyContext(
        classes=classes,
        object_properties=object_properties,
        datatype_properties=datatype_properties,
        labels=labels,
        prefixes=prefixes,
    )


def _local_name(graph: Graph, term: Optional[URIRef]) -> str:
    if term is None:
        return "unspecified"
    if not isinstance(term, URIRef):
        return str(term)
    try:
        qname = graph.qname(term)
    except Exception:
        qname = term.split("#")[-1] if "#" in term else str(term)
    if ":" in qname:
        return qname.split(":", 1)[1]
    return qname


def _first(items):
    for item in items:
        return item
    return None


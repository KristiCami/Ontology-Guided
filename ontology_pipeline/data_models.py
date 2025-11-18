"""Data models describing the ontology structures emitted by the LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class OntologyClass:
    """Represents a class declaration."""

    name: str
    parent: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ObjectProperty:
    name: str
    domain: Optional[str] = None
    range: Optional[str] = None
    characteristics: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class DataProperty:
    name: str
    domain: Optional[str] = None
    range: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Restriction:
    subject: str
    property: str
    target: str
    restriction_type: str
    cardinality: Optional[int] = None


@dataclass
class Individual:
    name: str
    class_name: str
    properties: Dict[str, str] = field(default_factory=dict)


@dataclass
class OntologyDraft:
    classes: List[OntologyClass] = field(default_factory=list)
    object_properties: List[ObjectProperty] = field(default_factory=list)
    data_properties: List[DataProperty] = field(default_factory=list)
    restrictions: List[Restriction] = field(default_factory=list)
    individuals: List[Individual] = field(default_factory=list)


__all__ = [
    "OntologyClass",
    "ObjectProperty",
    "DataProperty",
    "Restriction",
    "Individual",
    "OntologyDraft",
]

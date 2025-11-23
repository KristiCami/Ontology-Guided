"""Ontology graph assembly utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Optional

from rdflib import Graph, OWL, RDF, RDFS


@dataclass
class OntologyState:
    graph: Graph
    turtle_snippets: list[str]


@dataclass
class SchemaContext:
    """Structured vocabulary extracted from a gold ontology for grounding prompts."""

    classes: list[str]
    object_properties: Dict[str, Dict[str, str]]
    datatype_properties: Dict[str, Dict[str, str]]
    labels: Dict[str, str]
    prefixes: Dict[str, str]


class OntologyAssembler:
    def __init__(self, base_ontology_path: Optional[Path] = None) -> None:
        self.base_path = base_ontology_path

    def bootstrap(self) -> OntologyState:
        graph = Graph()
        snippets: list[str] = []
        if self.base_path and self.base_path.exists():
            graph.parse(self.base_path)
            snippets.append(self.base_path.read_text(encoding="utf-8"))
        return OntologyState(graph=graph, turtle_snippets=snippets)

    def add_turtle(self, state: OntologyState, turtle: str) -> None:
        cleaned = _ensure_standard_prefixes(_strip_code_fence(turtle))
        try:
            state.graph.parse(data=cleaned, format="turtle")
        except Exception as exc:  # pragma: no cover - requires rdflib parse error
            sanitized = _sanitize_turtle(cleaned)
            if sanitized != cleaned:
                try:
                    state.graph.parse(data=sanitized, format="turtle")
                except Exception as exc2:  # pragma: no cover - requires rdflib parse error
                    raise ValueError(
                        f"Failed to parse Turtle from LLM response after sanitization: {exc2}"
                    ) from exc2
                state.turtle_snippets.append(sanitized)
                return
            raise ValueError(f"Failed to parse Turtle from LLM response: {exc}") from exc
        state.turtle_snippets.append(cleaned)

    def serialize(self, state: OntologyState, path: Path) -> None:
        path.write_text(state.graph.serialize(format="turtle"), encoding="utf-8")


def load_schema_context(path: Path, base_namespace: str | None = None) -> SchemaContext:
    """Parse a Turtle ontology and extract a lightweight schema context.

    Only structural vocabulary is returned; axioms are intentionally omitted so the
    LLM receives guidance without an easy-to-copy solution. If ``base_namespace``
    is provided, terms outside that namespace are ignored.
    """

    graph = Graph()
    graph.parse(path)
    return extract_schema_context(graph, base_namespace)


def extract_schema_context(graph: Graph, base_namespace: str | None = None) -> SchemaContext:
    """Build a :class:`SchemaContext` from an rdflib graph."""

    def _qname(term) -> str:
        try:
            return graph.namespace_manager.normalizeUri(term)
        except Exception:  # pragma: no cover - rdflib normalization edge cases
            return str(term)

    def _in_scope(term) -> bool:
        return base_namespace is None or str(term).startswith(base_namespace)

    classes = {_qname(cls) for cls in graph.subjects(RDF.type, OWL.Class) if _in_scope(cls)}

    object_properties: Dict[str, Dict[str, str]] = {}
    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        if not _in_scope(prop):
            continue
        qname = _qname(prop)
        domain = next(graph.objects(prop, RDFS.domain), None)
        range_ = next(graph.objects(prop, RDFS.range), None)
        object_properties[qname] = {
            "domain": _qname(domain) if domain else "(unspecified)",
            "range": _qname(range_) if range_ else "(unspecified)",
        }

    datatype_properties: Dict[str, Dict[str, str]] = {}
    for prop in graph.subjects(RDF.type, OWL.DatatypeProperty):
        if not _in_scope(prop):
            continue
        qname = _qname(prop)
        domain = next(graph.objects(prop, RDFS.domain), None)
        range_ = next(graph.objects(prop, RDFS.range), None)
        datatype_properties[qname] = {
            "domain": _qname(domain) if domain else "(unspecified)",
            "range": _qname(range_) if range_ else "(unspecified)",
        }

    labels: Dict[str, str] = {}
    for subject, _, label in graph.triples((None, RDFS.label, None)):
        if not _in_scope(subject):
            continue
        labels[_qname(subject)] = str(label)

    prefixes = {prefix: str(uri) for prefix, uri in graph.namespace_manager.namespaces()}
    if base_namespace and not any(str(uri) == base_namespace for uri in prefixes.values()):
        prefixes["base"] = base_namespace

    return SchemaContext(
        classes=sorted(classes),
        object_properties=dict(sorted(object_properties.items())),
        datatype_properties=dict(sorted(datatype_properties.items())),
        labels=dict(sorted(labels.items())),
        prefixes=dict(sorted(prefixes.items())),
    )


_CODE_FENCE_RE = re.compile(r"```(?:turtle)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def _strip_code_fence(turtle: str) -> str:
    """Remove Markdown code fences often returned by LLMs."""

    match = _CODE_FENCE_RE.search(turtle)
    if match:
        return match.group(1).strip()
    return turtle.strip()


_STANDARD_PREFIXES = {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def _ensure_standard_prefixes(turtle: str) -> str:
    """Prepend common prefixes if they are referenced but not declared."""

    declared = {
        match.group(1).lower()
        for match in re.finditer(r"@prefix\s+([A-Za-z][\w-]*):", turtle)
    }
    missing = [
        f"@prefix {prefix}: <{uri}> ."
        for prefix, uri in _STANDARD_PREFIXES.items()
        if prefix not in declared
    ]
    if not missing:
        return turtle
    return "\n".join(missing + [turtle])


_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_QUOTED_PREFIX_RE = re.compile(r"'([A-Za-z][\w-]*:)")
_BYTE_LITERAL_RE = re.compile(r"^b['\"](.*)['\"]$", re.DOTALL)
_BARE_DECIMAL_RE = re.compile(r"(?<!\")([+-]?\d+(?:\.\d+)?)(\s*\^\^xsd:decimal)")


def _sanitize_turtle(turtle: str) -> str:
    """Apply lightweight heuristics to tolerate common LLM output glitches."""

    # Unwrap accidental Python byte-string reprs (e.g., "b'@prefix ...'")
    match = _BYTE_LITERAL_RE.match(turtle.strip())
    if match:
        turtle = match.group(1).replace("\\n", "\n")

    sanitized_lines = []
    for raw_line in turtle.splitlines():
        # Remove non-printable control characters that often sneak into LLM output
        line = _CONTROL_CHAR_RE.sub("", raw_line)

        # Remove accidental single quotes directly before prefixed names (e.g., 'atm:Class)
        line = _QUOTED_PREFIX_RE.sub(r"\1", line)

        # Ensure decimals are quoted so rdflib can parse them as literals
        if "^^xsd:decimal" in line and "\"" not in line:
            line = _BARE_DECIMAL_RE.sub(r'"\1"\2', line)

        stripped = line.lstrip()
        if stripped.upper().startswith("NOT "):
            sanitized_lines.append(f"# {line}" if not line.lstrip().startswith("#") else line)
            continue
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines)

"""Validation helpers for OG-NSD."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from rdflib import Graph
from pyshacl import validate

from .config import ValidationConfig
from .structures import ValidationResult


class OntologyValidator:
    """Run SHACL validation over generated Turtle snippets."""

    def __init__(self, config: ValidationConfig):
        self.config = config
        self._shapes_graph = Graph().parse(str(config.shacl_shapes))

    def validate_snippet(self, snippet: str) -> ValidationResult:
        data_graph = Graph().parse(data=snippet, format="turtle")
        conforms, report_graph, report_text = validate(
            data_graph,
            shacl_graph=self._shapes_graph,
            inference=self.config.inference,
            advanced=self.config.advanced,
            abort_on_first=self.config.abort_on_first,
            meta_shacl=False,
            debug=False,
        )
        graph_text = report_graph.serialize(format=self.config.report_graph_format).decode()
        return ValidationResult(
            conforms=bool(conforms),
            text_report=str(report_text),
            graph_report=graph_text,
        )

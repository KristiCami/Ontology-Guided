"""SHACL validation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rdflib import Graph

try:
    from pyshacl import validate
    _PYSHACL_IMPORT_ERROR: Optional[Exception] = None
except ImportError as exc:  # pragma: no cover
    validate = None  # type: ignore
    _PYSHACL_IMPORT_ERROR = exc


@dataclass
class ShaclReport:
    conforms: bool
    text_report: str
    report_graph_ttl: Optional[str]


class ShaclValidator:
    def __init__(self, shapes_path: Path) -> None:
        if not shapes_path.exists():
            raise FileNotFoundError(f"SHACL shapes file not found: {shapes_path}")
        self.shapes_path = shapes_path
        self.shapes_graph = Graph().parse(shapes_path)

    def validate(self, data_graph: Graph) -> ShaclReport:
        if validate is None:
            reason = (
                "pyshacl import failed"
                f" ({_PYSHACL_IMPORT_ERROR}); install dependencies via 'pip install -r requirements.txt'"
            )
            return ShaclReport(False, reason, None)
        conforms, report_graph, text_report = validate(
            data_graph,
            shacl_graph=self.shapes_graph,
            inference="both",
            serialize_report_graph=True,
        )
        report_graph_ttl = report_graph.serialize(format="turtle") if report_graph else None
        return ShaclReport(bool(conforms), str(text_report), report_graph_ttl)

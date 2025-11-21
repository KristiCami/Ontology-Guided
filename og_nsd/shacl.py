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
        """Run SHACL validation and normalize the report output.

        Setting ``serialize_report_graph=False`` only affects how the report
        graph is returned; the validation itself still runs, and the ``conforms``
        flag reflects whether the data graph satisfies the shapes.
        """
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
            # Request the raw report graph (not a serialized string/bytes) so we
            # can normalize the output ourselves and avoid attribute errors when
            # pyshacl returns serialized bytes. We still guard against bytes or
            # strings below in case the library changes its defaults.
            serialize_report_graph=False,
        )
        report_graph_ttl: Optional[str] = None
        if isinstance(report_graph, bytes):
            report_graph_ttl = report_graph.decode("utf-8")
        elif isinstance(report_graph, str):
            report_graph_ttl = report_graph
        elif report_graph:
            report_graph_ttl = report_graph.serialize(format="turtle")
        return ShaclReport(bool(conforms), str(text_report), report_graph_ttl)

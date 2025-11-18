"""Wrapper around pySHACL validation for the generated graphs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from pyshacl import validate
from rdflib import Graph, Namespace

SH = Namespace("http://www.w3.org/ns/shacl#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")


@dataclass
class ValidationIssue:
    focus_node: str
    result_path: str
    message: str


@dataclass
class ValidationResult:
    conforms: bool
    issues: List[ValidationIssue]


class SHACLValidator:
    def __init__(self, shacl_graph: Graph | None = None) -> None:
        self.shacl_graph = shacl_graph

    def validate(self, data_graph: Graph) -> ValidationResult:
        conforms, _, results_text = validate(
            data_graph,
            shacl_graph=self.shacl_graph,
            inference="rdfs",
            debug=False,
            serialize_report_graph=True,
        )
        issues = self._parse_results(results_text)
        return ValidationResult(conforms=conforms, issues=issues)

    def _parse_results(self, results_text: str) -> List[ValidationIssue]:
        report = Graph().parse(data=results_text, format="turtle")
        issues: List[ValidationIssue] = []
        for result in report.subjects(RDF.type, SH.ValidationResult):
            focus_node = next(report.objects(result, SH.focusNode), None)
            path = next(report.objects(result, SH.resultPath), None)
            message = next(report.objects(result, SH.resultMessage), None)
            issues.append(
                ValidationIssue(
                    focus_node=focus_node.n3(report.namespace_manager) if focus_node else "",
                    result_path=path.n3(report.namespace_manager) if path else "",
                    message=str(message) if message else "",
                )
            )
        return issues


__all__ = ["SHACLValidator", "ValidationResult", "ValidationIssue"]

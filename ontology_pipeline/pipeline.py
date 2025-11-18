"""End-to-end orchestration of the neuro-symbolic ontology drafting pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from rdflib import Graph

from .llm_interface import LLMClient
from .ontology_builder import OntologyBuilder
from .parser import DraftParser
from .prompting import build_drafting_prompt, build_repair_prompt
from .repair import to_messages
from .shacl_validator import SHACLValidator, ValidationResult


@dataclass
class PipelineResult:
    requirement: str
    graph: Graph
    validation: ValidationResult
    iterations: int


class OntologyDraftingPipeline:
    """Coordinates LLM calls, OWL construction and SHACL validation."""

    def __init__(
        self,
        llm_client: LLMClient,
        shacl_graph_path: str | Path,
        max_iterations: int = 3,
        context: Optional[Iterable[str]] = None,
    ) -> None:
        self.llm = llm_client
        self.max_iterations = max_iterations
        self.context = list(context or [])
        shacl_graph = Graph().parse(shacl_graph_path, format="turtle")
        self.validator = SHACLValidator(shacl_graph=shacl_graph)
        self.parser = DraftParser()
        self.builder = OntologyBuilder()

    def run(self, requirement: str) -> PipelineResult:
        prompt = build_drafting_prompt(requirement, context=self.context)
        draft = None
        validation: Optional[ValidationResult] = None
        graph = None
        iterations = 0
        for iteration in range(1, self.max_iterations + 1):
            iterations = iteration
            llm_response = self.llm.generate(prompt)
            draft = self.parser.parse(llm_response)
            graph = self.builder.build_graph(draft)
            validation = self.validator.validate(graph)
            if validation.conforms:
                break
            prompt = build_repair_prompt(requirement, to_messages(validation.issues))
        assert draft is not None and graph is not None and validation is not None
        return PipelineResult(requirement=requirement, graph=graph, validation=validation, iterations=iterations)


__all__ = ["OntologyDraftingPipeline", "PipelineResult"]

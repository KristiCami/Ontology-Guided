"""High-level orchestration for the OG-NSD pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from rdflib import Graph

from .config import DEFAULT_OUTPUT_NAME, LLMConfig, PipelineConfig, ValidationConfig
from .llm import BaseLLM, build_llm
from .prompts import PromptBuilder
from .structures import Requirement, ValidationResult
from .utils import ensure_directory, load_requirements
from .validators import OntologyValidator


class OntologyDraftingPipeline:
    """Coordinates LLM drafting, validation, and repair iterations."""

    def __init__(
        self,
        pipeline_config: PipelineConfig,
        llm_config: LLMConfig,
        validation_config: ValidationConfig,
    ):
        self.pipeline_config = pipeline_config
        self.prompt_builder = PromptBuilder(namespace=pipeline_config.namespace)
        self.llm: BaseLLM = build_llm(llm_config)
        self.validator = OntologyValidator(validation_config)

    def run(self, requirements_path: Path) -> Path:
        requirements = load_requirements(requirements_path)
        ensure_directory(self.pipeline_config.output_dir)
        combined_graph = Graph()
        reports: List[dict] = []

        for requirement in requirements:
            snippet, validation = self._draft_with_repair(requirement)
            combined_graph.parse(data=snippet, format="turtle")
            reports.append(
                {
                    "title": requirement.title,
                    "requirement": requirement.text,
                    "conforms": validation.conforms,
                    "report": validation.text_report,
                }
            )

        output_path = self.pipeline_config.output_dir / DEFAULT_OUTPUT_NAME
        combined_graph.serialize(destination=str(output_path), format="turtle")

        report_path = self.pipeline_config.output_dir / "validation_report.json"
        report_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")
        return output_path

    def _draft_with_repair(self, requirement: Requirement) -> tuple[str, ValidationResult]:
        prompt = self.prompt_builder.for_requirement(requirement)
        snippet = self.llm.generate(prompt, requirement=requirement)
        validation = self.validator.validate_snippet(snippet)
        iterations = 1

        while not validation.conforms and iterations < self.pipeline_config.iterations:
            repair_prompt = self.prompt_builder.for_repair(requirement, validation)
            snippet = self.llm.generate(repair_prompt, requirement=requirement)
            validation = self.validator.validate_snippet(snippet)
            iterations += 1

        return snippet, validation

"""High-level orchestration for the OG-NSD pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import PipelineConfig
from .llm import HeuristicLLM, LLMClient, LLMResponse, OpenAILLM
from .ontology import OntologyAssembler
from .queries import CompetencyQuestionRunner
from .reasoning import OwlreadyReasoner
from .reporting import build_report, save_report
from .requirements import RequirementLoader, chunk_requirements
from .shacl import ShaclValidator


class OntologyDraftingPipeline:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.config.ensure_output_dirs()
        self.assembler = OntologyAssembler(config.base_ontology_path)
        self.validator = ShaclValidator(config.shapes_path)
        self.reasoner = OwlreadyReasoner(enabled=config.reasoning_enabled)
        self.cq_runner: Optional[CompetencyQuestionRunner] = None
        if config.competency_questions_path:
            self.cq_runner = CompetencyQuestionRunner(config.competency_questions_path)
        self.llm = self._select_llm(config)

    def _select_llm(self, config: PipelineConfig) -> LLMClient:
        if config.llm_mode == "openai":
            return OpenAILLM(temperature=config.llm_temperature)
        return HeuristicLLM(base_namespace=config.base_namespace)

    def run(self) -> dict:
        loader = RequirementLoader(self.config.requirements_path)
        requirements = loader.load(self.config.max_requirements)
        state = self.assembler.bootstrap()
        llm_response: Optional[LLMResponse] = None
        for batch in chunk_requirements(requirements, size=5):
            llm_response = self.llm.generate_axioms(batch)
            self.assembler.add_turtle(state, llm_response.turtle)
        if llm_response is None:
            raise RuntimeError("LLM returned no axioms")
        shacl_report = self.validator.validate(state.graph)
        cq_results = self.cq_runner.run(state.graph) if self.cq_runner else None
        reasoner_report = self.reasoner.run(state.graph)
        report = build_report(
            llm_response=llm_response,
            shacl_report=shacl_report,
            cq_results=cq_results,
            reasoner_report=reasoner_report,
        )
        self.assembler.serialize(state, self.config.output_path)
        if self.config.report_path:
            save_report(report, self.config.report_path)
        return report

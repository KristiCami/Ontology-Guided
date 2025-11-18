"""Prompt builders used by the OG-NSD pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Optional

from .structures import Requirement, ValidationResult


@dataclass
class PromptBuilder:
    """Crafts prompts for the LLM using requirement metadata."""

    namespace: str

    def for_requirement(self, requirement: Requirement) -> str:
        placeholders = "\n".join(
            f"- {ph.type}: '{ph.span}'" for ph in requirement.placeholders
        )
        boilerplate = requirement.boilerplate.get("main", requirement.text)
        return dedent(
            f"""
            You are drafting OWL/Turtle axioms for the ATM ontology with namespace {self.namespace}.
            Requirement title: {requirement.title}
            Requirement text: {requirement.text}
            Boilerplate: {boilerplate}

            Requirement annotations:
            {placeholders or 'No annotations available.'}

            Produce a coherent Turtle snippet that introduces relevant classes, object properties,
            datatype properties, and restrictions. Use descriptive rdfs:comment statements to cite
            the original requirement.
            """
        ).strip()

    def for_repair(self, requirement: Requirement, validation: ValidationResult) -> str:
        prompt = self.for_requirement(requirement)
        return dedent(
            f"""
            {prompt}

            The previous attempt triggered validation issues:
            {validation.text_report}

            Provide an improved Turtle snippet that resolves the problems while preserving
            the intent of the requirement.
            """
        ).strip()

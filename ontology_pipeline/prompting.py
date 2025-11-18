"""Prompt builders for the neuro-symbolic pipeline."""
from __future__ import annotations

from textwrap import dedent
from typing import Iterable, List


BASE_INSTRUCTIONS = dedent(
    """
    You are an ontology engineer helping with the ATM domain.
    Transform the requirement into structured JSON describing OWL classes,
    object properties, data properties, restrictions and individuals.
    Use camel case names and map the terms to Requirement Boilerplate Ontology (RBO)
    concepts when possible. Provide valid JSON with the following keys:
    "classes", "object_properties", "data_properties", "restrictions", "individuals".
    """
).strip()


def build_drafting_prompt(requirement: str, context: Iterable[str] | None = None) -> str:
    """Creates the instruction sent to the LLM for the first pass."""

    contextual_clauses: List[str] = list(context or [])
    context_block = "\n".join(contextual_clauses)
    return dedent(
        f"""
        {BASE_INSTRUCTIONS}
        Requirement: "{requirement.strip()}"
        {context_block}
        Output JSON only.
        """
    ).strip()


def build_repair_prompt(requirement: str, validation_messages: Iterable[str]) -> str:
    """Creates the prompt when SHACL validation fails."""

    formatted_messages = "\n".join(f"- {msg}" for msg in validation_messages)
    return dedent(
        f"""
        Repair request.
        The previous ontology draft violated SHACL constraints extracted from the domain ontology.
        Requirement: "{requirement.strip()}"
        Violations:\n{formatted_messages}
        Provide corrected JSON using the same schema as before.
        """
    ).strip()


__all__ = ["build_drafting_prompt", "build_repair_prompt"]

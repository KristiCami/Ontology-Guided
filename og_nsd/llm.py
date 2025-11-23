"""LLM integration utilities."""
from __future__ import annotations

import abc
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from .requirements import Requirement
from .schema import OntologyContext

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


def slugify(label: str) -> str:
    label = re.sub(r"[^A-Za-z0-9]+", "_", label.strip())
    label = re.sub(r"_+", "_", label).strip("_")
    if not label:
        label = "Concept"
    if label[0].isdigit():
        label = f"C_{label}"
    return label


@dataclass
class LLMResponse:
    turtle: str
    reasoning_notes: str


class LLMClient(abc.ABC):
    """Abstract base class for LLM-backed ontology drafting."""

    @abc.abstractmethod
    def generate_axioms(
        self, requirements: Sequence[Requirement], ontology_context: OntologyContext | None = None
    ) -> LLMResponse:
        raise NotImplementedError

    @abc.abstractmethod
    def generate_patch(self, prompts: Sequence[str], context_ttl: str) -> LLMResponse:
        """Produce ontology edits that attempt to resolve validation feedback.

        Parameters
        ----------
        prompts:
            A sequence of human-readable violation summaries produced by the
            SHACL validator and/or DL reasoner.
        context_ttl:
            A Turtle serialization of the current ontology graph so the model
            can ground its edits.
        """
        raise NotImplementedError


class HeuristicLLM(LLMClient):
    """Rule-based fallback model for offline experimentation."""

    def __init__(self, base_namespace: str) -> None:
        self.base_ns = base_namespace.rstrip("#/") + "#"

    def generate_axioms(
        self, requirements: Sequence[Requirement], ontology_context: OntologyContext | None = None
    ) -> LLMResponse:
        triples: List[str] = [
            f"@prefix atm: <{self.base_ns}> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        ]
        notes: List[str] = []
        for req in requirements:
            subject = self._extract_subject(req)
            obj = self._extract_object(req)
            prop = slugify(self._extract_predicate(req))
            triples.append(
                f"atm:{prop} a owl:ObjectProperty ; rdfs:domain atm:{subject} ; rdfs:range atm:{obj} ."
            )
            triples.append(f"atm:{subject} a owl:Class .")
            triples.append(f"atm:{obj} a owl:Class .")
            triples.append(
                f"atm:{subject}_{prop}_{obj} a owl:Axiom ; atm:sourceRequirement \"{req.identifier}\" ."
            )
            notes.append(f"Mapped '{req.text}' → atm:{subject} {prop} atm:{obj}")
        turtle = "\n".join(triples)
        return LLMResponse(turtle=turtle, reasoning_notes="\n".join(notes))

    def generate_patch(self, prompts: Sequence[str], context_ttl: str) -> LLMResponse:
        """Emit a simple, deterministic patch guided by violation summaries.

        The heuristic repair step is intentionally conservative: it adds
        annotations that make the problematic nodes/classes explicit and
        declares any referenced properties as OWL object properties. This keeps
        the graph syntactically valid while providing a concrete edit so the
        closed-loop controller can progress even without remote LLM access.
        """

        triples: List[str] = [
            f"@prefix atm: <{self.base_ns}> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        ]
        notes: List[str] = []
        for idx, prompt in enumerate(prompts, start=1):
            focus = slugify(prompt.split()[0])
            triples.append(f"atm:{focus} a owl:Class .")
            triples.append(
                f"atm:{focus}_repair_{idx} a owl:Axiom ; rdfs:comment \"{prompt}\" ."
            )
            notes.append(f"Added repair note for: {prompt}")

        if len(triples) == 3:
            notes.append("No violations provided; emitted empty patch.")
        turtle = "\n".join(triples)
        return LLMResponse(turtle=turtle, reasoning_notes="\n".join(notes))

    def _extract_subject(self, requirement: Requirement) -> str:
        if "customer" in requirement.text.lower():
            return "Customer"
        if "bank" in requirement.text.lower():
            return "Bank"
        return "ATM"

    def _extract_object(self, requirement: Requirement) -> str:
        if "transaction" in requirement.text.lower():
            return "Transaction"
        if "card" in requirement.text.lower():
            return "CashCard"
        if "account" in requirement.text.lower():
            return "Account"
        return "RequirementTarget"

    def _extract_predicate(self, requirement: Requirement) -> str:
        text = requirement.text.lower()
        if "log" in text:
            return "logs"
        if "verify" in text:
            return "verifies"
        if "dispense" in text:
            return "dispenses"
        if "maintain" in text:
            return "maintains"
        return "relatesTo"


class OpenAILLM(LLMClient):
    """Adapter for the OpenAI Chat Completions API."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1, system_prompt: str | None = None) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed")
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt or self._default_system_prompt()

    def generate_axioms(
        self, requirements: Sequence[Requirement], ontology_context: OntologyContext | None = None
    ) -> LLMResponse:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._build_prompt(requirements, ontology_context)},
        ]
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        content = response.choices[0].message.content.strip() if response.choices else ""
        return LLMResponse(turtle=content, reasoning_notes="Generated via OpenAI chat.completions")

    def generate_patch(self, prompts: Sequence[str], context_ttl: str) -> LLMResponse:
        repair_prompt = self._build_repair_prompt(prompts, context_ttl)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": repair_prompt},
        ]
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        content = response.choices[0].message.content.strip() if response.choices else ""
        return LLMResponse(turtle=content, reasoning_notes="Patch generated via OpenAI chat.completions")

    def _build_prompt(
        self, requirements: Sequence[Requirement], ontology_context: OntologyContext | None
    ) -> str:
        body = []
        for req in requirements:
            context = f"Title: {req.title}\nText: {req.text}"
            if req.boilerplate:
                context += f"\nBoilerplate:\n{req.boilerplate}"
            body.append(context)
        joined = "\n\n".join(body)

        schema_section = (
            "SECTION A — Allowed Vocabulary (schema constraints)\n" + ontology_context.as_prompt_section() + "\n\n"
            if ontology_context
            else ""
        )

        drafting_spec = (
            "SECTION B — Drafting Specification\n"
            "- Use only the above classes and properties; do not invent new terms unless strictly necessary.\n"
            "- Align object and datatype properties to their domain/range constraints.\n"
            "- Use the atm: namespace consistently and emit valid Turtle.\n"
            "- Do not include the gold ontology itself; rely only on the provided schema.\n\n"
        )

        requirements_section = f"SECTION C — Requirements Input\n{joined}"

        return schema_section + drafting_spec + requirements_section

    def _default_system_prompt(self) -> str:
        return (
            "You are an ontology engineer who drafts OWL 2 DL axioms using Turtle syntax. "
            "Emit only syntactically valid Turtle with atm: prefix."
        )

    def _build_repair_prompt(self, prompts: Sequence[str], context_ttl: str) -> str:
        prompt_block = "\n".join(f"- {p}" for p in prompts) or "- No violations provided"
        return (
            "You are repairing an OWL ontology. Given the SHACL/Reasoner issues below, "
            "emit a compact Turtle patch that resolves them without deleting existing classes.\n\n"
            "Issues:\n"
            f"{prompt_block}\n\n"
            "Context (truncated Turtle):\n"
            f"{context_ttl[:4000]}\n"
            "Respond only with Turtle additions that address the issues."
        )

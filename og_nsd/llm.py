"""LLM integration utilities."""
from __future__ import annotations

import abc
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from .requirements import Requirement

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
    def generate_axioms(self, requirements: Sequence[Requirement]) -> LLMResponse:
        raise NotImplementedError


class HeuristicLLM(LLMClient):
    """Rule-based fallback model for offline experimentation."""

    def __init__(self, base_namespace: str) -> None:
        self.base_ns = base_namespace.rstrip("#/") + "#"

    def generate_axioms(self, requirements: Sequence[Requirement]) -> LLMResponse:
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

    def generate_axioms(self, requirements: Sequence[Requirement]) -> LLMResponse:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._build_prompt(requirements)},
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

    def _build_prompt(self, requirements: Sequence[Requirement]) -> str:
        body = []
        for req in requirements:
            context = f"Title: {req.title}\nText: {req.text}"
            if req.boilerplate:
                context += f"\nBoilerplate:\n{req.boilerplate}"
            body.append(context)
        joined = "\n\n".join(body)
        return f"Convert the following requirements into OWL Turtle axioms. Use atm: as the base prefix.\n\n{joined}"

    def _default_system_prompt(self) -> str:
        return (
            "You are an ontology engineer who drafts OWL 2 DL axioms using Turtle syntax. "
            "Emit only syntactically valid Turtle with atm: prefix."
        )

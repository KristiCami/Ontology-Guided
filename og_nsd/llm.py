"""Language-model helpers for the OG-NSD pipeline."""
from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from textwrap import dedent
from typing import Dict, Iterable, List, Optional

from .config import LLMConfig
from .structures import Requirement
from .utils import normalize_identifier


class BaseLLM(ABC):
    """Abstract base class that exposes a simple generate API."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, requirement: Optional[Requirement] = None) -> str:
        """Return the textual response for a prompt."""


class TemplateLLM(BaseLLM):
    """A deterministic LLM replacement used for offline testing.

    The class inspects boilerplate annotations and emits simple Turtle that
    captures systems, actions, and temporal guards in the requirement. While
    intentionally lightweight, this makes the rest of the pipeline executable
    without network connectivity or API keys.
    """

    def generate(self, prompt: str, requirement: Optional[Requirement] = None) -> str:
        if requirement is None:
            raise ValueError("TemplateLLM requires the originating requirement")

        classes: Dict[str, List[str]] = {}
        individuals: List[str] = []
        for placeholder in requirement.placeholders:
            name = normalize_identifier(placeholder.span)
            placeholder_type = placeholder.type
            classes.setdefault(placeholder_type, []).append(name)
            individuals.append(name)

        system_class = classes.get("System", ["System"])[0]
        function_class = classes.get("Function", ["Function"])[0]
        item_classes = classes.get("Item", [])

        triples: List[str] = [
            f"ex:{system_class} a owl:Class .",
            f"ex:{function_class} a owl:Class .",
        ]

        for item in item_classes:
            triples.append(f"ex:{item} a owl:Class .")

        triples.extend(
            [
                f"ex:performs a owl:ObjectProperty ;\n  rdfs:domain ex:{system_class} ;\n  rdfs:range ex:{function_class} .",
                f"ex:involvesItem a owl:ObjectProperty ;\n  rdfs:domain ex:{function_class} ;\n  rdfs:range ex:{item_classes[0] if item_classes else function_class} .",
            ]
        )

        comment = requirement.text.replace("\n", " ")
        triples.append(f"ex:{function_class} rdfs:comment \"{comment}\" .")

        turtle = dedent(
            f"""
            @prefix ex: <http://example.com/atm#> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

            {'\n'.join(triples)}
            """
        ).strip()

        return turtle


@dataclass
class ChatMessage:
    role: str
    content: str


class OpenAIChatLLM(BaseLLM):
    """Thin wrapper around the OpenAI chat completion API.

    The dependency is optional. The class is only instantiated when the model
    name is not ``template`` and an API key is present. Errors are annotated
    with actionable hints so that the CLI can guide the user.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _lazy_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - executed only with OpenAI usage
                raise RuntimeError(
                    "openai package is required for non-template models."
                ) from exc

            api_key = self.config.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")

            self._client = OpenAI(api_key=api_key)
        return self._client

    def generate(self, prompt: str, requirement: Optional[Requirement] = None) -> str:
        client = self._lazy_client()
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": prompt},
        ]
        response = client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            messages=messages,
        )
        return response.choices[0].message.content.strip()


def build_llm(config: LLMConfig) -> BaseLLM:
    """Factory that instantiates the correct backend."""

    if config.model.lower() == "template":
        return TemplateLLM(config)
    return OpenAIChatLLM(config)

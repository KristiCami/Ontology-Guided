"""Configuration dataclasses for the OG-NSD pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class LLMConfig:
    """Settings that control the behaviour of the language-model backend."""

    model: str = "template"
    system_prompt: str = (
        "You are an ontology engineer that converts NL requirements into OWL "
        "(Turtle syntax). Align output with provided ontology terms when "
        "possible."
    )
    temperature: float = 0.0
    max_retries: int = 2
    openai_api_key: Optional[str] = None


@dataclass
class ValidationConfig:
    """Parameters for SHACL/OWL validation."""

    shacl_shapes: Path
    inference: str = "both"  # options accepted by pyshacl: rdfs, owlrl, both, none
    advanced: bool = True
    abort_on_first: bool = False
    report_graph_format: str = "turtle"


@dataclass
class PipelineConfig:
    """High-level configuration for the ontology drafting pipeline."""

    namespace: str = "http://example.com/atm#"
    output_dir: Path = Path("artifacts")
    iterations: int = 2
    competency_questions: List[Path] = field(default_factory=list)
    alignments_path: Optional[Path] = None


DEFAULT_OUTPUT_NAME = "generated_ontology.ttl"

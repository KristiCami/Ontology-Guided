"""Lightweight validators that emulate SHACL, CQ, and reasoning feedback."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Tuple
import re

from .ontology import OntologyBuilder


@dataclass
class SHACLResult:
    conforms: bool
    violations: List[str] = field(default_factory=list)


@dataclass
class CQResult:
    total: int
    passed: int
    failed_descriptions: List[str] = field(default_factory=list)


@dataclass
class ReasonerResult:
    inferred_relations: int
    total_relations: int


class OntologyValidator:
    """Runs deterministic checks derived from SHACL and CQs."""

    def __init__(self, builder: OntologyBuilder, shapes_path: Path | None = None, cq_path: Path | None = None) -> None:
        self.builder = builder
        self.cq_path = cq_path
        self.shape_hints = self._load_shape_messages(shapes_path)

    def _load_shape_messages(self, path: Path | None) -> List[str]:
        if not path:
            return []
        text = Path(path).read_text(encoding="utf-8")
        return re.findall(r"sh:message \"([^\"]+)\"", text)

    def run_shacl(self) -> SHACLResult:
        violations: List[str] = []
        for node in self.builder.requirements.values():
            for idx, role in enumerate(("subject", "verb")):
                if role not in node.roles:
                    hint = self.shape_hints[idx % len(self.shape_hints)] if self.shape_hints else ""
                    message = f"{node.identifier} missing required role '{role}'"
                    if hint:
                        message = f"{message} :: {hint}"
                    violations.append(message)
            if node.boilerplate_type and node.boilerplate_type.startswith("M"):
                if "object" not in node.roles:
                    violations.append(f"{node.identifier} missing object for modal requirement")
            if "condition" in node.roles and not node.boilerplate_type:
                violations.append(f"{node.identifier} condition specified without boilerplate type")
        conforms = not violations
        return SHACLResult(conforms=conforms, violations=violations)

    def _parse_cq_descriptions(self) -> List[str]:
        if not self.cq_path:
            return []
        descriptions: List[str] = []
        for line in Path(self.cq_path).read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#"):
                descriptions.append(line.strip("# "))
        return descriptions

    def run_competency_questions(self) -> CQResult:
        descriptions = self._parse_cq_descriptions()
        passed = 0
        failed: List[str] = []
        for desc in descriptions:
            required_tokens = set(re.findall(r"atm:([A-Za-z0-9]+)", desc))
            if not required_tokens:
                continue
            available = self.builder.classes.union({value for node in self.builder.requirements.values() for values in node.roles.values() for value in values})
            if required_tokens.issubset(available):
                passed += 1
            else:
                missing = required_tokens - available
                failed.append(f"{desc} :: missing {', '.join(sorted(missing))}")
        total = len(descriptions)
        return CQResult(total=total, passed=passed, failed_descriptions=failed)

    def run_reasoner(self) -> ReasonerResult:
        total_relations = sum(len(values) for node in self.builder.requirements.values() for values in node.roles.values())
        inferred = len(self.builder.classes) * max(1, len(self.builder.requirements))
        return ReasonerResult(inferred_relations=inferred, total_relations=total_relations)


__all__ = [
    "OntologyValidator",
    "SHACLResult",
    "CQResult",
    "ReasonerResult",
]

"""LLM-inspired drafting heuristics for OWL axiom induction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from .ontology import OntologyBuilder
from .requirements import Requirement, extract_inline_placeholders

CLASS_LIKE = {
    "System",
    "Item",
    "Actor",
    "Function",
    "State",
    "Condition",
    "Environment",
    "Flow",
    "Event",
    "Role",
}

ROLE_PROPERTY_MAP: Dict[str, str] = {
    "System": "subject",
    "Actor": "actor",
    "Function": "verb",
    "State": "state",
    "Item": "object",
    "Condition": "condition",
    "Flow": "flow",
}


@dataclass
class DraftingStats:
    requirements: int = 0
    classes: int = 0
    relations: int = 0


class RuleBasedDraftGenerator:
    """Deterministic heuristic that emulates ontology-aware prompting."""

    def __init__(self, builder: OntologyBuilder) -> None:
        self.builder = builder

    @staticmethod
    def _normalize(label: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else " " for ch in label)
        words = [w.capitalize() for w in cleaned.split() if w]
        return "".join(words) or "Token"

    def draft(self, req: Requirement) -> DraftingStats:
        stats = DraftingStats(requirements=1)
        node = self.builder.register_requirement(req.identifier, req.title, req.text, req.boilerplate_type)
        placeholders = list(req.placeholders)
        for segment in req.iter_segments():
            placeholders.extend(extract_inline_placeholders(segment))

        for placeholder in placeholders:
            label = self._normalize(placeholder.span)
            if placeholder.type in CLASS_LIKE:
                self.builder.register_class(label)
                stats.classes += 1
            property_name = ROLE_PROPERTY_MAP.get(placeholder.type, "mentions")
            node.add_role(property_name, label)
            stats.relations += 1
        return stats


def draft_all(builder: OntologyBuilder, requirements: Iterable[Requirement]) -> Tuple[OntologyBuilder, DraftingStats]:
    generator = RuleBasedDraftGenerator(builder)
    aggregate = DraftingStats()
    for requirement in requirements:
        stats = generator.draft(requirement)
        aggregate.requirements += stats.requirements
        aggregate.classes += stats.classes
        aggregate.relations += stats.relations
    return builder, aggregate


__all__ = [
    "RuleBasedDraftGenerator",
    "DraftingStats",
    "draft_all",
]

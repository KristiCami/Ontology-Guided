from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_owl(
        self,
        sentences: List[str],
        prompt_template: str,
        *,
        available_terms: Optional[Tuple[List[str], List[str]]] = None,
        **kwargs,
    ) -> List[str]:
        """Generate OWL/Turtle snippets for the given sentences."""
        raise NotImplementedError

from typing import List, Tuple, Optional
from pathlib import Path
import logging

from transformers import pipeline

from .base_llm import BaseLLM


class LocalLLMInterface(BaseLLM):
    """Local LLM provider using HuggingFace transformers."""

    def __init__(self, model: str = "distilgpt2", cache_dir: Optional[str] = None):
        self.generator = pipeline("text-generation", model=model)
        self.model = model
        self.cache_dir = Path(cache_dir or Path(__file__).resolve().parent.parent / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def generate_owl(
        self,
        sentences: List[str],
        prompt_template: str,
        *,
        available_terms: Optional[Tuple[List[str], List[str]]] = None,
        max_new_tokens: int = 100,
    ) -> List[str]:
        """Generate OWL/Turtle snippets using a local text-generation model."""
        results = []
        classes = []
        properties = []
        if available_terms:
            classes, properties = available_terms
        for sent in sentences:
            prompt = "Return ONLY valid Turtle code, without any explanatory text or markdown fences.\n"
            if classes or properties:
                prompt += "Use existing ontology terms when appropriate.\n"
                if classes:
                    prompt += "Classes: " + ", ".join(classes) + "\n"
                if properties:
                    prompt += "Properties: " + ", ".join(properties) + "\n"
            prompt += prompt_template.format(sentence=sent)
            generated = self.generator(prompt, max_new_tokens=max_new_tokens)[0]["generated_text"]
            # Remove the prompt part from generated text
            results.append(generated[len(prompt):].strip())
        return results

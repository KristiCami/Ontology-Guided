import openai
import httpx
from typing import List, Tuple, Optional
import re
import time

class LLMInterface:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        openai.api_key = api_key
        self.model = model

    def generate_owl(
        self,
        sentences: List[str],
        prompt_template: str,
        *,
        available_terms: Optional[Tuple[List[str], List[str]]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> List[str]:
        """Call the LLM and return only the Turtle code."""
        results = []
        classes = properties = []
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
            attempts = 0
            resp = None
            while True:
                try:
                    resp = openai.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a Turtle/OWL code generator."},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    break
                except (openai.OpenAIError, httpx.HTTPError) as e:
                    attempts += 1
                    print(f"LLM call failed: {e}")
                    if attempts > max_retries:
                        print("Exiting gracefully.")
                        return results
                    time.sleep(retry_delay)

            raw = resp.choices[0].message.content
            match = re.search(r"```turtle\s*(.*?)```", raw, re.S)
            turtle_code = match.group(1).strip() if match else raw.strip()
            results.append(turtle_code)
        return results

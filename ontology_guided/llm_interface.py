import openai
import httpx
from typing import List, Tuple, Optional
import re
import time
import hashlib
import json
from pathlib import Path

class LLMInterface:
    def __init__(self, api_key: str, model: str = "gpt-4", cache_dir: Optional[str] = None):
        openai.api_key = api_key
        self.model = model
        self.cache_dir = Path(cache_dir or Path(__file__).resolve().parent.parent / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_file(self, sentence: str, available_terms: Optional[Tuple[List[str], List[str]]]):
        classes, properties = available_terms or ([], [])
        key_data = {
            "sentence": sentence,
            "classes": classes,
            "properties": properties,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def _load_cache(self, sentence: str, available_terms: Optional[Tuple[List[str], List[str]]]):
        path = self._cache_file(sentence, available_terms)
        if path.exists():
            with path.open("r") as f:
                return json.load(f).get("result")
        return None

    def _save_cache(self, sentence: str, available_terms: Optional[Tuple[List[str], List[str]]], result: str):
        path = self._cache_file(sentence, available_terms)
        with path.open("w") as f:
            json.dump({"result": result}, f)

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
        classes = []
        properties = []
        if available_terms:
            classes, properties = available_terms
        for sent in sentences:
            cached = self._load_cache(sent, available_terms)
            if cached is not None:
                results.append(cached)
                continue
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
            self._save_cache(sent, available_terms, turtle_code)
        return results

import openai
import httpx
from typing import List, Optional, Dict, Any
import re
import time
import hashlib
import json
from pathlib import Path
import logging
from rdflib import Graph


# Common namespace prefixes that may appear in LLM output. If a prefix is used
# but not declared, we will automatically insert a declaration using this map
# before attempting to parse the Turtle code.
KNOWN_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "schema": "http://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "foaf": "http://xmlns.com/foaf/0.1/",
}

class LLMInterface:
    def __init__(self, api_key: str, model: str = "gpt-4", cache_dir: Optional[str] = None):
        openai.api_key = api_key
        self.model = model
        self.cache_dir = Path(cache_dir or Path(__file__).resolve().parent.parent / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def _cache_file(self, sentence: str, available_terms: Optional[Dict[str, Any]]):
        classes = []
        properties = []
        hints = {}
        synonyms = {}
        if available_terms:
            classes = available_terms.get("classes", [])
            properties = available_terms.get("properties", [])
            hints = available_terms.get("domain_range_hints", {})
            synonyms = available_terms.get("synonyms", {})
        key_data = {
            "sentence": sentence,
            "classes": classes,
            "properties": properties,
            "hints": hints,
            "synonyms": synonyms,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def _load_cache(self, sentence: str, available_terms: Optional[Dict[str, Any]]):
        path = self._cache_file(sentence, available_terms)
        if path.exists():
            with path.open("r") as f:
                return json.load(f).get("result")
        return None

    def _save_cache(self, sentence: str, available_terms: Optional[Dict[str, Any]], result: str):
        path = self._cache_file(sentence, available_terms)
        with path.open("w") as f:
            json.dump({"result": result}, f)

    def generate_owl(
        self,
        sentences: List[str],
        prompt_template: str,
        *,
        available_terms: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ) -> List[str]:
        """Call the LLM and return only the Turtle code."""
        results = []
        classes = []
        properties = []
        hints = {}
        synonyms = {}
        if available_terms:
            classes = available_terms.get("classes", [])
            properties = available_terms.get("properties", [])
            hints = available_terms.get("domain_range_hints", {})
            synonyms = available_terms.get("synonyms", {})
        for sent in sentences:
            cached = self._load_cache(sent, available_terms)
            if cached is not None:
                results.append(cached)
                continue
            prompt = (
                "Return ONLY valid Turtle code, without any explanatory text or markdown fences.\n"
                "Include explicit @prefix declarations for any prefixes you use "
                "(e.g., @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .). "
                "If a prefix is not declared, use full IRIs enclosed in <> instead of shorthand.\n"
            )
            if classes or properties or hints or synonyms:
                prompt += "Use existing ontology terms when appropriate.\n"
                if classes:
                    prompt += "Classes: " + ", ".join(classes) + "\n"
                if properties:
                    prompt += "Properties: " + ", ".join(properties) + "\n"
                if hints:
                    prompt += "Property domains/ranges:\n"
                    for p, dr in hints.items():
                        dom = ", ".join(dr.get("domain", []))
                        rng = ", ".join(dr.get("range", []))
                        prompt += f"  - {p}: domain {dom or '-'}; range {rng or '-'}\n"
                if synonyms:
                    prompt += "Synonyms:\n"
                    for s, c in synonyms.items():
                        prompt += f"  - {s} -> {c}\n"
            prompt += prompt_template.format(sentence=sent)
            base_prompt = prompt
            attempts = 0
            current_delay = retry_delay
            while True:
                try:
                    resp = openai.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a Turtle/OWL code generator."},
                            {"role": "user", "content": prompt},
                        ],
                    )
                except (openai.OpenAIError, httpx.HTTPError) as e:
                    attempts += 1
                    self.logger.warning("LLM call failed: %s", e)
                    if attempts > max_retries:
                        self.logger.error(
                            "LLM call failed after %d retries", max_retries
                        )
                        raise RuntimeError(
                            f"LLM call failed after {max_retries} retries"
                        ) from e
                    time.sleep(current_delay)
                    current_delay = min(current_delay * 2, max_retry_delay)
                    continue

                raw = resp.choices[0].message.content
                match = re.search(r"```turtle\s*(.*?)```", raw, re.S)
                turtle_code = match.group(1).strip() if match else raw.strip()

                # Detect prefixes used in the Turtle that are not declared. For any
                # known prefix we add a corresponding @prefix declaration so that
                # rdflib can parse the graph without errors.
                used_prefixes = set(
                    re.findall(r"(?<!<)\b([A-Za-z][\w-]*):(?!//)", turtle_code)
                )
                declared_prefixes = set(
                    re.findall(r"@prefix\s+([A-Za-z][\w-]*):", turtle_code)
                )
                undeclared = used_prefixes - declared_prefixes
                prefix_lines = [
                    f"@prefix {p}: <{KNOWN_PREFIXES[p]}> ."
                    for p in sorted(undeclared)
                    if p in KNOWN_PREFIXES
                ]
                if prefix_lines:
                    turtle_code = "\n".join(prefix_lines) + "\n" + turtle_code

                try:
                    g = Graph()
                    g.parse(data=turtle_code, format="turtle")
                    break
                except Exception as e:
                    attempts += 1
                    self.logger.warning("Invalid Turtle returned: %s", e)
                    if attempts > max_retries:
                        self.logger.error(
                            "Failed to produce valid Turtle after %d retries", max_retries
                        )
                        raise ValueError("LLM returned invalid Turtle") from e
                    prompt = (
                        "Previous output was invalid Turtle; return only correct Turtle.\n"
                        + base_prompt
                    )
                    time.sleep(current_delay)
                    current_delay = min(current_delay * 2, max_retry_delay)

            results.append(turtle_code)
            self._save_cache(sent, available_terms, turtle_code)
        return results

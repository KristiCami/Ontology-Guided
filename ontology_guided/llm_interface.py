import openai
import httpx
from typing import List, Optional, Dict, Any, Union
import re
import time
import asyncio
import hashlib
import json
from pathlib import Path
import logging
from rdflib import Graph
from .exemplar_selector import select_examples


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
    "lex": "http://example.com/lexical#",
}


def build_prompt(
    sentence: str,
    vocab: Optional[Dict[str, List[str]]],
    hints: Optional[Dict[str, Any]] = None,
    synonyms: Optional[Dict[str, str]] = None,
    exemplars: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """Construct chat messages for the LLM.

    Parameters
    ----------
    sentence:
        Requirement to convert into OWL/Turtle.
    vocab:
        Dictionary with optional ``classes`` and ``properties`` lists to be
        advertised as the allowed vocabulary.
    hints:
        Optional mapping of properties to domain/range hints.
    synonyms:
        Optional mapping from synonyms to canonical terms.
    exemplars:
        Few-shot examples as dictionaries with ``user`` and ``assistant`` keys.
        The first ``k`` examples (with ``k`` clamped between 3 and 6) are used
        so that the exemplars remain fixed across test runs.
    """

    classes = vocab.get("classes", []) if vocab else []
    properties = vocab.get("properties", []) if vocab else []
    hints = hints or {}
    synonyms = synonyms or {}

    system_lines = [
        "You convert NL ATM requirements into OWL ontologies expressed in Turtle.",
        "Return only valid Turtle code with explicit @prefix declarations.",
        "Use only terms from the provided ALLOWED VOCAB.",
    ]
    if classes or properties or hints or synonyms:
        system_lines.append("ALLOWED VOCAB:")
        if classes:
            system_lines.append("Classes: " + ", ".join(classes))
        if properties:
            system_lines.append("Properties: " + ", ".join(properties))
        for prop, info in hints.items():
            dom = ", ".join(info.get("domain", []))
            ran = ", ".join(info.get("range", []))
            if dom:
                system_lines.append(f"{prop} domain {dom}")
            if ran:
                system_lines.append(f"{prop} range {ran}")
        for syn, real in synonyms.items():
            system_lines.append(f"{syn} -> {real}")

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "\n".join(system_lines)}
    ]

    if exemplars:
        # Use a deterministic slice so that prompts are stable across runs.
        # Clamp ``k`` to the [3, 6] range to keep a reasonable number of
        # exemplars while ensuring reproducibility.
        k = max(3, min(6, len(exemplars)))
        sample = exemplars[:k]
        for ex in sample:
            user_msg = ex.get("user") or ex.get("sentence")
            assistant_msg = ex.get("assistant") or ex.get("owl")
            if user_msg and assistant_msg:
                messages.append({"role": "user", "content": user_msg})
                messages.append(
                    {"role": "assistant", "content": assistant_msg}
                )

    messages.append({"role": "user", "content": sentence})
    return messages


# Keep a reference to the base prompt builder so that the LLMInterface class can
# define a method with the same name without causing recursion.
_BASE_PROMPT_BUILDER = build_prompt

class LLMInterface:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        *,
        backend: str = "openai",
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
        temperature: float = 0.0,
        max_new_tokens: int = 512,
        examples: Optional[Union[List[Dict[str, str]], str, Path]] = None,
        use_retrieval: bool = False,
        dev_pool: Optional[Union[List[Dict[str, str]], str, Path]] = None,
        retrieve_k: int = 3,
        prompt_log: Optional[Union[str, Path]] = None,
    ):
        self.backend = backend
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        if backend == "openai":
            openai.api_key = api_key
            self.model = model
        elif backend == "llama":
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            model_name = model_path or model
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            self.model.to(self.device)
        elif backend == "cache":
            self.model = model
        else:
            raise ValueError(f"Unsupported backend: {backend}")
        self.cache_dir = Path(
            cache_dir or Path(__file__).resolve().parent.parent / "cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        if isinstance(examples, (str, Path)):
            with open(examples, "r", encoding="utf-8") as f:
                examples = json.load(f)
        self.examples = examples or []
        # Retrieval-specific configuration
        if isinstance(dev_pool, (str, Path)):
            with open(dev_pool, "r", encoding="utf-8") as f:
                dev_pool = json.load(f)
        self.dev_pool = dev_pool or []
        self.use_retrieval = use_retrieval
        self.retrieve_k = retrieve_k
        self.prompt_log = Path(
            prompt_log
            or Path(__file__).resolve().parent.parent / "results" / "prompts.log"
        )
        if self.use_retrieval:
            self.prompt_log.parent.mkdir(parents=True, exist_ok=True)

    def build_prompt(
        self,
        sentence: str,
        vocab: Optional[Dict[str, List[str]]],
        hints: Optional[Dict[str, Any]] = None,
        synonyms: Optional[Dict[str, str]] = None,
        *,
        sentence_id: Optional[str] = None,
        raw_sentence: Optional[str] = None,
        log_examples: bool = True,
    ) -> List[Dict[str, str]]:
        """Build the prompt for a given sentence.

        When ``use_retrieval`` is True, the ``k`` most similar examples from
        ``dev_pool`` are selected; otherwise ``self.examples`` are used.  When a
        ``sentence_id`` is provided the IDs of the retrieved examples are logged
        in ``prompt_log``.
        """

        query = raw_sentence or sentence
        if self.use_retrieval and self.dev_pool:
            exemplars = select_examples(query, self.dev_pool, self.retrieve_k)
        else:
            exemplars = self.examples

        if log_examples and sentence_id is not None:
            ids = [ex.get("sentence_id") for ex in exemplars if ex.get("sentence_id") is not None]
            with self.prompt_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"sentence_id": sentence_id, "examples": ids}) + "\n")

        return _BASE_PROMPT_BUILDER(sentence, vocab, hints, synonyms, exemplars)

    def _cache_file(
        self,
        sentence: str,
        available_terms: Optional[Dict[str, Any]],
        base: Optional[str],
        prefix: Optional[str],
    ):
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
            "base": base,
            "prefix": prefix,
            "classes": classes,
            "properties": properties,
            "hints": hints,
            "synonyms": synonyms,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def _load_cache(
        self,
        sentence: str,
        available_terms: Optional[Dict[str, Any]],
        base: Optional[str],
        prefix: Optional[str],
    ):
        path = self._cache_file(sentence, available_terms, base, prefix)
        if path.exists():
            with path.open("r") as f:
                return json.load(f).get("result")
        return None

    def _save_cache(
        self,
        sentence: str,
        available_terms: Optional[Dict[str, Any]],
        base: Optional[str],
        prefix: Optional[str],
        result: str,
    ):
        path = self._cache_file(sentence, available_terms, base, prefix)
        with path.open("w") as f:
            json.dump({"result": result}, f)

    def _call_llama(self, messages: List[Dict[str, str]]) -> str:
        import torch

        prompt = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        ) + "\nassistant:"
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=self.temperature > 0,
                temperature=self.temperature,
            )
        generated = output[0][inputs["input_ids"].shape[-1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True)

    def generate_owl_sync(
        self,
        sentences: List[Union[str, Dict[str, Any]]],
        prompt_template: str,
        *,
        available_terms: Optional[Dict[str, Any]] = None,
        base: Optional[str] = None,
        prefix: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ) -> List[str]:
        """Synchronous helper that calls the LLM and returns Turtle code."""
        results: List[str] = []
        classes: List[str] = []
        properties: List[str] = []
        hints: Dict[str, Any] = {}
        synonyms: Dict[str, Any] = {}
        if available_terms:
            classes = available_terms.get("classes", [])
            properties = available_terms.get("properties", [])
            hints = available_terms.get("domain_range_hints", {})
            synonyms = available_terms.get("synonyms", {})
        vocab = {"classes": classes, "properties": properties}
        for sent in sentences:
            sent_text = sent.get("text") if isinstance(sent, dict) else sent
            sid = sent.get("sentence_id") if isinstance(sent, dict) else None
            cached = self._load_cache(sent_text, available_terms, base, prefix)
            if cached is not None:
                results.append(cached)
                continue
            if self.backend == "cache":
                raise RuntimeError(
                    f"Cache miss for sentence '{sent_text}'; run with a networked backend to populate the cache."
                )
            user_prompt = prompt_template.format(
                sentence=sent_text, base=base, prefix=prefix
            )
            base_prompt = user_prompt
            messages = self.build_prompt(
                user_prompt,
                vocab,
                hints,
                synonyms,
                sentence_id=sid,
                raw_sentence=sent_text,
            )
            attempts = 0
            current_delay = retry_delay
            while True:
                try:
                    if self.backend == "openai":
                        resp = openai.chat.completions.create(
                            model=self.model,
                            temperature=self.temperature,
                            messages=messages,
                        )
                        raw = resp.choices[0].message.content
                    else:
                        raw = self._call_llama(messages)
                except Exception as e:
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

                match = re.search(r"```turtle\s*(.*?)```", raw, re.S)
                turtle_code = match.group(1).strip() if match else raw.strip()

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
                            "Failed to produce valid Turtle after %d retries, returning empty output",
                            max_retries,
                        )
                        turtle_code = ""
                        break
                    user_prompt = (
                        "Previous output was invalid Turtle; return only correct Turtle.\n"
                        + base_prompt
                    )
                    messages = self.build_prompt(
                        user_prompt,
                        vocab,
                        hints,
                        synonyms,
                        sentence_id=sid,
                        raw_sentence=sent_text,
                        log_examples=False,
                    )
                    time.sleep(current_delay)
                    current_delay = min(current_delay * 2, max_retry_delay)

            self._save_cache(sent_text, available_terms, base, prefix, turtle_code)
            results.append(turtle_code)
        return results

    async def _generate_owl_async(
        self,
        sentences: List[Union[str, Dict[str, Any]]],
        prompt_template: str,
        *,
        available_terms: Optional[Dict[str, Any]] = None,
        base: Optional[str] = None,
        prefix: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ) -> List[str]:
        """Asynchronously call the LLM and return only the Turtle code."""

        classes: List[str] = []
        properties: List[str] = []
        hints: Dict[str, Any] = {}
        synonyms: Dict[str, Any] = {}
        if available_terms:
            classes = available_terms.get("classes", [])
            properties = available_terms.get("properties", [])
            hints = available_terms.get("domain_range_hints", {})
            synonyms = available_terms.get("synonyms", {})
        vocab = {"classes": classes, "properties": properties}

        async def process(sent: Any) -> str:
            sent_text = sent.get("text") if isinstance(sent, dict) else sent
            sid = sent.get("sentence_id") if isinstance(sent, dict) else None
            cached = self._load_cache(sent_text, available_terms, base, prefix)
            if cached is not None:
                return cached
            if self.backend == "cache":
                raise RuntimeError(
                    f"Cache miss for sentence '{sent_text}'; run with a networked backend to populate the cache."
                )

            user_prompt = prompt_template.format(
                sentence=sent_text, base=base, prefix=prefix
            )
            base_prompt = user_prompt
            messages = self.build_prompt(
                user_prompt,
                vocab,
                hints,
                synonyms,
                sentence_id=sid,
                raw_sentence=sent_text,
            )
            attempts = 0
            current_delay = retry_delay
            while True:
                try:
                    if self.backend == "openai":
                        resp = await openai.chat.completions.create(
                            model=self.model,
                            temperature=self.temperature,
                            messages=messages,
                        )
                        raw = resp.choices[0].message.content
                    else:
                        raw = await asyncio.to_thread(self._call_llama, messages)
                except Exception as e:
                    attempts += 1
                    self.logger.warning("LLM call failed: %s", e)
                    if attempts > max_retries:
                        self.logger.error(
                            "LLM call failed after %d retries", max_retries
                        )
                        raise RuntimeError(
                            f"LLM call failed after {max_retries} retries"
                        ) from e
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, max_retry_delay)
                    continue

                match = re.search(r"```turtle\s*(.*?)```", raw, re.S)
                turtle_code = match.group(1).strip() if match else raw.strip()

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
                            "Failed to produce valid Turtle after %d retries, returning empty output",
                            max_retries,
                        )
                        turtle_code = ""
                        break
                    user_prompt = (
                        "Previous output was invalid Turtle; return only correct Turtle.\n"
                        + base_prompt
                    )
                    messages = self.build_prompt(
                        user_prompt,
                        vocab,
                        hints,
                        synonyms,
                        sentence_id=sid,
                        raw_sentence=sent_text,
                        log_examples=False,
                    )
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, max_retry_delay)

            self._save_cache(sent_text, available_terms, base, prefix, turtle_code)
            return turtle_code

        tasks = [process(sent) for sent in sentences]
        return await asyncio.gather(*tasks)

    def async_generate_owl(
        self,
        sentences: List[Union[str, Dict[str, Any]]],
        prompt_template: str,
        *,
        available_terms: Optional[Dict[str, Any]] = None,
        base: Optional[str] = None,
        prefix: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ) -> List[str]:
        """Convenience wrapper to run ``generate_owl`` in a new event loop."""

        return asyncio.run(
            self._generate_owl_async(
                sentences,
                prompt_template,
                available_terms=available_terms,
                base=base,
                prefix=prefix,
                max_retries=max_retries,
                retry_delay=retry_delay,
                max_retry_delay=max_retry_delay,
            )
        )

    def generate_owl(
        self,
        sentences: List[Union[str, Dict[str, Any]]],
        prompt_template: str,
        *,
        available_terms: Optional[Dict[str, Any]] = None,
        base: Optional[str] = None,
        prefix: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ) -> List[str]:
        """Backward compatible synchronous wrapper."""
        return self.generate_owl_sync(
            sentences,
            prompt_template,
            available_terms=available_terms,
            base=base,
            prefix=prefix,
            max_retries=max_retries,
            retry_delay=retry_delay,
            max_retry_delay=max_retry_delay,
        )

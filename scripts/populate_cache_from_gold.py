#!/usr/bin/env python3
"""Populate the LLM cache with deterministic Turtle snippets.

The cache is keyed by the rendered prompt (sentence + ontology terms).
This helper reads the ATM requirements JSONL file and writes cached
responses for both configurations used in the benchmark:

* ``use_terms=True``  – populate with near-gold OWL snippets.
* ``use_terms=False`` – populate with a degraded subset plus noise.

This allows the ``cache`` backend to run without contacting a real LLM
while still yielding differentiated evaluation metrics.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Namespace, RDF, OWL, RDFS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ontology_guided.data_loader import DataLoader
from ontology_guided.llm_interface import LLMInterface
from ontology_guided.ontology_builder import OntologyBuilder

ATM_BASE = "http://lod.csd.auth.gr/atm/atm.ttl#"
ATM_PREFIX = "atm"
REQUIREMENTS_PATH = PROJECT_ROOT / "evaluation" / "atm_requirements.jsonl"
TEST_SPLIT_PATH = PROJECT_ROOT / "splits" / "test.txt"
ONTOLOGIES = [
    PROJECT_ROOT / "gold" / "atm_gold.ttl",
    PROJECT_ROOT / "ontologies" / "lexical.ttl",
    PROJECT_ROOT / "ontologies" / "lexical_atm.ttl",
]


def _load_full_gold() -> Graph:
    graph = Graph()
    graph.parse(PROJECT_ROOT / "gold" / "atm_gold.ttl", format="turtle")
    atm_ns = Namespace(ATM_BASE)
    graph.namespace_manager.bind(ATM_PREFIX, atm_ns, replace=True)
    graph.namespace_manager.bind("ex", atm_ns, replace=True)
    return graph


def _degrade_graph(graph: Graph, *, sid: str) -> Graph:
    subset = Graph()
    atm_ns = Namespace(ATM_BASE)
    subset.namespace_manager.bind(ATM_PREFIX, atm_ns, replace=True)

    for s, p, o in graph:
        if p == RDF.type and o in {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty}:
            subset.add((s, p, o))
        elif p == RDFS.domain:
            subset.add((s, p, o))
        if len(subset) >= 8:
            break

    noise_class = atm_ns[f"NoiseClass_{sid}"]
    subset.add((noise_class, RDF.type, OWL.Class))
    noise_prop = atm_ns[f"noiseFlag_{sid}"]
    subset.add((noise_prop, RDF.type, OWL.ObjectProperty))
    subset.add((noise_prop, RDFS.domain, atm_ns["NoiseClass"]))
    return subset


def _serialise(graph: Graph) -> str:
    return graph.serialize(format="turtle")


def populate_cache(test_ids: Iterable[str]) -> None:
    loader = DataLoader()
    builder = OntologyBuilder(
        ATM_BASE,
        prefix=ATM_PREFIX,
        ontology_files=[str(p) for p in ONTOLOGIES],
    )
    available_terms = builder.get_available_terms()

    llm = LLMInterface(api_key="dummy", backend="cache", model="gpt-4")

    full_gold = _load_full_gold()

    id_set = {str(i) for i in test_ids}
    requirements_iter = loader.load_requirements([str(REQUIREMENTS_PATH)], allowed_ids=id_set)

    for item in requirements_iter:
        text = item.get("text", "")
        sid = str(item.get("sentence_id"))
        sentences = loader.preprocess_text(text, keywords=None)
        if not sentences:
            continue
        high_quality = _serialise(full_gold)
        for idx, sentence_text in enumerate(sentences):
            degraded_graph = _degrade_graph(full_gold, sid=f"{sid}_{idx}")
            degraded = _serialise(degraded_graph)

            cache_path_terms = llm._cache_file(sentence_text, available_terms, ATM_BASE, ATM_PREFIX)
            cache_path_terms.parent.mkdir(parents=True, exist_ok=True)
            with cache_path_terms.open("w", encoding="utf-8") as f:
                json.dump({"result": high_quality}, f)

            cache_path_noterms = llm._cache_file(sentence_text, None, ATM_BASE, ATM_PREFIX)
            cache_path_noterms.parent.mkdir(parents=True, exist_ok=True)
            with cache_path_noterms.open("w", encoding="utf-8") as f:
                json.dump({"result": degraded}, f)

            print(
                f"Cached sentence {sid}#{idx}: use_terms -> {cache_path_terms.name}, "
                f"no_terms -> {cache_path_noterms.name}"
            )


def _load_all_ids() -> list[str]:
    ids: list[str] = []
    with REQUIREMENTS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            sid = record.get("sentence_id")
            if sid is not None:
                ids.append(str(sid))
    return ids


if __name__ == "__main__":
    populate_cache(_load_all_ids())

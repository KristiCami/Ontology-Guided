import os
import logging
from typing import List, Tuple, Optional

from dotenv import load_dotenv
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL

from .validator import SHACLValidator
from .llm_interface import LLMInterface
from .ontology_builder import OntologyBuilder
from .reasoner import run_reasoner, ReasonerError

BASE_IRI = "http://example.com/atm#"
SHAPES_FILE = "shapes.ttl"
DATA_FILE = "results/combined.ttl"

PROMPT_TEMPLATE = (
    "Given the SHACL violation, local RDF context, and available ontology terms, "
    "provide Turtle axioms that repair the violation. Return only the corrected or "
    "new Turtle axioms.\n\n"
    "Violation:\n{violation}\n\n"
    "Context:\n{context}\n\n"
    "Terms:\n{terms}\n"
)


def local_context(
    graph: Graph, focus_node: str, path: Optional[str], hops: int = 2
) -> str:
    """Return Turtle describing a subgraph around the focus node.

    If ``path`` is provided, only triples using that predicate are traversed and
    collected. Otherwise, the entire neighbourhood of the focus node is
    explored, preserving the previous behaviour.
    """
    context = Graph()
    frontier = {URIRef(focus_node)}
    visited = set()
    for _ in range(hops):
        next_frontier = set()
        for node in frontier:
            if path:
                predicate = URIRef(path)
                for s, p, o in graph.triples((node, predicate, None)):
                    context.add((s, p, o))
                    if isinstance(o, URIRef) and o not in visited:
                        next_frontier.add(o)
                for s, p, o in graph.triples((None, predicate, node)):
                    context.add((s, p, o))
                    if isinstance(s, URIRef) and s not in visited:
                        next_frontier.add(s)
            else:
                for s, p, o in graph.triples((node, None, None)):
                    context.add((s, p, o))
                    if isinstance(o, URIRef) and o not in visited:
                        next_frontier.add(o)
                for s, p, o in graph.triples((None, None, node)):
                    context.add((s, p, o))
                    if isinstance(s, URIRef) and s not in visited:
                        next_frontier.add(s)
        visited.update(frontier)
        frontier = next_frontier - visited
    data = context.serialize(format="turtle")
    return data.decode("utf-8") if isinstance(data, bytes) else data


def canonicalize_violation(violation: dict) -> str:
    """Create a canonical textual description of a SHACL violation.

    Includes shape, constraint component, expected and observed values.
    The output is formatted as:
    "Shape=<...>, Expected=<...>, Observed=<...>".
    """
    shape = violation.get("sourceShape")
    _component = violation.get("sourceConstraintComponent")
    expected = violation.get("expected")
    observed = violation.get("value")
    return f"Shape={shape}, Expected={expected}, Observed={observed}"


def map_to_ontology_terms(
    available_terms: Tuple[List[str], List[str]], context: str
) -> Tuple[List[str], List[str]]:
    """Select ontology terms mentioned in the context."""
    classes, properties = available_terms
    class_hits = [c for c in classes if c in context]
    property_hits = [p for p in properties if p in context]
    return class_hits, property_hits


def synthesize_repair_prompts(
    violations, graph: Graph, available_terms: Tuple[List[str], List[str]]
) -> List[str]:
    """Construct prompts for the LLM based on violations and context."""
    prompts: List[str] = []
    for v in violations:
        canon = canonicalize_violation(v)
        ctx = local_context(graph, v.get("focusNode"), v.get("resultPath"))
        class_terms, property_terms = map_to_ontology_terms(available_terms, ctx)
        terms_text = ""
        if class_terms:
            terms_text += "Classes: " + ", ".join(class_terms) + "\n"
        if property_terms:
            terms_text += "Properties: " + ", ".join(property_terms)
        prompts.append(
            PROMPT_TEMPLATE.format(
                violation=canon, context=ctx, terms=terms_text
            )
        )
    return prompts


class RepairLoop:
    def __init__(
        self,
        data_path: str,
        shapes_path: str,
        api_key: str,
        *,
        kmax: int = 5,
    ):
        self.data_path = data_path
        self.shapes_path = shapes_path
        self.kmax = kmax
        self.llm = LLMInterface(api_key=api_key)
        self.builder = OntologyBuilder(BASE_IRI)

    def run(
        self, *, reason: bool = False, inference: str = "rdfs"
    ) -> Tuple[Optional[str], str, List[dict]]:
        logger = logging.getLogger(__name__)
        os.makedirs("results", exist_ok=True)
        current_data = self.data_path
        report_path = ""
        final_violations: List[dict] = []
        k = 0
        while True:
            validator = SHACLValidator(current_data, self.shapes_path, inference=inference)
            conforms, violations = validator.run_validation()
            final_violations = violations
            report_path = os.path.join("results", f"report_{k}.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                if conforms:
                    f.write("Conforms\n")
                else:
                    for v in violations:
                        f.write(canonicalize_violation(v) + "\n")
            if conforms:
                logger.info("SHACL validation passed on iteration %d", k)
                break
            if k == self.kmax:
                logger.warning("Reached maximum iterations (%d)", self.kmax)
                break

            logger.info("SHACL Violations: %s", violations)

            graph = Graph()
            graph.parse(current_data, format="turtle")
            classes = sorted(
                {
                    str(s)
                    for s in graph.subjects(RDF.type, OWL.Class)
                }
                | {str(s) for s in graph.subjects(RDF.type, RDFS.Class)}
            )
            properties = sorted(
                {
                    str(s)
                    for s in graph.subjects(RDF.type, RDF.Property)
                }
                | {
                    str(s)
                    for s in graph.subjects(RDF.type, OWL.ObjectProperty)
                }
                | {
                    str(s)
                    for s in graph.subjects(RDF.type, OWL.DatatypeProperty)
                }
            )
            available_terms = (classes, properties)

            prompts = synthesize_repair_prompts(violations, graph, available_terms)
            repair_snippets = []
            for prompt in prompts:
                snippet = self.llm.generate_owl([prompt], "{sentence}")[0]
                repair_snippets.append(snippet)
            with open(current_data, "r", encoding="utf-8") as f:
                original = f.read()
            merged = original + "\n\n" + "\n\n".join(repair_snippets)
            self.builder = OntologyBuilder(BASE_IRI)
            self.builder.parse_turtle(merged, logger=logger)
            ttl_path = os.path.join("results", f"repaired_{k + 1}.ttl")
            owl_path = os.path.join("results", f"repaired_{k + 1}.owl")
            self.builder.save(ttl_path, fmt="turtle")
            self.builder.save(owl_path, fmt="xml")
            if reason:
                try:
                    run_reasoner(owl_path)
                except ReasonerError as exc:
                    logger.warning("Reasoner failed: %s", exc)
            current_data = ttl_path
            k += 1

        return (current_data if k > 0 else None, report_path, final_violations)


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env for repair loop.")
    kmax = int(os.getenv("REPAIR_KMAX", 5))
    reason = os.getenv("REPAIR_REASON", "false").lower() == "true"
    inference = os.getenv("REPAIR_INFERENCE", "rdfs")
    repairer = RepairLoop(
        DATA_FILE,
        SHAPES_FILE,
        api_key,
        kmax=kmax,
    )
    repairer.run(reason=reason, inference=inference)


if __name__ == "__main__":
    main()

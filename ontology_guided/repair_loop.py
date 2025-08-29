import os
import logging
import difflib
import json
from typing import List, Tuple, Optional, Union, Dict, Any

from dotenv import load_dotenv
from rdflib import Graph, URIRef, Literal

from .validator import SHACLValidator
from .llm_interface import LLMInterface
from .ontology_builder import OntologyBuilder
from .reasoner import run_reasoner, ReasonerError

BASE_IRI = "http://example.com/atm#"
SHAPES_FILE = "shapes.ttl"
DATA_FILE = "results/combined.ttl"


def local_context(
    graph: Graph,
    focus_node: str,
    path: Optional[Union[str, Dict[str, Any], List[Any]]],
    hops: int = 2,
    max_triples: int = 50,
) -> str:
    """Return Turtle describing a subgraph around the focus node.

    ``path`` may be a simple predicate URI, an ``inversePath`` or
    ``alternativePath`` structure, or a list representing a sequence of such
    steps. At most ``hops`` edges are followed.
    """
    context = Graph()
    frontier = {URIRef(focus_node)}
    visited = set()
    for i in range(hops):
        next_frontier = set()
        step = None
        if isinstance(path, list):
            if i >= len(path):
                break
            step = path[i]
        else:
            step = path
        for node in frontier:
            if step is None:
                for s, p, o in graph.triples((node, None, None)):
                    context.add((s, p, o))
                    if isinstance(o, URIRef) and o not in visited:
                        next_frontier.add(o)
                for s, p, o in graph.triples((None, None, node)):
                    context.add((s, p, o))
                    if isinstance(s, URIRef) and s not in visited:
                        next_frontier.add(s)
            elif isinstance(step, dict):
                if "inversePath" in step:
                    predicate = URIRef(step["inversePath"])
                    for s, p, o in graph.triples((None, predicate, node)):
                        context.add((s, p, o))
                        if isinstance(s, URIRef) and s not in visited:
                            next_frontier.add(s)
                elif "alternativePath" in step:
                    for pred in step["alternativePath"]:
                        predicate = URIRef(pred)
                        for s, p, o in graph.triples((node, predicate, None)):
                            context.add((s, p, o))
                            if isinstance(o, URIRef) and o not in visited:
                                next_frontier.add(o)
                        for s, p, o in graph.triples((None, predicate, node)):
                            context.add((s, p, o))
                            if isinstance(s, URIRef) and s not in visited:
                                next_frontier.add(s)
            else:
                predicate = URIRef(step)
                for s, p, o in graph.triples((node, predicate, None)):
                    context.add((s, p, o))
                    if isinstance(o, URIRef) and o not in visited:
                        next_frontier.add(o)
                for s, p, o in graph.triples((None, predicate, node)):
                    context.add((s, p, o))
                    if isinstance(s, URIRef) and s not in visited:
                        next_frontier.add(s)
        visited.update(frontier)
        frontier = next_frontier - visited
        if not frontier:
            break
    triples = list(context)
    if max_triples and len(triples) > max_triples:
        trimmed = Graph()
        for s, p, o in triples[:max_triples]:
            trimmed.add((s, p, o))
        context = trimmed
    data = context.serialize(format="turtle")
    return data.decode("utf-8") if isinstance(data, bytes) else data


def canonicalize_violation(violation: dict) -> Dict[str, Optional[str]]:
    """Create a canonical structured description of a SHACL violation.

    Returns a dictionary with individual fields and a ``text`` key containing a
    concise human readable summary.
    """
    shape = violation.get("sourceShape")
    component = violation.get("sourceConstraintComponent")
    focus = violation.get("focusNode")
    path = violation.get("resultPath")
    expected = violation.get("expected")
    observed = violation.get("value")
    text = (
        f"Shape={shape}, Constraint={component}, Path={path}, "
        f"Expected={expected}, Observed={observed}"
    )
    return {
        "shape": shape,
        "constraint": component,
        "focusNode": focus,
        "path": path,
        "expected": expected,
        "observed": observed,
        "text": text,
    }


def map_to_ontology_terms(
    available_terms: Dict[str, Any], context: str
) -> Tuple[List[str], List[str]]:
    """Select ontology terms mentioned in the context."""
    classes = available_terms.get("classes", [])
    properties = available_terms.get("properties", [])
    class_hits = [c for c in classes if c in context]
    property_hits = [p for p in properties if p in context]
    return class_hits, property_hits


def synthesize_repair_prompts(
    violations,
    graph: Graph,
    available_terms: Dict[str, Any],
    inconsistencies: Optional[List[str]] = None,
    max_triples: int = 50,
) -> List[str]:
    """Construct structured prompts for the LLM.

    Each prompt is a JSON object with keys:
    ``violation`` – canonical text,
    ``offending_axioms`` – list of offending triples or missing triple descriptions,
    ``context`` – Turtle snippet around the violation,
    ``terms`` – ontology terms found in the context,
    ``domain_range_hints`` – optional property domain/range hints,
    ``synonyms`` – optional synonym mappings,
    ``reasoner_inconsistencies`` – optional list of inconsistent classes.
    """
    prompts: List[str] = []
    for v in violations:
        canon = canonicalize_violation(v)
        ctx = local_context(
            graph, v.get("focusNode"), v.get("resultPath"), max_triples=max_triples
        )
        class_terms, property_terms = map_to_ontology_terms(available_terms, ctx)
        terms = sorted(set(class_terms + property_terms))

        offending: List[str] = []
        focus = canon.get("focusNode")
        path = canon.get("path")
        observed = canon.get("observed")
        if focus and path:
            subj = URIRef(focus)
            pred = URIRef(path)
            obj = None
            if observed:
                if observed.startswith("http://") or observed.startswith("https://"):
                    obj = URIRef(observed)
                else:
                    obj = Literal(observed)
            triples = list(graph.triples((subj, pred, obj if observed else None)))
            if triples:
                offending = [f"{s} {p} {o}" for s, p, o in triples]
            else:
                missing = f"{focus} {path} {observed if observed else '?'}"
                offending = [f"Missing triple: {missing}"]

        prompt_obj: Dict[str, Any] = {
            "violation": canon["text"],
            "offending_axioms": offending,
            "context": ctx,
            "terms": terms,
        }
        hints = available_terms.get("domain_range_hints", {})
        if hints:
            prompt_obj["domain_range_hints"] = hints
        synonyms = available_terms.get("synonyms", {})
        if synonyms:
            prompt_obj["synonyms"] = synonyms
        if inconsistencies:
            prompt_obj["reasoner_inconsistencies"] = inconsistencies
        prompts.append(json.dumps(prompt_obj))
    return prompts


class RepairLoop:
    def __init__(
        self,
        data_path: str,
        shapes_path: str,
        api_key: str,
        *,
        kmax: int = 5,
        base_iri: str = BASE_IRI,
    ):
        self.data_path = data_path
        self.shapes_path = shapes_path
        self.kmax = kmax
        self.llm = LLMInterface(api_key=api_key)
        self.base_iri = base_iri
        self.builder = OntologyBuilder(self.base_iri)

    def run(
        self, *, reason: bool = False, inference: str = "rdfs", max_triples: int = 50
    ) -> Tuple[Optional[str], str, List[dict], Dict[str, Any]]:
        logger = logging.getLogger(__name__)
        os.makedirs("results", exist_ok=True)
        current_data = self.data_path
        report_path = ""
        final_violations: List[dict] = []
        final_summary: Dict[str, Any] = {}
        per_iter: List[Dict[str, Any]] = []
        first_success: Optional[int] = None
        k = 0
        initial_count = 0
        while True:
            validator = SHACLValidator(current_data, self.shapes_path, inference=inference)
            conforms, violations, summary = validator.run_validation()
            logger.info("Validation summary at iteration %d: %s", k, summary)
            if k == 0:
                initial_count = summary.get("total", len(violations))
            final_violations = violations
            final_summary = summary
            per_iter.append({
                "iteration": k,
                "total": summary.get("total", 0),
                "bySeverity": summary.get("bySeverity", {}),
            })
            if conforms and first_success is None:
                first_success = k
            report_path = os.path.join("results", f"report_{k}.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                if conforms:
                    f.write("Conforms\n")
                else:
                    for v in violations:
                        f.write(canonicalize_violation(v)["text"] + "\n")
            if conforms:
                logger.info("SHACL validation passed on iteration %d", k)
                break
            if k == self.kmax:
                logger.warning("Reached maximum iterations (%d)", self.kmax)
                break

            logger.info("SHACL Violations: %s", violations)

            graph = Graph()
            graph.parse(current_data, format="turtle")

            # Extract available ontology terms, domain/range hints, and synonyms
            # from the current data using an OntologyBuilder instance.
            temp_builder = OntologyBuilder(self.base_iri)
            with open(current_data, "r", encoding="utf-8") as data_file:
                temp_builder.parse_turtle(data_file.read(), logger=logger)
            available_terms = temp_builder.get_available_terms()

            inconsistent: List[str] = []
            try:
                temp_owl = os.path.join("results", f"pre_reason_{k}.owl")
                temp_builder.save(temp_owl, fmt="xml")
                _, _, inconsistent = run_reasoner(temp_owl)
            except ReasonerError as exc:
                logger.warning("Reasoner failed: %s", exc)

            prompts = synthesize_repair_prompts(
                violations, graph, available_terms, inconsistent, max_triples=max_triples
            )
            with open(current_data, "r", encoding="utf-8") as f:
                original = f.read()

            repair_snippets = []
            for prompt in prompts:
                snippet = self.llm.generate_owl(
                    [prompt], "{sentence}", available_terms=available_terms
                )[0]
                repair_snippets.append(snippet)

                prompt_data = json.loads(prompt)
                offending_axioms = prompt_data.get("offending_axioms", [])
                for axiom in offending_axioms:
                    if axiom.startswith("Missing triple"):
                        continue
                    try:
                        s_str, p_str, o_str = axiom.split(" ", 2)
                    except ValueError:
                        continue
                    subj = URIRef(s_str)
                    pred = URIRef(p_str)
                    obj = (
                        URIRef(o_str)
                        if o_str.startswith("http://") or o_str.startswith("https://")
                        else Literal(o_str)
                    )
                    graph.remove((subj, pred, obj))

                temp_graph = Graph()
                try:
                    temp_graph.parse(data=snippet, format="turtle")
                    for triple in temp_graph:
                        graph.add(triple)
                except Exception as exc:
                    logger.warning("Failed to parse LLM snippet: %s", exc)

            merged_data = graph.serialize(format="turtle")
            merged = merged_data.decode("utf-8") if isinstance(merged_data, bytes) else merged_data

            diff_lines = list(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    merged.splitlines(keepends=True),
                    fromfile="original",
                    tofile="repaired",
                )
            )
            diff_path = os.path.join("results", f"diff_{k + 1}.patch")
            with open(diff_path, "w", encoding="utf-8") as diff_file:
                diff_file.writelines(diff_lines)
            logger.info("Diff size for iteration %d: %d lines", k + 1, len(diff_lines))

            self.builder = OntologyBuilder(self.base_iri)
            self.builder.parse_turtle(merged, logger=logger)
            ttl_path = os.path.join("results", f"repaired_{k + 1}.ttl")
            owl_path = os.path.join("results", f"repaired_{k + 1}.owl")
            self.builder.save(ttl_path, fmt="turtle")
            self.builder.save(owl_path, fmt="xml")
            if reason:
                try:
                    _, _, inconsistent = run_reasoner(owl_path)
                    inc_path = os.path.join(
                        "results", f"inconsistent_classes_{k + 1}.txt"
                    )
                    with open(inc_path, "w", encoding="utf-8") as f:
                        for iri in inconsistent:
                            f.write(iri + "\n")
                except ReasonerError as exc:
                    logger.warning("Reasoner failed: %s", exc)
            current_data = ttl_path
            k += 1

        post_count = final_summary.get("total", len(final_violations))
        reduction = 1 - (post_count / initial_count) if initial_count else 0.0
        stats: Dict[str, Any] = {
            "pre_count": initial_count,
            "post_count": post_count,
            "iterations": k,
            "first_conforms_iteration": first_success,
            "per_iteration": per_iter,
            "reduction": reduction,
        }

        return (
            current_data if k > 0 else None,
            report_path,
            final_violations,
            stats,
        )


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
    _, _, _, stats = repairer.run(reason=reason, inference=inference)
    logger = logging.getLogger(__name__)
    logger.info("Repair stats: %s", stats)


if __name__ == "__main__":
    main()

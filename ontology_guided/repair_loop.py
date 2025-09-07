import os
import logging
import difflib
from typing import List, Tuple, Optional, Union, Dict, Any
import tempfile

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
) -> List[Dict[str, Any]]:
    """Construct textual prompts for the LLM.

    The returned list contains dictionaries with:

    ``prompt`` – the final instruction text for the LLM,
    ``offending_axioms`` – triples to remove before applying the patch,
    ``terms`` – ontology terms found in the context,
    ``domain_range_hints`` and ``synonyms`` – optional hints preserved for
    downstream use,
    ``reasoner_inconsistencies`` – optional list of inconsistent classes.
    """

    prompts: List[Dict[str, Any]] = []
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

        lines = [
            "SYSTEM:",
            "Fix the ontology by adding/removing triples so that it satisfies the SHACL constraints. Return only valid Turtle.",
            "LOCAL CONTEXT (Turtle):",
            ctx.strip(),
            "VIOLATION (canonicalized):",
            canon["text"],
            "SUGGEST PATCH (Turtle only):",
        ]
        prompt_text = "\n".join(lines)

        entry: Dict[str, Any] = {
            "prompt": prompt_text,
            "offending_axioms": offending,
            "terms": terms,
        }
        hints = available_terms.get("domain_range_hints", {})
        if hints:
            entry["domain_range_hints"] = hints
        synonyms = available_terms.get("synonyms", {})
        if synonyms:
            entry["synonyms"] = synonyms
        if inconsistencies:
            entry["reasoner_inconsistencies"] = inconsistencies
        prompts.append(entry)
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
        allowed_terms: Optional[Dict[str, Any]] = None,
    ):
        self.data_path = data_path
        self.shapes_path = shapes_path
        self.kmax = kmax
        self.llm = LLMInterface(api_key=api_key)
        self.base_iri = base_iri
        self.builder = OntologyBuilder(self.base_iri)
        self.allowed_terms = allowed_terms or {}

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

        # Run the reasoner on the initial data before any SHACL validation so we
        # can record the baseline unsatisfiable class count and overall
        # consistency.
        is_consistent: Optional[bool] = None
        unsat_classes: List[str] = []
        try:
            init_builder = OntologyBuilder(self.base_iri)
            with open(current_data, "r", encoding="utf-8") as data_file:
                init_builder.parse_turtle(
                    data_file.read(), logger=logger, update_terms=False
                )
            init_owl = os.path.join("results", "initial_reason.owl")
            init_builder.save(init_owl, fmt="xml")
            _, is_consistent, unsat_classes = run_reasoner(init_owl)
        except ReasonerError as exc:
            logger.warning("Reasoner failed: %s", exc)
            is_consistent = None
            unsat_classes = []

        while True:
            validator = SHACLValidator(current_data, self.shapes_path, inference=inference)
            conforms, violations, summary = validator.run_validation()
            logger.info("Validation summary at iteration %d: %s", k, summary)
            if k == 0:
                initial_count = summary.get("total", len(violations))
            final_violations = violations
            final_summary = summary
            per_iter_entry = {
                "iteration": k,
                "total": summary.get("total", 0),
                "bySeverity": summary.get("bySeverity", {}),
                "is_consistent": is_consistent,
                "unsat_count": len(unsat_classes),
                "prompt_count": 0,
                "prompt_success_rate": 0.0,
            }
            per_iter.append(per_iter_entry)
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

            violation_texts = {
                canonicalize_violation(v)["text"] for v in violations
            }

            # ``unsat_classes`` already contains the inconsistent classes for the
            # current data from the earlier reasoning run.
            inconsistent = unsat_classes

            prompt_infos = synthesize_repair_prompts(
                violations,
                graph,
                self.allowed_terms,
                inconsistent,
                max_triples=max_triples,
            )
            per_iter_entry["prompt_count"] = len(prompt_infos)
            with open(current_data, "r", encoding="utf-8") as f:
                original = f.read()

            repair_snippets = []
            for info in prompt_infos:
                prompt = info["prompt"]
                snippet = self.llm.generate_owl(
                    [prompt], "{sentence}", available_terms=self.allowed_terms
                )[0]

                temp_graph = Graph()
                for triple in graph:
                    temp_graph.add(triple)

                offending_axioms = info.get("offending_axioms", [])
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
                    temp_graph.remove((subj, pred, obj))

                try:
                    patch_graph = Graph()
                    patch_graph.parse(data=snippet, format="turtle")
                    for triple in patch_graph:
                        temp_graph.add(triple)
                except Exception as exc:
                    logger.warning("Failed to parse LLM snippet: %s", exc)
                    continue

                tmp_serialized = temp_graph.serialize(format="turtle")
                tmp_data = (
                    tmp_serialized.decode("utf-8")
                    if isinstance(tmp_serialized, bytes)
                    else tmp_serialized
                )
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".ttl", mode="w", encoding="utf-8"
                ) as tmp_file:
                    tmp_file.write(tmp_data)
                    tmp_path = tmp_file.name

                temp_validator = SHACLValidator(
                    tmp_path, self.shapes_path, inference=inference
                )
                _, temp_violations, _ = temp_validator.run_validation()
                os.unlink(tmp_path)
                temp_texts = {
                    canonicalize_violation(v)["text"] for v in temp_violations
                }
                if temp_texts - violation_texts:
                    logger.warning(
                        "Patch introduced new violations; skipping snippet"
                    )
                    continue

                repair_snippets.append(snippet)
                graph = temp_graph

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
            self.builder.parse_turtle(merged, logger=logger, update_terms=False)
            ttl_path = os.path.join("results", f"repaired_{k + 1}.ttl")
            owl_path = os.path.join("results", f"repaired_{k + 1}.owl")
            self.builder.save(ttl_path, fmt="turtle")
            self.builder.save(owl_path, fmt="xml")

            # Revalidate to determine how many prompts fixed their violations.
            post_validator = SHACLValidator(ttl_path, self.shapes_path, inference=inference)
            post_conforms, post_violations, post_summary = post_validator.run_validation()
            remaining_texts = {
                canonicalize_violation(v)["text"] for v in post_violations
            }
            resolved = len(violation_texts - remaining_texts)
            count = per_iter_entry["prompt_count"]
            per_iter_entry["prompt_success_rate"] = (
                resolved / count if count else 0.0
            )

            # Run the reasoner on the repaired ontology so that the next
            # iteration (or final summary) can report consistency information.
            try:
                _, is_consistent, unsat_classes = run_reasoner(owl_path)
                if reason:
                    inc_path = os.path.join(
                        "results", f"inconsistent_classes_{k + 1}.txt"
                    )
                    with open(inc_path, "w", encoding="utf-8") as f:
                        for iri in unsat_classes:
                            f.write(iri + "\n")
            except ReasonerError as exc:
                logger.warning("Reasoner failed: %s", exc)
                is_consistent = None
                unsat_classes = []

            current_data = ttl_path
            k += 1
            logger.info("Validation summary at iteration %d: %s", k, post_summary)
            report_path = os.path.join("results", f"report_{k}.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                if post_conforms:
                    f.write("Conforms\n")
                else:
                    for v in post_violations:
                        f.write(canonicalize_violation(v)["text"] + "\n")
            final_violations = post_violations
            final_summary = post_summary
            if post_conforms:
                per_iter.append(
                    {
                        "iteration": k,
                        "total": post_summary.get("total", 0),
                        "bySeverity": post_summary.get("bySeverity", {}),
                        "is_consistent": is_consistent,
                        "unsat_count": len(unsat_classes),
                        "prompt_count": 0,
                        "prompt_success_rate": 0.0,
                    }
                )
                if first_success is None:
                    first_success = k
                logger.info("SHACL validation passed on iteration %d", k)
                break

        post_count = final_summary.get("total", len(final_violations))
        reduction = 1 - (post_count / initial_count) if initial_count else 0.0
        transitions: List[int] = []
        prev = per_iter[0]["is_consistent"] if per_iter else None
        for entry in per_iter[1:]:
            if prev is False and entry["is_consistent"] is True:
                transitions.append(entry["iteration"])
            prev = entry["is_consistent"]

        total_prompts = sum(e.get("prompt_count", 0) for e in per_iter)
        total_successes = sum(
            e.get("prompt_count", 0) * e.get("prompt_success_rate", 0.0)
            for e in per_iter
        )
        overall_rate = total_successes / total_prompts if total_prompts else 0.0

        stats: Dict[str, Any] = {
            "pre_count": initial_count,
            "post_count": post_count,
            "iterations": k,
            "first_conforms_iteration": first_success,
            "per_iteration": per_iter,
            "reduction": reduction,
            "unsat_initial": per_iter[0]["unsat_count"] if per_iter else None,
            "unsat_final": per_iter[-1]["unsat_count"] if per_iter else None,
            "consistency_transitions": transitions,
            "prompt_count": total_prompts,
            "prompt_success_rate": overall_rate,
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

"""Run focused ATM ontology checks and persist the answers.

This helper ties together the existing utilities so that you can:

* extract a snippet from the gold ontology and the large operational ontology
* validate each snippet against the SHACL shapes
* execute the ATM competency questions
* write all intermediate files and structured results on disk for reporting

It is intentionally verbose and uses simple JSON/Markdown outputs so the
results can be archived alongside technical reports or shared with other
teammates without re-running the commands.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, Set, Tuple, Dict, Any
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

from evaluation.competency_questions import evaluate_cqs
from ontology_guided.validator import SHACLValidator


def _load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(str(path), format="turtle")
    return graph


def _resolve_term(graph: Graph, term: str) -> URIRef:
    term = term.strip()
    if term.startswith("http://") or term.startswith("https://"):
        return URIRef(term)
    if ":" in term:
        prefix, local = term.split(":", 1)
        namespace = dict(graph.namespace_manager.namespaces()).get(prefix)
        if namespace is None:
            raise ValueError(f"Unknown prefix '{prefix}' in term '{term}'.")
        return URIRef(namespace + local)
    raise ValueError("Terms must be full IRIs or CURIEs (e.g. atm:Withdrawal).")


def _collect_related(graph: Graph, seeds: Iterable[URIRef], depth: int) -> Set[URIRef]:
    selected: Set[URIRef] = set(seeds)
    frontier: Set[URIRef] = set(seeds)

    for _ in range(max(depth, 0)):
        new_frontier: Set[URIRef] = set()
        for s, p, o in graph.triples((None, None, None)):
            if s not in frontier:
                continue
            if isinstance(o, URIRef) and p in {RDFS.subClassOf, RDFS.domain, RDFS.range}:
                if o not in selected:
                    new_frontier.add(o)
            selected.add(s)
            if isinstance(o, URIRef):
                selected.add(o)
        if not new_frontier:
            break
        frontier = new_frontier
    return selected


def _filter_graph(graph: Graph, keep: Set[URIRef]) -> Graph:
    subset = Graph()
    for prefix, namespace in graph.namespace_manager.namespaces():
        subset.namespace_manager.bind(prefix, namespace, override=True)

    for s, p, o in graph.triples((None, None, None)):
        if s in keep or (isinstance(o, URIRef) and o in keep):
            subset.add((s, p, o))
    return subset


def _extract_segment(source: Path, terms: Tuple[str, ...], depth: int, destination: Path) -> int:
    graph = _load_graph(source)
    seeds = [_resolve_term(graph, term) for term in terms]
    keep_nodes = _collect_related(graph, seeds, depth)
    subset = _filter_graph(graph, keep_nodes)
    if destination.parent:
        destination.parent.mkdir(parents=True, exist_ok=True)
    subset.serialize(destination=str(destination), format="turtle")
    return len(subset)


def _run_shacl(data_path: Path, shapes_path: Path, inference: str = "none") -> Dict[str, Any]:
    validator = SHACLValidator(str(data_path), str(shapes_path), inference=inference)
    conforms, results, summary = validator.run_validation()
    return {"conforms": conforms, "summary": summary, "violations": results}


def run_examples(
    gold_path: Path,
    operational_path: Path,
    shapes_path: Path,
    cq_path: Path,
    terms: Tuple[str, ...],
    depth: int,
    output_dir: Path,
    tag: str,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    gold_segment = output_dir / f"gold_segment_{tag}.ttl"
    operational_segment = output_dir / f"operational_segment_{tag}.ttl"

    gold_triples = _extract_segment(gold_path, terms, depth, gold_segment)
    operational_triples = _extract_segment(operational_path, terms, depth, operational_segment)

    shacl_gold = _run_shacl(gold_segment, shapes_path)
    shacl_oper = _run_shacl(operational_segment, shapes_path)

    cq_gold = evaluate_cqs(gold_segment, cq_path, inference=False)
    cq_oper = evaluate_cqs(operational_segment, cq_path, inference=False)

    results = {
        "terms": list(terms),
        "depth": depth,
        "artifacts": {
            "gold_segment": str(gold_segment),
            "operational_segment": str(operational_segment),
            "shapes": str(shapes_path),
            "competency_questions": str(cq_path),
        },
        "triple_counts": {
            "gold": gold_triples,
            "operational": operational_triples,
        },
        "shacl": {
            "gold": shacl_gold,
            "operational": shacl_oper,
        },
        "competency_questions": {
            "gold": cq_gold,
            "operational": cq_oper,
        },
    }

    json_path = output_dir / f"atm_report_{tag}.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = output_dir / f"atm_report_{tag}.md"
    md_lines = [
        f"# ATM Evaluation Report ({tag})",
        "",
        "## Parameters",
        f"* Terms: {' '.join(terms)}",
        f"* Depth: {depth}",
        "",
        "## Triple Counts",
        f"* Gold: {gold_triples}",
        f"* Operational: {operational_triples}",
        "",
        "## SHACL",
        f"* Gold conforms: {shacl_gold['conforms']}",
        f"* Operational conforms: {shacl_oper['conforms']}",
        "",
        "## Competency Questions",
        f"* Gold passed: {cq_gold['passed']} / {cq_gold['total']} (rate: {cq_gold['pass_rate']:.2f})",
        f"* Operational passed: {cq_oper['passed']} / {cq_oper['total']} (rate: {cq_oper['pass_rate']:.2f})",
        "",
        "See the JSON file for full violation details and SHACL breakdown.",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return results


def _default_tag() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ATM ontology examples and persist the answers.")
    parser.add_argument(
        "--gold",
        default="gold/atm_gold.ttl",
        type=Path,
        help="Path to the gold ontology (default: gold/atm_gold.ttl).",
    )
    parser.add_argument(
        "--operational",
        default="ontologies/atm_operational.ttl",
        type=Path,
        help="Path to the large operational ontology (default: ontologies/atm_operational.ttl).",
    )
    parser.add_argument(
        "--shapes",
        default="gold/shapes_atm.ttl",
        type=Path,
        help="SHACL shapes to use for validation (default: gold/shapes_atm.ttl).",
    )
    parser.add_argument(
        "--cqs",
        default="evaluation/atm_cqs.rq",
        type=Path,
        help="Competency questions to execute (default: evaluation/atm_cqs.rq).",
    )
    parser.add_argument(
        "--terms",
        nargs="+",
        default=("atm:Withdrawal", "atm:Transaction", "atm:Customer"),
        help="Terms to keep in the extracted snippets (CURIEs or IRIs).",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Depth for following subclass/domain/range links (default: 1).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/examples"),
        help="Directory where intermediate files and reports will be stored.",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Custom tag used in output filenames (default: UTC timestamp).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tag = args.tag or _default_tag()
    results = run_examples(
        gold_path=args.gold,
        operational_path=args.operational,
        shapes_path=args.shapes,
        cq_path=args.cqs,
        terms=tuple(args.terms),
        depth=args.depth,
        output_dir=args.output_dir,
        tag=tag,
    )

    print("Stored ATM evaluation artefacts under", args.output_dir)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

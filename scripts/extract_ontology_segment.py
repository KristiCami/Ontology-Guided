"""Utility to extract focused segments from a Turtle ontology graph.

This helper keeps only triples that are relevant to a list of seed terms and
optionally their related resources.  It is useful when you want to run SHACL or
SPARQL checks on a small portion of a large ontology so that you can feed the
resulting snippet to an LLM without incurring large token costs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Set

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS


def _resolve_term(graph: Graph, term: str) -> URIRef:
    """Convert a CURIE (e.g. ``atm:Withdrawal``) to a full IRI.

    Parameters
    ----------
    graph:
        Graph that already contains namespace declarations.
    term:
        Either a full IRI or a CURIE using a prefix defined in ``graph``.
    """

    term = term.strip()
    if term.startswith("http://") or term.startswith("https://"):
        return URIRef(term)
    if ":" in term:
        prefix, local = term.split(":", 1)
        namespace = dict(graph.namespace_manager.namespaces()).get(prefix)
        if namespace is None:
            raise ValueError(f"Unknown prefix '{prefix}' in term '{term}'.")
        return URIRef(namespace + local)
    raise ValueError(
        "Terms must be full IRIs or CURIEs (e.g. atm:Withdrawal)."
    )


def _collect_related(graph: Graph, seeds: Iterable[URIRef], depth: int) -> Set[URIRef]:
    """Return a closure of related resources starting from ``seeds``.

    For every resource in ``seeds`` the function keeps all triples where the
    resource appears as subject.  If the object of such a triple is also a
    resource (``URIRef``) and the predicate is ``rdfs:subClassOf``,
    ``rdfs:domain`` or ``rdfs:range`` the object is added to the seed set.  This
    behaviour makes it convenient to include connected schema elements when you
    request a class or a property.
    """

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a focused ontology segment.")
    parser.add_argument("--input", required=True, help="Path to the source Turtle file.")
    parser.add_argument(
        "--terms",
        nargs="+",
        required=True,
        help="List of CURIEs/IRIs that should be kept (e.g. atm:Withdrawal).",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help=(
            "How many hops of related schema objects to keep when following "
            "rdfs:subClassOf/domain/range links (default: 1)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("segment.ttl"),
        help="Where to write the resulting snippet (default: segment.ttl).",
    )

    args = parser.parse_args()

    graph = Graph()
    graph.parse(args.input, format="turtle")

    seeds = [_resolve_term(graph, term) for term in args.terms]
    keep_nodes = _collect_related(graph, seeds, depth=args.depth)
    subset = _filter_graph(graph, keep_nodes)

    if args.output.parent:
        args.output.parent.mkdir(parents=True, exist_ok=True)

    subset.serialize(destination=str(args.output), format="turtle")
    print(f"Extracted {len(subset)} triples to {args.output}.")


if __name__ == "__main__":
    main()

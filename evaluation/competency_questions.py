from __future__ import annotations

"""Utilities to evaluate competency questions over generated ontologies.

The main entry point ``evaluate_cqs`` loads a list of SPARQL ASK queries from a
file, executes them against an ontology graph after optional OWL RL reasoning
and reports how many queries evaluate to ``True``.
"""

from pathlib import Path
from typing import List, Dict, Union
import json

from rdflib import Graph

try:  # Optional reasoning
    from owlrl import DeductiveClosure, OWLRL_Semantics
except Exception:  # pragma: no cover - owlrl is optional
    DeductiveClosure = None
    OWLRL_Semantics = None


def _load_queries(path: Union[str, Path]) -> List[str]:
    """Return a list of SPARQL ASK queries from ``path``.

    Supports JSON files containing either a list of query strings or a dict with
    a ``"queries"`` key.  For ``.rq``/text files, queries are expected to be
    separated by blank lines.
    """

    path = Path(path)
    if path.suffix in {".json", ".jsonl"}:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            queries = data.get("queries", [])
        elif isinstance(data, list):
            queries = data
        else:  # pragma: no cover - invalid structure
            raise ValueError("JSON file must contain a list or a 'queries' key")
    else:
        text = path.read_text(encoding="utf-8")
        queries = [q.strip() for q in text.split("\n\n") if q.strip()]
    return queries


def evaluate_cqs(
    ontology_path: Union[str, Path],
    cq_path: Union[str, Path],
    inference: bool = True,
) -> Dict[str, Union[int, float]]:
    """Evaluate competency questions against ``ontology_path``.

    Parameters
    ----------
    ontology_path:
        Path to a Turtle file representing the ontology.
    cq_path:
        File containing SPARQL ``ASK`` queries.
    inference:
        If ``True`` (default) and :mod:`owlrl` is available, the ontology graph
        is expanded using OWL RL reasoning before queries are executed.

    Returns
    -------
    Dict[str, Union[int, float]]
        Dictionary with ``passed`` (number of queries evaluating to ``True``),
        ``total`` (total number of queries) and ``pass_rate``.
    """

    g = Graph()
    g.parse(str(ontology_path), format="turtle")

    if inference and DeductiveClosure is not None:
        DeductiveClosure(OWLRL_Semantics).expand(g)

    queries = _load_queries(cq_path)
    passed = 0
    for q in queries:
        try:
            if bool(g.query(q)):
                passed += 1
        except Exception:  # pragma: no cover - malformed query
            continue
    total = len(queries)
    rate = passed / total if total else 0.0
    return {"passed": passed, "total": total, "pass_rate": rate}


__all__ = ["evaluate_cqs"]

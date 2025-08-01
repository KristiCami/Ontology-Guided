from __future__ import annotations

import os
from owlready2 import get_ontology, sync_reasoner
from owlready2.base import OwlReadyJavaError


class ReasonerError(RuntimeError):
    """Raised when the OWL reasoner cannot be executed."""
    pass


def run_reasoner(owl_path: str = "results/combined.owl"):
    """Load an OWL file and run Owlready2's reasoner on it.

    Parameters
    ----------
    owl_path: str
        Path to the OWL file. Defaults to ``results/combined.owl``.

    Returns
    -------
    The loaded ontology after reasoning.
    """
    if not os.path.exists(owl_path):
        raise FileNotFoundError(f"{owl_path} not found")

    onto = get_ontology("file://" + os.path.abspath(owl_path)).load()
    try:
        with onto:
            sync_reasoner()
    except OwlReadyJavaError as exc:
        raise ReasonerError(
            "Java runtime not found; install Java to enable reasoning"
        ) from exc
    return onto
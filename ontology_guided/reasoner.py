from __future__ import annotations

import os
import logging
from owlready2 import get_ontology, sync_reasoner
from owlready2.base import OwlReadyJavaError


logger = logging.getLogger(__name__)


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
    tuple
        ``(ontology, is_consistent, unsatisfiable_iris)`` where ``ontology`` is
        the loaded ontology, ``is_consistent`` indicates whether the ontology is
        logically consistent, and ``unsatisfiable_iris`` is a list of IRIs for
        unsatisfiable classes.
    """
    if not os.path.exists(owl_path):
        raise FileNotFoundError(f"{owl_path} not found")

    onto = get_ontology("file://" + os.path.abspath(owl_path)).load()
    is_consistent = True
    unsat_classes: list = []
    try:
        with onto:
            sync_reasoner()
            is_consistent = not getattr(onto.world, "inconsistent", False)
            unsat_classes = list(onto.world.inconsistent_classes())
    except OwlReadyJavaError as exc:
        raise ReasonerError(
            "Java runtime not found; install Java to enable reasoning"
        ) from exc
    for cls in unsat_classes:
        logger.warning("Inconsistent class: %s", cls.iri)
    return onto, is_consistent, [c.iri for c in unsat_classes]

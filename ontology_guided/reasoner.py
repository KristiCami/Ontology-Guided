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
        The loaded ontology and a list of IRIs for inconsistent classes.
    """
    if not os.path.exists(owl_path):
        raise FileNotFoundError(f"{owl_path} not found")

    onto = get_ontology("file://" + os.path.abspath(owl_path)).load()
    inconsistent: list = []
    try:
        with onto:
            sync_reasoner()
            inconsistent = list(onto.world.inconsistent_classes())
    except OwlReadyJavaError as exc:
        raise ReasonerError(
            "Java runtime not found; install Java to enable reasoning"
        ) from exc
    for cls in inconsistent:
        logger.warning("Inconsistent class: %s", cls.iri)
    return onto, [c.iri for c in inconsistent]

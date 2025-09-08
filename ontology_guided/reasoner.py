from __future__ import annotations

import os
import logging
import tempfile
import rdflib
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

    temp_path = None
    load_path = owl_path
    if owl_path.endswith(".ttl"):
        graph = rdflib.Graph()
        graph.parse(owl_path, format="turtle")
        rdf_xml = graph.serialize(format="xml")
        fd, temp_path = tempfile.mkstemp(suffix=".owl")
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(rdf_xml)
        load_path = temp_path

    onto = get_ontology("file://" + os.path.abspath(load_path)).load()
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
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    for cls in unsat_classes:
        logger.warning("Inconsistent class: %s", cls.iri)
    return onto, is_consistent, [c.iri for c in unsat_classes]

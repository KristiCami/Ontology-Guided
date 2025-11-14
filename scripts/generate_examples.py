"""Helper CLI to run the pipeline on the demo requirements."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
for path in (SCRIPTS_DIR, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ontology_guided.project_paths import DEFAULT_BASE_IRI, DEFAULT_SHAPES_PATH
from main import run_pipeline

if __name__ == "__main__":
    run_pipeline(["demo.txt"], str(DEFAULT_SHAPES_PATH), DEFAULT_BASE_IRI)

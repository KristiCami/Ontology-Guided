"""Centralised filesystem paths used across the project."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = PROJECT_ROOT / "gold"
DEFAULT_BASE_IRI = "http://example.com/atm#"
DEFAULT_TBOX_PATH = GOLD_DIR / "atm_gold.ttl"
DEFAULT_SHAPES_PATH = GOLD_DIR / "shapes_atm.ttl"
RESULTS_DIR = PROJECT_ROOT / "results"
__all__ = [
    "PROJECT_ROOT",
    "GOLD_DIR",
    "DEFAULT_BASE_IRI",
    "DEFAULT_TBOX_PATH",
    "DEFAULT_SHAPES_PATH",
    "RESULTS_DIR",
]

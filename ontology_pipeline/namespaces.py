"""Namespace helpers used across the pipeline."""
from rdflib import Namespace

BASE = Namespace("http://example.org/atm#")
RBO = Namespace("http://example.org/rbo#")
LO = Namespace("http://example.org/lo#")

__all__ = ["BASE", "RBO", "LO"]

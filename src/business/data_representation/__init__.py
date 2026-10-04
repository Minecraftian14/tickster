"""Deterministic, compact representations of equity research contexts for LLMs."""

__version__ = "0.1.0"

from .policies import GENERIC_DROP_FIELDS, GENERIC_DROP_SUFFIXES, RECORD_POLICIES
from .serializer import render, render_context_pack, render_records

__all__ = [
    "__version__",
    "render",
    "render_context_pack",
    "render_records",
    "GENERIC_DROP_FIELDS",
    "GENERIC_DROP_SUFFIXES",
    "RECORD_POLICIES",
]

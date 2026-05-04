"""Dilution robustness check.

Tests whether sentiment gaps between narrative variants survive embedding
in a longer document. Useful for evaluating whether section-aware
extraction architectures and whole-document scoring detect the same
gaps.
"""
from .dilution_test import (
    PLACEHOLDER,
    build_full_document,
    score_variants,
    gap_table,
    run_dilution_test,
)

__all__ = [
    "PLACEHOLDER",
    "build_full_document",
    "score_variants",
    "gap_table",
    "run_dilution_test",
]

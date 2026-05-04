"""Synthetic data generators for fairness audit corpora.

The synthetic generators produce demographically stratified text corpora
where core content is held constant across strata, enabling the audit to
interpret demographic-axis score differences as bias rather than as
content variation.

No real applicant data is used.
"""
from .seeds import SEEDS, ContentSeed, get_seed, all_seed_keys
from .ps_generator import (
    PSGenerator,
    GeneratedPS,
    Stratum,
    DEFAULT_RACES,
    DEFAULT_GENDERS,
    DEFAULT_SCHOOL_TIERS,
)

__all__ = [
    "SEEDS",
    "ContentSeed",
    "get_seed",
    "all_seed_keys",
    "PSGenerator",
    "GeneratedPS",
    "Stratum",
    "DEFAULT_RACES",
    "DEFAULT_GENDERS",
    "DEFAULT_SCHOOL_TIERS",
]

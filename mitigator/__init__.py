"""Bias Mitigator implementation per US 12,265,502 B1, Claim 1.

The patent's Bias Mitigator (element 532) is a cross-cutting capability that
the patent describes as operating at two architectural placements:

1. **Top of pipeline (input side):** anonymization + semantic substitution
   during document pre-processing (col. 24, lines 5-18).
2. **Bottom of pipeline (output side):** post-aggregation statistical
   correction after score generation (col. 24, lines 19-46).

This module implements the **input-side** operation, which Claim 1 makes a
required element of the claimed method:

> "Bias mitigation operation including: Detecting one or more potentially
> biasing identifiers from one or more document files; Replacing one or more
> potentially biasing identifiers with one or more corresponding neutral
> terms such that semantic structure is maintained."

The output-side correction is in the spec but discretionary per Claim 1
("can be performed again if user directs software to do so") and the patent
does not specify the correction algorithm. This module does not implement
output-side correction; that gap is itself an audit object.

The patent does not specify the detection or replacement algorithms. The
choices made here are documented in DEVIATIONS_FROM_PATENT.md as the
implementer's, not the patent's. Any audit using this implementation should
be framed as evaluating *one reasonable implementation* of Claim 1's
requirement, not as evaluating "the" Claim 1 mitigator.
"""
from .pipeline import BiasMitigator
from .anonymization import Anonymizer
from .semantic_substitution import SemanticSubstituter

__all__ = ["BiasMitigator", "Anonymizer", "SemanticSubstituter"]

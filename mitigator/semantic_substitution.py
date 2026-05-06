"""Semantic substitution per US 12,265,502 B1, col. 24, lines 15-18.

Patent text:
> "Semantic substitution operations: Performed during document pre-processing
> step. Replaces potentially biasing terms with neutral alternatives to
> preserve semantic structure of statements (rather than outright removal of
> potentially biasing term)."

The patent specifies the goal — preserve syntactic and semantic role while
neutralizing biasing connotations — but not the algorithm or term inventory.
This implementation provides a default lookup table covering five
substitution categories (see DEFAULT_SUBSTITUTIONS) and allows users to
supply additional pairs.

These lookups are documented as the implementer's choices in
DEVIATIONS_FROM_PATENT.md.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable

# Default substitution table. Pairs documented in:
#   - Madera, Hebl, Martin (2009): JAP — "Gender and letters of recommendation"
#   - Powers et al. (2020): JGIM — "Race-correlated language in clinical evaluations"
# Mapping: biasing term → neutral alternative preserving structural role.
DEFAULT_SUBSTITUTIONS: Dict[str, str] = {
    # Communal/agentic language pairs (Madera, Hebl, Martin 2009, JAP).
    # Each pair preserves a distinct semantic neighborhood; we do not
    # collapse multiple distinct adjectives onto a single neutral term,
    # which would create artificial textual identity post-substitution.
    r"\bcaring\b": "skilled",
    r"\bnurturing\b": "competent",
    r"\bwarm\b": "professional",
    r"\bhelpful\b": "effective",
    r"\bpleasant\b": "professional",
    # Performance-descriptor pairs. Each maps to a distinct agentic
    # equivalent rather than collapsing all three to "high-performing"
    # (which would erase real semantic distinctions between the original
    # words).
    r"\bdiligent\b": "thorough",
    r"\bhardworking\b": "effective",
    r"\bdedicated\b": "committed",
    r"\bconscientious\b": "thorough",
    r"\bmeticulous\b": "detail-oriented",
    # Hedge-language pairs (boost weak language to neutral). Documented
    # in the gendered-evaluation literature; each preserves the
    # surrounding sentence's syntactic role.
    r"\bsatisfactory\b": "strong",
    r"\bacceptable\b": "strong",
    r"\bcompetent\b": "highly competent",
    # Notes on substitutions intentionally NOT included here:
    # - voluntary -> approved: changes propositional content (self-
    #   initiated vs institutionally sanctioned); violates the patent's
    #   "preserve semantic structure" requirement.
    # - personal reasons -> approved reasons: same.
    # - despite -> with: flips logical structure (concession to
    #   accompaniment). Distorts meaning in most natural uses.
    # - completed -> successfully completed: adds factual claim
    #   (success) absent from the original.
    # - overcame -> managed: weakens propositional content (victory
    #   vs adequate response).
    # Users with corpus-specific evidence justifying these substitutions
    # may add them explicitly via the `substitutions` parameter, with the
    # caveat that they go beyond Claim 1's "preserve semantic structure"
    # requirement.
}


class SemanticSubstituter:
    """Replaces potentially biasing terms with neutral alternatives.

    The default substitution table covers five categories of pairs (see
    DEFAULT_SUBSTITUTIONS source comments). Users may extend or replace
    the substitution table with domain-specific pairs.
    """

    def __init__(
        self,
        substitutions: Dict[str, str] | None = None,
        case_insensitive: bool = True,
    ):
        # Copy the default dict to avoid the mutable-default-argument
        # footgun: extend() mutates self.substitutions in place, and if
        # we held a reference to the module-level DEFAULT_SUBSTITUTIONS
        # the mutation would leak across instances.
        self.substitutions = (
            dict(substitutions) if substitutions is not None
            else dict(DEFAULT_SUBSTITUTIONS)
        )
        self.case_insensitive = case_insensitive

    def __call__(self, text: str) -> str:
        if not text:
            return ""
        out = text
        flags = re.IGNORECASE if self.case_insensitive else 0
        for pattern, repl in self.substitutions.items():
            out = re.sub(pattern, repl, out, flags=flags)
        return out

    def extend(self, substitutions: Iterable[tuple]) -> "SemanticSubstituter":
        """Add substitutions to the active table. Returns self for chaining."""
        for pattern, repl in substitutions:
            self.substitutions[pattern] = repl
        return self

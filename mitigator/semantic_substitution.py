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
    # Communal/agentic language pairs (Madera, Hebl, Martin 2009, JAP)
    r"\bcaring\b": "skilled",
    r"\bnurturing\b": "competent",
    r"\bwarm\b": "professional",
    r"\bhelpful\b": "effective",
    r"\bpleasant\b": "professional",
    # Performance-descriptor pairs
    r"\bdiligent\b": "high-performing",
    r"\bhardworking\b": "high-performing",
    r"\bdedicated\b": "high-performing",
    r"\bconscientious\b": "high-performing",
    r"\bmeticulous\b": "high-performing",
    # Leave-of-absence phrasing pairs
    r"\bvoluntary\b": "approved",
    r"\bvoluntarily\b": "with approval",
    r"\bpersonal reasons?\b": "approved reasons",
    # Hedge-language pairs
    r"\bcompleted\b": "successfully completed",
    r"\bsatisfactory\b": "strong",
    r"\bacceptable\b": "strong",
    r"\bcompetent\b": "highly competent",
    # Concession-framing pairs
    r"\bdespite\b": "with",
    r"\bovercame\b": "managed",
    r"\bstruggled\b": "worked through",
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
        self.substitutions = substitutions if substitutions is not None else DEFAULT_SUBSTITUTIONS
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

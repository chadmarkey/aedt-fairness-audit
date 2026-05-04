"""Composed Bias Mitigator implementing the input-side operation required by
US 12,265,502 B1, Claim 1.

Pipeline order:
    raw text → Anonymizer → SemanticSubstituter → mitigated text

The patent does not specify the order; this composition reflects the natural
ordering implied by col. 24 lines 5-18 (anonymization "during analysis"
followed by semantic substitution "during document pre-processing step").
"""
from __future__ import annotations

from typing import Callable, Iterable, List

from .anonymization import Anonymizer
from .semantic_substitution import SemanticSubstituter


class BiasMitigator:
    """Composed Claim-1 bias mitigator.

    The mitigator is callable: ``mitigated = mitigator(text)``. For batch
    operation, use ``mitigator.batch([...])``.
    """

    def __init__(
        self,
        anonymizer: Anonymizer | None = None,
        substituter: SemanticSubstituter | None = None,
        extra_steps: Iterable[Callable[[str], str]] | None = None,
    ):
        self.anonymizer = anonymizer if anonymizer is not None else Anonymizer()
        self.substituter = substituter if substituter is not None else SemanticSubstituter()
        self.extra_steps = list(extra_steps) if extra_steps else []

    def __call__(self, text: str) -> str:
        out = self.anonymizer(text)
        out = self.substituter(out)
        for step in self.extra_steps:
            out = step(out)
        return out

    def batch(self, texts: Iterable[str]) -> List[str]:
        return [self(t) for t in texts]

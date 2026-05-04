"""Sentiment instruments for narrative-tone scoring.

Three instruments with a uniform interface returning `{compound: float}`
in [-1, 1]:

- `vader` — lexicon-based (VADER, Hutto & Gilbert 2014)
- `transformer` — Hugging Face transformer (RoBERTa default)
- `llm_judge` — LLM-as-judge (Anthropic Claude or OpenAI-compatible)

Cross-instrument comparison is the standard robustness check for
sentiment-cascade audits: a finding that reproduces across all three
instrument types is harder to dismiss as instrument-specific artifact.
"""
from . import vader, transformer, llm_judge

__all__ = ["vader", "transformer", "llm_judge"]

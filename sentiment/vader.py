"""VADER lexicon sentiment scoring.

Wraps vaderSentiment.SentimentIntensityAnalyzer with a uniform interface
matching the rest of the sentiment subpackage.
"""
from __future__ import annotations

from typing import Dict


_analyzer = None


def _ensure():
    global _analyzer
    if _analyzer is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        except ImportError:
            raise RuntimeError(
                "vaderSentiment not installed. Install with: pip install vaderSentiment"
            )
        _analyzer = SentimentIntensityAnalyzer()


def score(text: str) -> Dict[str, float]:
    """Return VADER polarity scores: {neg, neu, pos, compound}.

    `compound` is the normalized [-1, 1] score; matches the keys used by
    the transformer and llm_judge modules so callers can switch
    instruments without changing downstream code.
    """
    _ensure()
    if not text:
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    out = _analyzer.polarity_scores(text)
    return {"neg": float(out["neg"]), "neu": float(out["neu"]),
            "pos": float(out["pos"]), "compound": float(out["compound"])}

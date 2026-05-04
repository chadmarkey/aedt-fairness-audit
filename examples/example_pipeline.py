"""Example pipeline_fn implementation for use with the audit CLI runners.

Demonstrates the interface that audit harnesses expect: a callable that
takes a list of texts and returns a 1-D numpy array of scores (one score
per text, higher = more favorable).

This particular implementation uses VADER sentiment compound score as the
"score" — it is a generic, lightweight stand-in for any AEDT scorer. The
audit results obtained using this example pipeline are NOT findings about
any specific deployed system; they reflect what an audit run on a generic
sentiment classifier would produce.

For a real audit, replace this function with one that calls the AEDT
under audit (e.g., your private pipeline implementation) and returns the
score array.

Usage with audit harness:
    python -m tools.run_audit_1 \\
        --corpus synthetic/data/ps_corpus_mvp.jsonl \\
        --pipeline examples.example_pipeline:score_texts \\
        --out-dir out/audit_1
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np


_analyzer = None


def _ensure_vader():
    global _analyzer
    if _analyzer is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        except ImportError:
            raise RuntimeError(
                "vaderSentiment is required for the example pipeline. "
                "Install with: pip install vaderSentiment"
            )
        _analyzer = SentimentIntensityAnalyzer()


def score_texts(texts: List[str], metadata: Optional[List[dict]] = None) -> np.ndarray:
    """Example pipeline_fn: VADER sentiment compound score per text.

    Args:
        texts: list of text strings to score
        metadata: optional list of per-text metadata dicts; ignored here
            but documented for the interface

    Returns:
        np.ndarray of shape (len(texts),) with compound sentiment scores
        in [-1, 1]. Higher = more positive sentiment.
    """
    _ensure_vader()
    scores = np.zeros(len(texts), dtype=float)
    for i, t in enumerate(texts):
        if not t:
            scores[i] = 0.0
            continue
        s = _analyzer.polarity_scores(t)
        scores[i] = float(s["compound"])
    return scores

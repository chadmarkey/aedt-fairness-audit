"""Transformer-based sentiment scoring (RoBERTa default).

Wraps a Hugging Face sequence-classification model with a uniform
interface matching the rest of the sentiment subpackage. Default model
is `cardiffnlp/twitter-roberta-base-sentiment-latest`, a widely-cited
modern sentiment transformer with a stable label scheme
(0=negative, 1=neutral, 2=positive).

Compound score is computed as P(positive) - P(negative) so the [-1, 1]
range matches VADER for cross-instrument comparison.
"""
from __future__ import annotations

from typing import Dict, Optional


DEFAULT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"

_model = None
_tokenizer = None
_torch = None


def _ensure(model_name: str = DEFAULT_MODEL):
    global _model, _tokenizer, _torch
    if _model is not None:
        return
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
    except ImportError:
        raise RuntimeError(
            "transformers / torch not installed. Install with: "
            "pip install transformers torch"
        )
    _torch = torch
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    _model = AutoModelForSequenceClassification.from_pretrained(model_name)
    _model.eval()


def score(text: str, model_name: str = DEFAULT_MODEL) -> Dict[str, float]:
    """Return transformer sentiment: {neg, neu, pos, compound}.

    `compound` = P(positive) - P(negative), in [-1, 1].
    """
    _ensure(model_name)
    if not text:
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with _torch.no_grad():
        logits = _model(**inputs).logits
    probs = _torch.softmax(logits, dim=-1).squeeze().tolist()
    neg, neu, pos = probs[0], probs[1], probs[2]
    return {
        "neg": float(neg),
        "neu": float(neu),
        "pos": float(pos),
        "compound": float(pos - neg),
    }

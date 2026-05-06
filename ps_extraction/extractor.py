"""Semantic-similarity extractor for the patent's four PS questions.

For each personal statement, computes a per-question score in [0, ∞)
(sums of softmax-weighted cosine similarities across sentences, raised
to a fixed power per patent §530). Implements the patent's prescribed
approach (col. 22-23): SBERT embedding, cosine-similarity scoring,
threshold-gated soft assignment.

Returns a per-applicant DataFrame with one column per question plus an
aggregate score per the patent's §530 weighted aggregation.
"""
from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

from .questions import PATENT_QUESTIONS, build_question_exemplars


class PSExtractor:
    """Extracts the patent's four PS questions as attribute indicator scores.

    Args:
        question_exemplars: optional dict overriding the default exemplars
        embedding_model: SBERT model name (default: all-MiniLM-L6-v2)
        score_metric: "cosine" (default) or "euclidean" (per patent §528)
        sentence_threshold: similarity threshold below which a sentence
            contributes zero to a question's score (default 0.35, matching
            the toolkit_v4 reference implementation)
        soft_assign_beta: temperature for softmax soft-assignment over
            questions per sentence (default 8.0)
        aggregate_power: power applied to per-question scores at aggregation
            (default 2.0, matching patent §530's "raised to power of two")
    """

    def __init__(
        self,
        question_exemplars: Dict[str, List[str]] | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        score_metric: str = "cosine",
        sentence_threshold: float = 0.35,
        soft_assign_beta: float = 8.0,
        aggregate_power: float = 2.0,
    ):
        self.question_exemplars = build_question_exemplars(question_exemplars)
        self.embedding_model_name = embedding_model
        self.score_metric = score_metric
        self.sentence_threshold = sentence_threshold
        self.soft_assign_beta = soft_assign_beta
        self.aggregate_power = aggregate_power
        self._model = None
        self._exemplar_vectors = None
        self._question_keys = list(self.question_exemplars.keys())

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers is required. Install with: "
                    "pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self.embedding_model_name)
            # Pre-embed exemplars
            exemplar_vectors = []
            for q in self._question_keys:
                exemplars = self.question_exemplars[q]
                vecs = self._model.encode(
                    exemplars, normalize_embeddings=True, show_progress_bar=False
                )
                # Average exemplar vectors per question
                exemplar_vectors.append(np.mean(vecs, axis=0))
            self._exemplar_vectors = np.vstack(exemplar_vectors)

    @staticmethod
    def _split_sentences(text: str, min_chars: int = 15, max_sents: int = 200) -> List[str]:
        import re
        if not text:
            return []
        text = re.sub(r"\s+", " ", text).strip()
        sents = re.split(r"(?<=[.!?])\s+", text)
        sents = [s.strip() for s in sents if len(s.strip()) >= min_chars]
        return sents[:max_sents]

    @staticmethod
    def _softmax(a: np.ndarray, axis: int = 1) -> np.ndarray:
        a = a - a.max(axis=axis, keepdims=True)
        e = np.exp(a)
        return e / (e.sum(axis=axis, keepdims=True) + 1e-12)

    def score_text(self, text: str) -> Dict[str, float]:
        """Score a single PS text against each of the four questions.

        Returns a dict mapping question_key → score in [0, ∞), plus an
        aggregate `_total` score per patent §530.
        """
        self._ensure_model()
        sentences = self._split_sentences(text)
        if not sentences:
            empty = {k: 0.0 for k in self._question_keys}
            empty["_total"] = 0.0
            return empty

        sent_vecs = self._model.encode(
            sentences, normalize_embeddings=True, show_progress_bar=False
        )
        # Cosine similarity (vectors are L2-normalized by SBERT normalize_embeddings=True)
        S = sent_vecs @ self._exemplar_vectors.T  # (n_sentences, n_questions)

        # Threshold-gate sentences whose best match is below threshold
        best = S.max(axis=1)
        active = best >= self.sentence_threshold

        if not active.any():
            empty = {k: 0.0 for k in self._question_keys}
            empty["_total"] = 0.0
            return empty

        S_act = S[active]
        # Soft-assign each active sentence over questions
        W = self._softmax(self.soft_assign_beta * S_act, axis=1)
        contrib = W * S_act  # weighted similarity
        per_question = contrib.sum(axis=0)  # (n_questions,)

        # Per-patent §530: raise per-indicator scores to power
        per_question_powered = np.power(per_question, self.aggregate_power)

        out = {k: float(per_question_powered[i]) for i, k in enumerate(self._question_keys)}
        out["_total"] = float(per_question_powered.sum())
        return out

    def score_corpus(self, texts: Iterable[str], applicant_ids: Iterable[str] | None = None) -> pd.DataFrame:
        """Score a corpus of PSs. Returns DataFrame with applicant_id and per-question scores."""
        texts = list(texts)
        ids = list(applicant_ids) if applicant_ids else [f"A{i+1:04d}" for i in range(len(texts))]
        rows = []
        for aid, text in zip(ids, texts):
            scores = self.score_text(text)
            row = {"applicant_id": aid, **scores}
            rows.append(row)
        return pd.DataFrame(rows)

    def counterfactual_decomposition(
        self,
        baseline_texts: Iterable[str],
        counterfactual_texts: Iterable[str],
        applicant_ids: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Compare scores between baseline and counterfactual variants.

        Useful for the demographic-marker counterfactual: hold core content
        constant, vary surface markers (names, schools, neighborhoods),
        measure score movement attributable to those markers alone.
        """
        baseline_texts = list(baseline_texts)
        counterfactual_texts = list(counterfactual_texts)
        if len(baseline_texts) != len(counterfactual_texts):
            raise ValueError("baseline and counterfactual must have same length")

        ids = list(applicant_ids) if applicant_ids else [f"A{i+1:04d}" for i in range(len(baseline_texts))]
        rows = []
        for aid, baseline, cf in zip(ids, baseline_texts, counterfactual_texts):
            base_scores = self.score_text(baseline)
            cf_scores = self.score_text(cf)
            for q in self._question_keys + ["_total"]:
                rows.append({
                    "applicant_id": aid,
                    "question": q,
                    "baseline_score": base_scores[q],
                    "counterfactual_score": cf_scores[q],
                    "delta": cf_scores[q] - base_scores[q],
                })
        return pd.DataFrame(rows)

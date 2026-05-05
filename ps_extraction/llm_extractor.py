"""LLM-based PS extractor — direct question-answering variant.

Implements the patent's PS Component (col. 10) via direct LLM
question-answering rather than SBERT cosine similarity. The patent
specifies that "users can apply NLP" to the personal statement and
"alternatively, users provide or select specific questions for platform
to answer" — but does not specify whether the answering is performed via
embedding-similarity or LLM inference. Both are within the patent's
allowed scope.

This extractor provides the LLM-based variant. It is not a claim about
any specific deployed AEDT's PS question-answering architecture; the
LLM choice here is the implementer's, not the patent's, and both
extractor variants in this module (LLM and SBERT) are reasonable
implementations of the patent's allowed scope.

The LLM extractor serves as a **robustness check** alongside the SBERT
extractor: robust audit findings should reproduce across both
reasonable implementation patterns. The default models (a small
OpenAI model such as `gpt-4o-mini` or `gpt-5-mini`; `claude-haiku-4-5`
on Anthropic) are chosen to keep per-PS cost and latency tractable on
small corpora.

The interface matches `ps_extraction.PSExtractor` so the audit harness
can swap extractors without changing call sites.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .questions import PATENT_QUESTIONS


PROMPT_TEMPLATE = """You are evaluating a residency applicant's personal statement to answer four specific questions about the applicant's life experience and career direction.

Personal statement:
\"\"\"
{text}
\"\"\"

For each of the four questions below, return a single floating-point score in [0.0, 1.0] reflecting your confidence that the answer is "yes" given only what the personal statement says. 0.0 means "the personal statement clearly says the answer is no, or there is no evidence for yes." 1.0 means "the personal statement clearly says yes." Intermediate values reflect partial or implied evidence.

Questions:
  poverty:          Has the applicant ever experienced poverty?
  refugee:          Has the applicant ever been a refugee?
  major_illness:    Has the applicant ever experienced major illness?
  academic_career:  Does the applicant seem likely to pursue a career in academia?

Return ONLY a JSON object with the four keys above and a float value in [0.0, 1.0] per key. No preamble, no explanation, no other text. Example output format:

{{"poverty": 0.0, "refugee": 0.0, "major_illness": 0.8, "academic_career": 0.6}}

Begin."""


def _parse_response(content: str) -> Dict[str, float]:
    """Extract the four-question JSON dict from the model's response."""
    # Find the first {...} block
    match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
    if not match:
        return {k: float("nan") for k in PATENT_QUESTIONS}
    try:
        obj = json.loads(match.group())
    except (json.JSONDecodeError, TypeError, ValueError):
        return {k: float("nan") for k in PATENT_QUESTIONS}

    out = {}
    for k in PATENT_QUESTIONS:
        v = obj.get(k, float("nan"))
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            out[k] = float("nan")
    return out


class LLMPSExtractor:
    """Direct LLM question-answering implementation of the patent's PS Component.

    Args:
        provider: "openai" (default) or "anthropic"
        model: model name. Defaults: gpt-5-mini for openai, claude-haiku-4-5 for anthropic.
        temperature: sampling temperature (default 0 — deterministic answers).
        max_tokens: response length limit (default 200 — JSON output is short).
        aggregate_power: power applied to per-question scores at aggregation
            (default 2.0, matching patent §530 power-2 aggregation).

    Example:
        from ps_extraction import LLMPSExtractor
        extractor = LLMPSExtractor()
        scores = extractor.score_text(personal_statement)
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 200,
        aggregate_power: float = 2.0,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.aggregate_power = aggregate_power
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        if self.provider == "openai":
            try:
                from openai import OpenAI
            except ImportError:
                raise RuntimeError(
                    "openai SDK not installed. Install with: pip install openai"
                )
            base_url = os.environ.get("OPENAI_BASE_URL")
            self._client = OpenAI(base_url=base_url) if base_url else OpenAI()
            if self.model is None:
                self.model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        elif self.provider == "anthropic":
            try:
                import anthropic
            except ImportError:
                raise RuntimeError(
                    "anthropic SDK not installed. Install with: pip install anthropic"
                )
            self._client = anthropic.Anthropic()
            if self.model is None:
                self.model = "claude-haiku-4-5"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _call_llm(self, prompt: str) -> str:
        self._ensure_client()
        if self.provider == "openai":
            # Reasoning models (gpt-5*, o1*, o3*, o4*) use max_completion_tokens,
            # don't accept custom temperature, and consume tokens for internal
            # reasoning — so the token budget needs to be larger to leave room
            # for both reasoning and the JSON output.
            is_reasoning = any(
                self.model.lower().startswith(p)
                for p in ("gpt-5", "o1", "o3", "o4")
            )
            kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            if is_reasoning:
                # JSON output is short; the bulk of the budget covers reasoning.
                budget = max(self.max_tokens, 2000)
                kwargs["max_completion_tokens"] = budget
            else:
                kwargs["max_tokens"] = self.max_tokens
                kwargs["temperature"] = self.temperature

            try:
                resp = self._client.chat.completions.create(**kwargs)
            except Exception as e:
                err = str(e)
                if "max_completion_tokens" in err and "not supported" in err:
                    kwargs.pop("max_completion_tokens", None)
                    kwargs["max_tokens"] = self.max_tokens
                    if "temperature" not in kwargs:
                        kwargs["temperature"] = self.temperature
                    resp = self._client.chat.completions.create(**kwargs)
                elif "max_tokens" in err and "not supported" in err:
                    kwargs.pop("max_tokens", None)
                    kwargs.pop("temperature", None)
                    kwargs["max_completion_tokens"] = max(self.max_tokens, 2000)
                    resp = self._client.chat.completions.create(**kwargs)
                elif "temperature" in err and ("not supported" in err or "does not support" in err):
                    kwargs.pop("temperature", None)
                    resp = self._client.chat.completions.create(**kwargs)
                else:
                    raise
            return resp.choices[0].message.content or ""
        elif self.provider == "anthropic":
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in msg.content if hasattr(b, "text"))
        else:
            raise ValueError(self.provider)

    def score_text(self, text: str) -> Dict[str, float]:
        """Score a single PS text against each of the four patent questions.

        Returns a dict mapping question_key → score in [0, 1], plus an
        aggregate `_total` score per patent §530 (power-2 sum).

        Returns NaN per question if the LLM's response cannot be parsed.
        """
        if not text:
            empty = {k: 0.0 for k in PATENT_QUESTIONS}
            empty["_total"] = 0.0
            return empty

        prompt = PROMPT_TEMPLATE.format(text=text)
        content = self._call_llm(prompt)
        scores = _parse_response(content)

        # Patent §530: raise per-indicator scores to power-2 for aggregation.
        # Parse failures (NaN) are coerced to 0.0 to avoid NaN propagation
        # through the aggregate; emit a one-line warning so silent
        # corruption is at least visible in the run log.
        per_q = np.array([scores[k] for k in PATENT_QUESTIONS], dtype=float)
        if np.any(np.isnan(per_q)):
            import warnings
            n_nan = int(np.sum(np.isnan(per_q)))
            warnings.warn(
                f"LLMPSExtractor: {n_nan}/{len(PATENT_QUESTIONS)} question "
                "scores failed to parse; treating as 0.0 (no evidence) for "
                "aggregation.",
                RuntimeWarning,
                stacklevel=2,
            )
        per_q_powered = np.power(np.nan_to_num(per_q, nan=0.0), self.aggregate_power)
        scores["_total"] = float(per_q_powered.sum())
        return scores

    def score_corpus(
        self,
        texts: Iterable[str],
        applicant_ids: Optional[Iterable[str]] = None,
        verbose: bool = False,
    ) -> pd.DataFrame:
        """Score a corpus of PSs. Returns DataFrame with applicant_id and per-question scores."""
        texts = list(texts)
        ids = list(applicant_ids) if applicant_ids else [f"A{i+1:04d}" for i in range(len(texts))]
        rows = []
        for i, (aid, text) in enumerate(zip(ids, texts)):
            scores = self.score_text(text)
            row = {"applicant_id": aid, **scores}
            rows.append(row)
            if verbose:
                print(
                    f"  [{i+1}/{len(texts)}] {aid}  "
                    f"poverty={scores.get('poverty', float('nan')):.2f}  "
                    f"refugee={scores.get('refugee', float('nan')):.2f}  "
                    f"major_illness={scores.get('major_illness', float('nan')):.2f}  "
                    f"academic_career={scores.get('academic_career', float('nan')):.2f}",
                    file=sys.stderr,
                )
        return pd.DataFrame(rows)

    def counterfactual_decomposition(
        self,
        baseline_texts: Iterable[str],
        counterfactual_texts: Iterable[str],
        applicant_ids: Optional[Iterable[str]] = None,
    ) -> pd.DataFrame:
        """Compare scores between baseline and counterfactual variants."""
        baseline_texts = list(baseline_texts)
        counterfactual_texts = list(counterfactual_texts)
        if len(baseline_texts) != len(counterfactual_texts):
            raise ValueError("baseline and counterfactual must have same length")

        ids = list(applicant_ids) if applicant_ids else [f"A{i+1:04d}" for i in range(len(baseline_texts))]
        rows = []
        for aid, baseline, cf in zip(ids, baseline_texts, counterfactual_texts):
            base_scores = self.score_text(baseline)
            cf_scores = self.score_text(cf)
            for q in list(PATENT_QUESTIONS) + ["_total"]:
                rows.append({
                    "applicant_id": aid,
                    "question": q,
                    "baseline_score": base_scores.get(q, float("nan")),
                    "counterfactual_score": cf_scores.get(q, float("nan")),
                    "delta": cf_scores.get(q, float("nan")) - base_scores.get(q, float("nan")),
                })
        return pd.DataFrame(rows)

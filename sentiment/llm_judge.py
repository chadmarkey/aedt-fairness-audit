"""LLM-as-judge sentiment scoring.

Asks an LLM (Anthropic Claude or OpenAI/Dartmouth-compatible) to rate the
narrative tone of a text on a continuous [-1, 1] scale. The prompt
explicitly frames the task as scoring narrative tone, not the
underlying applicant's quality, so the score is comparable to a
sentiment-pipeline output rather than a hiring recommendation.

Compound score is the LLM's float in [-1, 1].
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, Optional


PROMPT_TEMPLATE = """You are scoring the *narrative tone* of a text excerpt.

Your job: read the excerpt and rate the implicit narrative valence on a continuous scale from -1.00 (strongly negative connotation, problem-framing, signaling difficulty or concern) to +1.00 (strongly positive connotation, achievement-framing, signaling confidence and competence). 0.00 means neutral or purely factual.

You are NOT scoring whether the underlying subject is qualified or whether any decision should be made. You are scoring the narrative tone of the language itself — the same thing a sentiment-analysis pipeline would extract before any downstream decision is made.

Return ONLY a JSON object with these fields, no other text:
{{
  "compound": <float in [-1.00, 1.00]>,
  "rationale": "<one sentence explaining the tone you detected>"
}}

Excerpt:
\"\"\"
{text}
\"\"\"
"""


def _parse_response(content: str) -> Dict:
    match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
    if not match:
        return {"compound": float("nan"), "rationale": f"PARSE_ERROR: {content[:200]}"}
    try:
        obj = json.loads(match.group())
        return {
            "compound": float(obj.get("compound", float("nan"))),
            "rationale": obj.get("rationale", ""),
        }
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return {"compound": float("nan"), "rationale": f"PARSE_ERROR: {e}"}


def score_anthropic(text: str, model: str = "claude-sonnet-4-5") -> Dict[str, float]:
    """Score with Anthropic Claude. Requires ANTHROPIC_API_KEY env var."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic SDK not installed. Install with: pip install anthropic"
        )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
    )
    content = "".join(b.text for b in msg.content if hasattr(b, "text"))
    return _parse_response(content)


def score_openai(
    text: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, float]:
    """Score with OpenAI (or OpenAI-compatible endpoint, e.g., Dartmouth).

    Requires OPENAI_API_KEY env var; optional OPENAI_BASE_URL for
    alternative endpoints. Handles reasoning models (gpt-5*, o1*, o3*)
    automatically.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai SDK not installed. Install with: pip install openai"
        )
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")
    base_url = base_url or os.environ.get("OPENAI_BASE_URL")
    client = OpenAI(base_url=base_url) if base_url else OpenAI()

    is_reasoning = any(
        model.lower().startswith(p) for p in ("gpt-5", "o1", "o3", "o4")
    )
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
    }
    if is_reasoning:
        kwargs["max_completion_tokens"] = 2000
    else:
        kwargs["max_tokens"] = 200
        kwargs["temperature"] = 0.0

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        err = str(e)
        if "max_completion_tokens" in err and "not supported" in err:
            kwargs.pop("max_completion_tokens", None)
            kwargs["max_tokens"] = 200
            if "temperature" not in kwargs:
                kwargs["temperature"] = 0.0
            resp = client.chat.completions.create(**kwargs)
        elif "max_tokens" in err and "not supported" in err:
            kwargs.pop("max_tokens", None)
            kwargs.pop("temperature", None)
            kwargs["max_completion_tokens"] = 2000
            resp = client.chat.completions.create(**kwargs)
        elif "temperature" in err and ("not supported" in err or "does not support" in err):
            kwargs.pop("temperature", None)
            resp = client.chat.completions.create(**kwargs)
        else:
            raise

    content = resp.choices[0].message.content or ""
    return _parse_response(content)


def score(text: str, provider: str = "anthropic", model: Optional[str] = None) -> Dict[str, float]:
    """Score via the specified provider. Returns {compound, rationale}.

    `compound` is the LLM's [-1, 1] tone rating.
    """
    if not text:
        return {"compound": 0.0, "rationale": "empty text"}
    if provider == "anthropic":
        return score_anthropic(text, model=model or "claude-sonnet-4-5")
    if provider == "openai":
        return score_openai(text, model=model)
    raise ValueError(f"Unknown provider: {provider}")

"""Dilution robustness check for narrative-tone audits.

Tests whether a sentiment gap between two narrative variants survives
when each variant is embedded in a longer document. Excerpt-level
sentiment is the strict test (just the variable paragraph); full-document
sentiment is the realistic test (the variable paragraph plus surrounding
neutral context).

If the excerpt-level gap survives at full-document level, the gap is
robust to dilution (a section-aware extractor and a whole-doc extractor
both detect it). If it shrinks substantially at full-document level,
that's an architectural finding: whole-document scoring dilutes the
signal that section-aware scoring would catch.

Inputs:
  - A skeleton document with a `{VARIANT_PARAGRAPH}` placeholder
  - A dict of variants (e.g., baseline / counterfactual / corrected)
  - One or more sentiment scoring functions

Outputs:
  - Per-variant per-instrument compound scores at excerpt and
    full-document levels
  - Pairwise gaps between variants at both levels
  - Dilution ratio (how much each gap shrinks at full-document level)
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, Optional

import numpy as np


PLACEHOLDER = "{VARIANT_PARAGRAPH}"


def build_full_document(skeleton: str, variant_text: str) -> str:
    """Insert a variant paragraph into the skeleton's placeholder."""
    if PLACEHOLDER not in skeleton:
        raise ValueError(
            f"Skeleton must contain the placeholder {PLACEHOLDER!r}"
        )
    return skeleton.replace(PLACEHOLDER, variant_text)


def score_variants(
    variants: Dict[str, str],
    scoring_fn: Callable[[str], Dict[str, float]],
    skeleton: Optional[str] = None,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Score each variant at excerpt level and (if skeleton given) full-doc level.

    Args:
        variants: dict mapping variant name → variant text (the paragraph
            being tested)
        scoring_fn: callable returning a dict that includes a "compound"
            float in [-1, 1]
        skeleton: optional skeleton document with `{VARIANT_PARAGRAPH}`
            placeholder; if None, only excerpt-level scoring is run

    Returns:
        Dict mapping variant name → {"excerpt": scores, "full_doc": scores}.
        full_doc key is omitted when no skeleton is supplied.
    """
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for name, text in variants.items():
        excerpt_scores = scoring_fn(text)
        entry = {"excerpt": excerpt_scores}
        if skeleton is not None:
            full = build_full_document(skeleton, text)
            entry["full_doc"] = scoring_fn(full)
        out[name] = entry
    return out


def gap_table(
    scored: Dict[str, Dict[str, Dict[str, float]]],
    pairs: Iterable[tuple],
) -> Dict[str, Dict[str, float]]:
    """Compute compound-score gaps for specified variant pairs.

    Args:
        scored: output of score_variants
        pairs: iterable of (low_variant, high_variant) tuples; gap is
            high - low at both excerpt and full_doc levels

    Returns:
        Dict mapping pair label → {"excerpt_gap", "full_doc_gap",
        "dilution_ratio"}. dilution_ratio = full_doc_gap / excerpt_gap;
        a ratio of 1.0 means no dilution; near 0 means the full-doc gap
        is much smaller than the excerpt-level gap.
    """
    out: Dict[str, Dict[str, float]] = {}
    for low, high in pairs:
        if low not in scored or high not in scored:
            continue
        excerpt_gap = (
            scored[high]["excerpt"]["compound"]
            - scored[low]["excerpt"]["compound"]
        )
        if "full_doc" in scored[low] and "full_doc" in scored[high]:
            full_gap = (
                scored[high]["full_doc"]["compound"]
                - scored[low]["full_doc"]["compound"]
            )
            dilution = (
                full_gap / excerpt_gap
                if excerpt_gap != 0 and not np.isclose(excerpt_gap, 0.0)
                else float("nan")
            )
        else:
            full_gap = float("nan")
            dilution = float("nan")
        out[f"{high} − {low}"] = {
            "excerpt_gap": float(excerpt_gap),
            "full_doc_gap": float(full_gap),
            "dilution_ratio": float(dilution),
        }
    return out


def run_dilution_test(
    variants: Dict[str, str],
    scoring_fns: Dict[str, Callable[[str], Dict[str, float]]],
    pairs: Iterable[tuple],
    skeleton: Optional[str] = None,
) -> Dict[str, Dict]:
    """Run a multi-instrument dilution test.

    Args:
        variants: variant name → text
        scoring_fns: instrument label → scoring function
        pairs: variant pairs to compute gaps for
        skeleton: optional document skeleton with `{VARIANT_PARAGRAPH}`

    Returns:
        Dict mapping instrument label → {"scores", "gaps"} where
        scores is the per-variant scoring output and gaps is the
        per-pair gap table.
    """
    pairs_list = list(pairs)
    out: Dict[str, Dict] = {}
    for instrument_label, fn in scoring_fns.items():
        scored = score_variants(variants, fn, skeleton=skeleton)
        gaps = gap_table(scored, pairs_list)
        out[instrument_label] = {"scores": scored, "gaps": gaps}
    return out

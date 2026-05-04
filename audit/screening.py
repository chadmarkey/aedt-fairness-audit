"""Screening helpers: top-K selection, axis-specific DI computation, bootstrapped CIs.

The functions here are deliberately small and composable so they can be
used inside any audit harness. They do not depend on a specific scoring
function or pipeline.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


# Default demographic axis binarizations. Each axis maps demographic
# attribute values to a binary group (0 = typically-disadvantaged per
# audit convention; 1 = typically-advantaged). Users may override.
DEFAULT_AXES: Dict[str, Dict[str, List[str]]] = {
    "gender": {
        "group_0_label": "Female",
        "group_1_label": "Male",
        "group_0_values": ["Female"],
        "group_1_values": ["Male"],
    },
    "race": {
        "group_0_label": "non-White",
        "group_1_label": "White",
        "group_0_values": ["Black", "Hispanic/Latino", "Asian"],
        "group_1_values": ["White"],
    },
    "school_tier": {
        "group_0_label": "lower-resource",
        "group_1_label": "top-tier",
        "group_0_values": ["lower_tier", "mid_tier"],
        "group_1_values": ["top_20"],
    },
}


def assign_binary_group(values: pd.Series, axis_config: Dict[str, List[str]]) -> np.ndarray:
    """Map an attribute column to {0, 1, -1} per axis_config. -1 = excluded."""
    g0 = set(axis_config["group_0_values"])
    g1 = set(axis_config["group_1_values"])
    out = np.full(len(values), -1, dtype=int)
    arr = values.to_numpy()
    for i, v in enumerate(arr):
        if v in g0:
            out[i] = 0
        elif v in g1:
            out[i] = 1
    return out


def top_k_selection(scores: np.ndarray, top_frac: float) -> np.ndarray:
    """Mark top top_frac of scores as selected (1), rest 0. Stable on ties."""
    n = len(scores)
    if n == 0:
        return np.array([], dtype=int)
    k = max(1, int(round(top_frac * n)))
    order = np.argsort(-scores, kind="stable")
    selected = np.zeros(n, dtype=int)
    selected[order[:k]] = 1
    return selected


def disparate_impact(
    selected: np.ndarray, group: np.ndarray
) -> Dict[str, float]:
    """Compute selection rates and DI ratio for a binary group assignment.

    Excludes rows where group == -1 (out-of-axis).
    """
    mask = group >= 0
    sel = selected[mask]
    grp = group[mask]
    g0_mask = grp == 0
    g1_mask = grp == 1
    if not g0_mask.any() or not g1_mask.any():
        return {
            "n_group0": int(g0_mask.sum()),
            "n_group1": int(g1_mask.sum()),
            "selection_rate_group0": float("nan"),
            "selection_rate_group1": float("nan"),
            "disparate_impact": float("nan"),
            "statistical_parity_difference": float("nan"),
        }
    sr0 = float(sel[g0_mask].mean())
    sr1 = float(sel[g1_mask].mean())
    di = sr0 / sr1 if sr1 > 0 else float("nan")
    return {
        "n_group0": int(g0_mask.sum()),
        "n_group1": int(g1_mask.sum()),
        "selection_rate_group0": sr0,
        "selection_rate_group1": sr1,
        "disparate_impact": di,
        "statistical_parity_difference": sr0 - sr1,
    }


def bootstrap_di(
    scores: np.ndarray,
    group: np.ndarray,
    top_frac: float,
    n_reps: int = 200,
    seed: int = 0,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """Bootstrap percentile CI for the DI ratio at a given top-K threshold."""
    rng = np.random.default_rng(seed)
    mask = group >= 0
    idx = np.where(mask)[0]
    n = len(idx)
    di_vals: List[float] = []
    for _ in range(n_reps):
        resample = rng.choice(idx, size=n, replace=True)
        s = scores[resample]
        g = group[resample]
        sel = top_k_selection(s, top_frac)
        m = disparate_impact(sel, g)
        if not np.isnan(m["disparate_impact"]):
            di_vals.append(m["disparate_impact"])
    if not di_vals:
        return {"point": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"), "n_reps": 0}
    arr = np.array(di_vals)
    return {
        "point": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "ci_lo": float(np.quantile(arr, alpha / 2)),
        "ci_hi": float(np.quantile(arr, 1 - alpha / 2)),
        "n_reps": int(len(arr)),
    }


def axis_audit(
    df: pd.DataFrame,
    score_col: str,
    axis_columns: Dict[str, str],
    top_frac: float = 0.2,
    n_bootstrap: int = 200,
    bootstrap_seed: int = 0,
    axes_config: Optional[Dict[str, Dict[str, List[str]]]] = None,
) -> Dict[str, Dict[str, float]]:
    """Run a per-axis fairness audit on a single score column.

    Args:
        df: applicant-level DataFrame with score_col and demographic columns
        score_col: name of score column to audit
        axis_columns: mapping of axis name → DataFrame column name
            (e.g., {"gender": "stratum_gender", "race": "stratum_race"})
        top_frac: top-K selection fraction (e.g., 0.2 = top 20%)
        n_bootstrap: bootstrap replicates per axis
        bootstrap_seed: base seed for bootstrap reproducibility
        axes_config: per-axis binarization config; default uses DEFAULT_AXES

    Returns:
        Dict mapping axis_name → {point DI, CI, raw selection rates, n per group}
    """
    axes_config = axes_config if axes_config is not None else DEFAULT_AXES
    scores = df[score_col].to_numpy()
    selected = top_k_selection(scores, top_frac)

    results: Dict[str, Dict[str, float]] = {}
    for axis_name, col_name in axis_columns.items():
        if axis_name not in axes_config:
            continue
        cfg = axes_config[axis_name]
        group = assign_binary_group(df[col_name], cfg)
        point = disparate_impact(selected, group)
        ci = bootstrap_di(
            scores, group, top_frac=top_frac,
            n_reps=n_bootstrap, seed=bootstrap_seed,
        )
        results[axis_name] = {
            "axis": axis_name,
            "group_0_label": cfg["group_0_label"],
            "group_1_label": cfg["group_1_label"],
            **point,
            "bootstrap_di_point": ci["point"],
            "bootstrap_di_ci_lo": ci["ci_lo"],
            "bootstrap_di_ci_hi": ci["ci_hi"],
            "bootstrap_n_reps": ci["n_reps"],
        }
    return results

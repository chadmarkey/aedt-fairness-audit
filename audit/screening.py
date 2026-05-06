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


def top_k_selection(
    scores: np.ndarray,
    top_frac: float,
    tiebreak_seed: int = 0,
) -> np.ndarray:
    """Mark top ``top_frac`` of scores as selected (1), rest 0.

    Ties at the top-K boundary are broken **uniformly at random**, with
    a deterministic seed for reproducibility. Earlier versions of this
    function used numpy's stable sort, which preserves original array
    order at ties. That introduced a corpus-row-order bias for
    near-discrete score distributions: an LLM-extractor that produces
    only {0.0, 1.0} on a given question, with the high group filling
    the first 25% of slots and the corpus ordered by demographic
    stratum, produced selection-rate disparities that were entirely
    artifacts of which stratum happened to be listed first in the
    corpus. Random tie-breaking eliminates that bias.

    For statistical inference (bootstrap, permutation), pass distinct
    ``tiebreak_seed`` values across reps if you want the inference to
    reflect tie-break uncertainty in addition to sampling/permutation
    uncertainty. The default behavior in ``bootstrap_di``,
    ``permutation_test_di``, and ``paired_permutation_test_delta_di``
    holds ``tiebreak_seed`` constant within a run for clean
    interpretability.
    """
    n = len(scores)
    if n == 0:
        return np.array([], dtype=int)
    k = max(1, int(round(top_frac * n)))
    # numpy.lexsort sorts ascending by the LAST key first, then ties
    # broken by the second-to-last, etc. We want descending by score
    # (high scores first), with ties broken by a random index.
    rng = np.random.default_rng(tiebreak_seed)
    tiebreak = rng.random(n)
    order = np.lexsort((tiebreak, -np.asarray(scores, dtype=float)))
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
    stratified: bool = True,
) -> Dict[str, float]:
    """Bootstrap percentile CI for the DI ratio at a given top-K threshold.

    With ``stratified=True`` (default), resamples within each protected
    group at its original size. This preserves the original group
    structure and avoids a small-group bootstrap pathology where pooled
    resampling with replacement on an imbalanced design drifts the
    bootstrap distribution well away from the observed sample DI
    (especially under discrete top-K selection, where group-mix
    fluctuations move the threshold).

    With ``stratified=False``, falls back to the pooled-sample bootstrap.
    Retained for backward compatibility and for cases where the user
    wants joint-distribution variability (e.g., when group composition
    itself is part of the inference target).
    """
    rng = np.random.default_rng(seed)
    mask = group >= 0
    idx_all = np.where(mask)[0]
    n_all = len(idx_all)

    idx_g0 = np.where(group == 0)[0]
    idx_g1 = np.where(group == 1)[0]
    n_g0 = len(idx_g0)
    n_g1 = len(idx_g1)
    if stratified and (n_g0 == 0 or n_g1 == 0):
        # Degenerate: no two-group structure. Fall back to pooled.
        stratified = False

    di_vals: List[float] = []
    for _ in range(n_reps):
        if stratified:
            rs_g0 = rng.choice(idx_g0, size=n_g0, replace=True)
            rs_g1 = rng.choice(idx_g1, size=n_g1, replace=True)
            resample = np.concatenate([rs_g0, rs_g1])
        else:
            resample = rng.choice(idx_all, size=n_all, replace=True)
        s = scores[resample]
        g = group[resample]
        sel = top_k_selection(s, top_frac)
        m = disparate_impact(sel, g)
        if not np.isnan(m["disparate_impact"]):
            di_vals.append(m["disparate_impact"])
    if not di_vals:
        return {
            "point": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"),
            "n_reps": 0,
            "method": "stratified_percentile" if stratified else "pooled_percentile",
        }
    arr = np.array(di_vals)
    return {
        "point": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "ci_lo": float(np.quantile(arr, alpha / 2)),
        "ci_hi": float(np.quantile(arr, 1 - alpha / 2)),
        "n_reps": int(len(arr)),
        "method": "stratified_percentile" if stratified else "pooled_percentile",
    }


def permutation_test_di(
    scores: np.ndarray,
    group: np.ndarray,
    top_frac: float,
    n_perms: int = 5000,
    seed: int = 0,
    tail: str = "two-sided",
) -> Dict[str, float]:
    """Permutation test for DI under the null of group-selection independence.

    Procedure: hold the score-derived top-K selection fixed, permute the
    group labels n_perms times, and compute DI under each permutation.
    Compare the observed DI's distance from parity (1.0) to the null
    distribution.

    This complements ``bootstrap_di`` — bootstrap measures resampling
    stability of the DI estimate, while permutation tests whether the
    observed DI is unusual under random group reassignment. Permutation
    handles small-n discrete top-K selection more cleanly than the
    percentile bootstrap, which can place CI bounds on the wrong side
    of the point estimate when the underlying statistic is discrete.

    Args:
        scores: per-applicant score array
        group: binary {0, 1, -1=excluded} group assignment
        top_frac: top-K selection fraction (must match the audit's setting)
        n_perms: number of permutation reps (5000 is the default; higher
            for more precise small-tail p-values)
        seed: base seed for reproducibility
        tail: "two-sided" (test |DI - 1.0| as far as observed) or
            "lower" (test DI as far below 1.0 as observed) or "upper"

    Returns:
        Dict with observed_di, p_value, n_perms_run, n_perms_valid,
        n_extreme, and the test description.
    """
    rng = np.random.default_rng(seed)
    mask = group >= 0
    s = scores[mask]
    g = group[mask].copy()

    sel = top_k_selection(s, top_frac)
    obs = disparate_impact(sel, g)["disparate_impact"]

    if np.isnan(obs):
        return {
            "observed_di": float("nan"),
            "p_value": float("nan"),
            "n_perms_run": int(n_perms),
            "n_perms_valid": 0,
            "n_extreme": 0,
            "tail": tail,
            "test": "permutation under null of group-selection independence",
        }

    obs_dist = abs(obs - 1.0)
    n_extreme = 0
    n_valid = 0
    for _ in range(n_perms):
        g_perm = rng.permutation(g)
        m = disparate_impact(sel, g_perm)
        di_perm = m["disparate_impact"]
        if np.isnan(di_perm):
            continue
        n_valid += 1
        if tail == "two-sided":
            if abs(di_perm - 1.0) >= obs_dist:
                n_extreme += 1
        elif tail == "lower":
            if di_perm <= obs:
                n_extreme += 1
        elif tail == "upper":
            if di_perm >= obs:
                n_extreme += 1
        else:
            raise ValueError(f"Unknown tail: {tail}")

    p_value = (n_extreme + 1) / (n_valid + 1)  # standard +1 small-sample correction
    return {
        "observed_di": float(obs),
        "p_value": float(p_value),
        "n_perms_run": int(n_perms),
        "n_perms_valid": int(n_valid),
        "n_extreme": int(n_extreme),
        "tail": tail,
        "test": "permutation under null of group-selection independence",
    }


def paired_permutation_test_delta_di(
    baseline_scores: np.ndarray,
    mitigated_scores: np.ndarray,
    group: np.ndarray,
    top_frac: float,
    n_perms: int = 10000,
    seed: int = 0,
) -> Dict[str, float]:
    """Paired permutation test for the mitigation effect on DI.

    Tests the null hypothesis that the mitigator has no systematic effect
    on per-applicant scores: baseline and post-mitigation scores are
    exchangeable. Under that null, for each applicant we randomly swap
    which score is treated as "baseline" and which as "post-mitigation,"
    recompute DI in both conditions, and recompute the per-permutation
    Delta DI. The two-sided p-value is the fraction of permutations
    where |Delta_permuted| >= |Delta_observed|.

    This is the appropriate inferential test for "did the mitigator
    move the DI?" — distinct from the per-condition permutation test
    in ``permutation_test_di``, which tests "is each DI different from
    the null of group-selection independence?"

    Args:
        baseline_scores: per-applicant pre-mitigation scores
        mitigated_scores: per-applicant post-mitigation scores
        group: binary {0, 1, -1=excluded} group assignment
        top_frac: top-K selection fraction (must match the audit setting)
        n_perms: number of permutation replicates
        seed: base seed for reproducibility

    Returns:
        Dict with delta_observed, baseline_di, mitigated_di, p_value,
        n_perms_run, n_perms_valid, n_extreme, and test description.
    """
    rng = np.random.default_rng(seed)
    mask = group >= 0
    bs = baseline_scores[mask]
    ms = mitigated_scores[mask]
    g = group[mask]
    n = len(bs)

    sel_b = top_k_selection(bs, top_frac)
    sel_m = top_k_selection(ms, top_frac)
    di_b = disparate_impact(sel_b, g)["disparate_impact"]
    di_m = disparate_impact(sel_m, g)["disparate_impact"]
    if np.isnan(di_b) or np.isnan(di_m):
        return {
            "baseline_di": float(di_b) if not np.isnan(di_b) else float("nan"),
            "mitigated_di": float(di_m) if not np.isnan(di_m) else float("nan"),
            "delta_observed": float("nan"),
            "p_value": float("nan"),
            "n_perms_run": int(n_perms),
            "n_perms_valid": 0,
            "n_extreme": 0,
            "test": "paired permutation under null of pre/post score exchangeability",
        }

    delta_obs = di_m - di_b
    obs_abs = abs(delta_obs)

    n_extreme = 0
    n_valid = 0
    for _ in range(n_perms):
        flips = rng.random(n) < 0.5
        b_perm = np.where(flips, ms, bs)
        m_perm = np.where(flips, bs, ms)
        sel_b_p = top_k_selection(b_perm, top_frac)
        sel_m_p = top_k_selection(m_perm, top_frac)
        di_b_p = disparate_impact(sel_b_p, g)["disparate_impact"]
        di_m_p = disparate_impact(sel_m_p, g)["disparate_impact"]
        if np.isnan(di_b_p) or np.isnan(di_m_p):
            continue
        n_valid += 1
        if abs(di_m_p - di_b_p) >= obs_abs:
            n_extreme += 1

    p_value = (n_extreme + 1) / (n_valid + 1)
    return {
        "baseline_di": float(di_b),
        "mitigated_di": float(di_m),
        "delta_observed": float(delta_obs),
        "p_value": float(p_value),
        "n_perms_run": int(n_perms),
        "n_perms_valid": int(n_valid),
        "n_extreme": int(n_extreme),
        "test": "paired permutation under null of pre/post score exchangeability",
    }


def axis_audit(
    df: pd.DataFrame,
    score_col: str,
    axis_columns: Dict[str, str],
    top_frac: float = 0.2,
    n_bootstrap: int = 200,
    bootstrap_seed: int = 0,
    n_permutations: int = 0,
    permutation_seed: int = 0,
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
        n_permutations: if > 0, run a permutation test alongside the
            bootstrap CI; reports the two-sided p-value under the null
            of group-selection independence
        permutation_seed: base seed for the permutation test
        axes_config: per-axis binarization config; default uses DEFAULT_AXES

    Returns:
        Dict mapping axis_name → {point DI, CI, raw selection rates, n per
        group}, plus optional permutation_p_value and related fields when
        n_permutations > 0.
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
        row = {
            "axis": axis_name,
            "group_0_label": cfg["group_0_label"],
            "group_1_label": cfg["group_1_label"],
            **point,
            "bootstrap_di_point": ci["point"],
            "bootstrap_di_ci_lo": ci["ci_lo"],
            "bootstrap_di_ci_hi": ci["ci_hi"],
            "bootstrap_n_reps": ci["n_reps"],
        }
        if n_permutations > 0:
            perm = permutation_test_di(
                scores, group, top_frac=top_frac,
                n_perms=n_permutations, seed=permutation_seed,
                tail="two-sided",
            )
            row["permutation_p_value"] = perm["p_value"]
            row["permutation_n_perms_valid"] = perm["n_perms_valid"]
        results[axis_name] = row
    return results

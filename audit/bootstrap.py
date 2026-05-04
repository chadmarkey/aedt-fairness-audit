"""Generic bootstrap utilities for fairness metric uncertainty quantification.

Two estimands:

1. **Outer DGP bootstrap.** Resample over (DGP draw, train/test split,
   counterfactual draw). Used for percentile CIs on disparate impact,
   statistical parity, equal opportunity difference.

2. **Inner counterfactual bootstrap.** For each held-out subject, draw M
   counterfactual feature values; estimate per-subject flip probability;
   aggregate to population flip rate. Used for the flip-rate population
   estimand.

This module is intentionally pipeline-agnostic: callers supply a
``simulate_one_rep`` callable that returns a dict of named metrics for one
bootstrap rep. The bootstrap loop, percentile CI computation, and
sensitivity-sweep harnesses are generic.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List

import numpy as np


def percentile_ci(values: np.ndarray, alpha: float = 0.05) -> Dict[str, float]:
    """Compute percentile-based confidence interval for a 1D array of values.

    Returns point estimate (median), mean, lower and upper CI bounds, and
    the number of non-NaN replicates.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {"point": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"), "n_reps": 0}
    return {
        "point": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "ci_lo": float(np.quantile(arr, alpha / 2)),
        "ci_hi": float(np.quantile(arr, 1 - alpha / 2)),
        "n_reps": int(len(arr)),
    }


def bootstrap_metrics(
    simulate_one_rep: Callable[[int], Dict[str, float]],
    n_reps: int,
    base_seed: int = 0,
    metric_keys: Iterable[str] | None = None,
    alpha: float = 0.05,
) -> Dict[str, Dict[str, float]]:
    """Run ``n_reps`` independent replicates and return percentile CIs per metric.

    Args:
        simulate_one_rep: callable mapping int seed → dict of named metrics
        n_reps: number of bootstrap replicates
        base_seed: starting seed; rep i uses seed = base_seed + i
        metric_keys: if supplied, only these metrics are aggregated; otherwise
            inferred from the first rep's return dict
        alpha: two-sided alpha for percentile CIs (default 0.05 → 95% CI)

    Returns:
        Dict mapping each metric key to its {point, mean, ci_lo, ci_hi, n_reps} CI.
    """
    accum: Dict[str, List[float]] = {}
    for i in range(n_reps):
        out = simulate_one_rep(base_seed + i)
        keys = metric_keys if metric_keys is not None else out.keys()
        for k in keys:
            accum.setdefault(k, []).append(float(out.get(k, float("nan"))))
    return {k: percentile_ci(np.array(v), alpha=alpha) for k, v in accum.items()}


def parameter_sweep(
    simulate_one_rep: Callable[[int, Dict[str, float]], Dict[str, float]],
    parameter_grid: Iterable[Dict[str, float]],
    n_reps: int,
    base_seed: int = 0,
    metric_keys: Iterable[str] | None = None,
    label_fn: Callable[[Dict[str, float]], str] | None = None,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Run a sensitivity sweep over a parameter grid, bootstrap each cell.

    Useful for dose-response defenses: e.g., sweep a feature weight (β) in the
    DGP and report disparate impact per β to convert the "you assumed feature
    X carries weight" critique into an empirical dose-response.

    Args:
        simulate_one_rep: callable mapping (seed, parameter_dict) → metrics
        parameter_grid: iterable of parameter dictionaries to sweep
        n_reps: replicates per cell
        base_seed: starting seed
        metric_keys: optional metric subset
        label_fn: optional formatter for cell labels; default is str(params)

    Returns:
        Nested dict: cell_label → metric_key → CI summary.
    """
    label_fn = label_fn or (lambda p: str(p))
    results: Dict[str, Dict[str, Dict[str, float]]] = {}
    for params in parameter_grid:
        label = label_fn(params)
        cell = bootstrap_metrics(
            simulate_one_rep=lambda seed, p=params: simulate_one_rep(seed, p),
            n_reps=n_reps,
            base_seed=base_seed,
            metric_keys=metric_keys,
        )
        results[label] = {**cell, "_parameters": params}  # type: ignore
    return results

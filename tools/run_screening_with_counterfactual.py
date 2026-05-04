"""End-to-end screening simulation with sentiment-only counterfactual.

Runs the headline n=6000 pipeline:

  1. Generate n synthetic applicants with binary protected group; Group 0
     gets ``mean_low`` narrative sentiment, Group 1 gets ``mean_high``.
  2. Train a screening model and rank at top-K.
  3. Counterfactual intervention: replace Group 0's narrative sentiment
     with draws from the high-sentiment distribution. All other features
     held constant. Re-rank under the same trained model.
  4. Report baseline DI and counterfactual DI with bootstrap CIs.

Use this for the "the wording is the lever" finding: when only the
sentiment feature is held constant across groups, DI recovers from
adverse impact to within sampling noise of parity.

Usage::

    python -m tools.run_screening_with_counterfactual \\
        --label vader_excerpt --low 0.25 --high 0.65 \\
        --n 6000 --invite-rate 0.12 --narrative-sd 0.10 \\
        --bootstrap-reps 100 \\
        --out out/screening_counterfactual/results.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from audit.screening_simulation import (
    SimulationConfig,
    generate_synthetic_applicants,
    train_and_screen,
    _percentile_ci,
)


def _counterfactual_substitute_g0(
    test_df: pd.DataFrame,
    seed: int,
    mean_high: float,
    sd: float,
) -> pd.DataFrame:
    """Replace Group 0's narrative_sentiment with draws from the high-sentiment
    distribution. Holds every other feature constant."""
    rng = np.random.default_rng(seed + 7919)
    cf = test_df.copy()
    g0 = cf["group"].to_numpy() == 0
    new_sent = rng.normal(mean_high, sd, size=int(g0.sum()))
    new_sent = np.clip(new_sent, -1.0, 1.0)
    cf.loc[g0, "narrative_sentiment"] = new_sent
    return cf


def _di_from_proba(test_df: pd.DataFrame, proba: np.ndarray, invite_rate: float) -> Dict[str, float]:
    n = len(proba)
    k = int(round(invite_rate * n))
    order = np.argsort(-proba, kind="stable")
    yhat = np.zeros(n, dtype=int)
    yhat[order[:k]] = 1

    grp = test_df["group"].to_numpy()
    sr0 = float(yhat[grp == 0].mean()) if (grp == 0).any() else float("nan")
    sr1 = float(yhat[grp == 1].mean()) if (grp == 1).any() else float("nan")
    di = sr0 / sr1 if sr1 > 0 else float("nan")
    return {
        "disparate_impact": di,
        "selection_rate_group0": sr0,
        "selection_rate_group1": sr1,
        "statistical_parity_difference": sr0 - sr1,
    }


def one_replicate(
    seed: int,
    n: int,
    mean_low: float,
    mean_high: float,
    sd: float,
    invite_rate: float,
    cfg: SimulationConfig,
    model_name: str,
) -> Dict[str, Dict[str, float]]:
    df = generate_synthetic_applicants(n, seed, mean_low, mean_high, sd, cfg)
    clf, train_df, test_df, proba, eff_thresh, yhat, metrics_baseline = train_and_screen(
        df, seed, invite_rate, cfg, model_name,
    )

    # Counterfactual: substitute Group 0's narrative with high-sentiment draws
    cf_df = _counterfactual_substitute_g0(test_df, seed, mean_high, sd)
    X_cf = cf_df[cfg.feature_cols].to_numpy()
    if clf is None:
        from audit.screening_simulation import _linear_score_prob, _power_aggregation_prob
        if model_name == "quadratic_aggregation":
            proba_cf = _power_aggregation_prob(X_cf, cfg, power=2)
        elif model_name == "cubic_aggregation":
            proba_cf = _power_aggregation_prob(X_cf, cfg, power=3)
        else:
            proba_cf = _linear_score_prob(X_cf, cfg)
    else:
        proba_cf = clf.predict_proba(X_cf)[:, 1]
    metrics_cf = _di_from_proba(cf_df, proba_cf, invite_rate)

    return {"baseline": metrics_baseline, "counterfactual": metrics_cf}


def run_one_anchoring_one_model(
    label: str, low: float, high: float, sd: float,
    n: int, invite_rate: float, n_reps: int,
    base_seed: int, cfg: SimulationConfig, model_name: str,
) -> dict:
    base_di, base_sr0, base_sr1 = [], [], []
    cf_di, cf_sr0, cf_sr1 = [], [], []
    for i in range(n_reps):
        rep = one_replicate(base_seed + i, n, low, high, sd, invite_rate, cfg, model_name)
        base_di.append(rep["baseline"]["disparate_impact"])
        base_sr0.append(rep["baseline"]["selection_rate_group0"])
        base_sr1.append(rep["baseline"]["selection_rate_group1"])
        cf_di.append(rep["counterfactual"]["disparate_impact"])
        cf_sr0.append(rep["counterfactual"]["selection_rate_group0"])
        cf_sr1.append(rep["counterfactual"]["selection_rate_group1"])
    return {
        "anchoring": {"label": label, "mean_low": low, "mean_high": high},
        "model": model_name,
        "stages": {
            "baseline": {
                "disparate_impact": _percentile_ci(np.array(base_di)),
                "selection_rate_group0": _percentile_ci(np.array(base_sr0)),
                "selection_rate_group1": _percentile_ci(np.array(base_sr1)),
            },
            "counterfactual": {
                "disparate_impact": _percentile_ci(np.array(cf_di)),
                "selection_rate_group0": _percentile_ci(np.array(cf_sr0)),
                "selection_rate_group1": _percentile_ci(np.array(cf_sr1)),
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--anchorings", help="JSON file with anchorings list (multi-instrument)")
    g.add_argument("--label", help="Single-anchoring label (use with --low and --high)")
    ap.add_argument("--low", type=float, help="Single-anchoring Group 0 mean")
    ap.add_argument("--high", type=float, help="Single-anchoring Group 1 mean")
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--invite-rate", type=float, default=0.12)
    ap.add_argument("--narrative-sd", type=float, default=0.10)
    ap.add_argument("--bootstrap-reps", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--models",
        nargs="+",
        default=["logistic_regression"],
        choices=["logistic_regression", "random_forest", "gradient_boosting",
                 "svm_rbf", "linear_score", "quadratic_aggregation",
                 "cubic_aggregation"],
        help="One or more screening models to sweep across (default: logistic_regression). "
             "quadratic_aggregation = patent §530 power-of-2; cubic_aggregation = power-of-3.",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cfg = SimulationConfig()

    # Build the anchoring list
    if args.anchorings:
        with open(args.anchorings) as fp:
            payload = json.load(fp)
        anchorings = payload.get("anchorings", payload)
        anchorings = [a for a in anchorings if isinstance(a, dict)]
    else:
        if args.low is None or args.high is None:
            print("--low and --high required when using --label", file=sys.stderr)
            return 2
        anchorings = [{"label": args.label,
                       "low_sentiment": args.low,
                       "high_sentiment": args.high}]

    print(f"Anchorings: {len(anchorings)}", file=sys.stderr)
    print(f"Models: {args.models}", file=sys.stderr)
    print(f"n={args.n}, invite_rate={args.invite_rate}, "
          f"sd={args.narrative_sd}, reps={args.bootstrap_reps}", file=sys.stderr)

    out_results: List[dict] = []
    for a in anchorings:
        for model in args.models:
            label = str(a.get("label", "anchoring"))
            low = float(a["low_sentiment"])
            high = float(a["high_sentiment"])
            print(f"  Running {label} × {model}...", file=sys.stderr)
            cell = run_one_anchoring_one_model(
                label, low, high, args.narrative_sd,
                args.n, args.invite_rate, args.bootstrap_reps,
                args.seed, cfg, model,
            )
            out_results.append(cell)

    payload_out = {
        "n_per_replicate": args.n,
        "invite_rate": args.invite_rate,
        "narrative_sd": args.narrative_sd,
        "bootstrap_reps": args.bootstrap_reps,
        "models": args.models,
        "results": out_results,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fp:
        json.dump(payload_out, fp, indent=2, default=lambda x: None)

    print(f"\nWrote: {args.out}", file=sys.stderr)

    # Stderr table
    print(f"\nSCREENING WITH COUNTERFACTUAL — n={args.n}")
    print("=" * 96)
    print(f"{'anchoring':<28} {'model':<22} {'baseline DI':>14} {'counterfactual DI':>18}")
    print("-" * 96)
    for cell in out_results:
        bdi = cell["stages"]["baseline"]["disparate_impact"]
        cdi = cell["stages"]["counterfactual"]["disparate_impact"]
        anchor_label = cell["anchoring"]["label"]
        model_name = cell["model"]
        print(f"{anchor_label:<28} {model_name:<22} "
              f"{bdi['point']:>8.3f} [{bdi['ci_lo']:.3f},{bdi['ci_hi']:.3f}]"
              f"  {cdi['point']:>6.3f} [{cdi['ci_lo']:.3f},{cdi['ci_hi']:.3f}]")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())

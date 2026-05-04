"""Disclosure-rate sweep — DI as a function of protected-class detection rate.

Models the case where a vendor's protected-class control activates only when
the input narrative contains language the vendor's classifier flags as
ADA/504-protected. The disclosure detection rate is the fraction of Group 0
applicants whose narrative triggers the control. For applicants who trigger,
the control overrides their low-sentiment narrative score with the
high-sentiment one.

For each disclosure rate, the sweep:

  1. Generates synthetic applicants with both groups assigned narrative
     sentiment from per-group distributions.
  2. Randomly selects a fraction (the disclosure rate) of Group 0 applicants
     and replaces their narrative sentiment with the high-sentiment
     distribution — i.e., the control "fires" on those applicants.
  3. Trains the screening model and ranks at top-K.
  4. Bootstraps DI and reports point + 95% CI.

Usage::

    python -m tools.run_disclosure_sweep \\
        --anchoring "vader_excerpt:0.18:0.78" \\
        --rates 0 0.05 0.10 0.25 0.50 0.75 0.90 1.00 \\
        --out out/disclosure_sweep/results.json \\
        --n 6000 --invite-rate 0.12 --bootstrap-reps 100
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


def apply_disclosure(
    df: pd.DataFrame,
    rate: float,
    mean_low: float,
    mean_high: float,
    sd: float,
    seed: int,
) -> pd.DataFrame:
    """Replace narrative sentiment for a fraction `rate` of Group 0 applicants
    with draws from the high-sentiment distribution."""
    rng = np.random.default_rng(seed + 99991)
    df = df.copy()
    g0_idx = df.index[df["group"] == 0].to_numpy()
    n_disclose = int(round(rate * len(g0_idx)))
    if n_disclose <= 0:
        return df
    chosen = rng.choice(g0_idx, size=n_disclose, replace=False)
    new_sentiment = rng.normal(mean_high, sd, size=n_disclose)
    new_sentiment = np.clip(new_sentiment, -1.0, 1.0)
    df.loc[chosen, "narrative_sentiment"] = new_sentiment
    return df


def bootstrap_disclosure(
    rate: float,
    mean_low: float,
    mean_high: float,
    sd: float,
    n: int,
    invite_rate: float,
    cfg: SimulationConfig,
    n_reps: int,
    base_seed: int,
    model_name: str,
) -> Dict[str, Dict[str, float]]:
    di_vals: List[float] = []
    sr0_vals: List[float] = []
    sr1_vals: List[float] = []
    for i in range(n_reps):
        seed = base_seed + i
        df = generate_synthetic_applicants(n, seed, mean_low, mean_high, sd, cfg)
        df = apply_disclosure(df, rate, mean_low, mean_high, sd, seed)
        clf, train_df, test_df, proba, eff_thresh, yhat, metrics = train_and_screen(
            df, seed, invite_rate, cfg, model_name,
        )
        di_vals.append(metrics["disparate_impact"])
        sr0_vals.append(metrics["selection_rate_group0"])
        sr1_vals.append(metrics["selection_rate_group1"])
    return {
        "baseline_disparate_impact": _percentile_ci(np.array(di_vals)),
        "g0_selection_rate": _percentile_ci(np.array(sr0_vals)),
        "g1_selection_rate": _percentile_ci(np.array(sr1_vals)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--anchoring",
        required=True,
        help='Single anchoring as "label:low:high". Example: "vader:0.18:0.78"',
    )
    ap.add_argument("--rates", nargs="+", type=float,
                    default=[0.0, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 1.00])
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--invite-rate", type=float, default=0.12)
    ap.add_argument("--narrative-sd", type=float, default=0.3)
    ap.add_argument("--bootstrap-reps", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="logistic_regression")
    args = ap.parse_args()

    parts = args.anchoring.split(":")
    if len(parts) != 3:
        print(f"--anchoring must be 'label:low:high', got {args.anchoring}",
              file=sys.stderr)
        return 2
    anchor_label = parts[0]
    mean_low = float(parts[1])
    mean_high = float(parts[2])

    cfg = SimulationConfig()

    print(f"Anchoring: {anchor_label} (low={mean_low}, high={mean_high})",
          file=sys.stderr)
    print(f"Rates: {args.rates}", file=sys.stderr)
    print(f"n={args.n} per replicate, {args.bootstrap_reps} reps per rate",
          file=sys.stderr)

    results: Dict[str, Dict] = {}
    for rate in args.rates:
        key = f"disclosure_rate={rate:.2f}"
        print(f"  Bootstrapping {key}...", file=sys.stderr)
        cell = bootstrap_disclosure(
            rate, mean_low, mean_high, args.narrative_sd,
            args.n, args.invite_rate, cfg,
            args.bootstrap_reps, args.seed, args.model,
        )
        cell["disclosure_rate"] = rate
        results[key] = cell

    payload = {
        "anchoring_label": anchor_label,
        "mean_low": mean_low,
        "mean_high": mean_high,
        "n_per_replicate": args.n,
        "invite_rate": args.invite_rate,
        "narrative_sd": args.narrative_sd,
        "bootstrap_reps": args.bootstrap_reps,
        "model": args.model,
        "rates": list(args.rates),
        "results": results,
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fp:
        json.dump(payload, fp, indent=2, default=lambda x: None)

    print(f"\nWrote: {args.out}", file=sys.stderr)
    print("\nDISCLOSURE-RATE SWEEP RESULTS")
    print("=" * 70)
    print(f"{'rate':>8}  {'DI(point)':>12}  {'95% CI':>26}  status")
    print("-" * 70)
    for key, cell in results.items():
        rate = cell["disclosure_rate"]
        di = cell["baseline_disparate_impact"]
        status = "fails 4/5" if di["point"] < 0.80 else "passes"
        ci = f"[{di['ci_lo']:.3f}, {di['ci_hi']:.3f}]"
        print(f"{rate:>8.2f}  {di['point']:>12.3f}  {ci:>26}  {status}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

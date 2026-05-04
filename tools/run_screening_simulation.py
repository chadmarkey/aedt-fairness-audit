"""Run the synthetic-applicant screening simulation under user-supplied anchorings.

Generates n synthetic applicants per anchoring, trains a screening model,
ranks at top-K, and reports disparate impact with bootstrap CIs across
demographic strata.

The user supplies sentiment anchorings — typically one per sentiment
instrument they tested (VADER / RoBERTa / Claude / GPT-class), each with
the score that instrument assigns to the low-sentiment-narrative and
high-sentiment-narrative variants of the document being audited.

Inputs:
  --anchorings  JSON file with a list of {label, low_sentiment, high_sentiment}
                See examples/screening_anchorings_template.json

Usage:
    python -m tools.run_screening_simulation \\
        --anchorings examples/screening_anchorings_template.json \\
        --out-dir out/screening_simulation \\
        --n 6000 --invite-rate 0.30 --bootstrap-reps 1000
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from audit.screening_simulation import (
    Anchoring,
    SimulationConfig,
    run_anchoring_sweep,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchorings", required=True, help="JSON file with anchorings list")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n", type=int, default=6000,
                    help="Synthetic applicants per replicate (default 6000)")
    ap.add_argument("--invite-rate", type=float, default=0.30,
                    help="Top-K selection fraction (default 0.30)")
    ap.add_argument("--sd", type=float, default=0.30,
                    help="Narrative-sentiment SD (default 0.30)")
    ap.add_argument("--bootstrap-reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--model",
        default="logistic_regression",
        choices=["linear_score", "logistic_regression", "random_forest",
                 "gradient_boosting", "svm_rbf"],
    )
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    with open(args.anchorings, "r", encoding="utf-8") as f:
        spec = json.load(f)

    anchorings = [
        Anchoring(
            label=a["label"],
            low_sentiment=float(a["low_sentiment"]),
            high_sentiment=float(a["high_sentiment"]),
        )
        for a in spec["anchorings"]
    ]

    cfg = SimulationConfig(
        n=args.n,
        invite_rate=args.invite_rate,
        sd=args.sd,
    )

    print(f"Anchorings: {len(anchorings)}", file=sys.stderr)
    print(f"  n per replicate: {cfg.n}", file=sys.stderr)
    print(f"  invite rate: {cfg.invite_rate}", file=sys.stderr)
    print(f"  bootstrap reps: {args.bootstrap_reps}", file=sys.stderr)
    print(f"  model: {args.model}", file=sys.stderr)
    print("", file=sys.stderr)

    results = run_anchoring_sweep(
        anchorings=anchorings,
        cfg=cfg,
        n_reps=args.bootstrap_reps,
        base_seed=args.seed,
        model_name=args.model,
    )

    # Pretty print headline DI per anchoring
    print(f"{'Anchoring':<28} {'Gap':>8} {'DI':>10} {'95% CI':>22}")
    print("-" * 72)
    for label, r in results.items():
        gap = r["anchoring"]["gap"]
        di = r["metrics"]["disparate_impact"]
        di_str = f"{di['point']:.3f}" if not np.isnan(di["point"]) else "  N/A"
        ci = f"[{di['ci_lo']:.3f}, {di['ci_hi']:.3f}]" if not np.isnan(di['ci_lo']) else "[--, --]"
        print(f"{label:<28} {gap:>+8.3f} {di_str:>10} {ci:>22}")
    print("-" * 72)
    print("EEOC four-fifths threshold: DI < 0.80 = presumptive adverse impact.\n")

    out_json = os.path.join(args.out_dir, "screening_simulation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "n_per_replicate": cfg.n,
            "invite_rate": cfg.invite_rate,
            "narrative_sd": cfg.sd,
            "bootstrap_reps": args.bootstrap_reps,
            "model": args.model,
            "results": results,
        }, f, indent=2, default=lambda x: None
                  if (isinstance(x, float) and np.isnan(x)) else x)
    print(f"Wrote: {out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

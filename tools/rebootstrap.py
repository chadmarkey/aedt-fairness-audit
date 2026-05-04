"""Re-bootstrap CIs at higher rep counts from cached per-applicant scores.

Avoids re-running the SBERT or LLM extractor when only the bootstrap rep
count needs to change. Loads an existing
``audit_*_per_applicant_scores*.csv``, re-runs ``axis_audit`` at the
requested rep count, and writes a new results JSON next to the input.

Usage::

    python -m tools.rebootstrap \\
        --scores out/audit_2/audit_2_per_applicant_scores_llm.csv \\
        --score-cols poverty refugee major_illness academic_career _total \\
        --top-frac 0.3 \\
        --bootstrap-reps 1000 \\
        --out out/audit_2/audit_2_results_llm_reps1000.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from audit.screening import axis_audit


AXIS_COLUMNS = {
    "gender": "stratum_gender",
    "race": "stratum_race",
    "school_tier": "stratum_school_tier",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True, help="Per-applicant CSV from a prior audit run")
    ap.add_argument(
        "--score-cols",
        nargs="+",
        required=True,
        help="One or more score columns to bootstrap; e.g., 'score_baseline score_mitigated' "
             "or 'poverty refugee major_illness academic_career _total'",
    )
    ap.add_argument("--top-frac", type=float, default=0.3)
    ap.add_argument("--bootstrap-reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.scores)
    print(f"Loaded {len(df)} rows from {args.scores}", file=sys.stderr)

    out: Dict[str, Dict] = {
        "source_csv": args.scores,
        "top_frac": args.top_frac,
        "bootstrap_reps": args.bootstrap_reps,
        "score_columns": list(args.score_cols),
        "results_per_score_col": {},
    }

    for col in args.score_cols:
        if col not in df.columns:
            print(f"  SKIP: {col} not in CSV columns", file=sys.stderr)
            continue
        print(f"  Bootstrapping {col} at {args.bootstrap_reps} reps...", file=sys.stderr)
        res = axis_audit(
            df, col, AXIS_COLUMNS,
            top_frac=args.top_frac,
            n_bootstrap=args.bootstrap_reps,
            bootstrap_seed=args.seed,
        )
        out["results_per_score_col"][col] = res

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(out, fp, indent=2, default=lambda x: None)
    print(f"Wrote: {args.out}", file=sys.stderr)

    print("\nSUMMARY")
    print("=" * 78)
    for col, axis_results in out["results_per_score_col"].items():
        print(f"\n{col}:")
        for axis, m in axis_results.items():
            di = m["disparate_impact"]
            ci_lo = m["bootstrap_di_ci_lo"]
            ci_hi = m["bootstrap_di_ci_hi"]
            print(f"  {axis:<14} DI={di:.3f}  95% CI [{ci_lo:.3f}, {ci_hi:.3f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

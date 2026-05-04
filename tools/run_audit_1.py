"""Audit 1: Bias Mitigator efficacy.

Runs the pipeline twice — once on raw text, once on Bias-Mitigator-processed
text — and reports the change in disparate impact across demographic axes.

The audit framing: US Patent No. 12,265,502 B1, Claim 1, makes input-side
detect-and-replace bias mitigation a required element of the claimed method.
This audit measures whether a reasonable implementation of that requirement
reduces disparate impact when applied to demographically stratified inputs.

Inputs:
  --corpus    JSONL file produced by tools.generate_ps_corpus
  --pipeline  module:function spec for a callable taking list[str] → np.ndarray
              (see examples/example_pipeline.py for the interface)
  --out-dir   directory to write audit_1_results.json and per-axis tables

The pipeline_fn is treated as a black box. The audit does not include or
ship any specific AEDT implementation; users supply their own pipeline.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from typing import Callable, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from audit.screening import axis_audit, DEFAULT_AXES
from mitigator import BiasMitigator


def load_pipeline(spec: str) -> Callable[[List[str]], np.ndarray]:
    """Load pipeline_fn from a 'module:function' spec."""
    if ":" not in spec:
        raise ValueError(
            f"--pipeline must be 'module:function'. Got: {spec}\n"
            f"Example: examples.example_pipeline:score_texts"
        )
    module_name, fn_name = spec.split(":", 1)
    mod = importlib.import_module(module_name)
    fn = getattr(mod, fn_name)
    return fn


def load_corpus(path: str) -> pd.DataFrame:
    """Load a JSONL corpus produced by tools.generate_ps_corpus."""
    rows = []
    with open(path, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            stratum = rec["stratum"]
            rows.append({
                "applicant_id": rec["applicant_id"],
                "seed_key": rec["seed_key"],
                "instance": rec["instance"],
                "text": rec["text"],
                "stratum_race": stratum["race"],
                "stratum_gender": stratum["gender"],
                "stratum_school_tier": stratum["school_tier"],
            })
    return pd.DataFrame(rows)


def _print_axis_table(label: str, audit_results: Dict[str, Dict[str, float]]):
    print(f"\n{label}")
    print("-" * 78)
    print(f"{'Axis':<14} {'Group 0':<22} {'Group 1':<14} {'DI':>8} {'95% CI':>20}")
    print("-" * 78)
    for axis, m in audit_results.items():
        g0 = f"{m['group_0_label']} (n={m['n_group0']})"
        g1 = f"{m['group_1_label']} (n={m['n_group1']})"
        di = m["disparate_impact"]
        ci_lo = m["bootstrap_di_ci_lo"]
        ci_hi = m["bootstrap_di_ci_hi"]
        ci_str = f"[{ci_lo:.3f}, {ci_hi:.3f}]" if not np.isnan(ci_lo) else "[--, --]"
        di_str = f"{di:.3f}" if not np.isnan(di) else "  N/A"
        print(f"{axis:<14} {g0:<22} {g1:<14} {di_str:>8} {ci_str:>20}")
    print("-" * 78)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="JSONL corpus from generate_ps_corpus")
    ap.add_argument(
        "--pipeline",
        required=True,
        help="Pipeline as 'module:function' spec. Function takes list[str] → np.ndarray. "
             "See examples/example_pipeline.py.",
    )
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--top-frac", type=float, default=0.2,
                    help="Top-K selection fraction (default 0.2 = top 20%%)")
    ap.add_argument("--bootstrap-reps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Load corpus
    print(f"Loading corpus from {args.corpus}...", file=sys.stderr)
    df = load_corpus(args.corpus)
    print(f"  Loaded {len(df)} personal statements.", file=sys.stderr)

    # Load pipeline
    print(f"Loading pipeline {args.pipeline}...", file=sys.stderr)
    pipeline_fn = load_pipeline(args.pipeline)

    # Score baseline (raw text)
    print(f"Scoring {len(df)} raw texts through pipeline...", file=sys.stderr)
    texts = df["text"].tolist()
    baseline_scores = np.asarray(pipeline_fn(texts), dtype=float)
    df["score_baseline"] = baseline_scores
    print(f"  Baseline score range: [{baseline_scores.min():.3f}, {baseline_scores.max():.3f}]",
          file=sys.stderr)

    # Apply BiasMitigator and re-score
    print("Applying Bias Mitigator (Claim 1 input-side detect-and-replace)...",
          file=sys.stderr)
    mitigator = BiasMitigator()
    mitigated_texts = mitigator.batch(texts)
    print(f"Scoring {len(df)} mitigated texts through pipeline...", file=sys.stderr)
    mitigated_scores = np.asarray(pipeline_fn(mitigated_texts), dtype=float)
    df["score_mitigated"] = mitigated_scores
    print(f"  Mitigated score range: [{mitigated_scores.min():.3f}, {mitigated_scores.max():.3f}]",
          file=sys.stderr)

    # Audit per axis, baseline and mitigated
    axis_columns = {
        "gender": "stratum_gender",
        "race": "stratum_race",
        "school_tier": "stratum_school_tier",
    }
    print("Computing per-axis disparate impact (baseline)...", file=sys.stderr)
    baseline_audit = axis_audit(
        df, "score_baseline", axis_columns,
        top_frac=args.top_frac,
        n_bootstrap=args.bootstrap_reps,
        bootstrap_seed=args.seed,
    )
    print("Computing per-axis disparate impact (post-mitigation)...", file=sys.stderr)
    mitigated_audit = axis_audit(
        df, "score_mitigated", axis_columns,
        top_frac=args.top_frac,
        n_bootstrap=args.bootstrap_reps,
        bootstrap_seed=args.seed,
    )

    # Print summary tables
    _print_axis_table("BASELINE — disparate impact by demographic axis", baseline_audit)
    _print_axis_table("POST-MITIGATION — disparate impact by demographic axis", mitigated_audit)

    # Compute change
    print("\nMITIGATION EFFECT (post DI minus baseline DI per axis)")
    print("-" * 60)
    print(f"{'Axis':<14} {'Baseline DI':>12} {'Post DI':>12} {'Δ DI':>10}")
    print("-" * 60)
    for axis in baseline_audit:
        base_di = baseline_audit[axis]["disparate_impact"]
        post_di = mitigated_audit[axis]["disparate_impact"]
        if np.isnan(base_di) or np.isnan(post_di):
            delta_str = "    --"
        else:
            delta_str = f"{post_di - base_di:+10.3f}"
        base_str = f"{base_di:.3f}" if not np.isnan(base_di) else "  N/A"
        post_str = f"{post_di:.3f}" if not np.isnan(post_di) else "  N/A"
        print(f"{axis:<14} {base_str:>12} {post_str:>12} {delta_str}")
    print("-" * 60)
    print("EEOC four-fifths threshold: DI < 0.80 = presumptive adverse impact.\n")

    # Write results
    results = {
        "audit": "audit_1_bias_mitigator_efficacy",
        "patent": "US 12,265,502 B1, Claim 1",
        "corpus_path": args.corpus,
        "pipeline_spec": args.pipeline,
        "n_applicants": int(len(df)),
        "top_frac": args.top_frac,
        "bootstrap_reps": args.bootstrap_reps,
        "baseline": baseline_audit,
        "post_mitigation": mitigated_audit,
        "delta_di_per_axis": {
            axis: (
                mitigated_audit[axis]["disparate_impact"]
                - baseline_audit[axis]["disparate_impact"]
            )
            for axis in baseline_audit
            if not np.isnan(baseline_audit[axis]["disparate_impact"])
            and not np.isnan(mitigated_audit[axis]["disparate_impact"])
        },
    }
    out_json = os.path.join(args.out_dir, "audit_1_results.json")
    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2, default=lambda x: None
                  if (isinstance(x, float) and np.isnan(x)) else x)

    out_csv = os.path.join(args.out_dir, "audit_1_per_applicant_scores.csv")
    df.drop(columns=["text"]).to_csv(out_csv, index=False)

    print(f"Wrote: {out_json}", file=sys.stderr)
    print(f"Wrote: {out_csv} (no raw text — applicant-level scores only)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Counterfactual decomposition: marker-stripped re-score.

Tests whether per-question DI in Audit 2 is driven by demographic markers
(names, schools, identity phrases) or by within-seed content variation.

Procedure:

  1. Score each PS with the LLM extractor — original (markers present).
  2. Apply BiasMitigator (Claim 1 input-side anonymization) to strip
     names, schools, demographic identifiers.
  3. Re-score the marker-stripped PS with the same LLM extractor.
  4. Compute per-question DI on stripped scores.
  5. Compare to original DI.

Decomposition logic:

  - If DI(stripped) ≈ 1.0  → DI was marker-driven; LLM was reading
    demographic identifiers and using them as features.
  - If DI(stripped) ≈ DI(original) → DI was content-driven; the
    within-seed content held by demographic strata differs in ways the
    LLM picks up.
  - Intermediate → mixed; partial decomposition.

This is the diagnostic that turns "the LLM extractor produces race DI of
0.51 on three questions" into a falsifiable claim about *why*.

Usage::

    python -m tools.counterfactual_decomposition \\
        --corpus synthetic/data/ps_corpus_mvp.jsonl \\
        --original-scores out/audit_2/audit_2_per_applicant_scores_llm.csv \\
        --out-dir out/counterfactual \\
        --llm-provider openai --llm-model gpt-5-mini
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from audit.screening import (
    DEFAULT_AXES,
    assign_binary_group,
    axis_audit,
    paired_permutation_test_delta_di,
)
from mitigator import BiasMitigator
from ps_extraction import LLMPSExtractor, PATENT_QUESTIONS


AXIS_COLUMNS = {
    "gender": "stratum_gender",
    "race": "stratum_race",
    "school_tier": "stratum_school_tier",
}


def load_corpus(path: str) -> pd.DataFrame:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--original-scores", required=True,
                    help="Per-applicant CSV from prior LLM audit run")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--top-frac", type=float, default=0.3)
    ap.add_argument("--bootstrap-reps", type=int, default=1000)
    ap.add_argument("--n-permutations", type=int, default=10000,
                    help="Permutation replicates for the paired test of "
                         "Delta DI per (question × axis) cell (default 10,000)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--llm-provider", default="openai", choices=["openai", "anthropic"])
    ap.add_argument("--llm-model", default=None)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    df = load_corpus(args.corpus)
    print(f"Loaded {len(df)} PSs.", file=sys.stderr)

    print("Loading prior LLM scores...", file=sys.stderr)
    orig_scores = pd.read_csv(args.original_scores)
    score_cols = list(PATENT_QUESTIONS.keys()) + ["_total"]
    orig_scores = orig_scores[["applicant_id"] + score_cols].rename(
        columns={c: f"{c}_original" for c in score_cols}
    )

    print("Applying BiasMitigator (Claim 1 input-side anonymization)...",
          file=sys.stderr)
    mitigator = BiasMitigator()
    df["text_stripped"] = mitigator.batch(df["text"].tolist())

    sample_n = min(3, len(df))
    print(f"\nMITIGATOR SAMPLE — first {sample_n} PSs (truncated to 200 chars):",
          file=sys.stderr)
    for i in range(sample_n):
        orig_first = df.iloc[i]["text"][:200].replace("\n", " ")
        mitig_first = df.iloc[i]["text_stripped"][:200].replace("\n", " ")
        print(f"\n  [{df.iloc[i]['applicant_id']}] BEFORE: {orig_first}",
              file=sys.stderr)
        print(f"  [{df.iloc[i]['applicant_id']}] AFTER:  {mitig_first}",
              file=sys.stderr)

    print(f"\nInitializing LLM extractor "
          f"(provider={args.llm_provider}, model={args.llm_model or '(default)'})...",
          file=sys.stderr)
    extractor = LLMPSExtractor(provider=args.llm_provider, model=args.llm_model)

    print(f"\nScoring {len(df)} marker-stripped PSs via LLM...", file=sys.stderr)
    score_rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        scores = extractor.score_text(row["text_stripped"])
        score_rows.append({
            "applicant_id": row["applicant_id"],
            **{f"{k}_stripped": v for k, v in scores.items()},
        })
        if (i + 1) % 10 == 0:
            print(f"  Scored {i + 1}/{len(df)}...", file=sys.stderr)
    stripped_df = pd.DataFrame(score_rows)

    df = df.merge(orig_scores, on="applicant_id", how="left")
    df = df.merge(stripped_df, on="applicant_id", how="left")

    # Guard against silent applicant_id mismatch between corpus and
    # --original-scores. Left-join NaNs would otherwise propagate into
    # axis_audit and produce misleading-looking N/A cells with no warning.
    missing_orig = df[f"{list(PATENT_QUESTIONS.keys())[0]}_original"].isna().sum()
    if missing_orig:
        print(
            f"WARNING: {missing_orig} corpus applicant_ids have no matching row "
            f"in --original-scores={args.original_scores}. These will be dropped "
            f"from the per-cell audit.",
            file=sys.stderr,
        )

    # Per-question DI: original vs stripped, plus paired-permutation test
    # of the per-(question × axis) Delta DI under the null of pre/post score
    # exchangeability.
    decomposition: Dict[str, Dict] = {}
    score_cols = list(PATENT_QUESTIONS.keys()) + ["_total"]
    for q_key in score_cols:
        orig_col = f"{q_key}_original"
        stripped_col = f"{q_key}_stripped"
        orig_audit = axis_audit(
            df, orig_col, AXIS_COLUMNS,
            top_frac=args.top_frac,
            n_bootstrap=args.bootstrap_reps,
            bootstrap_seed=args.seed,
        )
        stripped_audit = axis_audit(
            df, stripped_col, AXIS_COLUMNS,
            top_frac=args.top_frac,
            n_bootstrap=args.bootstrap_reps,
            bootstrap_seed=args.seed,
        )

        delta_perm: Dict[str, Dict] = {}
        for axis_name, col_name in AXIS_COLUMNS.items():
            cfg = DEFAULT_AXES.get(axis_name)
            if cfg is None:
                continue
            valid = ~(df[orig_col].isna() | df[stripped_col].isna())
            if not valid.any():
                continue
            group = assign_binary_group(df.loc[valid, col_name], cfg)
            delta_perm[axis_name] = paired_permutation_test_delta_di(
                df.loc[valid, orig_col].to_numpy(),
                df.loc[valid, stripped_col].to_numpy(),
                group,
                top_frac=args.top_frac,
                n_perms=args.n_permutations,
                seed=args.seed,
            )

        decomposition[q_key] = {
            "original": orig_audit,
            "stripped": stripped_audit,
            "delta_di_paired_permutation": delta_perm,
        }

    # Print decomposition table
    print("\n\nCOUNTERFACTUAL DECOMPOSITION — per-question DI: original vs marker-stripped")
    print("=" * 110)
    print(f"{'Question':<18} {'Axis':<14} {'DI(orig)':>10} {'DI(stripped)':>14} "
          f"{'Δ':>10} {'paired-p':>10} {'Interpretation':<24}")
    print("-" * 110)
    for q_key, dec in decomposition.items():
        for axis in AXIS_COLUMNS:
            orig_di = dec["original"][axis]["disparate_impact"]
            strip_di = dec["stripped"][axis]["disparate_impact"]
            perm = dec.get("delta_di_paired_permutation", {}).get(axis, {})
            p_val = perm.get("p_value", float("nan"))
            if np.isnan(orig_di) or np.isnan(strip_di):
                interp = "n/a"
                delta_str = "    --"
            else:
                delta = strip_di - orig_di
                delta_str = f"{delta:+10.3f}"
                if abs(orig_di - 1.0) < 0.1:
                    interp = "no DI to explain"
                elif abs(strip_di - 1.0) < abs(orig_di - 1.0) * 0.4:
                    interp = "marker-driven"
                elif abs(strip_di - 1.0) > abs(orig_di - 1.0) * 0.7:
                    interp = "content-driven"
                else:
                    interp = "mixed"
            orig_str = f"{orig_di:.3f}" if not np.isnan(orig_di) else "  N/A"
            strip_str = f"{strip_di:.3f}" if not np.isnan(strip_di) else "  N/A"
            p_str = f"{p_val:.3f}" if not np.isnan(p_val) else "  N/A"
            print(f"{q_key:<18} {axis:<14} {orig_str:>10} {strip_str:>14} "
                  f"{delta_str:>10} {p_str:>10} {interp:<24}")
        print()
    print("=" * 110)
    print("paired-p tests the null of pre/post score exchangeability per applicant —")
    print("'is the Delta DI distinguishable from chance under random pre/post swaps?'\n")

    # Write results
    results = {
        "audit": "counterfactual_decomposition_marker_stripped",
        "corpus_path": args.corpus,
        "original_scores_path": args.original_scores,
        "n_applicants": int(len(df)),
        "top_frac": args.top_frac,
        "bootstrap_reps": args.bootstrap_reps,
        "n_permutations": args.n_permutations,
        "extractor": {
            "provider": args.llm_provider,
            "model": args.llm_model,
        },
        "decomposition": decomposition,
        "interpretation_thresholds": {
            "marker_driven_if": "|DI(stripped) - 1.0| < 0.4 * |DI(orig) - 1.0|",
            "content_driven_if": "|DI(stripped) - 1.0| > 0.7 * |DI(orig) - 1.0|",
            "no_DI_to_explain_if": "|DI(orig) - 1.0| < 0.1",
        },
        "delta_perm_test": (
            "Paired permutation under the null of pre/post score "
            "exchangeability per applicant. p_value = fraction of "
            "permutations where |Delta_perm| >= |Delta_observed|."
        ),
    }
    out_json = os.path.join(args.out_dir, "counterfactual_decomposition.json")
    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2, default=lambda x: None
                  if (isinstance(x, float) and np.isnan(x)) else x)
    out_csv = os.path.join(args.out_dir, "counterfactual_per_applicant_scores.csv")
    df.drop(columns=["text", "text_stripped"]).to_csv(out_csv, index=False)
    print(f"\nWrote: {out_json}", file=sys.stderr)
    print(f"Wrote: {out_csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Audit 2: PS four-question extraction.

Runs the patent's four enumerated PS-extraction questions
(US 12,265,502 B1, col. 10) against a synthetic PS corpus and reports
disparate impact per question and at the aggregate level.

The audit framing has two layers:

  1. The four questions themselves probe protected-class proxies (poverty
     correlates with race/SES; refugee status correlates with national
     origin; major illness correlates with disability status). The act of
     asking these questions, regardless of inference accuracy, may itself
     constitute discrimination under Title VII / Title VI / ADA.

  2. Inference-level bias may produce systematically different answers
     across demographic strata even when narrative content is held
     constant. This audit measures the within-stratum content-controlled
     score variation and the across-stratum DI at top-K selection.

Inputs:
  --corpus     JSONL file produced by tools.generate_ps_corpus
  --out-dir    directory to write audit_2_results.json and per-axis tables

No external pipeline is required; the PSExtractor is the audited system.
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

from audit.screening import axis_audit
from ps_extraction import PSExtractor, LLMPSExtractor, PATENT_QUESTIONS


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
                "expected_truth": rec["expected_question_truth"],
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
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--top-frac", type=float, default=0.3,
                    help="Top-K selection fraction (default 0.3 — patent §530 power-2 "
                         "aggregation produces a long-tailed distribution; "
                         "0.3 captures the upper-mass of inferred-true responses)")
    ap.add_argument("--bootstrap-reps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--extractor",
        default="sbert",
        choices=["sbert", "llm"],
        help="Extraction architecture: sbert (cosine-similarity, patent col. 22) "
             "or llm (direct LLM question-answering, patent col. 10). "
             "Default: sbert.",
    )
    ap.add_argument("--embedding-model", default="all-MiniLM-L6-v2",
                    help="SBERT model name (used when --extractor=sbert)")
    ap.add_argument("--llm-provider", default="openai", choices=["openai", "anthropic"],
                    help="LLM backend (used when --extractor=llm)")
    ap.add_argument("--llm-model", default=None,
                    help="LLM model name (used when --extractor=llm; "
                         "defaults: openai→gpt-5-mini, anthropic→claude-haiku-4-5)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print(f"Loading corpus from {args.corpus}...", file=sys.stderr)
    df = load_corpus(args.corpus)
    print(f"  Loaded {len(df)} personal statements.", file=sys.stderr)

    if args.extractor == "sbert":
        print(f"Initializing SBERT PS extractor ({args.embedding_model})...",
              file=sys.stderr)
        extractor = PSExtractor(embedding_model=args.embedding_model)
        extractor._ensure_model()
    else:
        print(f"Initializing LLM PS extractor "
              f"(provider={args.llm_provider}, model={args.llm_model or '(default)'})...",
              file=sys.stderr)
        extractor = LLMPSExtractor(
            provider=args.llm_provider,
            model=args.llm_model,
        )

    print(f"Scoring {len(df)} PSs against the patent's four questions...", file=sys.stderr)
    score_rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        scores = extractor.score_text(row["text"])
        score_rows.append({"applicant_id": row["applicant_id"], **scores})
        if args.extractor == "llm" and (i + 1) % 10 == 0:
            print(f"  Scored {i + 1}/{len(df)} via LLM...", file=sys.stderr)
    score_df = pd.DataFrame(score_rows)
    df = df.merge(score_df, on="applicant_id", how="left")

    # Per-question DI per axis
    axis_columns = {
        "gender": "stratum_gender",
        "race": "stratum_race",
        "school_tier": "stratum_school_tier",
    }

    per_question_audit: Dict[str, Dict] = {}
    for q_key in PATENT_QUESTIONS:
        results = axis_audit(
            df, q_key, axis_columns,
            top_frac=args.top_frac,
            n_bootstrap=args.bootstrap_reps,
            bootstrap_seed=args.seed,
        )
        per_question_audit[q_key] = results
        _print_axis_table(
            f"QUESTION: \"{PATENT_QUESTIONS[q_key]}\" — disparate impact",
            results,
        )

    # Aggregate-score DI (patent §530 power-2 sum)
    aggregate_audit = axis_audit(
        df, "_total", axis_columns,
        top_frac=args.top_frac,
        n_bootstrap=args.bootstrap_reps,
        bootstrap_seed=args.seed,
    )
    _print_axis_table("AGGREGATE SCORE (patent §530 power-2 sum) — DI", aggregate_audit)

    # Within-seed counterfactual: for each seed, compare per-question scores
    # across demographic strata holding seed (content) constant.
    print("\nWITHIN-SEED CONTENT-CONTROLLED VARIATION")
    print("-" * 78)
    print("For each content seed, the score differences across demographic strata")
    print("reflect inferred bias rather than content variation, since the seed's")
    print("core narrative is held constant across strata.\n")
    print(f"{'Seed':<22} {'Question':<18} {'Group 0 mean':>12} {'Group 1 mean':>12} {'Δ':>8}")
    print("-" * 78)
    for seed_key in df["seed_key"].unique():
        seed_df = df[df["seed_key"] == seed_key]
        for q_key in PATENT_QUESTIONS:
            for axis_name, col in axis_columns.items():
                from audit.screening import DEFAULT_AXES, assign_binary_group
                cfg = DEFAULT_AXES[axis_name]
                group = assign_binary_group(seed_df[col], cfg)
                g0_mask = group == 0
                g1_mask = group == 1
                if not g0_mask.any() or not g1_mask.any():
                    continue
                m0 = float(seed_df.loc[g0_mask, q_key].mean())
                m1 = float(seed_df.loc[g1_mask, q_key].mean())
                if axis_name == "race":  # only print one axis per seed for brevity
                    print(f"{seed_key:<22} {q_key:<18} {m0:>12.3f} {m1:>12.3f} {m1 - m0:>+8.3f}")
        print()
    print("-" * 78)

    # Write results
    results = {
        "audit": "audit_2_ps_four_question_extraction",
        "patent": "US 12,265,502 B1, col. 10 (PS Component)",
        "patent_questions": PATENT_QUESTIONS,
        "corpus_path": args.corpus,
        "n_applicants": int(len(df)),
        "top_frac": args.top_frac,
        "bootstrap_reps": args.bootstrap_reps,
        "extractor": args.extractor,
        "extractor_config": (
            {"embedding_model": args.embedding_model}
            if args.extractor == "sbert"
            else {"provider": args.llm_provider, "model": args.llm_model
                  or ("gpt-5-mini" if args.llm_provider == "openai"
                      else "claude-haiku-4-5")}
        ),
        "per_question": per_question_audit,
        "aggregate": aggregate_audit,
    }
    out_json = os.path.join(
        args.out_dir, f"audit_2_results_{args.extractor}.json"
    )
    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2, default=lambda x: None
                  if (isinstance(x, float) and np.isnan(x)) else x)

    out_csv = os.path.join(
        args.out_dir, f"audit_2_per_applicant_scores_{args.extractor}.csv"
    )
    df.drop(columns=["text", "expected_truth"]).to_csv(out_csv, index=False)

    print(f"\nWrote: {out_json}", file=sys.stderr)
    print(f"Wrote: {out_csv} (per-applicant per-question scores; raw text excluded)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

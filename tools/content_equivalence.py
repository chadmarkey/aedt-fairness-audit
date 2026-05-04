"""Content equivalence validation (lightweight).

For each content seed, computes pairwise SBERT embedding distances at
three nesting levels:

  - within_seed_within_stratum: same content seed, same demographic stratum
  - within_seed_across_stratum: same content seed, different demographic strata
  - across_seed: different content seeds

If the audit's content-held-constant claim is true, then::

    within_seed_within_stratum  <  within_seed_across_stratum  <<  across_seed

i.e., demographic markers add some embedding variance, but markedly less
than seed-level content shifts.

If ``within_seed_across_stratum ≈ across_seed``, then "content drift across
demographic strata" is comparable to seed-level content drift, and the
audit's premise that the comparison holds content constant is suspect.

Outputs:

  - JSON summary with mean/median/quantiles per nesting level, per seed
  - PNG distribution plot if matplotlib is installed (optional)

Usage::

    python -m tools.content_equivalence \\
        --corpus synthetic/data/ps_corpus_mvp.jsonl \\
        --out out/content_equivalence/results.json
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
                "stratum_key": (
                    f"{stratum['race']}|{stratum['gender']}|{stratum['school_tier']}"
                ),
            })
    return pd.DataFrame(rows)


def embed_corpus(df: pd.DataFrame, model_name: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    print(f"Loading SBERT model {model_name}...", file=sys.stderr)
    model = SentenceTransformer(model_name)
    print(f"Embedding {len(df)} PSs...", file=sys.stderr)
    embs = model.encode(
        df["text"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return np.asarray(embs)


def cosine_distance_matrix(embs: np.ndarray) -> np.ndarray:
    """Cosine distance = 1 - cosine similarity. Embeddings assumed unit-normed."""
    sim = embs @ embs.T
    return 1.0 - sim


def summarize(distances: np.ndarray) -> Dict[str, float]:
    if len(distances) == 0:
        return {
            "n": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "p10": float("nan"),
            "p90": float("nan"),
        }
    return {
        "n": int(len(distances)),
        "mean": float(np.mean(distances)),
        "median": float(np.median(distances)),
        "p10": float(np.quantile(distances, 0.1)),
        "p90": float(np.quantile(distances, 0.9)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--embedding-model", default="all-MiniLM-L6-v2")
    args = ap.parse_args()

    df = load_corpus(args.corpus)
    print(f"Loaded {len(df)} PSs across "
          f"{df['seed_key'].nunique()} seeds, "
          f"{df['stratum_key'].nunique()} strata.", file=sys.stderr)

    embs = embed_corpus(df, args.embedding_model)
    dist = cosine_distance_matrix(embs)

    seed_keys = df["seed_key"].to_numpy()
    stratum_keys = df["stratum_key"].to_numpy()
    n = len(df)

    # Collect distance pairs at three nesting levels
    within_seed_within_stratum: List[float] = []
    within_seed_across_stratum: List[float] = []
    across_seed: List[float] = []

    # Per-seed breakdown
    per_seed: Dict[str, Dict[str, List[float]]] = {
        s: {"within_stratum": [], "across_stratum": []}
        for s in df["seed_key"].unique()
    }

    for i in range(n):
        for j in range(i + 1, n):
            d = dist[i, j]
            same_seed = seed_keys[i] == seed_keys[j]
            same_stratum = stratum_keys[i] == stratum_keys[j]
            if same_seed and same_stratum:
                within_seed_within_stratum.append(d)
                per_seed[seed_keys[i]]["within_stratum"].append(d)
            elif same_seed and not same_stratum:
                within_seed_across_stratum.append(d)
                per_seed[seed_keys[i]]["across_stratum"].append(d)
            else:
                across_seed.append(d)

    overall = {
        "within_seed_within_stratum": summarize(np.array(within_seed_within_stratum)),
        "within_seed_across_stratum": summarize(np.array(within_seed_across_stratum)),
        "across_seed": summarize(np.array(across_seed)),
    }

    per_seed_summary = {
        s: {
            "within_stratum": summarize(np.array(v["within_stratum"])),
            "across_stratum": summarize(np.array(v["across_stratum"])),
        }
        for s, v in per_seed.items()
    }

    # Decision rule
    wsws = overall["within_seed_within_stratum"]["mean"]
    wsas = overall["within_seed_across_stratum"]["mean"]
    asd = overall["across_seed"]["mean"]
    content_holds = wsas < asd
    ratio = wsas / asd if asd > 0 else float("nan")

    output = {
        "corpus_path": args.corpus,
        "embedding_model": args.embedding_model,
        "n_documents": int(n),
        "overall": overall,
        "per_seed": per_seed_summary,
        "decision": {
            "content_holds_constant_within_seed": bool(content_holds),
            "ratio_within_seed_across_stratum_to_across_seed": ratio,
            "interpretation": (
                "Content holds constant within seed; demographic-marker "
                "embedding drift is smaller than seed-level content drift."
                if ratio < 0.7 else
                "Content variation across strata within a seed is meaningful; "
                "interpret demographic DI claims with caution."
                if ratio > 0.9 else
                "Marginal: demographic-marker drift approaches seed-level drift."
            ),
        },
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(output, fp, indent=2)
    print(f"Wrote: {args.out}", file=sys.stderr)

    print("\nCONTENT EQUIVALENCE SUMMARY")
    print("=" * 78)
    print(f"{'Nesting level':<36} {'mean':>8} {'median':>8} {'p10':>8} {'p90':>8}")
    print("-" * 78)
    for label, key in [
        ("within seed, within stratum", "within_seed_within_stratum"),
        ("within seed, across stratum", "within_seed_across_stratum"),
        ("across seed", "across_seed"),
    ]:
        s = overall[key]
        print(f"{label:<36} {s['mean']:>8.3f} {s['median']:>8.3f} "
              f"{s['p10']:>8.3f} {s['p90']:>8.3f}")
    print("-" * 78)
    print(f"\nratio (within-seed-across-stratum / across-seed) = {ratio:.3f}")
    print(f"interpretation: {output['decision']['interpretation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

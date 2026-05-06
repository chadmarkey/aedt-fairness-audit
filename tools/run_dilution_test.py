"""Run a multi-instrument dilution test on user-supplied variants.

The user provides:
  - A JSON config naming the variants and (optionally) the skeleton
    file path
  - The variant texts as fields in the JSON or as separate text files
    referenced from the JSON
  - The instruments to use (vader, transformer, llm_judge_anthropic,
    llm_judge_openai)

The harness scores each variant with each instrument at excerpt level
and (if a skeleton is supplied) full-document level. It then computes
gaps for the user-specified variant pairs and the dilution ratio
(full_doc_gap / excerpt_gap).

Usage:
    python -m tools.run_dilution_test \\
        --config examples/dilution_test_template.json \\
        --out-dir out/dilution_test
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Callable, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from dilution import run_dilution_test


def load_variants(config: dict, base_path: str) -> Dict[str, str]:
    """Load variants from inline strings or referenced files."""
    variants_spec = config.get("variants", {})
    out = {}
    for name, val in variants_spec.items():
        if isinstance(val, dict) and "file" in val:
            path = val["file"]
            if not os.path.isabs(path):
                path = os.path.join(base_path, path)
            with open(path, "r", encoding="utf-8") as f:
                out[name] = f.read()
        elif isinstance(val, str):
            out[name] = val
        else:
            raise ValueError(f"Variant {name!r} must be a string or {{file: path}} dict")
    return out


def load_skeleton(config: dict, base_path: str) -> str | None:
    skel = config.get("skeleton")
    if skel is None:
        return None
    if isinstance(skel, dict) and "file" in skel:
        path = skel["file"]
        if not os.path.isabs(path):
            path = os.path.join(base_path, path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    if isinstance(skel, str):
        return skel
    raise ValueError("skeleton must be a string or {file: path} dict")


def build_scoring_fns(config: dict) -> Dict[str, Callable[[str], Dict[str, float]]]:
    """Build the scoring functions per the config's instruments list."""
    instruments = config.get("instruments", ["vader"])
    out: Dict[str, Callable] = {}

    for inst in instruments:
        if inst == "vader":
            from sentiment import vader
            out["vader"] = vader.score
        elif inst == "transformer":
            from sentiment import transformer
            out["transformer"] = transformer.score
        elif inst.startswith("llm_judge_anthropic"):
            from sentiment import llm_judge
            # Per-instrument model lookup first, then provider-level
            # default. Lets a config use multiple Anthropic instruments
            # at different models (e.g., llm_judge_anthropic_haiku and
            # llm_judge_anthropic_sonnet) in a single run.
            model = config.get(f"{inst}_model") or config.get(
                "llm_judge_anthropic_model", "claude-sonnet-4-5"
            )
            out[inst] = lambda t, m=model: llm_judge.score(t, provider="anthropic", model=m)
        elif inst.startswith("llm_judge_openai"):
            from sentiment import llm_judge
            model = config.get(f"{inst}_model") or config.get(
                "llm_judge_openai_model", os.environ.get("OPENAI_MODEL", "gpt-4o")
            )
            out[inst] = lambda t, m=model: llm_judge.score(t, provider="openai", model=m)
        else:
            raise ValueError(f"Unknown instrument: {inst}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    config_path = os.path.abspath(args.config)
    base_path = os.path.dirname(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    variants = load_variants(config, base_path)
    skeleton = load_skeleton(config, base_path)
    scoring_fns = build_scoring_fns(config)
    pairs = [tuple(p) for p in config.get("pairs", [])]

    print(f"Variants: {list(variants.keys())}", file=sys.stderr)
    print(f"Instruments: {list(scoring_fns.keys())}", file=sys.stderr)
    print(f"Skeleton: {'yes' if skeleton else 'no'}", file=sys.stderr)
    print(f"Pairs: {pairs}\n", file=sys.stderr)

    results = run_dilution_test(
        variants=variants,
        scoring_fns=scoring_fns,
        pairs=pairs,
        skeleton=skeleton,
    )

    # Pretty print
    for inst_label, payload in results.items():
        print(f"\n=== {inst_label} ===", file=sys.stderr)
        print(f"{'Variant':<30} {'excerpt compound':>18} "
              f"{'full_doc compound':>18}", file=sys.stderr)
        print("-" * 70, file=sys.stderr)
        for name, scored in payload["scores"].items():
            ec = scored["excerpt"]["compound"]
            fc = scored.get("full_doc", {}).get("compound", float("nan"))
            fc_str = f"{fc:+.4f}" if not np.isnan(fc) else "  N/A"
            print(f"{name:<30} {ec:>+18.4f} {fc_str:>18}", file=sys.stderr)

        if payload["gaps"]:
            print(f"\n{'Pair':<40} {'excerpt gap':>14} {'full_doc gap':>14} "
                  f"{'dilution':>10}", file=sys.stderr)
            print("-" * 84, file=sys.stderr)
            for pair_label, g in payload["gaps"].items():
                fg = g["full_doc_gap"]
                fg_str = f"{fg:+.4f}" if not np.isnan(fg) else "  N/A"
                dr = g["dilution_ratio"]
                dr_str = f"{dr:+.3f}" if not np.isnan(dr) else " N/A"
                print(f"{pair_label:<40} {g['excerpt_gap']:>+14.4f} "
                      f"{fg_str:>14} {dr_str:>10}", file=sys.stderr)

    out_json = os.path.join(args.out_dir, "dilution_test_results.json")
    # Recursively replace NaN with None so the output is strict-RFC-8259 JSON.
    # json.dump by default emits the literal token `NaN`, which downstream
    # strict parsers (including jq, jsonschema, JS JSON.parse) reject.
    def _scrub_nan(obj):
        if isinstance(obj, float) and np.isnan(obj):
            return None
        if isinstance(obj, dict):
            return {k: _scrub_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_scrub_nan(v) for v in obj]
        return obj
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(_scrub_nan(results), f, indent=2)
    print(f"\nWrote: {out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

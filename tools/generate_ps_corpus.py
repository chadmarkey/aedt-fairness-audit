"""CLI runner for synthetic PS corpus generation.

Generates a demographically stratified corpus of synthetic personal
statements suitable for use as input to Audit 1 (Bias Mitigator efficacy)
and Audit 2 (PS four-question extraction).

Default configuration produces 4 seeds × 4 races × 2 genders × 3 school
tiers × 2 instances = 192 personal statements. Each invocation calls the
LLM once per PS; expect ~$0.30-$1.00 in API cost depending on provider
and model.

Usage:
    # With Anthropic Claude (default):
    ANTHROPIC_API_KEY=sk-ant-... python -m tools.generate_ps_corpus \\
        --out synthetic/data/ps_corpus.jsonl

    # With OpenAI (or any OpenAI-compatible endpoint via OPENAI_BASE_URL):
    OPENAI_API_KEY=... OPENAI_MODEL=gpt-4o python -m tools.generate_ps_corpus \\
        --out synthetic/data/ps_corpus.jsonl --provider openai

    # Smaller MVP run (8 PSs total — for smoke-test):
    python -m tools.generate_ps_corpus --out test.jsonl \\
        --instances-per-cell 1 --seeds control_neutral --school-tiers top_20

    # Custom strata:
    python -m tools.generate_ps_corpus --out out.jsonl \\
        --races White Black --genders Female Male --school-tiers top_20 mid_tier
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthetic.ps_generator import (
    PSGenerator,
    DEFAULT_RACES,
    DEFAULT_GENDERS,
    DEFAULT_SCHOOL_TIERS,
)
from synthetic.seeds import SEEDS, all_seed_keys, get_seed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output JSONL path")
    ap.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "openai"],
        help="LLM backend",
    )
    ap.add_argument("--model", default=None, help="Model name override")
    ap.add_argument(
        "--seeds",
        nargs="+",
        default=None,
        help=f"Subset of content seeds to use (default: all). Available: {all_seed_keys()}",
    )
    ap.add_argument(
        "--races",
        nargs="+",
        default=None,
        help=f"Race/ethnicity strata (default: {DEFAULT_RACES})",
    )
    ap.add_argument(
        "--genders",
        nargs="+",
        default=None,
        help=f"Gender strata (default: {DEFAULT_GENDERS})",
    )
    ap.add_argument(
        "--school-tiers",
        nargs="+",
        default=None,
        help=f"School tier strata (default: {DEFAULT_SCHOOL_TIERS})",
    )
    ap.add_argument(
        "--instances-per-cell",
        type=int,
        default=2,
        help="Number of PSs per (seed × stratum) cell (default: 2)",
    )
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=1200)
    ap.add_argument(
        "--prompt-variant",
        default="original",
        choices=["original", "content_neutral"],
        help=(
            "original: school_tier description includes a content cue "
            "('research lab, faculty mentor, institution-specific program') "
            "for top_20 and instructs voice variation across profiles. "
            "content_neutral: school_tier description is the school name only "
            "(no content cue) and prompt instructs that academic register / "
            "narrative sophistication be HELD CONSTANT across school tiers. "
            "Used to test whether the school_tier × academic_career signal "
            "is a corpus-prompt design effect."
        ),
    )
    ap.add_argument("--quiet", action="store_true", help="Suppress per-PS logging")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expected corpus size without making API calls",
    )
    args = ap.parse_args()

    seeds = (
        [get_seed(k) for k in args.seeds]
        if args.seeds is not None
        else list(SEEDS)
    )

    gen = PSGenerator(
        races=args.races,
        genders=args.genders,
        school_tiers=args.school_tiers,
        seeds=seeds,
        instances_per_cell=args.instances_per_cell,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        prompt_variant=args.prompt_variant,
    )

    expected = gen.expected_corpus_size()
    print(f"Generator configuration:", file=sys.stderr)
    print(f"  Provider:           {gen.provider}", file=sys.stderr)
    print(f"  Model:              {gen.model or '(provider default)'}", file=sys.stderr)
    print(f"  Prompt variant:     {gen.prompt_variant}", file=sys.stderr)
    print(f"  Seeds:              {[s.key for s in gen.seeds]}", file=sys.stderr)
    print(f"  Races:              {gen.races}", file=sys.stderr)
    print(f"  Genders:            {gen.genders}", file=sys.stderr)
    print(f"  School tiers:       {gen.school_tiers}", file=sys.stderr)
    print(f"  Instances per cell: {gen.instances_per_cell}", file=sys.stderr)
    print(f"  Expected corpus:    {expected} personal statements", file=sys.stderr)
    print(f"  Output:             {args.out}", file=sys.stderr)

    if args.dry_run:
        print(f"\n--dry-run: not generating. {expected} PSs would be produced.", file=sys.stderr)
        return 0

    print("", file=sys.stderr)
    n = gen.generate_to_jsonl(args.out, verbose=not args.quiet)
    print(f"\nGenerated {n} personal statements → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

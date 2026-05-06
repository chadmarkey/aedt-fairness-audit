"""Section-aware multi-instrument sentiment audit of a document.

Splits a document into labeled sections, scores each section under
multiple sentiment instruments, and reports the per-section
distribution. Tests whether any one section is a low-sentiment outlier
in an otherwise uniformly scored document — the architectural pattern
that section-aware extraction pipelines surface and whole-document
pipelines dilute.

Section detection. By default, sections are detected as all-caps lines
of length ≥5 followed by a body. Users supply their own
``--section-regex`` for documents that mark sections differently.

Inputs:
  --document        Path to a plain-text document (gitignored by default
                    for documents containing personal data).
  --instruments     One or more of: vader transformer llm
  --out             Path to write per-section scores JSON.
  --section-regex   Optional regex pattern for section header lines.
  --llm-provider    openai | anthropic (when --instruments includes llm)
  --llm-model       Model name (default: gpt-5-mini for openai)

Output:

  - JSON: per-section per-instrument scores + word counts + flagged
    rank-lowest sections per instrument
  - Table to stderr summarizing the per-section scores
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def split_sections(text: str, section_regex: str | None = None) -> List[Dict[str, str]]:
    """Split a document into labeled sections.

    Default: section header is an ALL-CAPS line of length ≥5 followed by
    a body. Override via section_regex (a Python regex matching the
    header line).
    """
    sections: List[Dict[str, str]] = []
    lines = text.split("\n")
    current_label = "PREAMBLE"
    buffer: List[str] = []

    pattern = re.compile(section_regex) if section_regex else None

    def flush(label: str, buf: List[str]):
        body = "\n".join(buf).strip()
        if body:
            sections.append({"label": label, "body": body})

    for i, line in enumerate(lines):
        stripped = line.strip()
        if pattern:
            is_header = bool(stripped) and pattern.match(stripped) is not None
        else:
            is_header = (
                stripped
                and stripped == stripped.upper()
                and len(stripped) >= 5
                and any(c.isalpha() for c in stripped)
                and not stripped.startswith("-")
            )
        if is_header:
            flush(current_label, buffer)
            current_label = stripped
            buffer = []
        else:
            buffer.append(line)
    flush(current_label, buffer)
    return sections


def score_section_with(
    instrument_name: str,
    section_body: str,
    *,
    llm_provider: str = "openai",
    llm_model: str | None = None,
) -> float:
    """Return compound sentiment score for one section under one instrument."""
    if instrument_name == "vader":
        from sentiment.vader import score as vader_score
        return float(vader_score(section_body)["compound"])
    if instrument_name == "transformer":
        from sentiment.transformer import score as transformer_score
        return float(transformer_score(section_body)["compound"])
    if instrument_name == "llm":
        from sentiment.llm_judge import score as llm_score
        return float(llm_score(
            section_body,
            provider=llm_provider,
            model=llm_model,
        )["compound"])
    raise ValueError(f"Unknown instrument: {instrument_name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--document", required=True, help="Path to plain-text document")
    ap.add_argument(
        "--instruments",
        nargs="+",
        default=["vader", "transformer"],
        choices=["vader", "transformer", "llm"],
        help="Which sentiment instruments to run",
    )
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--section-regex",
        default=None,
        help="Optional regex matching section header lines. Default heuristic: "
             "ALL-CAPS line of length ≥5.",
    )
    ap.add_argument("--llm-provider", default="openai", choices=["openai", "anthropic"])
    ap.add_argument("--llm-model", default=None)
    ap.add_argument(
        "--min-words",
        type=int,
        default=50,
        help="Minimum word count to score a section (default 50; shorter "
             "sections are reported but not flagged for outlier analysis).",
    )
    args = ap.parse_args()

    with open(args.document, "r", encoding="utf-8") as fp:
        text = fp.read()

    sections = split_sections(text, args.section_regex)
    print(f"Detected {len(sections)} sections.", file=sys.stderr)

    rows: List[Dict] = []
    for s in sections:
        wc = len(s["body"].split())
        row: Dict = {
            "label": s["label"],
            "word_count": wc,
            "scored": wc >= args.min_words,
        }
        if row["scored"]:
            for inst in args.instruments:
                print(f"  Scoring '{s['label'][:40]}' under {inst}...", file=sys.stderr)
                row[inst] = score_section_with(
                    inst, s["body"],
                    llm_provider=args.llm_provider,
                    llm_model=args.llm_model,
                )
        rows.append(row)

    # Find the rank-lowest substantive section under each instrument
    rank_lowest: Dict[str, str] = {}
    for inst in args.instruments:
        scored_rows = [r for r in rows if r.get("scored")]
        if not scored_rows:
            continue
        lowest = min(scored_rows, key=lambda r: r[inst])
        rank_lowest[inst] = lowest["label"]

    # Cross-instrument unanimous flag. Requires at least two
    # instruments — a single-instrument run is not "unanimous across
    # instruments."
    unanimous_lowest = (
        len(args.instruments) >= 2
        and len(set(rank_lowest.values())) == 1
        and len(rank_lowest) == len(args.instruments)
    )

    summary = {
        "document_path": args.document,
        "n_sections": len(sections),
        "min_words_to_score": args.min_words,
        "instruments": list(args.instruments),
        "sections": rows,
        "rank_lowest_per_instrument": rank_lowest,
        "rank_lowest_unanimous": unanimous_lowest,
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)
    print(f"\nWrote: {args.out}", file=sys.stderr)

    # Stderr table
    print("\nPER-SECTION SCORES", file=sys.stderr)
    print("=" * 96, file=sys.stderr)
    header = f"{'words':>6}  " + "  ".join(f"{inst:>10}" for inst in args.instruments) + "  label"
    print(header, file=sys.stderr)
    print("-" * 96, file=sys.stderr)
    for r in rows:
        marker = ""
        if r.get("scored") and any(r["label"] == v for v in rank_lowest.values()):
            marker = "  <<< RANK-LOWEST"
        scores = "  ".join(
            f"{r.get(inst, float('nan')):>+10.3f}" if r.get("scored") else f"{'  --':>10}"
            for inst in args.instruments
        )
        print(f"{r['word_count']:>6}  {scores}  {r['label'][:48]}{marker}", file=sys.stderr)
    print("=" * 96, file=sys.stderr)
    if unanimous_lowest:
        print(f"\nUNANIMOUS RANK-LOWEST: '{list(rank_lowest.values())[0]}' across all "
              f"{len(args.instruments)} instruments.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Plot paragraph-audit results.

Reads ``run_paragraph_audit`` JSON and renders a per-section plot — one
line per instrument, one tick per section, with the unanimous
rank-lowest section flagged.

Usage::

    python -m plots.plot_paragraph_audit \\
        --input out/paragraph_audit/scores.json \\
        --out-dir out/paragraph_audit
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import numpy as np

from plots.report_theme import (
    REPORT_COLORS,
    QUALITATIVE_PALETTE,
    apply_report_theme,
    save_publication_figure,
    style_axes,
)


def build_figure(data: dict) -> plt.Figure:
    sections = [s for s in data["sections"] if s.get("scored")]
    instruments = [i for i in data.get("instruments", []) if any(i in s for s in sections)]

    fig, ax = plt.subplots(figsize=(11.0, 5.5))
    x = np.arange(len(sections))
    labels = [s["label"][:24] for s in sections]

    for k, inst in enumerate(instruments):
        y = [s.get(inst, np.nan) for s in sections]
        color = QUALITATIVE_PALETTE[k % len(QUALITATIVE_PALETTE)]
        ax.plot(x, y, marker="o", label=inst, color=color,
                markersize=7, linewidth=1.6,
                markeredgecolor=REPORT_COLORS["background"], markeredgewidth=1.0)

    ax.axhline(0, color=REPORT_COLORS["ink_soft"], linewidth=0.8, alpha=0.6)

    rank_lowest = data.get("rank_lowest_per_instrument") or {}
    unanimous = data.get("rank_lowest_unanimous", False)
    if unanimous and rank_lowest:
        target = list(rank_lowest.values())[0]
        for i, s in enumerate(sections):
            if s["label"] == target:
                ax.axvline(i, color=REPORT_COLORS["threshold"],
                           linestyle="--", linewidth=1.2, alpha=0.8, zorder=0)
                ax.text(i, ax.get_ylim()[1] * 0.95,
                        "rank-lowest\nunanimous",
                        ha="center", va="top", fontsize=9.5,
                        color=REPORT_COLORS["threshold"], fontweight="semibold")
                break

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Compound sentiment score")
    style_axes(ax, gridaxis="y")
    ax.legend(loc="lower right", fontsize=10)

    fig.text(0.02, 0.96,
             "Paragraph-by-paragraph audit — per-section sentiment under multiple instruments",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.93,
             "A section that is rank-lowest under every instrument is the "
             "section a section-aware extraction architecture would surface.",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")
    fig.tight_layout(rect=(0, 0.02, 1, 0.91))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="paragraph_audit_per_section")
    args = ap.parse_args()

    apply_report_theme()
    with open(args.input) as fp:
        data = json.load(fp)
    fig = build_figure(data)
    written = save_publication_figure(fig, args.name, output_dir=Path(args.out_dir))
    plt.close(fig)
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

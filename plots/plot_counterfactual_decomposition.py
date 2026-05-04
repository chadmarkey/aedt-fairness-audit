"""Plot counterfactual-decomposition results.

Reads ``counterfactual_decomposition.json`` and renders, for each axis,
a paired dot plot of original vs marker-stripped DI per question. Lines
between the dots show the magnitude of the marker-stripping effect.

Usage::

    python -m plots.plot_counterfactual_decomposition \\
        --input out/counterfactual/counterfactual_decomposition.json \\
        --out-dir out/counterfactual
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
    apply_report_theme,
    save_publication_figure,
    style_axes,
    threshold_label,
)


AXES = ["gender", "race", "school_tier"]


def build_figure(data: dict) -> plt.Figure:
    decomposition = data["decomposition"]
    questions = list(decomposition.keys())

    fig, axes = plt.subplots(1, len(AXES), figsize=(13.5, 5.5), sharey=True)

    for ax_idx, axis in enumerate(AXES):
        ax = axes[ax_idx]
        ax.axhspan(0, 0.80, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)
        ax.axhspan(1.25, 2.5, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)

        for i, q in enumerate(questions):
            orig = decomposition[q]["original"][axis]["disparate_impact"]
            strip = decomposition[q]["stripped"][axis]["disparate_impact"]
            ax.plot([i - 0.18, i + 0.18], [orig, strip],
                    color=REPORT_COLORS["ink_soft"], linewidth=1.3, zorder=1)
            ax.plot(i - 0.18, orig, "o",
                    color=REPORT_COLORS["accent"], markersize=8,
                    markeredgecolor=REPORT_COLORS["background"], markeredgewidth=1.4,
                    zorder=3)
            ax.plot(i + 0.18, strip, "s",
                    color=REPORT_COLORS["highlight"], markersize=8,
                    markeredgecolor=REPORT_COLORS["background"], markeredgewidth=1.4,
                    zorder=3)

        ax.axhline(1.0, color=REPORT_COLORS["ink_soft"], linewidth=0.8, alpha=0.7)
        if ax_idx == 0:
            threshold_label(ax, 0.80, "EEOC 4/5 (0.80)",
                            orient="h", xfrac=0.02, yfrac=0.18)
        ax.set_xticks(range(len(questions)))
        ax.set_xticklabels(questions, rotation=30, ha="right")
        ax.set_title(f"axis: {axis}", fontsize=11, color=REPORT_COLORS["ink"])
        if ax_idx == 0:
            ax.set_ylabel("Disparate-impact ratio")
        style_axes(ax, gridaxis="y")

    # Shared legend in the first subplot
    axes[0].plot([], [], "o", color=REPORT_COLORS["accent"], label="Original")
    axes[0].plot([], [], "s", color=REPORT_COLORS["highlight"], label="Marker-stripped")
    axes[0].legend(loc="upper right", fontsize=10)

    axes[0].set_ylim(0, 2.0)
    fig.text(0.02, 0.96,
             "Counterfactual decomposition — original vs marker-stripped DI",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.93,
             "Marker-stripped runs the BiasMitigator (Claim 1 input-side anonymization) "
             "before re-scoring with the same LLM extractor.",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")
    fig.tight_layout(rect=(0, 0.02, 1, 0.91))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="counterfactual_decomposition")
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

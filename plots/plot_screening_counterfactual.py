"""Plot screening-with-counterfactual results.

Reads the JSON written by ``tools.run_screening_with_counterfactual`` and
renders a grouped bar chart: per anchoring (× model), the baseline DI
next to the counterfactual DI, with EEOC four-fifths bounds shaded.

If multiple models are present in the input, each becomes its own panel.

Usage::

    python -m plots.plot_screening_counterfactual \\
        --input out/screening_counterfactual/results.json \\
        --out-dir out/screening_counterfactual
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import numpy as np

from plots.report_theme import (
    REPORT_COLORS,
    add_sample_size_note,
    apply_report_theme,
    save_publication_figure,
    style_axes,
)


def build_figure(data: dict) -> plt.Figure:
    by_model: dict[str, list[dict]] = defaultdict(list)
    for cell in data["results"]:
        by_model[cell["model"]].append(cell)

    n_models = len(by_model)
    # 2×2 grid for 4 models, 1×n for fewer
    if n_models <= 2:
        nrows, ncols = 1, n_models
        figsize = (max(8.0, 5.5 * n_models), 6.0)
    elif n_models <= 4:
        nrows, ncols = 2, 2
        figsize = (12.0, 11.0)
    else:
        nrows, ncols = 2, (n_models + 1) // 2
        figsize = (5.5 * ncols, 11.0)

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=figsize,
        sharey=True,
        squeeze=False,
    )
    axes = axes.flatten()

    for ax_idx, (model_name, cells) in enumerate(by_model.items()):
        ax = axes[ax_idx]

        ax.axhspan(0, 0.80, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)
        ax.axhspan(1.25, 100, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)

        labels = [c["anchoring"]["label"] for c in cells]
        base_di = [c["stages"]["baseline"]["disparate_impact"]["point"] for c in cells]
        base_lo = [c["stages"]["baseline"]["disparate_impact"]["ci_lo"] for c in cells]
        base_hi = [c["stages"]["baseline"]["disparate_impact"]["ci_hi"] for c in cells]
        cf_di = [c["stages"]["counterfactual"]["disparate_impact"]["point"] for c in cells]
        cf_lo = [c["stages"]["counterfactual"]["disparate_impact"]["ci_lo"] for c in cells]
        cf_hi = [c["stages"]["counterfactual"]["disparate_impact"]["ci_hi"] for c in cells]

        x = np.arange(len(labels))
        width = 0.36

        ax.bar(x - width / 2, base_di, width=width,
               color=REPORT_COLORS["accent"],
               edgecolor=REPORT_COLORS["background"], linewidth=1, zorder=2,
               label="Baseline")
        ax.bar(x + width / 2, cf_di, width=width,
               color=REPORT_COLORS["accent_alt"],
               edgecolor=REPORT_COLORS["background"], linewidth=1, zorder=2,
               label="Counterfactual\n(sentiment-only intervention)")

        ax.errorbar(
            x - width / 2, base_di,
            yerr=[np.subtract(base_di, base_lo), np.subtract(base_hi, base_di)],
            fmt="none", ecolor=REPORT_COLORS["ink_soft"], elinewidth=1.2, capsize=3, zorder=3,
        )
        ax.errorbar(
            x + width / 2, cf_di,
            yerr=[np.subtract(cf_di, cf_lo), np.subtract(cf_hi, cf_di)],
            fmt="none", ecolor=REPORT_COLORS["ink_soft"], elinewidth=1.2, capsize=3, zorder=3,
        )

        for i, (b, c) in enumerate(zip(base_di, cf_di)):
            ax.text(i - width / 2, b + 0.03, f"{b:.3f}",
                    ha="center", va="bottom", fontsize=9, color=REPORT_COLORS["ink"])
            ax.text(i + width / 2, c + 0.03, f"{c:.3f}",
                    ha="center", va="bottom", fontsize=9, color=REPORT_COLORS["ink"])

        ax.axhline(1.0, color=REPORT_COLORS["ink_soft"], linewidth=0.8, alpha=0.7)
        ax.axhline(0.80, color=REPORT_COLORS["threshold"],
                   linestyle="--", linewidth=1.2, alpha=0.85)
        ax.axhline(1.25, color=REPORT_COLORS["threshold"],
                   linestyle="--", linewidth=1.2, alpha=0.85)

        if ax_idx == 0:
            ax.set_ylabel("Disparate-impact ratio (1.0 = parity)")
            ax.legend(loc="upper left", fontsize=9, frameon=False)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=9)
        ax.set_title(f"model: {model_name}", fontsize=11, color=REPORT_COLORS["ink"])
        style_axes(ax, gridaxis="y")

    axes[0].set_ylim(0, max(2.0,
        max(c["stages"]["baseline"]["disparate_impact"]["ci_hi"]
            for cs in by_model.values() for c in cs) * 1.1))

    fig.text(0.02, 0.96,
             f"Screening simulation with sentiment-only counterfactual "
             f"(n = {data.get('n_per_replicate'):,} per replicate)",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.93,
             "Baseline = both groups at their own sentiment anchoring. "
             "Counterfactual = Group 0 reassigned to the high-sentiment distribution.",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")

    add_sample_size_note(
        fig,
        f"n = {data.get('bootstrap_reps')} bootstrap resamples per cell; "
        f"error bars show 95% CI. SD = {data.get('narrative_sd')}.",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.91))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="screening_counterfactual")
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

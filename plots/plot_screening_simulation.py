"""Plot screening-simulation results.

Reads ``screening_simulation_results.json`` (per-anchoring DI metrics)
and renders a forest-style plot — one row per anchoring, x = DI,
horizontal error bars = bootstrap CI, EEOC threshold marked.

Usage::

    python -m plots.plot_screening_simulation \\
        --input out/screening_simulation/screening_simulation_results.json \\
        --out-dir out/screening_simulation
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
    add_sample_size_note,
    apply_report_theme,
    save_publication_figure,
    style_axes,
    threshold_label,
)


def extract_anchorings(data: dict) -> list[dict]:
    """Each anchoring should expose a DI point + CI.

    Matches the ``tools.run_screening_simulation`` output:
    {results: {label: {anchoring: {...}, metrics: {disparate_impact: {point, ci_lo, ci_hi}}}}}
    """
    rows: list[dict] = []
    results = data.get("results") or data.get("anchorings") or data
    if isinstance(results, dict):
        for label, v in results.items():
            if not isinstance(v, dict):
                continue
            metrics = v.get("metrics") or v
            di_block = metrics.get("disparate_impact")
            if isinstance(di_block, dict):
                di, lo, hi = di_block.get("point"), di_block.get("ci_lo"), di_block.get("ci_hi")
            else:
                di = di_block
                lo, hi = None, None
            if di is None:
                continue
            rows.append(dict(label=str(label), di=float(di),
                             ci_lo=float(lo) if lo is not None else float(di),
                             ci_hi=float(hi) if hi is not None else float(di)))
    return rows


def build_figure(rows: list[dict], n_reps: int) -> plt.Figure:
    rows = sorted(rows, key=lambda r: r["di"])
    fig, ax = plt.subplots(figsize=(11.0, max(4.5, 0.55 * len(rows) + 2.5)))

    # EEOC 4/5 failure regions: DI < 0.80 or DI > 1.25
    ax.axvspan(0, 0.80, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)
    ax.axvspan(1.25, 100, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)

    y = np.arange(len(rows))
    di = np.array([r["di"] for r in rows])
    lo = np.array([r["ci_lo"] for r in rows])
    hi = np.array([r["ci_hi"] for r in rows])

    ax.errorbar(
        di, y,
        xerr=[di - lo, hi - di],
        fmt="o", color=REPORT_COLORS["accent"],
        ecolor=REPORT_COLORS["ink_soft"], elinewidth=1.5, capsize=4,
        markersize=8, markeredgecolor=REPORT_COLORS["background"], markeredgewidth=1.5,
        zorder=3,
    )

    # Place DI labels to the LEFT of the error bar's right end so they don't
    # collide with the threshold line at 0.80
    for i, (d, h) in enumerate(zip(di, hi)):
        ax.text(h + 0.03, i, f"{d:.3f}", va="center", ha="left",
                fontsize=10, color=REPORT_COLORS["ink"], fontweight="semibold")

    ax.axvline(1.0, color=REPORT_COLORS["ink_soft"], linewidth=0.8, alpha=0.7)

    # Threshold lines without overlapping text labels
    ax.axvline(0.80, color=REPORT_COLORS["threshold"],
               linestyle="--", linewidth=1.4, alpha=0.85)
    ax.axvline(1.25, color=REPORT_COLORS["threshold"],
               linestyle="--", linewidth=1.4, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels([r["label"] for r in rows])
    ax.set_xlabel("Disparate-impact ratio")
    x_max = max(hi.max(), 1.4) * 1.12
    ax.set_xlim(-0.02, x_max)
    style_axes(ax, gridaxis="x")

    # Threshold + parity labels above the plot area to avoid data collision
    ymax = len(rows) - 0.4
    ax.text(0.80, ymax + 0.4, "0.80\n(EEOC 4/5)",
            ha="center", va="bottom", fontsize=9,
            color=REPORT_COLORS["threshold"], fontweight="medium",
            linespacing=1.1)
    ax.text(1.0, ymax + 0.4, "1.00\nparity",
            ha="center", va="bottom", fontsize=9,
            color=REPORT_COLORS["ink_soft"], fontstyle="italic",
            linespacing=1.1)
    ax.text(1.25, ymax + 0.4, "1.25\n(EEOC 4/5)",
            ha="center", va="bottom", fontsize=9,
            color=REPORT_COLORS["threshold"], fontweight="medium",
            linespacing=1.1)
    ax.set_ylim(-0.6, ymax + 1.1)

    fig.text(0.02, 0.96,
             "Screening simulation — disparate impact by sentiment-instrument anchoring",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.93,
             "Each row is one anchoring's DI point estimate with 95% bootstrap CI.",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")
    add_sample_size_note(fig, f"n = {n_reps} bootstrap resamples per anchoring.")
    fig.tight_layout(rect=(0, 0.04, 1, 0.91))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="screening_simulation_forest")
    args = ap.parse_args()

    apply_report_theme()
    with open(args.input) as fp:
        data = json.load(fp)
    rows = extract_anchorings(data)
    if not rows:
        print("No anchorings extracted from JSON; check the input shape.", file=sys.stderr)
        return 2
    n_reps = int(data.get("bootstrap_reps", data.get("n_bootstrap", 0)))
    fig = build_figure(rows, n_reps)
    written = save_publication_figure(fig, args.name, output_dir=Path(args.out_dir))
    plt.close(fig)
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

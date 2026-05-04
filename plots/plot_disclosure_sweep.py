"""Plot disclosure-rate sweep results.

Reads the JSON written by ``tools.run_disclosure_sweep`` and renders
disparate impact as a function of disclosure rate, with bootstrap CI
band, EEOC four-fifths threshold, and the realistic disclosure range
(5–15%) marked.

Usage::

    python -m plots.plot_disclosure_sweep \\
        --input out/disclosure_sweep/results.json \\
        --out-dir out/disclosure_sweep
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
import pandas as pd
import seaborn as sns

from plots.report_theme import (
    REPORT_COLORS,
    add_sample_size_note,
    apply_report_theme,
    save_publication_figure,
    style_axes,
    threshold_label,
)


def load_sweep(json_path: str) -> tuple[pd.DataFrame, dict]:
    with open(json_path) as fp:
        data = json.load(fp)
    rows = []
    for _, v in data["results"].items():
        rows.append(dict(
            disclosure_rate=v["disclosure_rate"] * 100,
            di_point=v["baseline_disparate_impact"]["point"],
            ci_lo=v["baseline_disparate_impact"]["ci_lo"],
            ci_hi=v["baseline_disparate_impact"]["ci_hi"],
        ))
    df = pd.DataFrame(rows).sort_values("disclosure_rate").reset_index(drop=True)
    return df, data


def build_figure(df: pd.DataFrame, meta: dict) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10.0, 6.0))

    # Realistic disclosure-rate band (5-15%)
    ax.axvspan(5, 15, color=REPORT_COLORS["highlight"], alpha=0.18, zorder=0)

    # CI band
    ax.fill_between(
        df["disclosure_rate"], df["ci_lo"], df["ci_hi"],
        color=REPORT_COLORS["accent_soft"], alpha=0.30, linewidth=0,
        zorder=1, label="95% bootstrap CI",
    )

    # Median line
    sns.lineplot(
        data=df, x="disclosure_rate", y="di_point",
        marker="o", markersize=8, linewidth=2.4,
        color=REPORT_COLORS["accent"], ax=ax, zorder=3,
        label="DI point estimate",
    )
    for line in ax.get_lines():
        line.set_markerfacecolor(REPORT_COLORS["accent"])
        line.set_markeredgecolor(REPORT_COLORS["background"])
        line.set_markeredgewidth(1.5)

    # Value labels
    for _, row in df.iterrows():
        offset = 0.05 if row["di_point"] < 0.85 else -0.07
        ax.text(row["disclosure_rate"], row["di_point"] + offset,
                f"{row['di_point']:.2f}",
                ha="center", va="bottom" if offset > 0 else "top",
                fontsize=9.5, fontweight="semibold",
                color=REPORT_COLORS["ink"])

    # Realistic-range annotation
    ax.text(
        10, 0.42, "Realistic\noperating range\n(5–15%)",
        fontsize=10, color=REPORT_COLORS["ink_soft"],
        ha="center", va="top", linespacing=1.25,
    )

    # Parity line
    ax.axhline(1.0, color=REPORT_COLORS["ink_soft"], linewidth=0.8, alpha=0.7)
    ax.text(2, 1.012, "parity",
            color=REPORT_COLORS["ink_soft"], fontsize=9,
            fontstyle="italic", va="bottom", ha="left")

    threshold_label(ax, 0.80, "EEOC four-fifths threshold (0.80)",
                    orient="h", xfrac=0.02, yfrac=0.83)

    style_axes(ax, gridaxis="y")
    ax.set_xlim(-3, 105)
    ax.set_ylim(0, 1.15)
    ax.set_xlabel("Protected-class disclosure detection rate (% of Group 0 applicants)")
    ax.set_ylabel("Disparate-impact ratio (1.0 = parity)")

    fig.text(0.02, 0.96,
             "Disclosure-rate sweep — DI as a function of protected-class detection rate",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    anchoring = meta.get("anchoring_label", "")
    if anchoring:
        fig.text(0.02, 0.93,
                 f"Anchoring: {anchoring} "
                 f"(low={meta.get('mean_low'):.2f}, high={meta.get('mean_high'):.2f}). "
                 f"At realistic disclosure (5–15%), the vendor's protected-class control "
                 f"reaches a small fraction of impacted applicants.",
                 fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")

    ax.legend(loc="lower right", fontsize=10, frameon=False)
    add_sample_size_note(
        fig,
        f"n = {meta.get('bootstrap_reps')} bootstrap resamples per rate; "
        f"band shows 95% bootstrap CI.",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.91))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="disclosure_rate_sweep")
    args = ap.parse_args()

    apply_report_theme()
    df, meta = load_sweep(args.input)
    fig = build_figure(df, meta)
    written = save_publication_figure(fig, args.name, output_dir=Path(args.out_dir))
    plt.close(fig)
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

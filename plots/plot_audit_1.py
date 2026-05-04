"""Plot Audit 1 (Bias Mitigator efficacy) results.

Reads ``audit_1_results.json`` (or ``*_reps1000.json``) and renders a
grouped bar chart of baseline vs post-mitigation DI per demographic
axis with bootstrap CIs and the EEOC four-fifths threshold marked.

Usage::

    python -m plots.plot_audit_1 \\
        --input out/audit_1/audit_1_reps1000.json \\
        --out-dir out/audit_1
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


def _normalize_results(data: dict) -> tuple[dict, dict, int]:
    """Accept either run_audit_1 or rebootstrap-style JSON."""
    if "baseline" in data and "post_mitigation" in data:
        return data["baseline"], data["post_mitigation"], int(data.get("bootstrap_reps", 0))
    if "results_per_score_col" in data:
        cols = data["results_per_score_col"]
        return cols["score_baseline"], cols["score_mitigated"], int(data.get("bootstrap_reps", 0))
    raise ValueError("Unrecognized JSON shape")


def build_figure(baseline: dict, post: dict, n_reps: int) -> plt.Figure:
    axes = list(baseline.keys())
    base_di = [baseline[a]["disparate_impact"] for a in axes]
    post_di = [post[a]["disparate_impact"] for a in axes]
    base_lo = [baseline[a]["bootstrap_di_ci_lo"] for a in axes]
    base_hi = [baseline[a]["bootstrap_di_ci_hi"] for a in axes]
    post_lo = [post[a]["bootstrap_di_ci_lo"] for a in axes]
    post_hi = [post[a]["bootstrap_di_ci_hi"] for a in axes]

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    # EEOC 4/5 rule is symmetric: DI < 0.80 OR DI > 1.25 indicates adverse impact.
    # Shade BOTH failure regions.
    ax.axhspan(0, 0.80, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)
    ax.axhspan(1.25, 100, color=REPORT_COLORS["threshold"], alpha=0.06, zorder=0)

    x = np.arange(len(axes))
    width = 0.36
    ax.bar(x - width / 2, base_di, width=width,
           color=REPORT_COLORS["accent"], label="Baseline",
           edgecolor=REPORT_COLORS["background"], linewidth=1, zorder=2)
    ax.bar(x + width / 2, post_di, width=width,
           color=REPORT_COLORS["accent_alt"], label="Post-mitigation",
           edgecolor=REPORT_COLORS["background"], linewidth=1, zorder=2)

    ax.errorbar(
        x - width / 2, base_di,
        yerr=[np.subtract(base_di, base_lo), np.subtract(base_hi, base_di)],
        fmt="none", ecolor=REPORT_COLORS["ink_soft"], elinewidth=1.2, capsize=3, zorder=3,
    )
    ax.errorbar(
        x + width / 2, post_di,
        yerr=[np.subtract(post_di, post_lo), np.subtract(post_hi, post_di)],
        fmt="none", ecolor=REPORT_COLORS["ink_soft"], elinewidth=1.2, capsize=3, zorder=3,
    )

    for i, (b, p) in enumerate(zip(base_di, post_di)):
        ax.text(i - width / 2, b + 0.04, f"{b:.3f}",
                ha="center", va="bottom", fontsize=9.5, color=REPORT_COLORS["ink"])
        ax.text(i + width / 2, p + 0.04, f"{p:.3f}",
                ha="center", va="bottom", fontsize=9.5, color=REPORT_COLORS["ink"])

    ax.axhline(1.0, color=REPORT_COLORS["ink_soft"], linewidth=0.8, alpha=0.7)
    # Plain threshold lines; labels placed at the right margin to avoid data overlap
    ax.axhline(0.80, color=REPORT_COLORS["threshold"],
               linestyle="--", linewidth=1.4, alpha=0.85)
    ax.axhline(1.25, color=REPORT_COLORS["threshold"],
               linestyle="--", linewidth=1.4, alpha=0.85)

    style_axes(ax, gridaxis="y")
    ax.set_xticks(x)
    ax.set_xticklabels(axes)
    ax.set_ylabel("Disparate-impact ratio (1.0 = parity)")
    ax.set_xlabel("Demographic axis")
    ymax = max(max(base_hi), max(post_hi), 1.5) * 1.08
    ax.set_ylim(0, ymax)
    ax.legend(loc="upper right", fontsize=10)

    # Threshold labels in the failure regions, well outside the data area
    ax.text(len(axes) - 0.5, 0.40, "EEOC 4/5\nlower bound\n(0.80)",
            ha="right", va="center", fontsize=9,
            color=REPORT_COLORS["threshold"], fontweight="medium",
            linespacing=1.15)
    ax.text(len(axes) - 0.5, ymax - (ymax - 1.25) / 2, "EEOC 4/5\nupper bound\n(1.25)",
            ha="right", va="center", fontsize=9,
            color=REPORT_COLORS["threshold"], fontweight="medium",
            linespacing=1.15)
    ax.text(-0.5, 1.0, "parity",
            color=REPORT_COLORS["ink_soft"], fontsize=9,
            fontstyle="italic", va="center", ha="left")

    fig.text(0.02, 0.95,
             "Audit 1 — Bias Mitigator efficacy (Claim 1, input-side anonymization)",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.91,
             "Baseline vs post-mitigation disparate impact per demographic axis",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")

    add_sample_size_note(fig, f"n = {n_reps} bootstrap resamples per axis; bars show 95% bootstrap CI.")
    fig.tight_layout(rect=(0, 0.04, 1, 0.89))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="audit_1_di_by_axis")
    args = ap.parse_args()

    apply_report_theme()
    with open(args.input) as fp:
        data = json.load(fp)
    baseline, post, n_reps = _normalize_results(data)
    fig = build_figure(baseline, post, n_reps)
    written = save_publication_figure(fig, args.name, output_dir=Path(args.out_dir))
    plt.close(fig)
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Plot Audit 2 (PS four-question extraction) results.

Reads ``audit_2_results_{sbert,llm}.json`` (or ``*_reps1000.json``) and
renders a heatmap of per-question DI by demographic axis, plus a row for
the aggregate score.

Usage::

    python -m plots.plot_audit_2 \\
        --input out/audit_2/audit_2_results_llm_reps1000.json \\
        --out-dir out/audit_2 --name audit_2_llm_di_heatmap
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
    threshold_label,
)


AXES_ORDER = ["gender", "race", "school_tier"]
QUESTION_ORDER = ["poverty", "refugee", "major_illness", "academic_career", "_total"]


def _normalize(data: dict) -> tuple[dict, int]:
    """Accept either run_audit_2 or rebootstrap-style JSON.

    Returns: dict[score_col_name -> dict[axis -> {disparate_impact, ...}]], n_reps
    """
    if "per_question" in data and "aggregate" in data:
        out = dict(data["per_question"])
        out["_total"] = data["aggregate"]
        return out, int(data.get("bootstrap_reps", 0))
    if "results_per_score_col" in data:
        return data["results_per_score_col"], int(data.get("bootstrap_reps", 0))
    raise ValueError("Unrecognized JSON shape")


def build_figure(per_score: dict, n_reps: int, title_suffix: str = "") -> plt.Figure:
    rows = [c for c in QUESTION_ORDER if c in per_score]
    matrix = np.full((len(rows), len(AXES_ORDER)), np.nan)
    for i, r in enumerate(rows):
        for j, a in enumerate(AXES_ORDER):
            if a in per_score[r]:
                matrix[i, j] = per_score[r][a]["disparate_impact"]

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    # Diverging around 1.0; cap visualization at [0, 2.0]
    norm = plt.matplotlib.colors.TwoSlopeNorm(vmin=0.0, vcenter=1.0, vmax=2.0)
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list(
        "audit",
        [REPORT_COLORS["threshold"], REPORT_COLORS["background"], REPORT_COLORS["accent"]],
        N=256,
    )
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, norm=norm)

    for i in range(len(rows)):
        for j in range(len(AXES_ORDER)):
            v = matrix[i, j]
            if np.isnan(v):
                txt = "N/A"
            else:
                txt = f"{v:.3f}"
            color = REPORT_COLORS["ink"] if 0.5 < v < 1.6 else REPORT_COLORS["background"]
            ax.text(j, i, txt, ha="center", va="center",
                    color=color, fontsize=10.5, fontweight="semibold")
            # Failure marker
            if not np.isnan(v) and v < 0.80:
                ax.text(j, i + 0.32, "fails 4/5",
                        ha="center", va="center",
                        color=REPORT_COLORS["threshold"],
                        fontsize=8, fontstyle="italic")

    ax.set_xticks(range(len(AXES_ORDER)))
    ax.set_xticklabels(AXES_ORDER)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    ax.set_xlabel("Demographic axis")
    ax.set_ylabel("PS question / aggregate")

    cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cbar.set_label("Disparate-impact ratio", fontsize=10)
    cbar.ax.axhline(0.80, color=REPORT_COLORS["threshold"], linewidth=1.2, linestyle="--")
    cbar.ax.axhline(1.25, color=REPORT_COLORS["threshold"], linewidth=1.2, linestyle="--")

    fig.text(0.02, 0.95,
             f"Audit 2 — PS four-question extraction{title_suffix}",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.91,
             "Per-question and aggregate disparate impact by demographic axis. "
             "Cells outside [0.80, 1.25] fail EEOC four-fifths.",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")

    add_sample_size_note(fig, f"n = {n_reps} bootstrap resamples per cell.")
    fig.tight_layout(rect=(0, 0.04, 1, 0.88))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="audit_2_di_heatmap")
    ap.add_argument("--title-suffix", default="")
    args = ap.parse_args()

    apply_report_theme()
    with open(args.input) as fp:
        data = json.load(fp)
    per_score, n_reps = _normalize(data)
    fig = build_figure(per_score, n_reps, args.title_suffix)
    written = save_publication_figure(fig, args.name, output_dir=Path(args.out_dir))
    plt.close(fig)
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

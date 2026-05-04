"""Plot content-equivalence validation results.

Reads ``content_equivalence/results.json`` and renders the cosine-distance
distribution at three nesting levels (within seed within stratum, within
seed across stratum, across seed) as a box+strip plot. Includes the
within/across ratio as the headline annotation.

Usage::

    python -m plots.plot_content_equivalence \\
        --input out/content_equivalence/results.json \\
        --out-dir out/content_equivalence
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
)


LEVELS = [
    ("within_seed_within_stratum", "Within seed,\nwithin stratum"),
    ("within_seed_across_stratum", "Within seed,\nacross stratum"),
    ("across_seed", "Across seed"),
]


def build_figure(data: dict) -> plt.Figure:
    overall = data["overall"]
    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    centers = np.arange(len(LEVELS))
    means = [overall[k]["mean"] for k, _ in LEVELS]
    medians = [overall[k]["median"] for k, _ in LEVELS]
    p10 = [overall[k]["p10"] for k, _ in LEVELS]
    p90 = [overall[k]["p90"] for k, _ in LEVELS]
    ns = [overall[k]["n"] for k, _ in LEVELS]

    palette = [REPORT_COLORS["accent"], REPORT_COLORS["highlight"], REPORT_COLORS["accent_alt"]]
    width = 0.55

    # IQR-style box (p10-p90) + median tick + mean dot
    for i, c in enumerate(centers):
        ax.bar(c, p90[i] - p10[i], bottom=p10[i], width=width,
               color=palette[i], alpha=0.55,
               edgecolor=REPORT_COLORS["background"], linewidth=1, zorder=2)
        ax.plot([c - width / 2, c + width / 2], [medians[i]] * 2,
                color=REPORT_COLORS["ink"], linewidth=2.2, zorder=3)
        ax.plot(c, means[i], "o", color=REPORT_COLORS["ink"],
                markersize=6, markeredgecolor=REPORT_COLORS["background"], zorder=4)
        ax.text(c, p90[i] + 0.012, f"mean {means[i]:.3f}\nn = {ns[i]:,}",
                ha="center", va="bottom", fontsize=9.5,
                color=REPORT_COLORS["ink_soft"], linespacing=1.2)

    ax.set_xticks(centers)
    ax.set_xticklabels([label for _, label in LEVELS])
    ax.set_ylabel("Cosine distance (lower = more similar)")
    style_axes(ax, gridaxis="y")

    ratio = means[1] / means[2] if means[2] else float("nan")
    fig.text(0.02, 0.96,
             "Content equivalence — embedding distance at three nesting levels",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.93,
             f"Within-seed-across-stratum / across-seed = {ratio:.3f}. "
             f"Demographic-marker drift is {ratio * 100:.1f}% of seed-level content drift.",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")

    fig.tight_layout(rect=(0, 0.02, 1, 0.91))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="content_equivalence_box")
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

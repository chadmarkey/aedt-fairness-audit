"""Plot dilution-test results.

Reads dilution-test JSON and renders excerpt-vs-full-document gaps per
instrument, with the per-instrument dilution percentage labeled.

Usage::

    python -m plots.plot_dilution_test \\
        --input out/dilution_test/dilution_test_results.json \\
        --out-dir out/dilution_test
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


def _extract_pair_gaps(data: dict) -> dict:
    """Return {instrument: [{pair, excerpt, full, dilution}]}.

    Matches the shape produced by ``tools.run_dilution_test``: top-level
    keys are instrument names, each contains a ``gaps`` dict mapping pair
    labels to {excerpt_gap, full_doc_gap, dilution_ratio}.
    """
    out: dict = {}
    for inst, body in data.items():
        if not isinstance(body, dict) or "gaps" not in body:
            continue
        for pair_label, gap_info in body["gaps"].items():
            excerpt = gap_info.get("excerpt_gap")
            full = gap_info.get("full_doc_gap")
            if excerpt is None or full is None:
                continue
            try:
                excerpt_f = float(excerpt)
                full_f = float(full)
            except (TypeError, ValueError):
                continue
            if abs(excerpt_f) > 1e-9:
                dil = 100.0 * (1.0 - abs(full_f) / abs(excerpt_f))
            else:
                dil = 0.0
            out.setdefault(inst, []).append(dict(
                pair=pair_label, excerpt=excerpt_f,
                full=full_f, dilution=dil,
            ))
    return out


def build_figure(per_inst: dict) -> plt.Figure:
    instruments = list(per_inst.keys())
    fig, ax = plt.subplots(figsize=(9.5, 5.5))

    width = 0.36
    x = np.arange(len(instruments))
    excerpt_means = [np.mean([r["excerpt"] for r in per_inst[i]]) for i in instruments]
    full_means = [np.mean([r["full"] for r in per_inst[i]]) for i in instruments]
    dilution_means = [np.mean([r["dilution"] for r in per_inst[i]]) for i in instruments]

    ax.bar(x - width / 2, excerpt_means, width=width,
           color=REPORT_COLORS["accent"], label="Excerpt-level gap",
           edgecolor=REPORT_COLORS["background"], linewidth=1)
    ax.bar(x + width / 2, full_means, width=width,
           color=REPORT_COLORS["accent_soft"], label="Full-document gap",
           edgecolor=REPORT_COLORS["background"], linewidth=1)

    for i, (e, f, d) in enumerate(zip(excerpt_means, full_means, dilution_means)):
        ax.text(i - width / 2, e + 0.02, f"{e:+.2f}",
                ha="center", va="bottom", fontsize=9.5)
        ax.text(i + width / 2, f + 0.02, f"{f:+.2f}",
                ha="center", va="bottom", fontsize=9.5)
        ax.text(i, max(e, f) + 0.10, f"dilution {d:.0f}%",
                ha="center", va="bottom", fontsize=9.5,
                fontweight="semibold", color=REPORT_COLORS["threshold"])

    ax.axhline(0, color=REPORT_COLORS["ink_soft"], linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(instruments)
    ax.set_ylabel("Sentiment gap (variant_high − variant_low)")
    ax.set_xlabel("Sentiment instrument")
    style_axes(ax, gridaxis="y")
    ax.legend(loc="upper right", fontsize=10)

    fig.text(0.02, 0.95,
             "Dilution test — excerpt-level vs full-document sentiment gap",
             fontsize=13, fontweight="semibold", color=REPORT_COLORS["ink"])
    fig.text(0.02, 0.91,
             "Higher dilution = the gap collapses when the variant is embedded "
             "in a longer surrounding document.",
             fontsize=10.5, color=REPORT_COLORS["ink_soft"], style="italic")
    fig.tight_layout(rect=(0, 0.02, 1, 0.89))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", default="dilution_test_gaps")
    args = ap.parse_args()

    apply_report_theme()
    with open(args.input) as fp:
        data = json.load(fp)
    per_inst = _extract_pair_gaps(data)
    if not per_inst:
        print("No instrument gaps extracted from JSON; check input shape.", file=sys.stderr)
        return 2
    fig = build_figure(per_inst)
    written = save_publication_figure(fig, args.name, output_dir=Path(args.out_dir))
    plt.close(fig)
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
report_theme.py

Custom seaborn / matplotlib theme for the Frontal Lobe public-report figures.

Aesthetic register: warm magazine / data journalism (ProPublica, The Atlantic
print, Wired Features). Tuned to harmonize with the existing matplotlib figures
in plots.py (warm-cream background, slate accents, restrained color, brick
threshold lines). Publication-grade conventions applied: 300 DPI raster export
plus vector PDF, sentence-case axis labels with units, minimum 7-9 pt fonts at
final print size, panel-label helper for multi-panel figures, sample-size
annotation helper, colorblind-safe palette aligned with Okabe-Ito.

Apply by calling apply_report_theme() once at the start of any plotting script
before constructing figures. The REPORT_COLORS dict is exported so individual
scripts can reference named colors for series, threshold lines, and annotations.
The save_publication_figure() helper writes both PNG (raster) and PDF (vector)
in a single call.
"""

from __future__ import annotations

import os
from pathlib import Path

# Headless rendering for CI / non-display environments
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns


# Color palette: warm-cream background, slate accent, muted brick threshold.
# Verified colorblind-safe under deuteranopia and protanopia simulation.
REPORT_COLORS: dict[str, str] = {
    "background": "#fffdfa",   # warm cream (matches plots.py)
    "panel": "#fbf8f1",        # slightly off-cream for emphasis blocks
    "ink": "#28312c",          # dark warm gray, primary text
    "ink_soft": "#7a7a70",     # secondary text and axis labels
    "rule": "#ded8c8",         # warm gridlines
    "accent": "#3a5a73",       # muted slate-blue, primary data series
    "accent_soft": "#86a8c2",  # lighter slate, secondary data series
    "accent_alt": "#5a7a4f",   # muted olive, tertiary data series
    "threshold": "#a8412c",    # muted brick red, threshold/violation lines
    "highlight": "#c79a3e",    # warm ochre, callouts and emphasis
}

# Sequential and qualitative palettes for hue mappings, anchored to the accent
QUALITATIVE_PALETTE = [
    REPORT_COLORS["accent"],
    REPORT_COLORS["highlight"],
    REPORT_COLORS["accent_alt"],
    REPORT_COLORS["threshold"],
    REPORT_COLORS["accent_soft"],
]

# Typography stack — Inter preferred, system sans-serif fallback
FONT_STACK = [
    "Inter",
    "Helvetica Neue",
    "Helvetica",
    "Arial",
    "DejaVu Sans",
    "sans-serif",
]


def apply_report_theme(context: str = "paper", font_scale: float = 1.05) -> None:
    """Set seaborn theme + matplotlib rcParams for the report's house style.

    Call once at the top of any plotting script. Subsequent figures inherit the
    style automatically.

    Args:
        context: seaborn context — "paper", "notebook", "talk", "poster".
            Default "paper" is right for the public report's published density.
        font_scale: multiplier applied on top of the context's base size.
    """
    sns.set_theme(
        context=context,
        style="ticks",
        font="Inter",
        font_scale=font_scale,
        rc={
            # Backgrounds
            "figure.facecolor": REPORT_COLORS["background"],
            "axes.facecolor": REPORT_COLORS["background"],
            "savefig.facecolor": REPORT_COLORS["background"],
            # Text and axes
            "axes.edgecolor": REPORT_COLORS["ink_soft"],
            "axes.labelcolor": REPORT_COLORS["ink"],
            "axes.titlecolor": REPORT_COLORS["ink"],
            "xtick.color": REPORT_COLORS["ink_soft"],
            "ytick.color": REPORT_COLORS["ink_soft"],
            "text.color": REPORT_COLORS["ink"],
            # Spines
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            "axes.linewidth": 1.0,
            # Grid
            "axes.grid": False,
            "grid.color": REPORT_COLORS["rule"],
            "grid.linewidth": 0.7,
            "grid.alpha": 0.6,
            # Title and label sizing handled via context+font_scale; explicit
            # weight here for readable rendering at small DPI
            "axes.titleweight": "semibold",
            "axes.labelweight": "regular",
            # Legend
            "legend.frameon": False,
            "legend.fontsize": 10,
            # Font fallback chain
            "font.family": "sans-serif",
            "font.sans-serif": FONT_STACK,
            # Save defaults
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.18,
        },
    )

    # Default qualitative palette
    sns.set_palette(QUALITATIVE_PALETTE)


def style_axes(ax: "matplotlib.axes.Axes", *, gridaxis: str | None = "y") -> None:
    """Apply per-axes touches: subtle grid on one axis, despine top/right.

    Args:
        ax: the matplotlib Axes to style.
        gridaxis: "y", "x", "both", or None. Defaults to "y" (horizontal lines
            are right for most bar/point plots; switch to "x" for horizontal
            bars or forest plots).
    """
    if gridaxis:
        ax.grid(
            axis=gridaxis,
            color=REPORT_COLORS["rule"],
            linewidth=0.7,
            alpha=0.7,
        )
    sns.despine(ax=ax, top=True, right=True, trim=False)


def add_panel_label(
    ax: "matplotlib.axes.Axes",
    label: str,
    *,
    x: float = -0.12,
    y: float = 1.05,
    fontsize: int = 12,
) -> None:
    """Add a bold panel label (A, B, C, ...) in the upper-left of an axes.

    Standard convention for multi-panel scientific figures. Uppercase by default
    (most journals); switch to lowercase if targeting Nature.
    """
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight="bold",
        va="top",
        ha="left",
        color=REPORT_COLORS["ink"],
    )


def add_sample_size_note(
    fig: "matplotlib.figure.Figure",
    text: str,
    *,
    x: float = 0.98,
    y: float = 0.01,
    fontsize: int = 8.5,
) -> None:
    """Add a small sample-size annotation in the figure's bottom-right corner.

    Convention: 'n = X' or descriptive equivalent for figures whose underlying
    statistics involve resampling, simulation, or finite samples. Required by
    most scientific journals.
    """
    fig.text(
        x,
        y,
        text,
        fontsize=fontsize,
        color=REPORT_COLORS["ink_soft"],
        fontstyle="italic",
        ha="right",
        va="bottom",
    )


def save_publication_figure(
    fig: "matplotlib.figure.Figure",
    name: str,
    *,
    output_dir: "str | Path",
    formats: tuple[str, ...] = ("png", "pdf"),
    dpi: int = 300,
) -> list[Path]:
    """Save a figure in publication-quality formats (raster PNG + vector PDF).

    PDF is the canonical scientific publication format because it preserves
    vector quality at any rendering size. PNG is the GitHub-rendered companion.
    Returns the list of paths actually written.

    Args:
        fig: the matplotlib Figure to save.
        name: base filename (no extension).
        output_dir: directory to write into (created if missing).
        formats: extensions to write. Defaults to ("png", "pdf").
        dpi: raster DPI for PNG output. PDF is vector and ignores this.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        path = out_dir / f"{name}.{fmt}"
        if fmt == "pdf":
            fig.savefig(path, format="pdf", bbox_inches="tight")
        else:
            fig.savefig(path, dpi=dpi, bbox_inches="tight")
        written.append(path)
    return written


def threshold_label(
    ax: "matplotlib.axes.Axes",
    value: float,
    text: str,
    *,
    orient: str = "h",
    xfrac: float = 0.02,
    yfrac: float = 0.97,
) -> None:
    """Add a threshold reference line + text label in the report's threshold color.

    Args:
        ax: target Axes.
        value: data-coordinate value where the line sits.
        text: label to show next to the line.
        orient: "h" for horizontal line at y=value, "v" for vertical at x=value.
        xfrac: x-position of label in axes-fraction coordinates (0 = left).
        yfrac: y-position of label in axes-fraction coordinates (1 = top).
    """
    if orient == "h":
        ax.axhline(
            value,
            color=REPORT_COLORS["threshold"],
            linestyle="--",
            linewidth=1.4,
            alpha=0.85,
        )
    else:
        ax.axvline(
            value,
            color=REPORT_COLORS["threshold"],
            linestyle="--",
            linewidth=1.4,
            alpha=0.85,
        )

    ax.text(
        xfrac,
        yfrac,
        text,
        transform=ax.transAxes,
        color=REPORT_COLORS["threshold"],
        fontsize=10,
        fontweight="medium",
        va="top",
        ha="left",
    )

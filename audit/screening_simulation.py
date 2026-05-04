"""Synthetic-applicant screening simulation with bootstrap CIs.

Generates n synthetic applicants stratified by binary protected group, where
the protected group differs only in the narrative-sentiment feature (a stand-in
for the "MSPE sentiment" or other narrative-derived score that an AEDT might
use). All other features are drawn from the same distribution for both groups.

Trains a screening model on the synthetic data, ranks applicants by predicted
probability, and reports per-group selection rates, disparate impact, and
related fairness metrics. Bootstraps over (DGP draw, train/test split) for
percentile CIs.

The user supplies the narrative-sentiment anchorings — typically two values
per sentiment instrument (the score the instrument assigns to the
disadvantaged-group narrative and the favored-group narrative). The
simulation answers: under those anchorings and a given screening pipeline,
what disparate impact does the top-K selection produce?

This is the harness that produces the headline DI numbers in any
sentiment-cascade audit. It does not require the user's actual narrative
text — only the sentiment scores extracted from that text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# Fairness-metric definitions follow AI Fairness 360 (AIF360) conventions.
# AIF360 itself is NOT a runtime dependency — the metrics here are
# reimplemented in numpy/pandas to keep installation light. Definitions:
# https://github.com/Trusted-AI/AIF360/blob/master/aif360/metrics/classification_metric.py
# Citation: Bellamy et al. (2018), AI Fairness 360, arXiv:1810.01943


# Default feature names for the simulation. The last column is the
# narrative-sentiment feature that varies across protected groups; the first
# five are structured-credential features that do not vary by group.
DEFAULT_FEATURE_COLS: List[str] = [
    "score_a",          # e.g., a board exam score
    "publications",     # e.g., publication count
    "score_b",          # e.g., a clerkship grade composite
    "score_c",          # e.g., letters-of-recommendation aggregate
    "score_d",          # e.g., research-fit composite
    "narrative_sentiment",
]


# Default DGP coefficients. Exposed so sensitivity sweeps can vary
# beta_narrative_sentiment.
DEFAULT_BETAS: Dict[str, float] = {
    "score_a": 0.030,
    "publications": 0.080,
    "score_b": 0.180,
    "score_c": 0.120,
    "score_d": 0.080,
    "narrative_sentiment": 1.200,
}


# Default DGP feature distributions. Override via SimulationConfig.
DEFAULT_DGP_PARAMS: Dict[str, Dict[str, float]] = {
    "score_a": {"mean": 250.0, "sd": 10.0, "center": 250.0},
    "publications": {"poisson_rate": 3.0, "center": 3.0},
    "score_b": {"mean": 3.6, "sd": 0.25, "center": 3.6},
    "score_c": {"mean": 0.0, "sd": 1.0, "center": 0.0},
    "score_d": {"mean": 0.0, "sd": 1.0, "center": 0.0},
}


@dataclass
class SimulationConfig:
    n: int = 6000
    invite_rate: float = 0.30
    sd: float = 0.30                          # narrative_sentiment SD
    feature_cols: List[str] = field(default_factory=lambda: list(DEFAULT_FEATURE_COLS))
    betas: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_BETAS))
    dgp_params: Dict[str, Dict[str, float]] = field(default_factory=lambda: dict(DEFAULT_DGP_PARAMS))


@dataclass
class Anchoring:
    """A single sentiment-instrument anchoring.

    Attributes:
        label: human-readable label (e.g., "vader_excerpt", "claude_full_doc")
        low_sentiment: mean narrative_sentiment for the disadvantaged group
        high_sentiment: mean narrative_sentiment for the favored group
    """
    label: str
    low_sentiment: float
    high_sentiment: float


def generate_synthetic_applicants(
    n: int,
    seed: int,
    mean_low: float,
    mean_high: float,
    sd: float,
    cfg: Optional[SimulationConfig] = None,
) -> pd.DataFrame:
    """Generate n synthetic applicants with binary protected group.

    Group 0 gets `mean_low` narrative sentiment; Group 1 gets `mean_high`.
    All other features are drawn from group-invariant distributions.
    """
    cfg = cfg or SimulationConfig()
    rng = np.random.default_rng(seed)

    group = rng.integers(0, 2, size=n)

    # Structured features (group-invariant by design)
    score_a = rng.normal(cfg.dgp_params["score_a"]["mean"],
                         cfg.dgp_params["score_a"]["sd"], size=n)
    publications = rng.poisson(cfg.dgp_params["publications"]["poisson_rate"], size=n)
    score_b = rng.normal(cfg.dgp_params["score_b"]["mean"],
                         cfg.dgp_params["score_b"]["sd"], size=n)
    score_c = rng.normal(cfg.dgp_params["score_c"]["mean"],
                         cfg.dgp_params["score_c"]["sd"], size=n)
    score_d = rng.normal(cfg.dgp_params["score_d"]["mean"],
                         cfg.dgp_params["score_d"]["sd"], size=n)

    narrative_sentiment = rng.normal(
        loc=np.where(group == 0, mean_low, mean_high),
        scale=sd,
        size=n,
    )
    narrative_sentiment = np.clip(narrative_sentiment, -1.0, 1.0)

    b = cfg.betas
    z = (
        b["score_a"] * (score_a - cfg.dgp_params["score_a"]["center"])
        + b["score_b"] * (score_b - cfg.dgp_params["score_b"]["center"])
        + b["publications"] * (publications - cfg.dgp_params["publications"]["center"])
        + b["score_c"] * score_c
        + b["score_d"] * score_d
        + b["narrative_sentiment"] * narrative_sentiment
    )
    p = 1.0 / (1.0 + np.exp(-z))
    label = (rng.random(n) < p).astype(int)

    return pd.DataFrame({
        "group": group,
        "score_a": score_a,
        "publications": publications,
        "score_b": score_b,
        "score_c": score_c,
        "score_d": score_d,
        "narrative_sentiment": narrative_sentiment,
        "label": label,
    })


def _build_model(model_name: str, seed: int):
    if model_name == "logistic_regression":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=2000, solver="lbfgs")),
        ])
    if model_name == "random_forest":
        return RandomForestClassifier(
            n_estimators=250, max_depth=6, min_samples_leaf=8, random_state=seed,
        )
    if model_name == "gradient_boosting":
        return GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=2, random_state=seed,
        )
    if model_name == "svm_rbf":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("svc", SVC(kernel="rbf", probability=True, C=1.0, gamma="scale", random_state=seed)),
        ])
    if model_name == "linear_score":
        return None
    raise ValueError(f"Unsupported model_name: {model_name}")


def _linear_score_prob(X: np.ndarray, cfg: SimulationConfig) -> np.ndarray:
    b = cfg.betas
    z = (
        b["score_a"] * (X[:, 0] - cfg.dgp_params["score_a"]["center"])
        + b["publications"] * (X[:, 1] - cfg.dgp_params["publications"]["center"])
        + b["score_b"] * (X[:, 2] - cfg.dgp_params["score_b"]["center"])
        + b["score_c"] * X[:, 3]
        + b["score_d"] * X[:, 4]
        + b["narrative_sentiment"] * X[:, 5]
    )
    return 1.0 / (1.0 + np.exp(-z))


def _rank_select_top_k(proba: np.ndarray, invite_rate: float):
    n = len(proba)
    k = int(round(invite_rate * n))
    if k <= 0:
        return np.zeros(n, dtype=int), float("inf")
    order = np.argsort(-proba, kind="stable")
    invited_idx = order[:k]
    yhat = np.zeros(n, dtype=int)
    yhat[invited_idx] = 1
    eff_thresh = float(proba[invited_idx[-1]])
    return yhat, eff_thresh


def _classification_metrics(
    df: pd.DataFrame, yhat: np.ndarray, feature_cols: List[str]
) -> Dict[str, float]:
    """Per-group selection metrics. Uses AIF360 if available, otherwise computes
    disparate impact and statistical parity directly."""
    df_reset = df.reset_index(drop=True)
    group = df_reset["group"].to_numpy()
    label = df_reset["label"].to_numpy()

    g0 = group == 0
    g1 = group == 1

    sr0 = float(yhat[g0].mean()) if g0.any() else float("nan")
    sr1 = float(yhat[g1].mean()) if g1.any() else float("nan")
    di = sr0 / sr1 if sr1 > 0 else float("nan")

    # TPR / FPR per group
    pos = label == 1
    tpr0 = float(yhat[g0 & pos].mean()) if (g0 & pos).any() else float("nan")
    tpr1 = float(yhat[g1 & pos].mean()) if (g1 & pos).any() else float("nan")
    eod = tpr0 - tpr1 if not (np.isnan(tpr0) or np.isnan(tpr1)) else float("nan")

    neg = label == 0
    fpr0 = float(yhat[g0 & neg].mean()) if (g0 & neg).any() else float("nan")
    fpr1 = float(yhat[g1 & neg].mean()) if (g1 & neg).any() else float("nan")
    fpd = fpr0 - fpr1 if not (np.isnan(fpr0) or np.isnan(fpr1)) else float("nan")

    return {
        "disparate_impact": di,
        "statistical_parity_difference": sr0 - sr1,
        "equal_opportunity_difference": eod,
        "false_positive_rate_difference": fpd,
        "selection_rate_group0": sr0,
        "selection_rate_group1": sr1,
        "accuracy": float((yhat == label).mean()),
    }


def train_and_screen(
    df: pd.DataFrame,
    seed: int,
    invite_rate: float,
    cfg: SimulationConfig,
    model_name: str = "logistic_regression",
):
    train_df, test_df = train_test_split(
        df, test_size=0.30, random_state=seed,
        stratify=df["group"].astype(str) + "_" + df["label"].astype(str),
    )
    X_train = train_df[cfg.feature_cols].to_numpy()
    y_train = train_df["label"].to_numpy()
    X_test = test_df[cfg.feature_cols].to_numpy()

    clf = _build_model(model_name, seed)
    if clf is None:
        proba = _linear_score_prob(X_test, cfg)
    else:
        clf.fit(X_train, y_train)
        proba = clf.predict_proba(X_test)[:, 1]

    yhat, eff_thresh = _rank_select_top_k(proba, invite_rate)
    metrics = _classification_metrics(test_df, yhat, cfg.feature_cols)
    return clf, train_df, test_df, proba, eff_thresh, yhat, metrics


# ---------------- Bootstrap over anchorings ----------------


def _percentile_ci(values: np.ndarray, alpha: float = 0.05) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {"point": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"), "n_reps": 0}
    return {
        "point": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "ci_lo": float(np.quantile(arr, alpha / 2)),
        "ci_hi": float(np.quantile(arr, 1 - alpha / 2)),
        "n_reps": int(len(arr)),
    }


def bootstrap_anchoring(
    anchoring: Anchoring,
    cfg: SimulationConfig,
    n_reps: int,
    base_seed: int,
    model_name: str = "logistic_regression",
) -> Dict[str, Dict[str, float]]:
    """Run n_reps independent (DGP, train/test) draws under one anchoring.

    Returns percentile CIs on each headline metric across the replicates.
    """
    keys = [
        "disparate_impact",
        "statistical_parity_difference",
        "equal_opportunity_difference",
        "false_positive_rate_difference",
        "selection_rate_group0",
        "selection_rate_group1",
        "accuracy",
    ]
    accum: Dict[str, List[float]] = {k: [] for k in keys}
    for i in range(n_reps):
        seed = base_seed + i
        df = generate_synthetic_applicants(
            n=cfg.n, seed=seed,
            mean_low=anchoring.low_sentiment, mean_high=anchoring.high_sentiment,
            sd=cfg.sd, cfg=cfg,
        )
        _, _, _, _, _, _, m = train_and_screen(
            df=df, seed=seed, invite_rate=cfg.invite_rate, cfg=cfg, model_name=model_name,
        )
        for k in keys:
            accum[k].append(m[k])
    return {k: _percentile_ci(np.array(v)) for k, v in accum.items()}


def run_anchoring_sweep(
    anchorings: Iterable[Anchoring],
    cfg: SimulationConfig,
    n_reps: int,
    base_seed: int = 42,
    model_name: str = "logistic_regression",
) -> Dict[str, Dict]:
    """Run the bootstrap simulation under each anchoring; return per-anchoring results."""
    results: Dict[str, Dict] = {}
    for a in anchorings:
        results[a.label] = {
            "anchoring": {
                "label": a.label,
                "low_sentiment": a.low_sentiment,
                "high_sentiment": a.high_sentiment,
                "gap": a.high_sentiment - a.low_sentiment,
            },
            "metrics": bootstrap_anchoring(
                anchoring=a, cfg=cfg, n_reps=n_reps,
                base_seed=base_seed, model_name=model_name,
            ),
        }
    return results

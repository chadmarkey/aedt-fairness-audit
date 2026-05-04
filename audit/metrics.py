"""Generic fairness audit metrics.

Computes AIF360-style fairness metrics on any binary-group, binary-label
prediction problem. Pipeline-agnostic: the user supplies the data, the
group assignment, the labels, and the model predictions; this module
computes the metrics.

Usage:
    from audit.metrics import group_outcome_summary, disparity_summary
    metrics = group_outcome_summary(df, yhat, proba)
    disparity = disparity_summary(metrics)

Required DataFrame columns:
    - "group": int (0 or 1) — protected attribute
    - "label": int (0 or 1) — ground-truth outcome
"""
from __future__ import annotations

import json
import os
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def _safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return float("nan")
    return float(numerator / denominator)


def _group_confusion(
    df: pd.DataFrame, yhat: np.ndarray, proba: np.ndarray, group_value: int
) -> Dict[str, float]:
    mask = df["group"].to_numpy() == group_value
    y_true = df.loc[mask, "label"].to_numpy()
    y_pred = yhat[mask]
    scores = proba[mask]

    positives = y_true == 1
    negatives = y_true == 0
    pred_pos = y_pred == 1
    pred_neg = y_pred == 0

    tp = int(np.sum(positives & pred_pos))
    fp = int(np.sum(negatives & pred_pos))
    tn = int(np.sum(negatives & pred_neg))
    fn = int(np.sum(positives & pred_neg))

    return {
        "n": int(mask.sum()),
        "base_rate": float(y_true.mean()) if len(y_true) else float("nan"),
        "selection_rate": float(y_pred.mean()) if len(y_pred) else float("nan"),
        "mean_score": float(scores.mean()) if len(scores) else float("nan"),
        "tpr": _safe_rate(tp, tp + fn),
        "fpr": _safe_rate(fp, fp + tn),
        "fnr": _safe_rate(fn, fn + tp),
        "tnr": _safe_rate(tn, tn + fp),
        "precision": _safe_rate(tp, tp + fp),
        "negative_predictive_value": _safe_rate(tn, tn + fn),
        "brier_score": float(np.mean((scores - y_true) ** 2)) if len(scores) else float("nan"),
    }


def group_outcome_summary(
    df: pd.DataFrame, yhat: np.ndarray, proba: np.ndarray
) -> Dict[str, Dict[str, float]]:
    """Per-group confusion summary for a binary-group, binary-label problem."""
    return {
        "group_0": _group_confusion(df, yhat, proba, 0),
        "group_1": _group_confusion(df, yhat, proba, 1),
    }


def _diff(a: float, b: float) -> float:
    if any(np.isnan([a, b])):
        return float("nan")
    return float(a - b)


def _ratio(a: float, b: float) -> float:
    if any(np.isnan([a, b])) or b == 0:
        return float("nan")
    return float(a / b)


def disparity_summary(group_metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Compute disparate impact and parity metrics from per-group outcomes.

    Disparate impact (DI) ratio: group_0 selection rate / group_1 selection rate.
    EEOC four-fifths rule treats DI < 0.80 as presumptive evidence of adverse
    impact in employment selection.
    """
    g0 = group_metrics["group_0"]
    g1 = group_metrics["group_1"]
    return {
        "selection_rate_ratio_group0_over_group1": _ratio(g0["selection_rate"], g1["selection_rate"]),
        "selection_rate_difference_group0_minus_group1": _diff(g0["selection_rate"], g1["selection_rate"]),
        "tpr_difference_group0_minus_group1": _diff(g0["tpr"], g1["tpr"]),
        "fpr_difference_group0_minus_group1": _diff(g0["fpr"], g1["fpr"]),
        "precision_difference_group0_minus_group1": _diff(g0["precision"], g1["precision"]),
        "predictive_parity_ratio_group0_over_group1": _ratio(g0["precision"], g1["precision"]),
        "mean_score_difference_group0_minus_group1": _diff(g0["mean_score"], g1["mean_score"]),
        "brier_score_difference_group0_minus_group1": _diff(g0["brier_score"], g1["brier_score"]),
    }


def threshold_sweep(
    df: pd.DataFrame, proba: np.ndarray, invite_rates: Iterable[float]
) -> Dict[str, Dict[str, float]]:
    """Rank-based selection at each invite rate (no tie inflation)."""
    results: Dict[str, Dict[str, float]] = {}
    group = df["group"].to_numpy()
    n = len(proba)
    order = np.argsort(-proba, kind="stable")

    for invite_rate in invite_rates:
        k = int(round(invite_rate * n))
        invited = np.zeros(n, dtype=int)
        invited[order[:k]] = 1
        eff_thresh = float(proba[order[k - 1]]) if k > 0 else float("inf")

        g0_rate = float(invited[group == 0].mean()) if (group == 0).any() else float("nan")
        g1_rate = float(invited[group == 1].mean()) if (group == 1).any() else float("nan")
        results[f"{invite_rate:.2f}"] = {
            "threshold": eff_thresh,
            "selection_rate_group0": g0_rate,
            "selection_rate_group1": g1_rate,
            "disparate_impact_group0_over_group1": _ratio(g0_rate, g1_rate),
            "statistical_parity_difference_group0_minus_group1": _diff(g0_rate, g1_rate),
        }
    return results


def feature_proxy_audit(
    df: pd.DataFrame, feature_cols: Iterable[str]
) -> Dict[str, Dict[str, float]]:
    """For each feature, report mean difference, standardized mean difference,
    and Pearson correlation with the protected group. Useful for identifying
    features that may serve as proxies for protected attributes.
    """
    results: Dict[str, Dict[str, float]] = {}
    group = df["group"].to_numpy()
    for feature in feature_cols:
        values = df[feature].to_numpy()
        g0 = values[group == 0]
        g1 = values[group == 1]
        pooled_sd = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        m0 = float(np.mean(g0)) if len(g0) else float("nan")
        m1 = float(np.mean(g1)) if len(g1) else float("nan")
        smd = (m0 - m1) / pooled_sd if pooled_sd else float("nan")
        if np.std(values) > 0 and np.std(group) > 0:
            corr = float(np.corrcoef(values, group)[0, 1])
        else:
            corr = float("nan")
        results[feature] = {
            "mean_group0": m0,
            "mean_group1": m1,
            "mean_difference_group0_minus_group1": _diff(m0, m1),
            "standardized_mean_difference": smd,
            "pearson_corr_with_group": corr,
        }
    return results


def calibration_audit(df: pd.DataFrame, proba: np.ndarray) -> Dict[str, Dict[str, float]]:
    """Per-group calibration: slope/intercept of logit-isotonic fit.

    For each group, fit logistic regression of label on logit(proba). A perfectly
    calibrated probability has slope=1, intercept=0. Slope < 1 means scores are
    over-confident; intercept != 0 means systematic over- or under-prediction.
    """
    results: Dict[str, Dict[str, float]] = {}
    proba = np.clip(proba, 1e-6, 1 - 1e-6)
    logit = np.log(proba / (1 - proba))

    for g in [0, 1]:
        mask = df["group"].to_numpy() == g
        y = df.loc[mask, "label"].to_numpy()
        x = logit[mask]
        if len(y) < 10 or len(np.unique(y)) < 2:
            results[f"group_{g}"] = {
                "calibration_slope": float("nan"),
                "calibration_intercept": float("nan"),
                "n": int(mask.sum()),
            }
            continue
        clf = LogisticRegression(C=1e6, max_iter=2000)  # near-unregularized
        clf.fit(x.reshape(-1, 1), y)
        results[f"group_{g}"] = {
            "calibration_slope": float(clf.coef_[0, 0]),
            "calibration_intercept": float(clf.intercept_[0]),
            "n": int(mask.sum()),
        }
    return results


def counterfactual_flip_summary(
    baseline_df: pd.DataFrame,
    baseline_yhat: np.ndarray,
    cf_yhat: np.ndarray,
) -> Dict[str, Dict[str, float]]:
    """Summarize prediction changes between a baseline and counterfactual run.

    Useful for measuring how much a textual or feature-level perturbation
    changes individual outcomes. Reports per-group flip rates and direction.
    """
    group = baseline_df["group"].to_numpy()
    baseline_yhat = np.asarray(baseline_yhat)
    cf_yhat = np.asarray(cf_yhat)
    changed = baseline_yhat != cf_yhat
    reject_to_invite = (baseline_yhat == 0) & (cf_yhat == 1)
    invite_to_reject = (baseline_yhat == 1) & (cf_yhat == 0)

    def summarize(mask: np.ndarray) -> Dict[str, float]:
        return {
            "n": int(mask.sum()),
            "flip_rate": float(changed[mask].mean()) if mask.any() else float("nan"),
            "reject_to_invite_rate": float(reject_to_invite[mask].mean()) if mask.any() else float("nan"),
            "invite_to_reject_rate": float(invite_to_reject[mask].mean()) if mask.any() else float("nan"),
        }

    return {
        "overall": summarize(np.ones_like(group, dtype=bool)),
        "group_0": summarize(group == 0),
        "group_1": summarize(group == 1),
    }


def export_prediction_frame(
    df: pd.DataFrame,
    proba: np.ndarray,
    yhat: np.ndarray,
    out_path: str,
) -> pd.DataFrame:
    """Export per-applicant scores and selection decisions to CSV."""
    export_df = df.reset_index(drop=True).copy()
    export_df["score"] = proba
    export_df["invited"] = yhat
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    export_df.to_csv(out_path, index=False)
    return export_df


def write_audit_report(report: Dict, out_path: str) -> None:
    """Write a JSON audit report, NaN-safe."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(
            report,
            fp,
            indent=2,
            default=lambda x: None if (isinstance(x, float) and np.isnan(x)) else x,
        )


def model_suite_summary(model_metrics: Dict[str, Dict]) -> Dict[str, Dict[str, float]]:
    """Summarize across model architectures for cross-model robustness checks."""
    summary = {}
    for model_name, metrics in model_metrics.items():
        baseline = metrics.get("baseline", {})
        cf_fixed = metrics.get("counterfactual_fixed_threshold", {})
        cf_rethresh = metrics.get("counterfactual_rethresholded", {})
        summary[model_name] = {
            "baseline_disparate_impact": baseline.get("disparate_impact"),
            "cf_fixed_disparate_impact": cf_fixed.get("disparate_impact"),
            "rethresh_disparate_impact": cf_rethresh.get("disparate_impact"),
            "baseline_equal_opportunity_difference": baseline.get("equal_opportunity_difference"),
            "cf_fixed_equal_opportunity_difference": cf_fixed.get("equal_opportunity_difference"),
            "rethresh_equal_opportunity_difference": cf_rethresh.get("equal_opportunity_difference"),
            "baseline_accuracy": baseline.get("accuracy"),
            "cf_fixed_accuracy": cf_fixed.get("accuracy"),
            "rethresh_accuracy": cf_rethresh.get("accuracy"),
        }
    return summary


def coefficient_audit(clf, feature_cols: Iterable[str]) -> Optional[Dict[str, Dict[str, float]]]:
    """Standardized LR coefficients. Returns None if clf is not the LR pipeline."""
    if not isinstance(clf, Pipeline):
        return None
    step = clf.named_steps.get("lr")
    if not isinstance(step, LogisticRegression):
        return None
    coef = step.coef_[0]
    return {
        feature: {
            "standardized_coefficient": float(weight),
            "odds_ratio_per_1sd_increase": float(np.exp(weight)),
        }
        for feature, weight in zip(feature_cols, coef)
    }

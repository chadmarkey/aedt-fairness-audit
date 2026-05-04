"""Generic fairness audit metrics for automated employment decision tools.

Methods are pipeline-agnostic: they consume a DataFrame with a `group` column
and a labeled outcome, plus model predictions, and return AIF360-style
metrics. The toolkit does not include or require any specific AEDT
implementation; users supply their own scoring function.
"""
from .metrics import (
    group_outcome_summary,
    disparity_summary,
    threshold_sweep,
    feature_proxy_audit,
    calibration_audit,
    counterfactual_flip_summary,
    export_prediction_frame,
    write_audit_report,
    model_suite_summary,
)
from .screening import (
    DEFAULT_AXES,
    assign_binary_group,
    top_k_selection,
    disparate_impact,
    bootstrap_di,
    axis_audit,
)
from .screening_simulation import (
    Anchoring,
    SimulationConfig,
    DEFAULT_FEATURE_COLS,
    DEFAULT_BETAS,
    DEFAULT_DGP_PARAMS,
    generate_synthetic_applicants,
    train_and_screen,
    bootstrap_anchoring,
    run_anchoring_sweep,
)

__all__ = [
    "group_outcome_summary",
    "disparity_summary",
    "threshold_sweep",
    "feature_proxy_audit",
    "calibration_audit",
    "counterfactual_flip_summary",
    "export_prediction_frame",
    "write_audit_report",
    "model_suite_summary",
    "DEFAULT_AXES",
    "assign_binary_group",
    "top_k_selection",
    "disparate_impact",
    "bootstrap_di",
    "axis_audit",
]

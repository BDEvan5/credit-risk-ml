"""Reusable binary classification metrics for credit-style modelling (ROC-AUC, Gini, KS, PR)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


def binary_classifier_metrics(
    y_true,
    y_score,
    *,
    y_pred=None,
    pos_label: int = 1,
) -> dict[str, float]:
    """
    Core metrics for a binary classifier from labels and scores (positive-class probability).

    Returns ROC-AUC, Gini (2×AUC−1), average precision (PR-AUC), and the two-sample KS
    statistic comparing score distributions between positive and negative classes.
    Optionally includes accuracy when ``y_pred`` is provided.

    Parameters
    ----------
    y_true : array-like
        True labels (0/1).
    y_score : array-like
        Predicted probability of the positive class (or monotone risk score).
    y_pred : array-like, optional
        Hard predictions; if given, accuracy is computed.
    pos_label : int
        Label treated as the positive (e.g. default) class.
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)

    out: dict[str, float] = {}

    if y_pred is not None:
        y_pred = np.asarray(y_pred)
        out["accuracy"] = float(accuracy_score(y_true, y_pred))

    labels = np.unique(y_true)
    if labels.size < 2:
        nan = float("nan")
        out["roc_auc"] = nan
        out["gini"] = nan
        out["average_precision"] = nan
        out["ks"] = nan
        return out

    auc = float(roc_auc_score(y_true, y_score))
    out["roc_auc"] = auc
    out["gini"] = 2.0 * auc - 1.0
    out["average_precision"] = float(average_precision_score(y_true, y_score))

    pos = y_score[y_true == pos_label]
    neg = y_score[y_true != pos_label]
    if pos.size == 0 or neg.size == 0:
        out["ks"] = float("nan")
    else:
        out["ks"] = float(ks_2samp(pos, neg, method="auto").statistic)

    return out


_METRIC_LABELS: dict[str, str] = {
    "accuracy": "Accuracy",
    "roc_auc": "ROC-AUC",
    "gini": "Gini (2×AUC − 1)",
    "average_precision": "Average precision (PR-AUC)",
    "ks": "KS statistic",
}


def format_metrics_lines(metrics: dict[str, float], *, precision: int = 4) -> str:
    """Pretty-print a metrics dict from :func:`binary_classifier_metrics` (stable key order)."""
    order = ("accuracy", "roc_auc", "gini", "average_precision", "ks")
    lines = []
    for key in order:
        if key not in metrics:
            continue
        label = _METRIC_LABELS.get(key, key)
        val = metrics[key]
        if val != val:  # NaN
            lines.append(f"{label}: nan")
        else:
            lines.append(f"{label}: {val:.{precision}f}")
    return "\n".join(lines)


def roc_pr_curve_data(
    y_true,
    y_score,
    *,
    pos_label: int | None = None,
) -> dict[str, Any]:
    """
    Return arrays for custom ROC/PR plots (or inspection).

    Keys: ``fpr``, ``tpr``, ``roc_thresholds``, ``precision``, ``recall``, ``pr_thresholds``.
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    fpr, tpr, roc_thresholds = roc_curve(y_true, y_score, pos_label=pos_label)
    precision, recall, pr_thresholds = precision_recall_curve(
        y_true, y_score, pos_label=pos_label
    )
    return {
        "fpr": fpr,
        "tpr": tpr,
        "roc_thresholds": roc_thresholds,
        "precision": precision,
        "recall": recall,
        "pr_thresholds": pr_thresholds,
    }


def plot_roc_pr_curves(
    y_true,
    y_score,
    *,
    title_prefix: str = "",
    figsize: tuple[float, float] = (10, 4),
) -> Any:
    """
    Draw ROC and precision-recall curves (uses sklearn's display helpers).

    Returns the matplotlib figure. Use in notebooks with ``plt.show()`` if not using %matplotlib inline.
    """
    import matplotlib.pyplot as plt
    from sklearn.metrics import PrecisionRecallDisplay, RocCurveDisplay

    fig, axes = plt.subplots(1, 2, figsize=figsize)
    RocCurveDisplay.from_predictions(y_true, y_score, ax=axes[0])
    axes[0].set_title(f"{title_prefix}ROC curve".strip())
    PrecisionRecallDisplay.from_predictions(y_true, y_score, ax=axes[1])
    axes[1].set_title(f"{title_prefix}Precision–recall curve".strip())
    fig.tight_layout()
    return fig

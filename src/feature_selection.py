"""Feature pruning helpers for tabular credit-risk models (correlation, importance, optional RFE)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.feature_selection import SelectFromModel
from sklearn.model_selection import StratifiedKFold


def drop_highly_correlated(
    X: pd.DataFrame,
    *,
    threshold: float = 0.95,
    keep_order: list[str] | None = None,
) -> list[str]:
    """Return column names to **keep**, dropping one from each pair with |corr| >= threshold.

    When two numeric columns are highly correlated, the column with lower priority is dropped
    (``keep_order`` lists preferred columns first; unlisted columns use a large default rank).
    """
    num = X.select_dtypes(include=[np.number]).columns.tolist()
    if len(num) < 2:
        return X.columns.tolist()

    corr = X[num].corr().abs()
    cols = corr.columns.tolist()
    drop: set[str] = set()
    priority = {name: i for i, name in enumerate(keep_order or [])}

    for i, c1 in enumerate(cols):
        for j in range(i + 1, len(cols)):
            c2 = cols[j]
            v = corr.iloc[i, j]
            if pd.isna(v) or v < threshold:
                continue
            if priority.get(c1, 10_000) <= priority.get(c2, 10_000):
                drop.add(c2)
            else:
                drop.add(c1)

    return [c for c in X.columns if c not in drop]


def mean_lgbm_gain_importance(
    estimator: Any,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    cv: StratifiedKFold | None = None,
    categorical_feature: list[str] | None = None,
) -> pd.Series:
    """Average ``feature_importances_`` (gain-style) across stratified CV folds."""
    if cv is None:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    importances = np.zeros(X.shape[1], dtype=np.float64)
    cat_idx = [X.columns.get_loc(c) for c in (categorical_feature or []) if c in X.columns]

    for train_idx, _ in cv.split(X, y):
        est = clone(estimator)
        fit_kw: dict[str, Any] = {}
        if cat_idx:
            fit_kw["categorical_feature"] = cat_idx
        est.fit(X.iloc[train_idx], y.iloc[train_idx], **fit_kw)
        importances += est.feature_importances_

    importances /= cv.get_n_splits()
    return pd.Series(importances, index=X.columns).sort_values(ascending=False)


def select_from_lgbm_model(
    estimator: Any,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    threshold: str | float = "median",
    categorical_feature: list[str] | None = None,
) -> list[str]:
    """Wrap ``SelectFromModel`` for a fitted gradient boosting estimator with gain importances."""
    cat_idx = [X.columns.get_loc(c) for c in (categorical_feature or []) if c in X.columns]
    fit_kw: dict[str, Any] = {}
    if cat_idx:
        fit_kw["categorical_feature"] = cat_idx
    est = clone(estimator)
    est.fit(X, y, **fit_kw)
    selector = SelectFromModel(est, threshold=threshold, prefit=True)
    mask = selector.get_support()
    return [c for c, m in zip(X.columns, mask, strict=True) if m]

"""Heterogeneous treatment effects / uplift modelling (Milestone 6).

Uses EconML's ``CausalForestDML`` (a double-machine-learning causal forest) to
estimate conditional average treatment effects (CATE), then evaluates
targeting quality with a Qini curve and AUUC.  A scikit-learn T-learner
fallback keeps the endpoint working if EconML is unavailable.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from econml.dml import CausalForestDML  # type: ignore

    _HAS_ECONML = True
except Exception:  # pragma: no cover
    _HAS_ECONML = False
    logger.warning("EconML not available - using T-learner fallback")

from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

__all__ = ["estimate_uplift", "qini_curve"]


def qini_curve(y: np.ndarray, t: np.ndarray, cate: np.ndarray, n_points: int = 100) -> Dict[str, object]:
    """Compute the Qini curve and AUUC for a predicted uplift ranking.

    Units are sorted by predicted CATE (descending).  At each prefix the Qini
    statistic is ``y_treated_cum - y_control_cum * (n_treated / n_control)``.
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    cate = np.asarray(cate, dtype=float)

    order = np.argsort(-cate)
    y, t = y[order], t[order]

    cum_t = np.cumsum(t)
    cum_c = np.cumsum(1 - t)
    cum_y_t = np.cumsum(y * t)
    cum_y_c = np.cumsum(y * (1 - t))

    with np.errstate(divide="ignore", invalid="ignore"):
        qini = cum_y_t - cum_y_c * (cum_t / np.maximum(cum_c, 1))
    qini = np.nan_to_num(qini)

    n = len(y)
    fractions = np.linspace(0, 1, n)
    # Random-targeting baseline (linear between 0 and the overall Qini).
    baseline = np.linspace(0, qini[-1], n)
    auuc = float(np.trapezoid(qini - baseline, fractions))

    # Sample the curve for charting.
    idx = np.unique(np.linspace(0, n - 1, n_points).astype(int))
    return {
        "qini_curve": {
            "fraction": fractions[idx].tolist(),
            "qini": qini[idx].tolist(),
            "random_baseline": baseline[idx].tolist(),
        },
        "auuc": auuc,
        "qini_at_10pct": float(qini[max(1, int(0.1 * n)) - 1]),
        "qini_at_30pct": float(qini[max(1, int(0.3 * n)) - 1]),
    }


def _t_learner_cate(X: pd.DataFrame, t: np.ndarray, y: np.ndarray, binary: bool) -> np.ndarray:
    model_cls = GradientBoostingClassifier if binary else GradientBoostingRegressor
    m1 = model_cls(random_state=0).fit(X[t == 1], y[t == 1])
    m0 = model_cls(random_state=0).fit(X[t == 0], y[t == 0])
    if binary:
        p1 = m1.predict_proba(X)[:, 1]
        p0 = m0.predict_proba(X)[:, 1]
        return p1 - p0
    return m1.predict(X) - m0.predict(X)


def estimate_uplift(
    df: pd.DataFrame,
    treatment: str,
    outcome: str,
    features: Sequence[str],
    learner: str = "causal_forest",
    n_estimators: int = 200,
    seed: int = 42,
    top_k: int = 20,
) -> Dict[str, object]:
    """Estimate heterogeneous treatment effects and targeting quality."""
    data = df[[treatment, outcome] + list(features)].dropna().copy()
    t = data[treatment].astype(int).values
    y = data[outcome].astype(float).values
    X = data[list(features)].astype(float)

    if len(np.unique(t)) < 2:
        raise ValueError("Treatment column must contain both 0 and 1")

    binary_outcome = bool(set(np.unique(y)).issubset({0.0, 1.0}))
    engine = learner

    cate: Optional[np.ndarray] = None
    importance: Dict[str, float] = {}

    if learner == "causal_forest" and _HAS_ECONML:
        try:
            model_y = GradientBoostingClassifier(random_state=seed) if binary_outcome else GradientBoostingRegressor(random_state=seed)
            est = CausalForestDML(
                model_y=model_y,
                model_t=GradientBoostingClassifier(random_state=seed),
                discrete_outcome=binary_outcome,
                discrete_treatment=True,
                n_estimators=n_estimators,
                random_state=seed,
            )
            est.fit(y, t, X=X.values)
            cate = np.asarray(est.effect(X.values)).ravel()
            try:
                imp = est.feature_importances_
                importance = {f: float(v) for f, v in zip(features, imp)}
            except Exception:  # pragma: no cover
                importance = {}
        except Exception as exc:  # pragma: no cover
            logger.warning("CausalForestDML failed (%s); using T-learner", exc)
            cate = None

    if cate is None:
        engine = "t_learner"
        cate = _t_learner_cate(X, t, y, binary_outcome)

    qini = qini_curve(y, t, cate)

    ranked = pd.DataFrame({"cate": cate})
    for f in features:
        ranked[f] = X[f].values
    ranked = ranked.sort_values("cate", ascending=False)
    top_segment = ranked.head(top_k).mean(numeric_only=True).to_dict()
    bottom_segment = ranked.tail(top_k).mean(numeric_only=True).to_dict()

    # Segment summary in predicted-uplift quartiles.
    ranked["quartile"] = pd.qcut(ranked["cate"], 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
    segment_means = ranked.groupby("quartile", observed=True)["cate"].mean().to_dict()

    if not importance:
        # crude importance via correlation of each feature with CATE
        importance = {
            f: float(abs(np.corrcoef(X[f].values, cate)[0, 1])) if X[f].std() > 0 else 0.0
            for f in features
        }

    return {
        "method": "uplift_cate",
        "engine": engine,
        "ate": float(np.mean(cate)),
        "cate_mean": float(np.mean(cate)),
        "cate_std": float(np.std(cate)),
        "cate_positive_share": float(np.mean(cate > 0)),
        "cate": cate.tolist(),
        "n_obs": int(len(y)),
        "binary_outcome": binary_outcome,
        "feature_importance": importance,
        "top_segment_profile": {k: float(v) for k, v in top_segment.items() if k != "quartile"},
        "bottom_segment_profile": {k: float(v) for k, v in bottom_segment.items() if k != "quartile"},
        "segment_mean_cate": {str(k): float(v) for k, v in segment_means.items()},
        "qini": qini["qini_curve"],
        "auuc": qini["auuc"],
        "qini_at_10pct": qini["qini_at_10pct"],
        "qini_at_30pct": qini["qini_at_30pct"],
    }

"""Propensity-score matching (PSM) with balance diagnostics (Milestone 6).

Two entry points are provided:

* :func:`propensity_score_matching` — a transparent scikit-learn implementation
  with covariate-balance (standardised mean difference) diagnostics.
* :func:`dowhy_propensity_estimate` — the same estimand via DoWhy's
  ``backdoor.propensity_score_matching`` estimator, plus a refutation test.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors

__all__ = ["propensity_score_matching", "dowhy_propensity_estimate", "standardised_mean_diff"]

logger = logging.getLogger(__name__)


def standardised_mean_diff(treated: np.ndarray, control: np.ndarray) -> float:
    """Absolute standardised mean difference (SMD) for one covariate."""
    treated = np.asarray(treated, dtype=float)
    control = np.asarray(control, dtype=float)
    mean_t, mean_c = treated.mean(), control.mean()
    var_t, var_c = treated.var(ddof=1), control.var(ddof=1)
    denom = np.sqrt((var_t + var_c) / 2.0)
    if denom == 0:
        return 0.0
    return float(abs(mean_t - mean_c) / denom)


def _fit_propensity(X: pd.DataFrame, treatment: pd.Series) -> np.ndarray:
    model = LogisticRegression(max_iter=1000, solver="lbfgs")
    model.fit(X.values, treatment.values)
    return model.predict_proba(X.values)[:, 1]


def propensity_score_matching(
    df: pd.DataFrame,
    treatment: str,
    outcome: str,
    covariates: Sequence[str],
    caliper: Optional[float] = 0.05,
    n_bootstrap: int = 500,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, object]:
    """1:1 nearest-neighbour propensity-score matching returning the ATT."""
    data = df[[treatment, outcome] + list(covariates)].dropna().copy()
    t = data[treatment].astype(int)
    X = data[list(covariates)]

    ps = _fit_propensity(X, t)
    data["_ps"] = ps
    # Match on the logit of the propensity score (more stable tail behaviour).
    logit_ps = np.log(np.clip(ps, 1e-6, 1 - 1e-6) / (1 - np.clip(ps, 1e-6, 1 - 1e-6)))

    treated_idx = np.where(t.values == 1)[0]
    control_idx = np.where(t.values == 0)[0]
    if len(treated_idx) == 0 or len(control_idx) == 0:
        raise ValueError("Both treatment and control groups must be present")

    nn = NearestNeighbors(n_neighbors=1).fit(logit_ps[control_idx].reshape(-1, 1))
    dist, neigh = nn.kneighbors(logit_ps[treated_idx].reshape(-1, 1))
    dist, neigh = dist.ravel(), neigh.ravel()

    keep = np.ones(len(treated_idx), dtype=bool)
    if caliper is not None:
        keep = dist <= caliper

    matched_treated = treated_idx[keep]
    matched_control = control_idx[neigh[keep]]

    y = data[outcome].astype(float).values
    pair_diff = y[matched_treated] - y[matched_control]
    att = float(pair_diff.mean())

    rng = np.random.default_rng(seed)
    boot = [
        float(rng.choice(pair_diff, size=len(pair_diff), replace=True).mean())
        for _ in range(n_bootstrap)
    ]
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])

    # Balance diagnostics before and after matching.
    before, after = {}, {}
    for c in covariates:
        before[c] = standardised_mean_diff(X.loc[t == 1, c].values, X.loc[t == 0, c].values)
        after[c] = standardised_mean_diff(
            X.iloc[matched_treated][c].values, X.iloc[matched_control][c].values
        )
    max_before = max(before.values()) if before else 0.0
    max_after = max(after.values()) if after else 0.0

    naive = float(y[t.values == 1].mean() - y[t.values == 0].mean())

    return {
        "method": "propensity_score_matching",
        "effect": att,
        "ate": att,
        "ci": [float(lo), float(hi)],
        "ci_level": 1 - alpha,
        "std_err": float(np.std(pair_diff, ddof=1) / np.sqrt(len(pair_diff))),
        "naive_estimate": naive,
        "confounding_bias": naive - att,
        "n_treated": int(len(treated_idx)),
        "n_control": int(len(control_idx)),
        "n_matched_pairs": int(len(matched_treated)),
        "caliper": caliper,
        "balance_smd_before": before,
        "balance_smd_after": after,
        "max_smd_before": max_before,
        "max_smd_after": max_after,
        "balanced": bool(max_after < 0.1),
        "propensity_scores": ps.tolist(),
        "treatment_flags": t.tolist(),
        "alpha": alpha,
    }


def dowhy_propensity_estimate(
    df: pd.DataFrame,
    treatment: str,
    outcome: str,
    covariates: Sequence[str],
    refute: bool = True,
    seed: int = 42,
) -> Dict[str, object]:
    """Estimate the ATE with DoWhy's backdoor propensity-score matching."""
    try:
        from dowhy import CausalModel  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("DoWhy is not installed") from exc

    data = df[[treatment, outcome] + list(covariates)].dropna().copy()
    model = CausalModel(
        data=data,
        treatment=treatment,
        outcome=outcome,
        common_causes=list(covariates),
    )
    identified = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(
        identified,
        method_name="backdoor.propensity_score_matching",
        target_units="ate",
        control_value=0,
        treatment_value=1,
    )
    estimator_name = getattr(estimate, "estimator_name", None)
    if estimator_name is None:
        estimator = getattr(estimate, "estimator", None)
        estimator_name = type(estimator).__name__ if estimator is not None else "backdoor.propensity_score_matching"
    result: Dict[str, object] = {
        "method": "dowhy_psm",
        "effect": float(estimate.value),
        "ate": float(estimate.value),
        "estimator": str(estimator_name),
    }

    if refute:
        try:
            ref = model.refute_estimate(
                identified,
                estimate,
                method_name="random_common_cause",
                num_simulations=20,
                random_seed=seed,
            )
            result["refutation_random_common_cause"] = {
                "new_effect": float(ref.new_effect),
                "change": float(ref.new_effect - estimate.value),
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("DoWhy refutation failed: %s", exc)
    return result

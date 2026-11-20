"""Synthetic control method (Milestone 6).

Constructs a weighted combination of untreated "donor" units that best tracks
the treated unit during the pre-period, then reads the post-period gap as the
causal effect.  Weights are constrained to be non-negative and sum to one
(Abadie & Gardeazabal).  A placebo/permutation test provides a p-value.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize

__all__ = ["synthetic_control"]


def _fit_weights(y_pre: np.ndarray, Y_pre: np.ndarray) -> np.ndarray:
    """Solve for donor weights minimising ||y_pre - Y_pre @ w||, w>=0, sum(w)=1."""
    n_donors = Y_pre.shape[1]
    w0 = np.full(n_donors, 1.0 / n_donors)

    def loss(w: np.ndarray) -> float:
        resid = y_pre - Y_pre @ w
        return float(resid @ resid)

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = [(0.0, 1.0)] * n_donors
    res = minimize(loss, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"maxiter": 1000, "ftol": 1e-12})
    w = np.clip(res.x, 0, None)
    return w / w.sum() if w.sum() > 0 else w0


def synthetic_control(
    df: pd.DataFrame,
    unit_col: str,
    time_col: str,
    outcome_col: str,
    treated_unit,
    treatment_time,
    donor_units: Optional[Sequence] = None,
    alpha: float = 0.05,
) -> Dict[str, object]:
    """Estimate the effect of an intervention on a single treated unit.

    Parameters
    ----------
    treated_unit:
        The unit that received the intervention (e.g. ``"California"``).
    treatment_time:
        First period the intervention is active (e.g. ``1989``).
    donor_units:
        Optional explicit list of comparison units; defaults to all others.
    """
    pivot = df.pivot_table(index=time_col, columns=unit_col, values=outcome_col).sort_index()
    if treated_unit not in pivot.columns:
        raise ValueError(f"treated_unit '{treated_unit}' not in {unit_col} column")

    donors = list(donor_units) if donor_units is not None else [
        c for c in pivot.columns if c != treated_unit
    ]
    times = pivot.index.values
    pre_mask = times < treatment_time
    post_mask = times >= treatment_time

    y_treated = pivot[treated_unit].astype(float)
    Y_donors = pivot[donors].astype(float)

    # Scale every series by the *same* constant so the optimisation is well
    # conditioned while relative levels are preserved (essential for matching
    # the treated unit's level, which is the whole point of synthetic control).
    pooled = Y_donors.loc[pre_mask].values
    scale = float(np.nanstd(pooled))
    scale = scale if scale > 0 else 1.0
    Y_scaled = Y_donors / scale
    y_scaled = y_treated / scale

    weights = _fit_weights(y_scaled.loc[pre_mask].values, Y_scaled.loc[pre_mask].values)
    synthetic = pd.Series(Y_donors.values @ weights, index=pivot.index)
    gap = y_treated - synthetic

    pre_rmse = float(np.sqrt(np.mean(gap.loc[pre_mask].values ** 2)))
    att = float(gap.loc[post_mask].mean())
    pre_mean = float(gap.loc[pre_mask].mean())

    # Placebo test: recompute for each donor as pseudo-treated unit.
    placebo_gaps = []
    for donor in donors:
        others = [d for d in donors if d != donor]
        if not others:
            continue
        w_pl = _fit_weights(
            (Y_donors.loc[pre_mask, donor] / scale).values,
            (Y_donors.loc[pre_mask, others] / scale).values,
        )
        synth_pl = Y_donors.loc[:, others].values @ w_pl
        gap_pl = (Y_donors[donor].values - synth_pl)
        placebo_gaps.append(abs(np.mean(gap_pl[post_mask])))

    placebo_gaps = np.asarray(placebo_gaps)
    p_value = float(np.mean(placebo_gaps >= abs(att))) if len(placebo_gaps) else np.nan

    weight_table = sorted(
        [{"unit": d, "weight": float(w)} for d, w in zip(donors, weights)],
        key=lambda r: r["weight"],
        reverse=True,
    )

    return {
        "method": "synthetic_control",
        "effect": att,
        "att": att,
        "pre_period_rmse": pre_rmse,
        "pre_period_bias": pre_mean,
        "p_value": p_value,
        "significant": bool(p_value < alpha) if not np.isnan(p_value) else False,
        "treated_unit": treated_unit,
        "treatment_time": treatment_time,
        "n_donors": len(donors),
        "weights": weight_table,
        "time": [str(t) for t in pivot.index.tolist()],
        "treated": y_treated.tolist(),
        "synthetic": synthetic.tolist(),
        "gap": gap.tolist(),
        "pre_mask": pre_mask.tolist(),
        "alpha": alpha,
    }

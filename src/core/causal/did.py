"""Difference-in-differences (DiD) estimator (Milestone 6).

Uses an OLS regression of the outcome on group, time and their interaction,
with heteroskedasticity-robust standard errors.  The interaction coefficient
is the average treatment effect on the treated (ATT).
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

__all__ = ["difference_in_differences"]


def difference_in_differences(
    df: pd.DataFrame,
    outcome: str,
    treated_col: str,
    post_col: str,
    covariates: Optional[Sequence[str]] = None,
    alpha: float = 0.05,
) -> Dict[str, object]:
    """Estimate the ATT with a two-group, two-period DiD regression.

    Parameters
    ----------
    outcome:
        Numeric outcome column.
    treated_col:
        0/1 indicator of belonging to the treated group.
    post_col:
        0/1 indicator for the post-treatment period.
    covariates:
        Optional list of additional control variables.
    """
    data = df[[outcome, treated_col, post_col] + list(covariates or [])].dropna().copy()
    data[treated_col] = data[treated_col].astype(float)
    data[post_col] = data[post_col].astype(float)

    covar_terms = f" + {' + '.join(covariates)}" if covariates else ""
    formula = (
        f"{outcome} ~ {treated_col} + {post_col} + "
        f"{treated_col}:{post_col}{covar_terms}"
    )
    model = smf.ols(formula, data=data).fit(cov_type="HC1")

    interaction = f"{treated_col}:{post_col}"
    att = float(model.params.get(interaction, np.nan))
    ci = model.conf_int(alpha=alpha).loc[interaction].tolist()
    p_value = float(model.pvalues.get(interaction, np.nan))

    # Naive (unadjusted) difference-in-means for comparison.
    means = data.groupby([treated_col, post_col])[outcome].mean()
    try:
        naive = float(
            (means.loc[(1.0, 1.0)] - means.loc[(1.0, 0.0)])
            - (means.loc[(0.0, 1.0)] - means.loc[(0.0, 0.0)])
        )
    except KeyError:
        naive = np.nan

    # Build the 2x2 cell means table for charting.
    cell_means = {
        "control_pre": float(means.get((0.0, 0.0), np.nan)),
        "control_post": float(means.get((0.0, 1.0), np.nan)),
        "treated_pre": float(means.get((1.0, 0.0), np.nan)),
        "treated_post": float(means.get((1.0, 1.0), np.nan)),
    }

    return {
        "method": "difference_in_differences",
        "att": att,
        "effect": att,
        "ci": [float(ci[0]), float(ci[1])],
        "ci_level": 1 - alpha,
        "p_value": p_value,
        "std_err": float(model.bse.get(interaction, np.nan)),
        "naive_estimate": naive,
        "significant": bool(p_value < alpha),
        "n_obs": int(model.nobs),
        "cell_means": cell_means,
        "r_squared": float(model.rsquared),
        "alpha": alpha,
    }

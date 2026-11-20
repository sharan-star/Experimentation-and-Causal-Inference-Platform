"""Frequentist hypothesis tests for A/B experiments (Milestone 3)."""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

__all__ = [
    "two_sample_ttest",
    "two_proportion_ztest",
    "chi_square_test",
    "welch_degrees_of_freedom",
]


def two_sample_ttest(
    control: Sequence[float],
    treatment: Sequence[float],
    alpha: float = 0.05,
    equal_var: bool = False,
) -> Dict[str, float]:
    """Welch's two-sample t-test on a continuous metric.

    Returns means, absolute/relative lift, a confidence interval for the
    difference, the t statistic, p-value and Cohen's d.
    """
    a = np.asarray(control, dtype=float)
    b = np.asarray(treatment, dtype=float)
    n_a, n_b = len(a), len(b)
    if n_a < 2 or n_b < 2:
        raise ValueError("Each arm needs at least 2 observations")

    mean_a, mean_b = a.mean(), b.mean()
    var_a, var_b = a.var(ddof=1), b.var(ddof=1)
    diff = mean_b - mean_a

    se = np.sqrt(var_a / n_a + var_b / n_b)
    t_stat, p_value = stats.ttest_ind(b, a, equal_var=equal_var)

    # Welch–Satterthwaite degrees of freedom
    df = welch_degrees_of_freedom(var_a, n_a, var_b, n_b) if not equal_var else n_a + n_b - 2
    crit = stats.t.ppf(1 - alpha / 2, df)
    ci = (diff - crit * se, diff + crit * se)

    # Cohen's d using pooled SD
    pooled_sd = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    cohens_d = diff / pooled_sd if pooled_sd > 0 else 0.0

    return {
        "test": "welch_ttest" if not equal_var else "student_ttest",
        "n_control": int(n_a),
        "n_treatment": int(n_b),
        "mean_control": float(mean_a),
        "mean_treatment": float(mean_b),
        "absolute_lift": float(diff),
        "relative_lift": float(diff / mean_a) if mean_a != 0 else None,
        "ci_lower": float(ci[0]),
        "ci_upper": float(ci[1]),
        "ci_level": 1 - alpha,
        "std_err": float(se),
        "t_stat": float(t_stat),
        "degrees_of_freedom": float(df),
        "p_value": float(p_value),
        "cohens_d": float(cohens_d),
        "significant": bool(p_value < alpha),
        "alpha": alpha,
    }


def welch_degrees_of_freedom(var_a: float, n_a: int, var_b: float, n_b: int) -> float:
    """Welch–Satterthwaite approximation for unequal-variance t-tests."""
    num = (var_a / n_a + var_b / n_b) ** 2
    den = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    return num / den if den > 0 else float(n_a + n_b - 2)


def two_proportion_ztest(
    control_success: int,
    control_n: int,
    treatment_success: int,
    treatment_n: int,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """Two-proportion z-test for a binary (conversion) metric."""
    if control_n <= 0 or treatment_n <= 0:
        raise ValueError("Sample sizes must be positive")

    p_a = control_success / control_n
    p_b = treatment_success / treatment_n
    diff = p_b - p_a

    z_stat, p_value = proportions_ztest(
        count=[treatment_success, control_success],
        nobs=[treatment_n, control_n],
        alternative="two-sided",
    )

    se = np.sqrt(p_a * (1 - p_a) / control_n + p_b * (1 - p_b) / treatment_n)
    crit = stats.norm.ppf(1 - alpha / 2)
    ci = (diff - crit * se, diff + crit * se)

    # Cohen's h for proportions
    cohens_h = 2 * np.arcsin(np.sqrt(p_b)) - 2 * np.arcsin(np.sqrt(p_a))

    return {
        "test": "two_proportion_ztest",
        "n_control": int(control_n),
        "n_treatment": int(treatment_n),
        "success_control": int(control_success),
        "success_treatment": int(treatment_success),
        "rate_control": float(p_a),
        "rate_treatment": float(p_b),
        "absolute_lift": float(diff),
        "relative_lift": float(diff / p_a) if p_a != 0 else None,
        "ci_lower": float(ci[0]),
        "ci_upper": float(ci[1]),
        "ci_level": 1 - alpha,
        "std_err": float(se),
        "z_stat": float(z_stat),
        "p_value": float(p_value),
        "cohens_h": float(cohens_h),
        "significant": bool(p_value < alpha),
        "alpha": alpha,
    }


def chi_square_test(table: Sequence[Sequence[int]], alpha: float = 0.05) -> Dict[str, float]:
    """Pearson chi-square test of independence on a contingency table.

    ``table`` is a 2-D array of observed counts (rows = groups, columns = outcomes).
    """
    observed = np.asarray(table, dtype=float)
    if observed.ndim != 2 or observed.shape[0] < 2 or observed.shape[1] < 2:
        raise ValueError("Need a 2x2 (or larger) contingency table")

    chi2, p_value, dof, expected = stats.chi2_contingency(observed)
    n = observed.sum()
    cramers_v = np.sqrt(chi2 / (n * (min(observed.shape) - 1)))

    return {
        "test": "chi_square",
        "chi2_stat": float(chi2),
        "p_value": float(p_value),
        "degrees_of_freedom": int(dof),
        "cramers_v": float(cramers_v),
        "expected": expected.tolist(),
        "significant": bool(p_value < alpha),
        "alpha": alpha,
    }

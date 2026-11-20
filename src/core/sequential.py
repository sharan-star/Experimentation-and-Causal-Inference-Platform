"""Sequential / "peek-safe" testing (Milestone 4).

Two complementary tools are provided:

* **Group-sequential boundaries** using Lan-DeMets alpha-spending functions
  (O'Brien-Fleming and Pocock).  These tell a team the *adjusted* critical
  p-value / z-score at each interim look so that the family-wise type-I error
  stays at ``alpha``.
* **Always-valid p-values (mSPRT)** via a Gaussian mixture sequential
  probability ratio test.  These remain valid no matter how often you peek,
  which is the strongest answer to "can we check the results early?".
"""
from __future__ import annotations

from itertools import product
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.stats import multivariate_normal, norm

__all__ = [
    "obrien_fleming_spending",
    "pocock_spending",
    "group_sequential_boundaries",
    "always_valid_pvalue_continuous",
    "always_valid_pvalue_binary",
    "sequential_monitoring",
]


# ---------------------------------------------------------------------------
# Alpha-spending functions
# ---------------------------------------------------------------------------
def obrien_fleming_spending(t: np.ndarray, alpha: float) -> np.ndarray:
    """Lan-DeMets O'Brien-Fleming spending function ``alpha*(t)``."""
    t = np.asarray(t, dtype=float)
    z = norm.ppf(1 - alpha / 2.0)
    return 2.0 * (1.0 - norm.cdf(z / np.sqrt(t)))


def pocock_spending(t: np.ndarray, alpha: float) -> np.ndarray:
    """Lan-DeMets Pocock spending function ``alpha*(t)``."""
    t = np.asarray(t, dtype=float)
    return alpha * np.log(1.0 + (np.e - 1.0) * t)


_SPENDING = {
    "obrien-fleming": obrien_fleming_spending,
    "obrien_fleming": obrien_fleming_spending,
    "obf": obrien_fleming_spending,
    "pocock": pocock_spending,
}


def _corr_matrix(t: np.ndarray) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    k = len(t)
    idx = np.arange(k)
    i, j = np.meshgrid(idx, idx, indexing="ij")
    lo = np.minimum(i, j)
    hi = np.maximum(i, j)
    return np.sqrt(t[lo] / t[hi])


def _orthant_prob(corr: np.ndarray, point: np.ndarray) -> float:
    """P(Z <= point) for ``Z ~ N(0, corr)`` (a lower-orthant probability)."""
    k = len(point)
    if k == 1:
        return float(norm.cdf(point[0]))
    mvn = multivariate_normal(mean=np.zeros(k), cov=corr, allow_singular=True)
    return float(mvn.cdf(point))


def _no_cross_prob(boundaries: Sequence[float], t: Sequence[float]) -> float:
    """Probability that the sequential statistics never cross any boundary.

    This is the rectangular probability ``P(-b_i <= Z_i <= b_i for all i)`` for
    the correlated (canonical joint distribution) test statistics.  It is
    evaluated with the inclusion-exclusion expansion of a multivariate normal
    rectangle probability::

        P(a < Z <= b) = sum_{S} (-1)^{|S|} P(Z <= c_S)

    where ``c_{S,i} = a_i`` if ``i in S`` else ``b_i``.  With ``a_i = -b_i``
    this gives the two-sided probability scipy's ``multivariate_normal.cdf``
    cannot express directly (it only accepts a single lower-limit vector).
    """
    k = len(boundaries)
    if k == 0:
        return 1.0
    corr = _corr_matrix(np.asarray(t[:k], dtype=float))
    b = np.asarray(boundaries, dtype=float)
    total = 0.0
    for signs in product((1.0, -1.0), repeat=k):
        s = np.asarray(signs)
        total += ((-1) ** int(np.sum(s < 0))) * _orthant_prob(corr, b * s)
    return float(min(1.0, max(0.0, total)))


def group_sequential_boundaries(
    n_looks: int,
    alpha: float = 0.05,
    spending: str = "obrien-fleming",
    information_times: Optional[Sequence[float]] = None,
) -> Dict[str, list]:
    """Compute two-sided critical z / p-value boundaries for ``n_looks`` looks.

    ``information_times`` are the information fractions (default: equally
    spaced ``k / n_looks``).  The boundaries guarantee an overall two-sided
    type-I error of ``alpha`` under the null, accounting for the correlation
    between the sequential test statistics.
    """
    if n_looks < 1:
        raise ValueError("n_looks must be >= 1")
    key = spending.lower().strip()
    if key not in _SPENDING:
        raise ValueError(f"Unknown spending function '{spending}'")
    spend = _SPENDING[key]

    if information_times is None:
        t = np.arange(1, n_looks + 1) / n_looks
    else:
        t = np.asarray(information_times, dtype=float)
        if len(t) != n_looks:
            raise ValueError("information_times length must equal n_looks")

    cumulative = spend(t, alpha)
    boundaries: List[float] = []
    for k in range(n_looks):
        target = 1.0 - cumulative[k]
        lo, hi = 0.0, 12.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            p = _no_cross_prob(boundaries + [mid], t.tolist())
            if p > target:
                hi = mid
            else:
                lo = mid
        boundaries.append(0.5 * (lo + hi))

    nominal_p = [
        float(cumulative[0]) if k == 0 else float(cumulative[k] - cumulative[k - 1])
        for k in range(n_looks)
    ]

    return {
        "spending": key,
        "alpha": alpha,
        "n_looks": n_looks,
        "information_times": t.tolist(),
        "cumulative_alpha": cumulative.tolist(),
        "z_boundaries": boundaries,
        "nominal_p_boundaries": nominal_p,
    }


# ---------------------------------------------------------------------------
# Always-valid p-values (mSPRT)
# ---------------------------------------------------------------------------
def always_valid_pvalue_continuous(
    mean_diff: float,
    n: int,
    sigma: float,
    tau: Optional[float] = None,
) -> float:
    """Always-valid p-value for a difference in means (Gaussian mixture).

    Parameters
    ----------
    mean_diff:
        Current estimate of the treatment-minus-control mean difference.
    n:
        Effective sample size *per arm* (so the variance of ``mean_diff`` is
        ``2*sigma^2/n``).
    sigma:
        Per-observation standard deviation (plug-in estimate).
    tau:
        Prior standard deviation of the effect under the alternative
        (mixture).  Defaults to ``sigma / sqrt(n)``-independent scale of
        ``0.5 * sigma``.
    """
    if n <= 0:
        return 1.0
    sigma = max(float(sigma), 1e-12)
    if tau is None:
        tau = 0.5 * sigma
    tau = max(float(tau), 1e-12)

    # Variance of the observed mean difference:
    v = 2.0 * sigma ** 2 / n
    # Mixture likelihood ratio for a Gaussian prior N(0, tau^2) on the effect.
    # Lambda = sqrt(v / (v + tau^2)) * exp( tau^2 * mean_diff^2 / (2 * v * (v + tau^2)) )
    log_lambda = 0.5 * np.log(v / (v + tau ** 2)) + (tau ** 2 * mean_diff ** 2) / (
        2.0 * v * (v + tau ** 2)
    )
    return float(min(1.0, np.exp(-log_lambda)))


def always_valid_pvalue_binary(
    p_control: float,
    p_treatment: float,
    n_control: int,
    n_treatment: int,
    tau: Optional[float] = None,
) -> float:
    """Always-valid p-value for a difference in proportions (normal approx)."""
    if n_control <= 0 or n_treatment <= 0:
        return 1.0
    diff = p_treatment - p_control
    # Variance of the difference in proportions under a plug-in pooled estimate
    p_pool = (p_control * n_control + p_treatment * n_treatment) / (n_control + n_treatment)
    var = p_pool * (1 - p_pool) * (1.0 / n_control + 1.0 / n_treatment)
    var = max(var, 1e-12)
    if tau is None:
        tau = max(0.02, 0.5 * np.sqrt(var))  # sensible default for conversion lift
    tau = max(float(tau), 1e-12)

    log_lambda = 0.5 * np.log(var / (var + tau ** 2)) + (tau ** 2 * diff ** 2) / (
        2.0 * var * (var + tau ** 2)
    )
    return float(min(1.0, np.exp(-log_lambda)))


# ---------------------------------------------------------------------------
# Monitoring a data stream at several looks
# ---------------------------------------------------------------------------
def sequential_monitoring(
    control: Sequence[float],
    treatment: Sequence[float],
    n_looks: int = 5,
    alpha: float = 0.05,
    spending: str = "obrien-fleming",
    metric_type: str = "continuous",
) -> Dict[str, object]:
    """Evaluate an experiment at ``n_looks`` equally spaced look points.

    Returns, for each look: the naive p-value (what you would get if you
    peeked without correction), the alpha-spending boundary, and the
    always-valid p-value.
    """
    a = np.asarray(control, dtype=float)
    b = np.asarray(treatment, dtype=float)
    n_total_per_arm = min(len(a), len(b))
    if n_total_per_arm < n_looks:
        raise ValueError("Not enough observations for the requested number of looks")

    look_sizes = np.linspace(n_total_per_arm // n_looks, n_total_per_arm, n_looks).astype(int)
    boundaries = group_sequential_boundaries(n_looks, alpha, spending)

    looks: List[Dict[str, float]] = []
    for k, m in enumerate(look_sizes):
        a_k, b_k = a[:m], b[:m]
        mean_diff = float(b_k.mean() - a_k.mean())
        if metric_type == "continuous":
            var_a = a_k.var(ddof=1) if m > 1 else 0.0
            var_b = b_k.var(ddof=1) if m > 1 else 0.0
            se = np.sqrt(var_a / m + var_b / m) if m > 1 else np.nan
            from scipy.stats import ttest_ind

            naive_p = float(ttest_ind(b_k, a_k, equal_var=False).pvalue) if m > 1 else 1.0
            sigma = np.sqrt((var_a + var_b) / 2.0)
            av_p = always_valid_pvalue_continuous(mean_diff, m, sigma if sigma > 0 else 1e-6)
        else:  # binary
            pc, pt = float(a_k.mean()), float(b_k.mean())
            from statsmodels.stats.proportion import proportions_ztest

            try:
                naive_p = float(
                    proportions_ztest(
                        [int(b_k.sum()), int(a_k.sum())], [m, m], alternative="two-sided"
                    )[1]
                )
            except Exception:
                naive_p = 1.0
            av_p = always_valid_pvalue_binary(pc, pt, m, m)

        z_obs = float(norm.ppf(1 - naive_p / 2)) if 0 < naive_p < 1 else float("inf")

        looks.append(
            {
                "look": k + 1,
                "n_per_arm": int(m),
                "mean_control": float(a_k.mean()),
                "mean_treatment": float(b_k.mean()),
                "effect": mean_diff,
                "z_stat": z_obs,
                "naive_p_value": naive_p,
                "z_boundary": boundaries["z_boundaries"][k],
                "nominal_p_boundary": boundaries["nominal_p_boundaries"][k],
                "always_valid_p_value": av_p,
                "crosses_boundary": bool(abs(z_obs) >= boundaries["z_boundaries"][k]),
                "always_valid_significant": bool(av_p < alpha),
            }
        )

    return {
        "alpha": alpha,
        "metric_type": metric_type,
        "spending": boundaries["spending"],
        "boundaries": boundaries,
        "looks": looks,
        "final_decision": "reject_null"
        if looks[-1]["crosses_boundary"] or looks[-1]["always_valid_significant"]
        else "fail_to_reject_null",
    }

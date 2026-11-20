"""Bayesian A/B analysis with PyMC (Milestone 5).

The headline number is ``P(B beats A)`` — the posterior probability that the
treatment is better than the control — together with the expected loss of
shipping the wrong variant and a 95% credible interval on the lift.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

try:  # PyMC is optional at runtime so the API still works without it.
    import pymc as pm  # type: ignore

    _HAS_PYMC = True
except Exception:  # pragma: no cover
    _HAS_PYMC = False
    logger.warning("PyMC not available - falling back to closed-form posteriors")

__all__ = ["bayesian_ab_binary", "bayesian_ab_continuous"]


def _summarise_samples(diff_samples: np.ndarray, alpha: float = 0.05) -> Dict[str, object]:
    diff_samples = np.asarray(diff_samples, dtype=float).ravel()
    prob_better = float(np.mean(diff_samples > 0))
    expected_loss_treatment = float(np.mean(np.clip(-diff_samples, 0, None)))
    expected_loss_control = float(np.mean(np.clip(diff_samples, 0, None)))
    lo, hi = np.percentile(diff_samples, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    hist, edges = np.histogram(diff_samples, bins=40)

    if prob_better >= 0.95:
        decision = "ship_treatment"
    elif prob_better <= 0.05:
        decision = "keep_control"
    else:
        decision = "inconclusive"

    return {
        "prob_treatment_better": prob_better,
        "prob_control_better": 1 - prob_better,
        "posterior_mean_diff": float(diff_samples.mean()),
        "posterior_std_diff": float(diff_samples.std()),
        "credible_interval": [float(lo), float(hi)],
        "credible_level": 1 - alpha,
        "expected_loss_if_ship_treatment": expected_loss_treatment,
        "expected_loss_if_keep_control": expected_loss_control,
        "decision": decision,
        "posterior_histogram": {"counts": hist.tolist(), "edges": edges.tolist()},
    }


def _beta_posterior_samples(a: float, b: float, size: int, rng: np.random.Generator) -> np.ndarray:
    return rng.beta(a, b, size=size)


def bayesian_ab_binary(
    control_success: int,
    control_n: int,
    treatment_success: int,
    treatment_n: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    draws: int = 4000,
    seed: int = 42,
) -> Dict[str, object]:
    """Bayesian analysis of a binary (conversion) A/B test.

    Uses a Beta-Binomial model.  When PyMC is installed the posterior is
    sampled with MCMC; otherwise an exact Beta conjugate posterior is used
    (they agree closely for this model).
    """
    rng = np.random.default_rng(seed)
    post_alpha_a = prior_alpha + control_success
    post_beta_a = prior_beta + (control_n - control_success)
    post_alpha_b = prior_alpha + treatment_success
    post_beta_b = prior_beta + (treatment_n - treatment_success)

    used_pymc = False
    if _HAS_PYMC:
        try:
            with pm.Model():
                p_a = pm.Beta("p_a", alpha=prior_alpha, beta=prior_beta)
                p_b = pm.Beta("p_b", alpha=prior_alpha, beta=prior_beta)
                pm.Binomial("obs_a", n=control_n, p=p_a, observed=control_success)
                pm.Binomial("obs_b", n=treatment_n, p=p_b, observed=treatment_success)
                diff = pm.Deterministic("diff", p_b - p_a)
                idata = pm.sample(
                    draws=draws,
                    tune=max(500, draws // 2),
                    chains=2,
                    cores=1,
                    progressbar=False,
                    random_seed=seed,
                    target_accept=0.9,
                )
            diff_samples = idata.posterior["diff"].values.ravel()
            used_pymc = True
        except Exception as exc:  # pragma: no cover
            logger.warning("PyMC sampling failed (%s); using conjugate posterior", exc)

    if not used_pymc:
        p_a_samples = _beta_posterior_samples(post_alpha_a, post_beta_a, draws, rng)
        p_b_samples = _beta_posterior_samples(post_alpha_b, post_beta_b, draws, rng)
        diff_samples = p_b_samples - p_a_samples

    summary = _summarise_samples(diff_samples)
    rate_a = control_success / control_n
    rate_b = treatment_success / treatment_n
    summary.update(
        {
            "method": "beta_binomial",
            "engine": "pymc" if used_pymc else "conjugate",
            "rate_control": float(rate_a),
            "rate_treatment": float(rate_b),
            "posterior_mean_control": float(post_alpha_a / (post_alpha_a + post_beta_a)),
            "posterior_mean_treatment": float(post_alpha_b / (post_alpha_b + post_beta_b)),
            "relative_lift_posterior_mean": float(
                np.mean(diff_samples) / rate_a if rate_a > 0 else np.nan
            ),
            "n_control": int(control_n),
            "n_treatment": int(treatment_n),
        }
    )
    return summary


def bayesian_ab_continuous(
    control: Sequence[float],
    treatment: Sequence[float],
    draws: int = 4000,
    seed: int = 42,
) -> Dict[str, object]:
    """Bayesian analysis of a continuous A/B test (Normal likelihood)."""
    a = np.asarray(control, dtype=float)
    b = np.asarray(treatment, dtype=float)
    pooled = np.concatenate([a, b])
    prior_mu = float(pooled.mean())
    prior_sigma = float(pooled.std() + 1e-6)

    used_pymc = False
    diff_samples: Optional[np.ndarray] = None

    if _HAS_PYMC:
        try:
            with pm.Model():
                mu_a = pm.Normal("mu_a", mu=prior_mu, sigma=2 * prior_sigma)
                mu_b = pm.Normal("mu_b", mu=prior_mu, sigma=2 * prior_sigma)
                sigma_a = pm.HalfNormal("sigma_a", sigma=2 * prior_sigma)
                sigma_b = pm.HalfNormal("sigma_b", sigma=2 * prior_sigma)
                pm.Normal("obs_a", mu=mu_a, sigma=sigma_a, observed=a)
                pm.Normal("obs_b", mu=mu_b, sigma=sigma_b, observed=b)
                diff = pm.Deterministic("diff", mu_b - mu_a)
                idata = pm.sample(
                    draws=draws,
                    tune=max(500, draws // 2),
                    chains=2,
                    cores=1,
                    progressbar=False,
                    random_seed=seed,
                    target_accept=0.9,
                )
            diff_samples = idata.posterior["diff"].values.ravel()
            used_pymc = True
        except Exception as exc:  # pragma: no cover
            logger.warning("PyMC sampling failed (%s); using normal approximation", exc)

    if diff_samples is None:
        # Normal-normal approximation using a weakly informative prior.
        rng = np.random.default_rng(seed)
        var_diff = a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)
        post_mean = b.mean() - a.mean() + (var_diff / (var_diff + (2 * prior_sigma) ** 2)) * 0
        diff_samples = rng.normal(post_mean, np.sqrt(var_diff), size=draws)

    summary = _summarise_samples(diff_samples)
    mean_a, mean_b = float(a.mean()), float(b.mean())
    summary.update(
        {
            "method": "normal_normal",
            "engine": "pymc" if used_pymc else "normal_approx",
            "mean_control": mean_a,
            "mean_treatment": mean_b,
            "relative_lift_posterior_mean": float(
                np.mean(diff_samples) / mean_a if mean_a != 0 else np.nan
            ),
            "n_control": int(len(a)),
            "n_treatment": int(len(b)),
        }
    )
    return summary

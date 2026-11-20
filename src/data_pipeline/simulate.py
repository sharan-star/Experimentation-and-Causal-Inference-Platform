"""Simulated A/B experiment data generators.

Everything in this module is deterministic given a ``seed`` so results can be
reproduced in notebooks, tests and the API.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

__all__ = [
    "simulate_continuous_ab",
    "simulate_binary_ab",
    "simulate_multimetric_ab",
    "simulate_sequential_stream",
    "simulate_confounded_observational",
]


def simulate_continuous_ab(
    n_a: int = 1000,
    n_b: int = 1000,
    mean_a: float = 10.0,
    mean_b: Optional[float] = None,
    relative_lift: float = 0.05,
    std: float = 5.0,
    seed: Optional[int] = 42,
    metric_name: str = "revenue",
) -> pd.DataFrame:
    """Simulate a two-arm experiment with a continuous outcome.

    Parameters
    ----------
    mean_a, mean_b:
        Absolute means for the two arms. If ``mean_b`` is ``None`` it is derived
        from ``mean_a * (1 + relative_lift)``.
    """
    if mean_b is None:
        mean_b = mean_a * (1.0 + relative_lift)

    rng = np.random.default_rng(seed)
    control = rng.normal(mean_a, std, size=n_a)
    treatment = rng.normal(mean_b, std, size=n_b)

    df = pd.DataFrame(
        {
            "user_id": np.arange(1, n_a + n_b + 1),
            "variant": ["A"] * n_a + ["B"] * n_b,
            metric_name: np.concatenate([control, treatment]),
        }
    )
    return df


def simulate_binary_ab(
    n_a: int = 1000,
    n_b: int = 1000,
    p_a: float = 0.10,
    p_b: Optional[float] = None,
    relative_lift: float = 0.20,
    seed: Optional[int] = 42,
    metric_name: str = "converted",
) -> pd.DataFrame:
    """Simulate a two-arm experiment with a Bernoulli (conversion) outcome.

    ``p_b`` defaults to ``p_a * (1 + relative_lift)`` capped at 1.0.
    """
    if p_b is None:
        p_b = min(1.0, p_a * (1.0 + relative_lift))

    rng = np.random.default_rng(seed)
    control = rng.binomial(1, p_a, size=n_a)
    treatment = rng.binomial(1, p_b, size=n_b)

    df = pd.DataFrame(
        {
            "user_id": np.arange(1, n_a + n_b + 1),
            "variant": ["A"] * n_a + ["B"] * n_b,
            metric_name: np.concatenate([control, treatment]),
        }
    )
    return df


def simulate_multimetric_ab(
    n_per_arm: int = 1000,
    baseline_rates: Sequence[float] = (0.10, 0.15, 0.20, 0.05, 0.12),
    relative_lifts: Optional[Sequence[float]] = None,
    seed: Optional[int] = 7,
    metric_prefix: str = "metric",
) -> pd.DataFrame:
    """Simulate an experiment measuring several binary metrics at once.

    Useful for demonstrating multiple-testing corrections (Bonferroni / BH).
    By default only the *first* metric has a real effect and the rest are null,
    which makes the false-discovery machinery easy to visualise.
    """
    n_metrics = len(baseline_rates)
    if relative_lifts is None:
        relative_lifts = [0.0] * n_metrics
        relative_lifts[0] = 0.25  # only metric_0 truly moves

    rng = np.random.default_rng(seed)
    data: Dict[str, np.ndarray] = {
        "user_id": np.arange(1, 2 * n_per_arm + 1),
        "variant": ["A"] * n_per_arm + ["B"] * n_per_arm,
    }
    for i, (base, lift) in enumerate(zip(baseline_rates, relative_lifts)):
        p_b = min(1.0, base * (1.0 + lift))
        data[f"{metric_prefix}_{i}"] = np.concatenate(
            [
                rng.binomial(1, base, size=n_per_arm),
                rng.binomial(1, p_b, size=n_per_arm),
            ]
        )
    return pd.DataFrame(data)


def simulate_sequential_stream(
    n_total: int = 5000,
    p_a: float = 0.10,
    relative_lift: float = 0.10,
    seed: Optional[int] = 11,
) -> pd.DataFrame:
    """Simulate a single binary outcome stream with an incremental user index.

    The returned frame is ordered so peeking at prefixes (looks) is meaningful.
    """
    rng = np.random.default_rng(seed)
    p_b = min(1.0, p_a * (1.0 + relative_lift))
    n_per_arm = n_total // 2
    control = rng.binomial(1, p_a, size=n_per_arm)
    treatment = rng.binomial(1, p_b, size=n_per_arm)

    order = rng.permutation(2 * n_per_arm)  # interleave assignment order
    variants = np.array(["A"] * n_per_arm + ["B"] * n_per_arm)[order]
    outcomes = np.concatenate([control, treatment])[order]

    return pd.DataFrame(
        {
            "user_id": np.arange(1, 2 * n_per_arm + 1),
            "variant": variants,
            "converted": outcomes,
        }
    )


def simulate_confounded_observational(
    n: int = 2000,
    seed: Optional[int] = 3,
    treated_share: float = 0.35,
) -> pd.DataFrame:
    """Simulate observational data where treatment is *confounded*.

    Confounding means a naive comparison of treated vs. control is biased;
    it is the ideal playground for propensity-score matching and DoWhy.
    """
    rng = np.random.default_rng(seed)

    # Two confounders: age (continuous) and prior_spend (continuous).
    age = rng.normal(40, 12, size=n)
    prior_spend = rng.normal(50, 20, size=n) + 0.4 * age

    # Treatment assignment depends on the confounders (selection bias).
    latent = (
        0.05 * (age - 40)
        + 0.04 * (prior_spend - 50)
        + rng.normal(0, 1.0, size=n)
    )
    threshold = np.quantile(latent, 1 - treated_share)
    treatment = (latent >= threshold).astype(int)

    # True treatment effect is +5. The observed outcome is also driven by the
    # confounders, so the naive difference-in-means is biased upward.
    true_effect = 5.0
    noise = rng.normal(0, 8, size=n)
    outcome = 20 + 0.6 * age + 0.35 * prior_spend + true_effect * treatment + noise

    return pd.DataFrame(
        {
            "age": age,
            "prior_spend": prior_spend,
            "treatment": treatment,
            "outcome": outcome,
            "true_effect": true_effect,
        }
    )

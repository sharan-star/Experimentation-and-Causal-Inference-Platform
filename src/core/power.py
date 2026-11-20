"""Power analysis and sample-size calculations (Milestone 1 & 2).

Built on :mod:`statsmodels.stats.power` and
:mod:`statsmodels.stats.proportion`.
"""
from __future__ import annotations

from typing import Dict, Optional

from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize

__all__ = [
    "sample_size_two_proportions",
    "power_two_proportions",
    "mde_two_proportions",
    "sample_size_continuous",
    "power_continuous",
    "mde_continuous",
]

_ind_power = NormalIndPower()
_ttest_power = TTestIndPower()


def _round_up(value: float) -> int:
    import math

    return int(math.ceil(value))


def sample_size_two_proportions(
    p_control: float,
    p_treatment: Optional[float] = None,
    relative_lift: Optional[float] = None,
    alpha: float = 0.05,
    power: float = 0.80,
    ratio: float = 1.0,
) -> Dict[str, float]:
    """Sample size per arm needed to detect a difference between two proportions.

    Provide either ``p_treatment`` (absolute) or ``relative_lift``.
    """
    if p_treatment is None:
        if relative_lift is None:
            raise ValueError("Provide p_treatment or relative_lift")
        p_treatment = p_control * (1.0 + relative_lift)

    effect = proportion_effectsize(p_treatment, p_control)
    n_per_arm = _ind_power.solve_power(
        effect_size=abs(effect), alpha=alpha, power=power, ratio=ratio, alternative="two-sided"
    )
    n1 = _round_up(n_per_arm)
    n2 = _round_up(n_per_arm * ratio)
    return {
        "method": "two_proportions",
        "p_control": p_control,
        "p_treatment": p_treatment,
        "absolute_lift": p_treatment - p_control,
        "relative_lift": (p_treatment - p_control) / p_control,
        "cohens_h": effect,
        "alpha": alpha,
        "power": power,
        "n_control": n1,
        "n_treatment": n2,
        "n_total": n1 + n2,
    }


def power_two_proportions(
    p_control: float,
    p_treatment: float,
    n_control: int,
    n_treatment: Optional[int] = None,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """Statistical power for a two-proportion test given sample sizes."""
    if n_treatment is None:
        n_treatment = n_control
    effect = abs(proportion_effectsize(p_treatment, p_control))
    ratio = n_treatment / n_control
    power = _ind_power.power(
        effect_size=effect, nobs1=n_control, alpha=alpha, ratio=ratio, alternative="two-sided"
    )
    return {
        "method": "two_proportions",
        "power": float(power),
        "cohens_h": effect,
        "n_control": n_control,
        "n_treatment": n_treatment,
        "alpha": alpha,
    }


def mde_two_proportions(
    p_control: float,
    n_control: int,
    n_treatment: Optional[int] = None,
    alpha: float = 0.05,
    power: float = 0.80,
) -> Dict[str, float]:
    """Minimum detectable effect (Cohen's h) for a two-proportion test."""
    if n_treatment is None:
        n_treatment = n_control
    ratio = n_treatment / n_control
    h = _ind_power.solve_power(
        effect_size=None, nobs1=n_control, alpha=alpha, power=power, ratio=ratio,
        alternative="two-sided",
    )
    return {
        "method": "two_proportions",
        "cohens_h": float(h),
        "approx_absolute_lift": float(h) * (p_control * (1 - p_control)) ** 0.5,
        "alpha": alpha,
        "power": power,
        "n_control": n_control,
        "n_treatment": n_treatment,
    }


def sample_size_continuous(
    cohens_d: float,
    alpha: float = 0.05,
    power: float = 0.80,
    ratio: float = 1.0,
    two_sided: bool = True,
) -> Dict[str, float]:
    """Sample size per arm for a two-sample t-test on a continuous metric."""
    n_per_arm = _ttest_power.solve_power(
        effect_size=abs(cohens_d), alpha=alpha, power=power, ratio=ratio,
        alternative="two-sided" if two_sided else "larger",
    )
    n1 = _round_up(n_per_arm)
    n2 = _round_up(n_per_arm * ratio)
    return {
        "method": "continuous_ttest",
        "cohens_d": cohens_d,
        "alpha": alpha,
        "power": power,
        "n_control": n1,
        "n_treatment": n2,
        "n_total": n1 + n2,
    }


def power_continuous(
    cohens_d: float,
    n_control: int,
    n_treatment: Optional[int] = None,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """Power for a two-sample t-test given sample sizes."""
    if n_treatment is None:
        n_treatment = n_control
    ratio = n_treatment / n_control
    power = _ttest_power.power(
        effect_size=abs(cohens_d), nobs1=n_control, alpha=alpha, ratio=ratio,
        alternative="two-sided",
    )
    return {
        "method": "continuous_ttest",
        "power": float(power),
        "cohens_d": cohens_d,
        "n_control": n_control,
        "n_treatment": n_treatment,
        "alpha": alpha,
    }


def mde_continuous(
    n_control: int,
    n_treatment: Optional[int] = None,
    alpha: float = 0.05,
    power: float = 0.80,
) -> Dict[str, float]:
    """Minimum detectable Cohen's d for a two-sample t-test."""
    if n_treatment is None:
        n_treatment = n_control
    ratio = n_treatment / n_control
    d = _ttest_power.solve_power(
        effect_size=None, nobs1=n_control, alpha=alpha, power=power, ratio=ratio,
        alternative="two-sided",
    )
    return {
        "method": "continuous_ttest",
        "cohens_d": float(d),
        "alpha": alpha,
        "power": power,
        "n_control": n_control,
        "n_treatment": n_treatment,
    }

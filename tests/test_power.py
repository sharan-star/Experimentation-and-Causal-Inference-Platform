"""Tests for power analysis and sample-size calculations."""
from src.core import power


def test_sample_size_grows_as_effect_shrinks():
    small = power.sample_size_two_proportions(0.10, relative_lift=0.20)
    large = power.sample_size_two_proportions(0.10, relative_lift=0.05)
    assert large["n_total"] == large["n_control"] + large["n_treatment"]
    assert large["n_control"] > small["n_control"] > 0


def test_sample_size_achieves_target_power():
    result = power.sample_size_two_proportions(0.10, p_treatment=0.13, power=0.80)
    achieved = power.power_two_proportions(
        0.10, 0.13, result["n_control"], result["n_treatment"]
    )
    assert achieved["power"] >= 0.79


def test_continuous_sample_size_and_power_roundtrip():
    ss = power.sample_size_continuous(cohens_d=0.2, power=0.80)
    pwr = power.power_continuous(cohens_d=0.2, n_control=ss["n_control"],
                                 n_treatment=ss["n_treatment"])
    assert 0.78 <= pwr["power"] <= 0.90


def test_mde_is_positive_and_decreases_with_n():
    mde_small = power.mde_continuous(n_control=500)
    mde_large = power.mde_continuous(n_control=5000)
    assert 0 < mde_large["cohens_d"] < mde_small["cohens_d"]


def test_mde_proportions_returns_lift():
    mde = power.mde_two_proportions(p_control=0.10, n_control=1000)
    assert mde["cohens_h"] > 0
    assert mde["approx_absolute_lift"] > 0

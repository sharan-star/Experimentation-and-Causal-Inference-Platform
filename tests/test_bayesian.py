"""Tests for Bayesian A/B analysis."""
from src.core import bayesian


def test_binary_posterior_favours_clear_winner():
    out = bayesian.bayesian_ab_binary(
        control_success=1000, control_n=10000,
        treatment_success=1300, treatment_n=10000, draws=2000, seed=1,
    )
    assert out["prob_treatment_better"] > 0.99
    assert out["decision"] == "ship_treatment"
    assert out["credible_interval"][0] > 0
    assert "posterior_histogram" in out


def test_binary_posterior_inconclusive_on_null():
    out = bayesian.bayesian_ab_binary(
        control_success=1000, control_n=10000,
        treatment_success=1005, treatment_n=10000, draws=2000, seed=1,
    )
    assert 0.05 < out["prob_treatment_better"] < 0.95
    assert out["decision"] == "inconclusive"


def test_continuous_bayesian_runs():
    a = [10.0] * 500 + [11.0] * 500
    b = [12.0] * 500 + [13.0] * 500
    out = bayesian.bayesian_ab_continuous(a, b, draws=1500, seed=3)
    assert out["prob_treatment_better"] > 0.9
    assert out["posterior_mean_diff"] > 0
    assert out["engine"] in {"pymc", "normal_approx"}

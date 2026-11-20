"""Tests for frequentist hypothesis tests."""
import numpy as np
import pytest

from src.core import frequentist
from src.data_pipeline.simulate import simulate_binary_ab, simulate_continuous_ab


def test_welch_ttest_detects_large_effect():
    df = simulate_continuous_ab(n_a=2000, n_b=2000, mean_a=10, mean_b=12, std=5, seed=1)
    a = df.loc[df.variant == "A", "revenue"]
    b = df.loc[df.variant == "B", "revenue"]
    result = frequentist.two_sample_ttest(a, b)
    assert result["p_value"] < 0.05
    assert result["significant"] is True
    assert result["ci_lower"] > 0  # CI excludes zero
    assert 1.5 < result["absolute_lift"] < 2.5


def test_ttest_no_effect_not_significant():
    df = simulate_continuous_ab(n_a=1000, n_b=1000, mean_a=10, mean_b=10, std=5, seed=1)
    a = df.loc[df.variant == "A", "revenue"]
    b = df.loc[df.variant == "B", "revenue"]
    result = frequentist.two_sample_ttest(a, b)
    assert result["p_value"] > 0.05


def test_two_proportion_ztest():
    df = simulate_binary_ab(n_a=5000, n_b=5000, p_a=0.10, p_b=0.13, seed=2)
    a = df.loc[df.variant == "A", "converted"]
    b = df.loc[df.variant == "B", "converted"]
    result = frequentist.two_proportion_ztest(int(a.sum()), len(a), int(b.sum()), len(b))
    assert result["p_value"] < 0.05
    assert result["absolute_lift"] > 0
    assert result["cohens_h"] != 0


def test_chi_square_and_cramers_v():
    table = [[100, 50], [60, 90]]
    result = frequentist.chi_square_test(table)
    assert result["p_value"] < 0.05
    assert 0 < result["cramers_v"] <= 1
    assert result["significant"] is True


def test_ttest_requires_two_observations():
    with pytest.raises(ValueError):
        frequentist.two_sample_ttest([1.0], [2.0, 3.0])

"""Tests for multiple-testing corrections."""
from src.core import multiple_testing


def test_bonferroni_is_conservative_vs_bh():
    pvalues = [0.001, 0.01, 0.03, 0.04, 0.2, 0.5]
    bonf = multiple_testing.adjust_pvalues(pvalues, "bonferroni")
    bh = multiple_testing.adjust_pvalues(pvalues, "benjamini-hochberg")

    # BH always gives adjusted p-values <= Bonferroni
    assert all(b <= bo + 1e-12 for b, bo in zip(bh["adjusted_pvalues"], bonf["adjusted_pvalues"]))


def test_bonferroni_scales_by_number_of_tests():
    pvalues = [0.01, 0.02, 0.03, 0.04]
    bonf = multiple_testing.adjust_pvalues(pvalues, "bonferroni")
    assert abs(bonf["adjusted_pvalues"][0] - 0.04) < 1e-9  # 0.01 * 4
    assert bonf["reject"][0] is True


def test_analyze_metric_batch_structure():
    out = multiple_testing.analyze_metric_batch(
        [0.01, 0.2, 0.04], metric_names=["a", "b", "c"]
    )
    assert set(out["by_method"].keys()) == {"bonferroni", "benjamini-hochberg"}
    assert out["n_tests"] == 3


def test_unknown_method_raises():
    import pytest

    with pytest.raises(ValueError):
        multiple_testing.adjust_pvalues([0.1], "not-a-method")

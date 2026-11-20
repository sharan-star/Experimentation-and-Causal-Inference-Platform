"""Tests for causal-inference estimators."""
import pytest

from src.core.causal import did as did_core
from src.core.causal import propensity as psm_core
from src.core.causal import synthetic_control as sc_core
from src.core.causal import uplift as uplift_core
from src.data_pipeline import datasets
from src.data_pipeline.simulate import simulate_confounded_observational


def test_did_recovers_known_effect():
    df = datasets.load_card_krueger()
    out = did_core.difference_in_differences(
        df, outcome="fte_employment", treated_col="treated", post_col="post"
    )
    assert 1.0 < out["att"] < 2.0  # simulated effect is 1.5
    assert out["method"] == "difference_in_differences"


def test_psm_reduces_confounding_bias():
    df = simulate_confounded_observational(n=4000, seed=5)
    out = psm_core.propensity_score_matching(
        df, treatment="treatment", outcome="outcome",
        covariates=["age", "prior_spend"], caliper=0.2, n_bootstrap=100,
    )
    # PSM estimate should be closer to the true effect (5.0) than the naive one
    assert abs(out["effect"] - 5.0) < abs(out["naive_estimate"] - 5.0)
    assert out["max_smd_after"] < out["max_smd_before"]


def test_synthetic_control_detects_negative_effect():
    df = datasets.load_prop99()
    out = sc_core.synthetic_control(
        df, unit_col="state", time_col="year", outcome_col="cigsales",
        treated_unit="California", treatment_time=1989,
    )
    assert out["effect"] < 0
    assert out["pre_period_rmse"] >= 0
    assert len(out["synthetic"]) == len(out["treated"])


def test_uplift_t_learner_runs():
    df = datasets.load_ihdp()
    features = [c for c in df.columns if c.startswith("x")][:10]
    out = uplift_core.estimate_uplift(
        df, treatment="treatment", outcome="y_factual", features=features,
        learner="t_learner", n_estimators=50,
    )
    assert "auuc" in out
    assert 0 <= out["cate_positive_share"] <= 1
    assert len(out["qini"]["fraction"]) > 0

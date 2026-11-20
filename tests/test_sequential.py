"""Tests for sequential testing (alpha spending + always-valid p-values)."""
import numpy as np

from src.core import sequential
from src.data_pipeline.simulate import simulate_sequential_stream


def test_obf_boundaries_are_conservative_early():
    bounds = sequential.group_sequential_boundaries(5, alpha=0.05, spending="obrien-fleming")
    z = bounds["z_boundaries"]
    assert len(z) == 5
    # O'Brien-Fleming spends very little early -> first boundary is large
    assert z[0] > z[-1]
    assert z[0] > 3.0


def test_pocock_boundaries_more_constant():
    obf = sequential.group_sequential_boundaries(5, spending="obrien-fleming")["z_boundaries"]
    pocock = sequential.group_sequential_boundaries(5, spending="pocock")["z_boundaries"]
    assert (max(pocock) - min(pocock)) < (max(obf) - min(obf))


def test_always_valid_pvalue_shrinks_with_evidence():
    weak = sequential.always_valid_pvalue_continuous(0.05, 100, sigma=1.0)
    strong = sequential.always_valid_pvalue_continuous(0.5, 1000, sigma=1.0)
    assert 0 < strong < weak <= 1.0
    assert strong < 0.05


def test_sequential_monitoring_runs_and_decides():
    df = simulate_sequential_stream(n_total=6000, p_a=0.10, relative_lift=0.30, seed=9)
    a = df.loc[df.variant == "A", "converted"].values
    b = df.loc[df.variant == "B", "converted"].values
    out = sequential.sequential_monitoring(a, b, n_looks=6, metric_type="binary")
    assert len(out["looks"]) == 6
    assert out["final_decision"] in {"reject_null", "fail_to_reject_null"}
    # each look carries both naive and always-valid p-values
    assert all("always_valid_p_value" in look for look in out["looks"])

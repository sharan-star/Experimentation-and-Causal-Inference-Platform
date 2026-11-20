"""Tests for the FastAPI service."""
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_root_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json()["status"] == "ok"


def test_power_sample_size_endpoint():
    resp = client.post("/api/power/sample-size", json={
        "metric_type": "proportion", "p_control": 0.10, "relative_lift": 0.10,
    })
    assert resp.status_code == 200
    assert resp.json()["n_control"] > 0


def test_frequentist_endpoint_with_simulated_data():
    resp = client.post("/api/analysis/frequentist", json={
        "metric_type": "continuous",
        "data": {"source": "simulate", "simulate": {
            "kind": "continuous", "n_a": 1500, "n_b": 1500, "mean_a": 10,
            "relative_lift": 0.30, "std": 5, "seed": 1}},
        "metric_column": "revenue", "variant_column": "variant",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "p_value" in body["result"]
    assert body["result"]["p_value"] < 0.05
    assert "headline" in body["conclusion"]


def test_multiple_testing_endpoint():
    resp = client.post("/api/analysis/multiple-testing", json={
        "pvalues": [0.001, 0.02, 0.03, 0.2],
    })
    assert resp.status_code == 200
    assert "by_method" in resp.json()


def test_datasets_list_and_simulate():
    assert client.get("/api/datasets").status_code == 200
    resp = client.post("/api/datasets/simulate", json={
        "source": "simulate", "simulate": {"kind": "binary", "n_a": 300, "n_b": 300, "seed": 1}}
    )
    assert resp.status_code == 200
    assert "columns" in resp.json()


def test_causal_did_endpoint():
    resp = client.post("/api/causal/did", json={
        "data": {"source": "dataset", "name": "card_krueger"},
    })
    assert resp.status_code == 200
    assert "att" in resp.json()["result"]

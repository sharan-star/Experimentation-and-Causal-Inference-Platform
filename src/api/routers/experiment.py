"""Experiment-analysis endpoints: frequentist, multiple-testing, sequential, Bayesian."""
from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException

from src.core import frequentist as freq_core
from src.core import multiple_testing as mt_core
from src.core import sequential as seq_core
from src.core import bayesian as bayes_core
from src.core.conclude import (
    bayesian_conclusion,
    frequentist_conclusion,
    sequential_conclusion,
)
from src.api.dependencies import resolve_dataframe, split_arms
from src.api.schemas import (
    BayesianRequest,
    FrequentistRequest,
    MultipleTestingRequest,
    SequentialRequest,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _distribution_payload(control, treatment, is_binary, bins: int = 30):
    """Small histogram payload the front end can chart without raw arrays."""
    control = np.asarray(control, dtype=float)
    treatment = np.asarray(treatment, dtype=float)
    if is_binary:
        return {
            "type": "bar",
            "categories": ["control", "treatment"],
            "success_rate": [float(control.mean()), float(treatment.mean())],
            "counts": [len(control), len(treatment)],
        }
    lo = float(min(control.min(), treatment.min()))
    hi = float(max(control.max(), treatment.max()))
    edges = np.linspace(lo, hi, bins + 1)
    c_hist, _ = np.histogram(control, bins=edges)
    t_hist, _ = np.histogram(treatment, bins=edges)
    centers = ((edges[:-1] + edges[1:]) / 2).tolist()
    return {
        "type": "histogram",
        "bin_centers": centers,
        "control": c_hist.tolist(),
        "treatment": t_hist.tolist(),
    }


@router.post("/frequentist")
def frequentist(req: FrequentistRequest):
    """Run a t-test (continuous) or two-proportion z-test (binary)."""
    try:
        df = resolve_dataframe(req.data)
        control, treatment, is_binary = split_arms(
            df, req.variant_column, req.metric_column, req.control_label, req.treatment_label
        )
        if req.metric_type == "continuous" and not is_binary:
            result = freq_core.two_sample_ttest(control, treatment, alpha=req.alpha)
        elif req.metric_type == "proportion" or is_binary:
            result = freq_core.two_proportion_ztest(
                int(sum(control)), len(control), int(sum(treatment)), len(treatment), alpha=req.alpha
            )
        else:
            result = freq_core.two_sample_ttest(control, treatment, alpha=req.alpha)

        return {
            "result": result,
            "conclusion": frequentist_conclusion(result),
            "distribution": _distribution_payload(control, treatment, is_binary),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/multiple-testing")
def multiple_testing(req: MultipleTestingRequest):
    """Apply Bonferroni / Benjamini-Hochberg corrections to a batch of p-values."""
    try:
        return mt_core.analyze_metric_batch(
            req.pvalues, alpha=req.alpha, methods=list(req.methods),
            metric_names=req.metric_names,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sequential")
def sequential(req: SequentialRequest):
    """Peek-safe sequential analysis with alpha-spending and always-valid p-values."""
    try:
        df = resolve_dataframe(req.data)
        control, treatment, is_binary = split_arms(
            df, req.variant_column, req.metric_column, req.control_label, req.treatment_label
        )
        metric_type = "binary" if (req.metric_type == "binary" or is_binary) else "continuous"
        result = seq_core.sequential_monitoring(
            control, treatment, n_looks=req.n_looks, alpha=req.alpha,
            spending=req.spending, metric_type=metric_type,
        )
        return {"result": result, "conclusion": sequential_conclusion(result)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/bayesian")
def bayesian(req: BayesianRequest):
    """Bayesian A/B analysis returning P(B beats A) and expected loss."""
    try:
        df = resolve_dataframe(req.data)
        control, treatment, is_binary = split_arms(
            df, req.variant_column, req.metric_column, req.control_label, req.treatment_label
        )
        if req.metric_type == "continuous" and not is_binary:
            result = bayes_core.bayesian_ab_continuous(control, treatment, draws=req.draws, seed=req.seed)
        else:
            result = bayes_core.bayesian_ab_binary(
                int(sum(control)), len(control), int(sum(treatment)), len(treatment),
                draws=req.draws, seed=req.seed,
            )
        return {"result": result, "conclusion": bayesian_conclusion(result)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

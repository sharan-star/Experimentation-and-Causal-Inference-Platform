"""Observational causal-inference endpoints (Milestone 6)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.core.causal import did as did_core
from src.core.causal import propensity as psm_core
from src.core.causal import synthetic_control as sc_core
from src.core.causal import uplift as uplift_core
from src.core.conclude import causal_conclusion
from src.api.dependencies import binarize_treatment, resolve_dataframe
from src.api.schemas import (
    DidRequest,
    PropensityRequest,
    SyntheticControlRequest,
    UpliftRequest,
)

router = APIRouter(prefix="/causal", tags=["causal"])


@router.post("/propensity")
def propensity(req: PropensityRequest):
    """Propensity-score matching (optionally via DoWhy)."""
    try:
        df = resolve_dataframe(req.data)
        if req.use_dowhy:
            result = psm_core.dowhy_propensity_estimate(
                df, req.treatment_column, req.outcome_column, req.covariates,
            )
        else:
            result = psm_core.propensity_score_matching(
                df, req.treatment_column, req.outcome_column, req.covariates,
                caliper=req.caliper, alpha=req.alpha,
            )
        # keep payload small: drop raw score arrays
        result.pop("propensity_scores", None)
        result.pop("treatment_flags", None)
        return {"result": result, "conclusion": causal_conclusion(result)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/did")
def did(req: DidRequest):
    """Difference-in-differences estimate of the ATT."""
    try:
        df = resolve_dataframe(req.data)
        result = did_core.difference_in_differences(
            df, req.outcome_column, req.treated_column, req.post_column,
            covariates=req.covariates, alpha=req.alpha,
        )
        return {"result": result, "conclusion": causal_conclusion(result)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/synthetic-control")
def synthetic_control(req: SyntheticControlRequest):
    """Synthetic control estimate for a single treated unit."""
    try:
        df = resolve_dataframe(req.data)
        result = sc_core.synthetic_control(
            df, req.unit_column, req.time_column, req.outcome_column,
            treated_unit=req.treated_unit, treatment_time=req.treatment_time,
            donor_units=req.donor_units, alpha=req.alpha,
        )
        return {"result": result, "conclusion": causal_conclusion(result)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/uplift")
def uplift(req: UpliftRequest):
    """Heterogeneous treatment effects (CATE) + Qini/AUUC targeting evaluation."""
    try:
        df = resolve_dataframe(req.data).copy()
        df["_treatment"] = binarize_treatment(df, req.treatment_column, req.positive_treatment)
        features = [f for f in req.features if f in df.columns]
        result = uplift_core.estimate_uplift(
            df, "_treatment", req.outcome_column, features,
            learner=req.learner, n_estimators=req.n_estimators, seed=req.seed,
        )
        # drop per-row CATE from the default payload (kept for the notebook)
        result.pop("cate", None)
        return {"result": result, "conclusion": causal_conclusion({
            "method": "uplift (CATE)", "effect": result["ate"],
        })}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

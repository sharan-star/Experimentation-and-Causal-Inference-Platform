"""Power-analysis and sample-size calculator endpoints (Milestone 2)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.core import power as power_core
from src.api.schemas import MdeRequest, PowerRequest, SampleSizeRequest

router = APIRouter(prefix="/power", tags=["power"])


@router.post("/sample-size")
def sample_size(req: SampleSizeRequest):
    """Compute the required sample size per arm for a target power."""
    try:
        if req.metric_type == "proportion":
            return power_core.sample_size_two_proportions(
                p_control=req.p_control, p_treatment=req.p_treatment,
                relative_lift=req.relative_lift, alpha=req.alpha,
                power=req.power, ratio=req.ratio,
            )
        return power_core.sample_size_continuous(
            cohens_d=req.cohens_d, alpha=req.alpha, power=req.power, ratio=req.ratio,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/power")
def power(req: PowerRequest):
    """Compute statistical power given sample sizes."""
    try:
        if req.metric_type == "proportion":
            return power_core.power_two_proportions(
                p_control=req.p_control, p_treatment=req.p_treatment,
                n_control=req.n_control, n_treatment=req.n_treatment, alpha=req.alpha,
            )
        return power_core.power_continuous(
            cohens_d=req.cohens_d, n_control=req.n_control,
            n_treatment=req.n_treatment, alpha=req.alpha,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/mde")
def minimum_detectable_effect(req: MdeRequest):
    """Compute the minimum detectable effect for a fixed sample size."""
    try:
        if req.metric_type == "proportion":
            return power_core.mde_two_proportions(
                p_control=req.p_control, n_control=req.n_control,
                n_treatment=req.n_treatment, alpha=req.alpha, power=req.power,
            )
        return power_core.mde_continuous(
            n_control=req.n_control, n_treatment=req.n_treatment,
            alpha=req.alpha, power=req.power,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

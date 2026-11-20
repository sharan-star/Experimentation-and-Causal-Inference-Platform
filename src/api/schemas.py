"""FastAPI request/response schemas (Pydantic v2)."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

__all__ = [
    "SimulateSpec",
    "DataSource",
    "SampleSizeRequest",
    "PowerRequest",
    "MdeRequest",
    "FrequentistRequest",
    "MultipleTestingRequest",
    "SequentialRequest",
    "BayesianRequest",
    "PropensityRequest",
    "DidRequest",
    "SyntheticControlRequest",
    "UpliftRequest",
]

MetricType = Literal["proportion", "continuous"]


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------
class SimulateSpec(BaseModel):
    """Parameters used to generate a synthetic experiment."""

    kind: Literal["continuous", "binary", "multimetric", "sequential", "observational"] = "binary"
    n_a: int = 5000
    n_b: int = 5000
    p_a: float = 0.10
    relative_lift: float = 0.10
    mean_a: float = 10.0
    std: float = 5.0
    seed: int = 42


class DataSource(BaseModel):
    """A flexible description of where the analysis data comes from."""

    source: Literal["inline", "simulate", "dataset", "upload"] = "simulate"
    records: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None
    upload_id: Optional[str] = None
    simulate: Optional[SimulateSpec] = None


# ---------------------------------------------------------------------------
# Power / sample size
# ---------------------------------------------------------------------------
class SampleSizeRequest(BaseModel):
    metric_type: MetricType = "proportion"
    p_control: float = 0.10
    p_treatment: Optional[float] = None
    relative_lift: Optional[float] = 0.10
    cohens_d: float = 0.2
    alpha: float = 0.05
    power: float = 0.80
    ratio: float = 1.0


class PowerRequest(BaseModel):
    metric_type: MetricType = "proportion"
    p_control: float = 0.10
    p_treatment: float = 0.12
    n_control: int = 1000
    n_treatment: Optional[int] = None
    cohens_d: float = 0.2
    alpha: float = 0.05


class MdeRequest(BaseModel):
    metric_type: MetricType = "proportion"
    p_control: float = 0.10
    n_control: int = 1000
    n_treatment: Optional[int] = None
    alpha: float = 0.05
    power: float = 0.80


# ---------------------------------------------------------------------------
# Experiment analysis
# ---------------------------------------------------------------------------
class FrequentistRequest(BaseModel):
    metric_type: MetricType = "continuous"
    data: DataSource = Field(default_factory=DataSource)
    variant_column: str = "variant"
    metric_column: str = "converted"
    control_label: str = "A"
    treatment_label: str = "B"
    alpha: float = 0.05


class MultipleTestingRequest(BaseModel):
    pvalues: List[float]
    metric_names: Optional[List[str]] = None
    methods: Sequence[str] = ("bonferroni", "benjamini-hochberg")
    alpha: float = 0.05


class SequentialRequest(BaseModel):
    metric_type: MetricType = "proportion"
    data: DataSource = Field(default_factory=DataSource)
    variant_column: str = "variant"
    metric_column: str = "converted"
    control_label: str = "A"
    treatment_label: str = "B"
    n_looks: int = 5
    spending: Literal["obrien-fleming", "pocock"] = "obrien-fleming"
    alpha: float = 0.05


class BayesianRequest(BaseModel):
    metric_type: MetricType = "proportion"
    data: DataSource = Field(default_factory=DataSource)
    variant_column: str = "variant"
    metric_column: str = "converted"
    control_label: str = "A"
    treatment_label: str = "B"
    draws: int = 3000
    seed: int = 42


# ---------------------------------------------------------------------------
# Causal inference
# ---------------------------------------------------------------------------
class PropensityRequest(BaseModel):
    data: DataSource = Field(default_factory=DataSource)
    treatment_column: str = "treatment"
    outcome_column: str = "outcome"
    covariates: List[str] = Field(default_factory=lambda: ["age", "prior_spend"])
    caliper: float = 0.1
    use_dowhy: bool = False
    alpha: float = 0.05


class DidRequest(BaseModel):
    data: DataSource = Field(default_factory=DataSource)
    outcome_column: str = "fte_employment"
    treated_column: str = "treated"
    post_column: str = "post"
    covariates: Optional[List[str]] = None
    alpha: float = 0.05


class SyntheticControlRequest(BaseModel):
    data: DataSource = Field(default_factory=DataSource)
    unit_column: str = "state"
    time_column: str = "year"
    outcome_column: str = "cigsales"
    treated_unit: str = "California"
    treatment_time: int = 1989
    donor_units: Optional[List[str]] = None
    alpha: float = 0.05


class UpliftRequest(BaseModel):
    data: DataSource = Field(default_factory=DataSource)
    treatment_column: str = "segment"
    outcome_column: str = "visit"
    features: List[str] = Field(default_factory=lambda: ["recency", "history", "mens", "womens", "newbie"])
    positive_treatment: Optional[str] = None
    learner: Literal["causal_forest", "t_learner"] = "causal_forest"
    n_estimators: int = 200
    seed: int = 42

"""Resolve :class:`DataSource` objects into pandas DataFrames.

Also handles CSV uploads (stored under ``data/processed/uploads``) and
column-based arm splitting for the analysis endpoints.
"""
from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.config import processed_path, ensure_directories
from src.data_pipeline import datasets as ds
from src.data_pipeline import simulate as sim

from src.api.schemas import DataSource, SimulateSpec

__all__ = [
    "resolve_dataframe",
    "save_upload",
    "get_upload_path",
    "split_arms",
    "binarize_treatment",
    "UPLOAD_SUBDIR",
]

UPLOAD_SUBDIR = "uploads"


def get_upload_path(upload_id: str) -> str:
    ensure_directories()
    upload_dir = processed_path(UPLOAD_SUBDIR)
    os.makedirs(upload_dir, exist_ok=True)
    return os.path.join(upload_dir, f"{upload_id}.csv")


def save_upload(content: bytes) -> Tuple[str, pd.DataFrame]:
    """Persist an uploaded CSV and return ``(upload_id, dataframe)``."""
    import io

    df = pd.read_csv(io.BytesIO(content))
    upload_id = uuid.uuid4().hex[:12]
    df.to_csv(get_upload_path(upload_id), index=False)
    return upload_id, df


def _simulate(spec: Optional[SimulateSpec]) -> pd.DataFrame:
    spec = spec or SimulateSpec()
    if spec.kind == "continuous":
        return sim.simulate_continuous_ab(
            n_a=spec.n_a, n_b=spec.n_b, mean_a=spec.mean_a,
            relative_lift=spec.relative_lift, std=spec.std, seed=spec.seed,
        )
    if spec.kind == "binary":
        return sim.simulate_binary_ab(
            n_a=spec.n_a, n_b=spec.n_b, p_a=spec.p_a,
            relative_lift=spec.relative_lift, seed=spec.seed,
        )
    if spec.kind == "multimetric":
        return sim.simulate_multimetric_ab(n_per_arm=max(spec.n_a, 100), seed=spec.seed)
    if spec.kind == "sequential":
        return sim.simulate_sequential_stream(
            n_total=spec.n_a + spec.n_b, p_a=spec.p_a,
            relative_lift=spec.relative_lift, seed=spec.seed,
        )
    if spec.kind == "observational":
        return sim.simulate_confounded_observational(n=max(spec.n_a, 500), seed=spec.seed)
    raise ValueError(f"Unknown simulate kind '{spec.kind}'")


def resolve_dataframe(ds: DataSource) -> pd.DataFrame:
    """Turn a data-source description into a concrete DataFrame."""
    if ds.source == "inline":
        if not ds.records:
            raise ValueError("inline source requires 'records'")
        return pd.DataFrame(ds.records)
    if ds.source == "dataset":
        if not ds.name:
            raise ValueError("dataset source requires 'name'")
        loader = datasets_loader().get(ds.name)
        if loader is None:
            raise ValueError(f"Unknown dataset '{ds.name}'")
        return loader()
    if ds.source == "upload":
        if not ds.upload_id:
            raise ValueError("upload source requires 'upload_id'")
        path = get_upload_path(ds.upload_id)
        if not os.path.exists(path):
            raise ValueError(f"Upload '{ds.upload_id}' not found")
        return pd.read_csv(path)
    if ds.source == "simulate":
        return _simulate(ds.simulate)
    raise ValueError(f"Unknown source '{ds.source}'")


def datasets_loader() -> Dict[str, object]:
    """Return a mapping of dataset names to loader callables."""
    return {
        "cookie_cats": ds.load_cookie_cats,
        "hillstrom": ds.load_hillstrom,
        "lalonde": ds.load_lalonde,
        "card_krueger": ds.load_card_krueger,
        "prop99": ds.load_prop99,
        "ihdp": ds.load_ihdp,
    }


def split_arms(
    df: pd.DataFrame,
    variant_column: str,
    metric_column: str,
    control_label: str = "A",
    treatment_label: str = "B",
) -> Tuple[List[float], List[float], bool]:
    """Split a two-arm experiment frame into control/treatment metric vectors.

    Returns ``(control_values, treatment_values, is_binary)``.
    """
    if variant_column not in df.columns:
        raise ValueError(f"Column '{variant_column}' not found")
    if metric_column not in df.columns:
        raise ValueError(f"Column '{metric_column}' not found")

    control = df.loc[df[variant_column].astype(str) == str(control_label), metric_column]
    treatment = df.loc[df[variant_column].astype(str) == str(treatment_label), metric_column]
    if len(control) == 0 or len(treatment) == 0:
        raise ValueError(
            f"Could not find both arms. control='{control_label}', "
            f"treatment='{treatment_label}'. Variants present: "
            f"{sorted(df[variant_column].astype(str).unique().tolist())}"
        )

    values = pd.concat([control, treatment]).dropna()
    is_binary = bool(set(values.unique()).issubset({0, 1, 0.0, 1.0}))
    return control.dropna().astype(float).tolist(), treatment.dropna().astype(float).tolist(), is_binary


def binarize_treatment(
    df: pd.DataFrame, column: str, positive: Optional[str] = None
) -> pd.Series:
    """Convert a (possibly multi-level) treatment column into a 0/1 indicator."""
    series = df[column]
    uniques = series.dropna().unique().tolist()
    if set(uniques).issubset({0, 1, 0.0, 1.0, "0", "1"}):
        return series.astype(int)

    if positive is None:
        # choose the most frequent non-baseline-looking label
        positive = sorted(map(str, uniques))[-1]
    if positive not in map(str, uniques):
        raise ValueError(f"positive treatment '{positive}' not in column values {uniques}")
    return (series.astype(str) == str(positive)).astype(int)

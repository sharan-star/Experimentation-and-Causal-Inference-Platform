"""Dataset, simulation and upload endpoints."""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from src.api.dependencies import datasets_loader, resolve_dataframe, save_upload
from src.api.schemas import DataSource

router = APIRouter(prefix="/datasets", tags=["datasets"])

DATASET_INFO: List[Dict[str, str]] = [
    {"name": "cookie_cats", "description": "Cookie Cats mobile-game A/B test (retention).",
     "analysis": "binary"},
    {"name": "hillstrom", "description": "Hillstrom e-mail marketing experiment (visit/conversion/spend).",
     "analysis": "uplift"},
    {"name": "lalonde", "description": "LaLonde NSW job-training data (observational).",
     "analysis": "propensity"},
    {"name": "card_krueger", "description": "Card & Krueger minimum-wage panel (difference-in-differences).",
     "analysis": "did"},
    {"name": "prop99", "description": "California Proposition 99 tobacco panel (synthetic control).",
     "analysis": "synthetic_control"},
    {"name": "ihdp", "description": "IHDP semi-synthetic benchmark (heterogeneous effects).",
     "analysis": "uplift"},
]


def _preview(df: pd.DataFrame, n: int = 25) -> Dict[str, Any]:
    head = df.head(n).replace({np.nan: None}).to_dict(orient="records")
    dtypes = {c: str(t) for c, t in df.dtypes.items()}
    return {
        "columns": df.columns.tolist(),
        "dtypes": dtypes,
        "n_rows": int(len(df)),
        "preview": head,
    }


@router.get("")
def list_datasets():
    """List the datasets available for one-click loading."""
    return {"datasets": DATASET_INFO}


@router.post("/simulate")
def simulate(ds: DataSource):
    """Generate a simulated dataset and return a preview."""
    try:
        if ds.source != "simulate":
            raise ValueError("This endpoint expects source='simulate'")
        df = resolve_dataframe(ds)
        return {"source": "simulate", **_preview(df)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{name}")
def get_dataset(name: str, limit: int = 2000):
    """Load a named dataset and return a preview."""
    loader = datasets_loader().get(name)
    if loader is None:
        raise HTTPException(status_code=404, detail=f"Unknown dataset '{name}'")
    try:
        df = loader()
        return {"name": name, **_preview(df.head(limit))}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Upload a CSV file for analysis; returns an ``upload_id`` + preview."""
    try:
        content = await file.read()
        upload_id, df = save_upload(content)
        return {"upload_id": upload_id, "filename": file.filename, **_preview(df)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

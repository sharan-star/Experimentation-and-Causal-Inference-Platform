"""FastAPI application entry point for the Experimentation & Causal Inference Platform."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import ensure_directories
from src.api.routers import causal, datasets, experiment, power


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the data/artifact directories exist on start-up."""
    ensure_directories()
    yield


app = FastAPI(
    title="Experimentation & Causal Inference Platform",
    description=(
        "Design A/B tests, analyse them correctly (frequentist, sequential and "
        "Bayesian) and estimate cause and effect when experiments are not "
        "possible (propensity-score matching, difference-in-differences, "
        "synthetic control and uplift modelling)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(power.router, prefix="/api")
app.include_router(experiment.router, prefix="/api")
app.include_router(causal.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "Experimentation & Causal Inference Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/api/power/sample-size",
            "/api/power/power",
            "/api/power/mde",
            "/api/analysis/frequentist",
            "/api/analysis/multiple-testing",
            "/api/analysis/sequential",
            "/api/analysis/bayesian",
            "/api/causal/propensity",
            "/api/causal/did",
            "/api/causal/synthetic-control",
            "/api/causal/uplift",
            "/api/datasets",
        ],
    }


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}

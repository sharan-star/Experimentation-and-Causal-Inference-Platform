"""Central configuration and path handling for the platform.

All file paths are built with :func:`os.path.join` so that the project works
identically on Windows, macOS and Linux (a hard requirement for this project).
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Project root resolution
# ---------------------------------------------------------------------------
# This file lives at <PROJECT_ROOT>/src/config.py
#   os.path.dirname(__file__)            -> <PROJECT_ROOT>/src
#   os.path.dirname(os.path.dirname(..)) -> <PROJECT_ROOT>
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
SIMULATED_DATA_DIR = os.path.join(DATA_DIR, "simulated")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
NOTEBOOKS_DIR = os.path.join(PROJECT_ROOT, "notebooks")
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")

DIRECTORIES = (
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    SIMULATED_DATA_DIR,
    MODELS_DIR,
    NOTEBOOKS_DIR,
    ARTIFACTS_DIR,
)


def ensure_directories() -> None:
    """Create every directory the project expects to exist."""
    for directory in DIRECTORIES:
        os.makedirs(directory, exist_ok=True)


def data_path(*parts: str) -> str:
    """Return an absolute path inside the ``data`` folder."""
    return os.path.join(DATA_DIR, *parts)


def raw_path(*parts: str) -> str:
    """Return an absolute path inside ``data/raw``."""
    return os.path.join(RAW_DATA_DIR, *parts)


def processed_path(*parts: str) -> str:
    """Return an absolute path inside ``data/processed``."""
    return os.path.join(PROCESSED_DATA_DIR, *parts)


def simulated_path(*parts: str) -> str:
    """Return an absolute path inside ``data/simulated``."""
    return os.path.join(SIMULATED_DATA_DIR, *parts)


def artifact_path(*parts: str) -> str:
    """Return an absolute path inside ``artifacts``."""
    return os.path.join(ARTIFACTS_DIR, *parts)


# Default statistical settings used across services + notebooks.
DEFAULT_ALPHA = 0.05
DEFAULT_POWER = 0.80

__all__ = [
    "PROJECT_ROOT",
    "SRC_DIR",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "SIMULATED_DATA_DIR",
    "MODELS_DIR",
    "NOTEBOOKS_DIR",
    "ARTIFACTS_DIR",
    "DIRECTORIES",
    "ensure_directories",
    "data_path",
    "raw_path",
    "processed_path",
    "simulated_path",
    "artifact_path",
    "DEFAULT_ALPHA",
    "DEFAULT_POWER",
]

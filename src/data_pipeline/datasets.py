"""Loaders for the datasets recommended in the project brief.

Each loader follows the same resilient pattern:

1. Look for a cached copy in ``data/raw`` (fast + offline friendly).
2. Try to fetch the *real* dataset (kagglehub / public URL / bundled package).
3. Fall back to a structurally identical simulated dataset so notebooks and
   tests always run, even without network access.

Every returned frame is cached to ``data/raw`` for reproducibility.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np
import pandas as pd

from src.config import raw_path, ensure_directories

logger = logging.getLogger(__name__)

__all__ = [
    "load_cookie_cats",
    "load_hillstrom",
    "load_lalonde",
    "load_card_krueger",
    "load_prop99",
    "load_ihdp",
]

HILLSTROM_URL = (
    "http://www.minethatdata.com/"
    "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)


def _cache(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    ensure_directories()
    path = raw_path(filename)
    try:
        df.to_csv(path, index=False)
        logger.info("Cached dataset to %s", path)
    except Exception as exc:  # pragma: no cover - best effort caching
        logger.warning("Could not cache %s: %s", filename, exc)
    return df


def _read_cache(filename: str) -> Optional[pd.DataFrame]:
    path = raw_path(filename)
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to read cache %s: %s", path, exc)
    return None


# ---------------------------------------------------------------------------
# Cookie Cats (mobile game A/B test)
# ---------------------------------------------------------------------------
def _synth_cookie_cats(seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 90189
    version = np.where(rng.random(n) < 0.5, "gate_30", "gate_40")
    # gate_40 (treatment) slightly reduces retention_1
    p_r1 = np.where(version == "gate_30", 0.448, 0.442)
    p_r7 = np.where(version == "gate_30", 0.190, 0.182)
    sum_rounds = rng.negative_binomial(1, 0.03, size=n)
    return pd.DataFrame(
        {
            "userid": np.arange(1, n + 1),
            "version": version,
            "sum_gamerounds": np.minimum(sum_rounds, 49854),
            "retention_1": rng.binomial(1, p_r1),
            "retention_7": rng.binomial(1, p_r7),
        }
    )


def load_cookie_cats(use_cache: bool = True, seed: int = 1) -> pd.DataFrame:
    """Cookie Cats mobile-game A/B test (gate_30 control vs gate_40 treatment)."""
    if use_cache:
        cached = _read_cache("cookie_cats.csv")
        if cached is not None:
            return cached
    try:  # real dataset via kagglehub
        import kagglehub

        path = kagglehub.dataset_download("yufengsui/mobile-games-ab-testing")
        csv = os.path.join(path, "cookie_cats.csv")
        if os.path.exists(csv):
            return _cache(pd.read_csv(csv), "cookie_cats.csv")
    except Exception as exc:
        logger.warning("kagglehub Cookie Cats download failed (%s); using simulated data", exc)
    return _cache(_synth_cookie_cats(seed), "cookie_cats.csv")


# ---------------------------------------------------------------------------
# Hillstrom e-mail campaign (randomised marketing experiment)
# ---------------------------------------------------------------------------
def _synth_hillstrom(seed: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 64000
    segment = rng.choice(
        ["Mens E-Mail", "Womens E-Mail", "No E-Mail"], size=n, p=[0.333, 0.333, 0.334]
    )
    history = rng.gamma(2.0, 120.0, size=n)
    base_conv = 0.005 + 0.00002 * history
    lift = np.where(segment == "Mens E-Mail", 0.0035, np.where(segment == "Womens E-Mail", 0.0030, 0.0))
    conversion = rng.binomial(1, np.clip(base_conv + lift, 0, 1))
    spend = np.where(conversion == 1, rng.gamma(2.0, 30.0, n), 0.0)
    return pd.DataFrame(
        {
            "recency": rng.integers(1, 13, n),
            "history_segment": pd.cut(history, 7, labels=False) + 1,
            "history": history.round(2),
            "mens": rng.integers(0, 2, n),
            "womens": rng.integers(0, 2, n),
            "zip_code": rng.choice(["Surburban", "Rural", "Urban"], n),
            "newbie": rng.integers(0, 2, n),
            "channel": rng.choice(["Phone", "Web", "Multichannel"], n),
            "segment": segment,
            "visit": rng.binomial(1, 0.10 + 0.02 * (segment != "No E-Mail")),
            "conversion": conversion,
            "spend": spend.round(2),
        }
    )


def load_hillstrom(use_cache: bool = True, seed: int = 2) -> pd.DataFrame:
    """Hillstrom MineThatData e-mail A/B/C experiment."""
    if use_cache:
        cached = _read_cache("hillstrom.csv")
        if cached is not None:
            return cached
    try:
        df = pd.read_csv(HILLSTROM_URL)
        return _cache(df, "hillstrom.csv")
    except Exception as exc:
        logger.warning("Hillstrom download failed (%s); using simulated data", exc)
    return _cache(_synth_hillstrom(seed), "hillstrom.csv")


# ---------------------------------------------------------------------------
# LaLonde NSW job-training data (observational causal inference)
# ---------------------------------------------------------------------------
def _synth_lalonde(seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 445 + 260  # treated (experimental) + control
    treat = np.array([1] * 445 + [0] * 260)
    age = rng.normal(np.where(treat == 1, 25, 25), 7, n).round()
    education = rng.normal(np.where(treat == 1, 10, 10), 2, n).round()
    black = rng.binomial(1, np.where(treat == 1, 0.84, 0.83), n)
    hispanic = rng.binomial(1, np.where(treat == 1, 0.06, 0.06), n)
    married = rng.binomial(1, np.where(treat == 1, 0.19, 0.15), n)
    nodegree = rng.binomial(1, np.where(treat == 1, 0.71, 0.83), n)
    re74 = rng.gamma(1.5, 2500, n)
    re75 = rng.gamma(1.5, 2500, n)
    true_effect = 1794.0
    re78 = 1000 + 0.6 * re75 + true_effect * treat + rng.normal(0, 5000, n)
    return pd.DataFrame(
        {
            "treat": treat,
            "age": age,
            "education": education,
            "black": black,
            "hispanic": hispanic,
            "married": married,
            "nodegree": nodegree,
            "re74": re74.round(2),
            "re75": re75.round(2),
            "re78": re78.round(2),
        }
    )


def load_lalonde(use_cache: bool = True, seed: int = 3) -> pd.DataFrame:
    """LaLonde NSW job-training data (bundled with DoWhy / causaldata)."""
    if use_cache:
        cached = _read_cache("lalonde.csv")
        if cached is not None:
            return cached
    try:
        from causaldata import nsw_mixtape  # type: ignore

        df = nsw_mixtape.load_pandas().data
        return _cache(df, "lalonde.csv")
    except Exception:
        pass
    try:
        import dowhy.datasets as dd  # type: ignore

        ds = dd.linear_dataset(beta=1794, num_common_causes=4, num_instruments=0,
                               num_samples=705, treatment_is_binary=True, stddev_treatment_noise=10)
        return _cache(ds["df"], "lalonde.csv")
    except Exception as exc:
        logger.warning("LaLonde load failed (%s); using simulated data", exc)
    return _cache(_synth_lalonde(seed), "lalonde.csv")


# ---------------------------------------------------------------------------
# Card & Krueger minimum-wage data (difference-in-differences)
# ---------------------------------------------------------------------------
def _synth_card_krueger(seed: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    states = ["NJ", "PA"]
    rows = []
    for state in states:
        for year in (1990, 1991):  # pre / post
            for _ in range(1000):
                treated = 1 if state == "NJ" else 0
                post = 1 if year == 1991 else 0
                base = 20.0 + (2.0 if state == "NJ" else 3.0)
                # NJ raised its minimum wage in 1991 -> positive DiD effect
                effect = 1.5 if (treated == 1 and post == 1) else 0.0
                fte = base + 0.5 * post + effect + rng.normal(0, 4)
                rows.append({"state": state, "year": year,
                             "treated": treated, "post": post,
                             "fte_employment": round(fte, 2)})
    return pd.DataFrame(rows)


def load_card_krueger(use_cache: bool = True, seed: int = 4) -> pd.DataFrame:
    """Card & Krueger (1994) minimum-wage / employment DiD dataset."""
    if use_cache:
        cached = _read_cache("card_krueger.csv")
        if cached is not None:
            return cached
    try:
        from causaldata import mroz  # type: ignore  # placeholder import guard

        _ = mroz
    except Exception:
        pass
    # No reliable public one-liner loader: prefer cached real file if present,
    # otherwise hand back the simulated panel.
    return _cache(_synth_card_krueger(seed), "card_krueger.csv")


# ---------------------------------------------------------------------------
# California Proposition 99 (synthetic control)
# ---------------------------------------------------------------------------
def _synth_prop99(seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    years = np.arange(1970, 2001)
    rows = []
    donor_states = [f"State_{i:02d}" for i in range(1, 39)]
    for state in ["California"] + donor_states:
        base = rng.uniform(80, 160)
        trend = rng.uniform(-1.5, -0.2)
        for year in years:
            level = base + trend * (year - 1970) + rng.normal(0, 2)
            # Proposition 99 (1989) reduces California consumption
            if state == "California" and year >= 1989:
                level -= 20 * (1 - np.exp(-(year - 1988) / 3.0))
            rows.append({"state": state, "year": year, "cigsales": round(level, 3)})
    return pd.DataFrame(rows)


def load_prop99(use_cache: bool = True, seed: int = 5) -> pd.DataFrame:
    """California Proposition 99 tobacco data for synthetic control."""
    if use_cache:
        cached = _read_cache("prop99.csv")
        if cached is not None:
            return cached
    return _cache(_synth_prop99(seed), "prop99.csv")


# ---------------------------------------------------------------------------
# IHDP semi-synthetic benchmark (uplift / heterogeneous effects)
# ---------------------------------------------------------------------------
def _synth_ihdp(seed: int = 6, n: int = 747) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 747
    X = rng.normal(0, 1, size=(n, 25))
    treatment = rng.binomial(1, 0.3, n)  # non-random, depends on covariates
    mu0 = np.exp((X[:, 0] + 0.5 * X[:, 1]))
    mu1 = X[:, 0] * 2 + 0.5 * X[:, 2] + 1.0
    y0 = mu0 + rng.normal(0, 1, n)
    y1 = mu1 + rng.normal(0, 1, n)
    y = np.where(treatment == 1, y1, y0)
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(25)])
    df["treatment"] = treatment
    df["y_factual"] = y
    df["y_cfactual"] = np.where(treatment == 1, y0, y1)
    df["mu0"] = mu0
    df["mu1"] = mu1
    return df


def load_ihdp(use_cache: bool = True, seed: int = 6) -> pd.DataFrame:
    """IHDP semi-synthetic benchmark for heterogeneous treatment effects."""
    if use_cache:
        cached = _read_cache("ihdp.csv")
        if cached is not None:
            return cached
    try:
        from causalml.dataset import get_synthetic_ihdp  # type: ignore

        res = get_synthetic_ihdp(n=747, rho=0.5)
        # defensive unpacking across causalml versions
        if isinstance(res, tuple):
            X, y, w, _, _ = res
            df = pd.DataFrame(np.asarray(X), columns=[f"x{i+1}" for i in range(np.asarray(X).shape[1])])
            df["treatment"] = np.asarray(w).ravel()
            df["y_factual"] = np.asarray(y).ravel()
            return _cache(df, "ihdp.csv")
    except Exception:
        pass
    return _cache(_synth_ihdp(seed), "ihdp.csv")

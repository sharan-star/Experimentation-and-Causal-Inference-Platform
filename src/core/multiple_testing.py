"""Multiple-testing corrections (Milestone 3).

Wraps :func:`statsmodels.stats.multitest.multipletests` for Bonferroni and
Benjamini–Hochberg (FDR), and adds a convenience "batch of metrics" analyzer.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
from statsmodels.stats.multitest import multipletests

__all__ = ["adjust_pvalues", "analyze_metric_batch"]

_METHOD_MAP = {
    "bonferroni": "bonferroni",
    "benjamini-hochberg": "fdr_bh",
    "benjamini_hochberg": "fdr_bh",
    "bh": "fdr_bh",
    "fdr": "fdr_bh",
    "holm": "holm",
    "sidak": "sidak",
    "none": None,
}


def adjust_pvalues(pvalues: Sequence[float], method: str = "benjamini-hochberg", alpha: float = 0.05) -> Dict[str, list]:
    """Adjust a list of p-values for multiple comparisons.

    Returns both the adjusted p-values and the reject/accept decisions at
    ``alpha`` for the requested method.
    """
    key = method.lower().strip()
    if key not in _METHOD_MAP:
        raise ValueError(f"Unknown method '{method}'. Choose from {sorted(_METHOD_MAP)}")

    pvals = np.asarray(pvalues, dtype=float)
    if pvals.ndim != 1:
        raise ValueError("pvalues must be one-dimensional")

    statsmodels_method = _METHOD_MAP[key]
    if statsmodels_method is None:
        return {
            "method": "none",
            "pvalues": pvals.tolist(),
            "adjusted_pvalues": pvals.tolist(),
            "reject": (pvals < alpha).tolist(),
            "alpha": alpha,
        }

    reject, adjusted, _, _ = multipletests(pvals, alpha=alpha, method=statsmodels_method)
    return {
        "method": key,
        "pvalues": pvals.tolist(),
        "adjusted_pvalues": np.asarray(adjusted).tolist(),
        "reject": np.asarray(reject).tolist(),
        "alpha": alpha,
    }


def analyze_metric_batch(
    pvalues: Sequence[float],
    alpha: float = 0.05,
    methods: Optional[Sequence[str]] = None,
    metric_names: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Compare several correction methods side-by-side for a batch of metrics."""
    if methods is None:
        methods = ("bonferroni", "benjamini-hochberg")

    results: List[Dict[str, object]] = [adjust_pvalues(pvalues, m, alpha) for m in methods]
    names = list(metric_names) if metric_names is not None else [f"metric_{i}" for i in range(len(pvalues))]

    return {
        "metric_names": names,
        "pvalues": list(map(float, pvalues)),
        "n_tests": len(pvalues),
        "alpha": alpha,
        "by_method": {r["method"]: r for r in results},  # type: ignore[index]
    }

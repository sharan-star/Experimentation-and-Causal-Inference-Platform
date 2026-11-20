"""Turn statistical output into a plain-English conclusion (Milestone 7).

The front end shows these strings directly, so they are written for a
non-technical audience (product managers, marketers) while still being
accurate.
"""
from __future__ import annotations

from typing import Dict

__all__ = [
    "frequentist_conclusion",
    "bayesian_conclusion",
    "sequential_conclusion",
    "causal_conclusion",
]


def _pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%"


def frequentist_conclusion(result: Dict) -> Dict[str, str]:
    test = result.get("test", "test")
    p = result.get("p_value")
    alpha = result.get("alpha", 0.05)
    lift = result.get("absolute_lift")
    rel = result.get("relative_lift")
    lo, hi = result.get("ci_lower"), result.get("ci_upper")

    if p is None:
        return {"headline": "Not enough information to reach a conclusion.",
                "details": "", "recommendation": "Check the input data."}

    unit = "percentage points" if test == "two_proportion_ztest" else "units"
    lift_txt = f"{lift:+.4g} {unit}" if lift is not None else "n/a"
    rel_txt = f" ({rel:+.1%} relative)" if rel is not None else ""

    if p < alpha:
        headline = (
            f"Statistically significant: the variant changed the metric by "
            f"{lift_txt}{rel_txt}."
        )
    else:
        headline = "No statistically significant difference detected."

    ci_txt = (
        f"The 95% confidence interval for the effect is [{lo:.4g}, {hi:.4g}] {unit}."
        if lo is not None and hi is not None
        else ""
    )
    details = (
        f"Estimated effect: {lift_txt}{rel_txt}. p-value = {p:.4g} "
        f"(threshold {alpha}). {ci_txt}"
    )
    recommendation = (
        "The effect is unlikely to be a fluke — consider shipping, but weigh it "
        "against practical significance and business guardrails."
        if p < alpha
        else "There is not enough evidence to claim an effect yet — keep running "
        "the test or check for underpowered sample size."
    )
    return {"headline": headline, "details": details, "recommendation": recommendation}


def bayesian_conclusion(result: Dict) -> Dict[str, str]:
    prob = result.get("prob_treatment_better", 0.5)
    decision = result.get("decision", "inconclusive")
    ci = result.get("credible_interval", [None, None])
    rel = result.get("relative_lift_posterior_mean")

    if decision == "ship_treatment":
        headline = f"Strong evidence the treatment is better: P(B beats A) = {_pct(prob)}."
    elif decision == "keep_control":
        headline = f"Evidence favours the control: P(B beats A) = {_pct(prob)}."
    else:
        headline = f"Inconclusive: P(B beats A) = {_pct(prob)} — keep running the test."

    rel_txt = f" The posterior mean relative lift is {rel:+.1%}." if rel is not None else ""
    details = (
        f"There is a {_pct(prob)} posterior probability that B outperforms A. "
        f"The 95% credible interval for the lift is [{ci[0]:.4g}, {ci[1]:.4g}].{rel_txt}"
    )
    loss = result.get("expected_loss_if_ship_treatment")
    recommendation = (
        "Ship the treatment; the expected loss from being wrong is small."
        if decision == "ship_treatment"
        else (
            "Keep the control; the treatment is more likely to hurt than help."
            if decision == "keep_control"
            else "Not a clear winner yet — collect more data before deciding."
        )
    )
    if loss is not None:
        recommendation += f" Expected loss if you ship B anyway: {loss:.4g}."
    return {"headline": headline, "details": details, "recommendation": recommendation}


def sequential_conclusion(result: Dict) -> Dict[str, str]:
    decision = result.get("final_decision")
    alpha = result.get("alpha", 0.05)
    looks = result.get("looks", [])
    if not looks:
        return {"headline": "No looks available.", "details": "", "recommendation": ""}
    last = looks[-1]

    if decision == "reject_null":
        headline = "A significant effect was detected using a peek-safe sequential rule."
    else:
        headline = "No significant effect yet after applying peek-safe corrections."

    details = (
        f"At the final look ({last['n_per_arm']} users/arm) the raw p-value was "
        f"{last['naive_p_value']:.4g}, the always-valid p-value was "
        f"{last['always_valid_p_value']:.4g}, and the significance boundary for "
        f"this look was p < {last['nominal_p_boundary']:.4g} (alpha spending: "
        f"{result.get('spending')})."
    )
    recommendation = (
        "You can stop and ship — the result is robust to repeated peeking."
        if decision == "reject_null"
        else "Keep collecting data; peeking so far has not crossed the corrected boundary."
    )
    return {"headline": headline, "details": details, "recommendation": recommendation}


def causal_conclusion(result: Dict) -> Dict[str, str]:
    method = result.get("method", "causal method")
    estimate = result.get("effect") if result.get("effect") is not None else result.get("ate")
    if estimate is None:
        estimate = result.get("att")

    if estimate is None:
        return {"headline": "Causal estimate unavailable.", "details": "", "recommendation": ""}

    ci = result.get("ci") or result.get("confidence_interval")
    ci_txt = f" (95% CI [{ci[0]:.4g}, {ci[1]:.4g}])" if ci else ""
    headline = (
        f"{method}: the estimated causal effect of treatment is {estimate:+.4g}{ci_txt}."
    )
    details = (
        f"Using {method}, we estimate that receiving the treatment changes the "
        f"outcome by {estimate:+.4g}. This estimate adjusts for confounding "
        f"variables rather than relying on a raw group comparison."
    )
    direction = "positive" if estimate > 0 else "negative"
    recommendation = (
        f"The treatment appears to have a {direction} causal impact — validate with a "
        f"randomised test where possible and run sensitivity checks on unmeasured "
        f"confounding."
    )
    if result.get("naive_estimate") is not None:
        recommendation += (
            f" Note the naive (unadjusted) difference was "
            f"{result['naive_estimate']:+.4g}, illustrating the confounding bias."
        )
    return {"headline": headline, "details": details, "recommendation": recommendation}

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

N = statistics.NormalDist()
TEAM_COUNT = 12.0
DISCOUNT = 0.85
BASELINE = ((120.0, 0.25), (160.0, 0.50), (200.0, 0.25))
STATES = {
    "out": (-math.inf, 0.0),
    "depth": (0.0, 60.0),
    "usable": (60.0, 120.0),
    "starter": (120.0, 200.0),
    "premium": (200.0, 280.0),
    "elite": (280.0, math.inf),
}


def phi(z: float) -> float:
    return 0.0 if not math.isfinite(z) else N.pdf(z)


def marginal_at_x(x: float) -> float:
    return sum(p * max(0.0, x - b) for b, p in BASELINE)


def c2_at_x(x: float) -> float:
    return (TEAM_COUNT * marginal_at_x(x) + 0.5 * max(0.0, x)) / (TEAM_COUNT + 1.0)


def direct_conditional_c2(mu: float, sd: float, state: str) -> float:
    if state == "out":
        return 0.0
    lo, hi = STATES[state]
    zl = (lo - mu) / sd if math.isfinite(lo) else -math.inf
    zu = (hi - mu) / sd if math.isfinite(hi) else math.inf
    pl = 0.0 if zl == -math.inf else N.cdf(zl)
    pu = 1.0 if zu == math.inf else N.cdf(zu)
    mass = max(0.0, min(1.0, pu - pl))
    if mass <= 1e-12:
        return 0.0
    ex = mu + sd * (phi(zl) - phi(zu)) / mass
    em = 0.0
    for b, p in BASELINE:
        lower = max(lo, b)
        if lower >= hi:
            continue
        za = (lower - mu) / sd
        zb = (hi - mu) / sd if math.isfinite(hi) else math.inf
        pa = N.cdf(za)
        pb = 1.0 if zb == math.inf else N.cdf(zb)
        m = max(0.0, pb - pa)
        numerator = (mu - b) * m + sd * (phi(za) - phi(zb))
        em += p * max(0.0, numerator / mass)
    return (TEAM_COUNT * em + 0.5 * max(0.0, ex)) / (TEAM_COUNT + 1.0)


def central_c2(mu: float, state: str) -> float:
    if state == "out":
        return 0.0
    lo, hi = STATES[state]
    x = max(0.0, mu, lo)
    if math.isfinite(hi):
        x = min(x, hi)
    return c2_at_x(x)


def future_value(mu: float, sd: float, probs: dict[str, float], mode: str) -> float:
    if mode == "direct":
        return sum(probs.get(state, 0.0) * direct_conditional_c2(mu, sd, state) for state in STATES)
    return sum(probs.get(state, 0.0) * central_c2(mu, state) for state in STATES)


def three_year(y1: float, y2: tuple[float, float], y3: tuple[float, float], p2: dict[str, float], p3: dict[str, float], mode: str) -> float:
    return c2_at_x(y1) + DISCOUNT * future_value(*y2, p2, mode) + DISCOUNT**2 * future_value(*y3, p3, mode)


def suite(mode: str) -> dict:
    same_probs = {"usable": 0.15, "starter": 0.60, "premium": 0.20, "elite": 0.05}
    high_quality = three_year(165, (205, 35), (210, 35), same_probs, same_probs, mode)
    low_quality = three_year(165, (150, 35), (145, 35), same_probs, same_probs, mode)

    better_probs = {"usable": 0.10, "starter": 0.45, "premium": 0.35, "elite": 0.10}
    worse_probs = {"depth": 0.20, "usable": 0.35, "starter": 0.35, "premium": 0.09, "elite": 0.01}
    better_states = three_year(150, (175, 40), (175, 40), better_probs, better_probs, mode)
    worse_states = three_year(150, (175, 40), (175, 40), worse_probs, worse_probs, mode)

    stable_probs = {"usable": 0.05, "starter": 0.55, "premium": 0.35, "elite": 0.05}
    backup_probs = {"depth": 0.55, "usable": 0.35, "starter": 0.09, "premium": 0.01}
    stable_qb = three_year(225, (220, 30), (215, 30), stable_probs, stable_probs, mode)
    high_variance_backup = three_year(90, (150, 110), (155, 115), backup_probs, backup_probs, mode)

    dev_qb_probs2 = {"depth": 0.15, "usable": 0.25, "starter": 0.45, "premium": 0.13, "elite": 0.02}
    dev_qb_probs3 = {"depth": 0.10, "usable": 0.20, "starter": 0.45, "premium": 0.20, "elite": 0.05}
    credible_dev_qb = three_year(70, (175, 65), (195, 65), dev_qb_probs2, dev_qb_probs3, mode)

    strong_wr_probs = {"depth": 0.10, "usable": 0.20, "starter": 0.40, "premium": 0.23, "elite": 0.07}
    weak_wr_probs = {"depth": 0.35, "usable": 0.40, "starter": 0.20, "premium": 0.05}
    strong_dev_wr = three_year(55, (165, 60), (185, 60), strong_wr_probs, strong_wr_probs, mode)
    weak_dev_wr = three_year(55, (105, 60), (110, 60), weak_wr_probs, weak_wr_probs, mode)

    fixed_probs = {"usable": 0.20, "starter": 0.60, "premium": 0.18, "elite": 0.02}
    low_variance = three_year(150, (160, 25), (160, 25), fixed_probs, fixed_probs, mode)
    high_variance = three_year(150, (160, 90), (160, 90), fixed_probs, fixed_probs, mode)
    uplift = (high_variance / low_variance - 1.0) * 100.0

    return {
        "same_state_different_quality": {
            "higher_quality": high_quality,
            "lower_quality": low_quality,
            "ratio": high_quality / low_quality,
            "pass": high_quality > low_quality,
        },
        "same_quality_different_state_probabilities": {
            "better_state_probs_value": better_states,
            "worse_state_probs_value": worse_states,
            "ratio": better_states / worse_states,
            "pass": better_states > worse_states,
        },
        "stable_starting_qb": stable_qb,
        "weak_path_high_variance_backup_qb": high_variance_backup,
        "stable_over_backup_pass": stable_qb > high_variance_backup,
        "credible_developmental_qb": credible_dev_qb,
        "developmental_value_pass": credible_dev_qb > 0.0,
        "strong_upside_developmental_wr": strong_dev_wr,
        "weak_upside_developmental_wr": weak_dev_wr,
        "strong_over_weak_wr_pass": strong_dev_wr > weak_dev_wr,
        "low_generic_variance": low_variance,
        "high_generic_variance": high_variance,
        "generic_variance_uplift_pct": uplift,
        "generic_variance_no_free_option_pass": uplift <= 5.0,
    }


def main() -> None:
    result = {
        "research_question": "Can within-state player quality be represented without generic Forecast dispersion adding material value already represented by explicit state probabilities?",
        "candidate": "parameter-free state-restricted central Forecast mean",
        "direct_conditional": suite("direct"),
        "central": suite("central"),
        "gate_pct": 5.0,
        "market_inputs_used": False,
        "team_inputs_used": False,
    }
    out = Path("artifacts/variance-orthogonality/variance_orthogonality_synthetic.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

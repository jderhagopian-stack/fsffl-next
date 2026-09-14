from __future__ import annotations

import argparse
import importlib.util
import math
import statistics
import sys
from pathlib import Path

NORMAL = statistics.NormalDist()
ZNODES = tuple(NORMAL.inv_cdf((i + 0.5) / 41) for i in range(41))


def load_base():
    path = Path(__file__).with_name("run_intrinsic_marginal_franchise_challenge.py")
    spec = importlib.util.spec_from_file_location("smooth_candidate_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def weighted_quantile(pmf, p):
    total = 0.0
    for value, weight in sorted(pmf):
        total += weight
        if total >= p:
            return value
    return pmf[-1][0] if pmf else 0.0


def tau_from_baseline(pmf):
    if not pmf:
        return 10.0
    median = weighted_quantile(pmf, 0.50)
    iqr = max(0.0, weighted_quantile(pmf, 0.75) - weighted_quantile(pmf, 0.25))
    return max(5.0, 0.5 * iqr, 0.10 * max(1.0, median))


def softplus(z):
    if z > 40:
        return z
    if z < -40:
        return math.exp(z)
    return math.log1p(math.exp(z))


def install(form, base):
    hard = base.marginal_at_x
    original_metrics = base.metrics

    if form == "C1_softplus":
        def value_at_x(x, baseline):
            x = max(0.0, x)
            tau = tau_from_baseline(baseline)
            return sum(
                prob * tau * (softplus((x - b) / tau) - softplus((-b) / tau))
                for b, prob in baseline
            )
        definition = "shifted softplus surplus; smooth positive sub-frontier contribution; tau derives from neutral frontier spread"

    elif form == "C2_jeffreys_supply_integral":
        def value_at_x(x, baseline):
            x = max(0.0, x)
            n = float(base.TEAM_COUNT)
            return (n * hard(x, baseline) + 0.5 * x) / (n + 1.0)
        definition = "Jeffreys-smoothed neutral supply-CDF integral; hard marginal surplus plus a mathematically defined small sub-frontier option mass"

    elif form == "C3_smooth_utilization":
        def sigmoid(z):
            if z >= 35:
                return 1.0
            if z <= -35:
                return 0.0
            return 1.0 / (1.0 + math.exp(-z))

        def value_at_x(x, baseline):
            x = max(0.0, x)
            tau = tau_from_baseline(baseline)
            usage = sum(prob * sigmoid((x - b) / tau) for b, prob in baseline)
            return x * usage
        definition = "production multiplied by smooth probability of improving a neutral eligible starter; width derives from neutral frontier spread"
    else:
        raise SystemExit(f"unknown form: {form}")

    def expected(mu, sd, baseline):
        mu, sd = max(0.0, mu), max(0.0, sd)
        if sd <= 1e-9:
            return value_at_x(mu, baseline)
        return base.mean(value_at_x(max(0.0, mu + sd * z), baseline) for z in ZNODES)

    def metrics_with_developmental(rows, key):
        result = original_metrics(rows, key)
        target_median = base.quantile([r["target"] for r in rows], 0.50)
        developmental = [
            r for r in rows
            if base.age_band(r["position"], r["age"]) == "young" and r["target"] < target_median
        ]
        result["developmental_n"] = len(developmental)
        result["developmental_mae"] = base.mean(abs(r[key] - r["target"]) for r in developmental)
        result["developmental_mean_prediction"] = base.mean(r[key] for r in developmental)
        result["developmental_mean_target"] = base.mean(r["target"] for r in developmental)
        return result

    base.marginal_at_x = value_at_x
    base.expected_marginal = expected
    base.metrics = metrics_with_developmental
    base.MODEL_VERSION = f"intrinsic-smooth-format-normalized-franchise-{form}-v1"
    return definition


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--form", required=True)
    known, remaining = parser.parse_known_args()
    base = load_base()
    definition = install(known.form, base)
    sys.argv = [sys.argv[0], *remaining]
    base.main()
    output_dir = Path(remaining[remaining.index("--output-dir") + 1])
    path = output_dir / "intrinsic_marginal_franchise_challenge.json"
    import json
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["smooth_candidate_form"] = known.form
    payload["smooth_candidate_definition"] = definition
    payload["parameter_provenance"] = {
        "C1_C3_width": "max(5 fantasy points, half neutral weakest-slot IQR, 10% neutral weakest-slot median), recomputed from format-wide supply",
        "C2_prior": "Jeffreys 0.5 pseudocount over a neutral team-count-sized frontier; mathematical smoothing policy, not market-fitted",
        "developmental_group": "young career-state observations below the holdout realized-contribution median; diagnostic only, never a fitting target",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import Position

DISCOUNT = 0.85
REALIZED_HORIZON = 6
POSITIONS = ("QB", "RB", "WR", "TE")
STATE_NAMES = ("out", "depth", "usable", "starter", "premium", "elite")
POSITIVE_STATES = STATE_NAMES[1:]
MEANINGFUL_STATES = ("starter", "premium", "elite")
MIN_TRAIN = 400
MIN_CELL = 30
MODEL_VERSION = "intrinsic-explicit-career-state-v1"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def mean(values):
    xs = list(values)
    return sum(xs) / len(xs) if xs else 0.0


def corr(xs, ys):
    xs, ys = list(xs), list(ys)
    if len(xs) < 2:
        return 0.0
    mx, my = mean(xs), mean(ys)
    dx, dy = [x - mx for x in xs], [y - my for y in ys]
    den = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    return sum(a * b for a, b in zip(dx, dy, strict=True)) / den if den > 1e-12 else 0.0


def quantile(values, p):
    xs = sorted(values)
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo, hi = int(math.floor(z)), int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    f = z - lo
    return xs[lo] * (1 - f) + xs[hi] * f


def age_band(position: str, age: float | None) -> str:
    if age is None:
        return "unknown"
    if position == "QB":
        return "young" if age <= 25 else ("prime" if age <= 31 else "aging")
    return "young" if age <= 23 else ("prime" if age <= 27 else "aging")


def kmeans_1d(values, k=5, iterations=60):
    xs = sorted(math.log1p(max(0.0, float(v))) for v in values if v > 0)
    if len(xs) < k:
        centers = [mean(xs)] * k if xs else [0.0] * k
    else:
        centers = [quantile(xs, (i + 0.5) / k) for i in range(k)]
    for _ in range(iterations):
        groups = [[] for _ in range(k)]
        for x in xs:
            j = min(range(k), key=lambda i: abs(x - centers[i]))
            groups[j].append(x)
        new = [mean(g) if g else centers[i] for i, g in enumerate(groups)]
        new.sort()
        if max(abs(a - b) for a, b in zip(new, centers, strict=True)) < 1e-9:
            centers = new
            break
        centers = new
    centers_raw = [max(0.0, math.expm1(x)) for x in centers]
    thresholds = [(centers_raw[i] + centers_raw[i + 1]) / 2 for i in range(k - 1)]
    return tuple(centers_raw), tuple(thresholds)


def fit_state_boundaries(panel_rows, cutoff_season):
    out = {}
    for pos in POSITIONS:
        vals = [r.points for r in panel_rows if r.position == pos and r.season < cutoff_season and r.points > 0]
        out[pos] = kmeans_1d(vals, 5)
    return out


def state_for_points(points, boundaries):
    if points <= 0:
        return "out"
    _centers, thresholds = boundaries
    idx = 0
    while idx < len(thresholds) and points > thresholds[idx]:
        idx += 1
    return POSITIVE_STATES[idx]


def state_index(name):
    return STATE_NAMES.index(name)


def empirical_state_samples(panel_rows, cutoff_season, boundaries):
    samples = defaultdict(list)
    for r in panel_rows:
        if r.season >= cutoff_season or r.position not in POSITIONS:
            continue
        s = state_for_points(r.points, boundaries[r.position])
        samples[(r.position, s)].append(max(0.0, r.points))
    return samples


def fit_transition_counts(panel_rows, cutoff_season, boundaries, max_horizon=2):
    by_key = {(r.player_id, r.season): r for r in panel_rows if r.position in POSITIONS}
    detailed = defaultdict(lambda: defaultdict(float))
    pos_state = defaultdict(lambda: defaultdict(float))
    pos_only = defaultdict(lambda: defaultdict(float))
    for r in panel_rows:
        if r.season >= cutoff_season or r.position not in POSITIONS:
            continue
        current = state_for_points(r.points, boundaries[r.position])
        band = age_band(r.position, r.age)
        for h in range(1, max_horizon + 1):
            nxt = by_key.get((r.player_id, r.season + h))
            if nxt is None or nxt.season >= cutoff_season:
                continue
            ns = state_for_points(nxt.points, boundaries[r.position])
            detailed[(r.position, band, current, h)][ns] += 1.0
            pos_state[(r.position, current, h)][ns] += 1.0
            pos_only[(r.position, h)][ns] += 1.0
    return detailed, pos_state, pos_only


def smoothed_probs(counts):
    total = sum(counts.values()) + 0.5 * len(STATE_NAMES)
    return {s: (counts.get(s, 0.0) + 0.5) / total for s in STATE_NAMES}


def transition_probs(model, position, band, current, horizon):
    detailed, pos_state, pos_only = model
    d = detailed.get((position, band, current, horizon))
    if d and sum(d.values()) >= MIN_CELL:
        return smoothed_probs(d)
    d = pos_state.get((position, current, horizon))
    if d and sum(d.values()) >= MIN_CELL:
        return smoothed_probs(d)
    d = pos_only.get((position, horizon), {})
    return smoothed_probs(d)


def enforce_qb_meaningful(prob, meaningful_probability):
    p = min(1.0, max(0.0, meaningful_probability))
    hi_total = sum(prob[s] for s in MEANINGFUL_STATES)
    lo_states = tuple(s for s in STATE_NAMES if s not in MEANINGFUL_STATES)
    lo_total = sum(prob[s] for s in lo_states)
    out = {}
    for s in MEANINGFUL_STATES:
        out[s] = p * (prob[s] / hi_total if hi_total > 0 else 1.0 / len(MEANINGFUL_STATES))
    for s in lo_states:
        out[s] = (1 - p) * (prob[s] / lo_total if lo_total > 0 else 1.0 / len(lo_states))
    return out


def state_distribution_for_example(e, boundaries, transitions, qb_probs, horizon):
    current = state_for_points(e.means[0], boundaries[e.position])
    prob = transition_probs(transitions, e.position, age_band(e.position, e.age), current, horizon)
    if e.position == "QB":
        p = qb_probs.get((e.season, e.player_id))
        if p is not None:
            prob = enforce_qb_meaningful(prob, p[horizon - 1])
    return prob


def state_contribution(position, state, samples, baseline, marginal):
    vals = samples.get((position, state), ())
    if not vals or state == "out":
        return 0.0
    return mean(marginal.marginal_at_x(v, baseline[position]) for v in vals)


def d_explicit(e, boundaries, transitions, samples, baseline, qb_probs, marginal):
    current = state_for_points(e.means[0], boundaries[e.position])
    total = state_contribution(e.position, current, samples, baseline, marginal)
    probs = {}
    for h in (1, 2):
        pr = state_distribution_for_example(e, boundaries, transitions, qb_probs, h)
        probs[h + 1] = pr
        expected = sum(pr[s] * state_contribution(e.position, s, samples, baseline, marginal) for s in STATE_NAMES)
        total += (DISCOUNT ** h) * expected
    return total, probs


def d_terminal(e, boundaries, transitions, samples, baseline, qb_probs, marginal):
    pr = state_distribution_for_example(e, boundaries, transitions, qb_probs, 2)
    expected = sum(pr[s] * state_contribution(e.position, s, samples, baseline, marginal) for s in STATE_NAMES)
    return (DISCOUNT ** 3) * expected


def fit_d_continuation(training, targets, contexts, qb_probs, marginal):
    parents, cells = {}, {}
    for pos in POSITIONS:
        vals = [e for e in training if e.position == pos and e.season in contexts]
        xs, ys = [], []
        for e in vals:
            boundaries, transitions, samples, baseline = contexts[e.season]
            base, _ = d_explicit(e, boundaries, transitions, samples, baseline, qb_probs, marginal)
            x = d_terminal(e, boundaries, transitions, samples, baseline, qb_probs, marginal)
            xs.append(x)
            ys.append(max(0.0, targets[id(e)] - base))
        den = sum(x * x for x in xs)
        parents[pos] = max(0.0, sum(x * y for x, y in zip(xs, ys, strict=True)) / den) if den > 1e-9 else 0.0
        for band in ("young", "prime", "aging"):
            band_vals = [e for e in vals if age_band(pos, e.age) == band]
            xx, yy = [], []
            for e in band_vals:
                boundaries, transitions, samples, baseline = contexts[e.season]
                base, _ = d_explicit(e, boundaries, transitions, samples, baseline, qb_probs, marginal)
                x = d_terminal(e, boundaries, transitions, samples, baseline, qb_probs, marginal)
                xx.append(x)
                yy.append(max(0.0, targets[id(e)] - base))
            den2 = sum(x * x for x in xx)
            raw = max(0.0, sum(x * y for x, y in zip(xx, yy, strict=True)) / den2) if den2 > 1e-9 else parents[pos]
            n = len(band_vals)
            w = n / (n + 100.0) if n >= MIN_CELL else 0.0
            cells[(pos, band)] = w * raw + (1 - w) * parents[pos]
    return parents, cells


def d_predict(e, contexts, qb_probs, marginal, parents, cells):
    boundaries, transitions, samples, baseline = contexts[e.season]
    base, probs = d_explicit(e, boundaries, transitions, samples, baseline, qb_probs, marginal)
    terminal = d_terminal(e, boundaries, transitions, samples, baseline, qb_probs, marginal)
    cf = cells.get((e.position, age_band(e.position, e.age)), parents[e.position])
    return base + terminal * cf, probs


def build_fold_contexts(panel_rows, forecast_baselines, seasons):
    contexts = {}
    for season in seasons:
        boundaries = fit_state_boundaries(panel_rows, season)
        transitions = fit_transition_counts(panel_rows, season, boundaries)
        samples = empirical_state_samples(panel_rows, season, boundaries)
        contexts[season] = (boundaries, transitions, samples, forecast_baselines[season])
    return contexts


def hard_targets(examples, panel_rows, actual_baselines, marginal):
    by_key = {(r.player_id, r.season): r for r in panel_rows}
    return {id(e): marginal.realized_marginal_target(e, by_key, actual_baselines) for e in examples}


def c2_at_x(x, baseline, marginal):
    return (12.0 * marginal.marginal_at_x(x, baseline) + 0.5 * max(0.0, x)) / 13.0


def c2_expected(mu, sd, baseline, marginal):
    if sd <= 1e-9:
        return c2_at_x(mu, baseline, marginal)
    return mean(c2_at_x(max(0.0, mu + sd * z), baseline, marginal) for z in marginal.ZNODES)


def fit_generic_continuation(training, targets, baselines, explicit_fn, terminal_fn):
    parents, cells = {}, {}
    for pos in POSITIONS:
        vals = [e for e in training if e.position == pos and e.season in baselines]
        xs = [terminal_fn(e, baselines[e.season]) for e in vals]
        ys = [max(0.0, targets[id(e)] - explicit_fn(e, baselines[e.season])) for e in vals]
        den = sum(x * x for x in xs)
        parents[pos] = max(0.0, sum(x * y for x, y in zip(xs, ys, strict=True)) / den) if den > 1e-9 else 0.0
        for band in ("young", "prime", "aging"):
            subset = [e for e in vals if age_band(pos, e.age) == band]
            xx = [terminal_fn(e, baselines[e.season]) for e in subset]
            yy = [max(0.0, targets[id(e)] - explicit_fn(e, baselines[e.season])) for e in subset]
            den2 = sum(x * x for x in xx)
            raw = max(0.0, sum(x * y for x, y in zip(xx, yy, strict=True)) / den2) if den2 > 1e-9 else parents[pos]
            n = len(subset)
            w = n / (n + 100.0) if n >= MIN_CELL else 0.0
            cells[(pos, band)] = w * raw + (1 - w) * parents[pos]
    return parents, cells


def metrics(rows, key):
    errs = [abs(r[key] - r["target"]) for r in rows]
    targets = [r["target"] for r in rows]
    q90, q25, q50 = quantile(targets, 0.90), quantile(targets, 0.25), quantile(targets, 0.50)
    groups = {
        "young": [r for r in rows if age_band(r["position"], r["age"]) == "young"],
        "prime": [r for r in rows if age_band(r["position"], r["age"]) == "prime"],
        "aging": [r for r in rows if age_band(r["position"], r["age"]) == "aging"],
        "elite": [r for r in rows if r["target"] >= q90],
        "fringe": [r for r in rows if r["target"] <= q25],
        "developmental": [r for r in rows if age_band(r["position"], r["age"]) == "young" and r["target"] < q50],
    }
    by_pos = {p: [r for r in rows if r["position"] == p] for p in POSITIONS}
    by_fold = defaultdict(list)
    for r in rows:
        by_fold[r["season"]].append(r)
    return {
        "n": len(rows),
        "mae": mean(errs),
        "correlation": corr([r[key] for r in rows], targets),
        "position_mae": {p: mean(abs(r[key] - r["target"]) for r in rs) for p, rs in by_pos.items() if rs},
        "group_mae": {g: mean(abs(r[key] - r["target"]) for r in rs) for g, rs in groups.items() if rs},
        "fold_mae": {str(s): mean(abs(r[key] - r["target"]) for r in rs) for s, rs in sorted(by_fold.items())},
    }


def state_calibration(rows):
    brier, pred_up, obs_up, pred_down, obs_down = [], [], [], [], []
    for r in rows:
        current = state_index(r["current_state"])
        probs, actual = r["state_probs_y2"], r["actual_state_y2"]
        if actual is None:
            continue
        for s in STATE_NAMES:
            brier.append((probs[s] - (1.0 if s == actual else 0.0)) ** 2)
        pred_up.append(sum(p for s, p in probs.items() if state_index(s) > current))
        obs_up.append(1.0 if state_index(actual) > current else 0.0)
        pred_down.append(sum(p for s, p in probs.items() if state_index(s) < current))
        obs_down.append(1.0 if state_index(actual) < current else 0.0)
    return {
        "multiclass_brier": mean(brier),
        "upward_predicted": mean(pred_up),
        "upward_realized": mean(obs_up),
        "downward_predicted": mean(pred_down),
        "downward_realized": mean(obs_down),
        "n": len(obs_up),
    }


def evaluate(examples, panel_rows, forecast_pools, forecast_baselines, forecast_econ, actual_baselines, qb_probs, legacy, v5c, marginal):
    targets = hard_targets(examples, panel_rows, actual_baselines, marginal)
    seasons = sorted({e.season for e in examples if e.season in forecast_baselines})
    contexts = build_fold_contexts(panel_rows, forecast_baselines, seasons)
    panel_by = {(r.player_id, r.season): r for r in panel_rows}
    rows = []
    for holdout in seasons:
        train = [e for e in examples if e.season <= holdout - REALIZED_HORIZON and e.season in contexts]
        test = [e for e in examples if e.season == holdout and e.season in contexts]
        if len(train) < MIN_TRAIN or not test:
            continue
        fitted = v5c.old_fit(train, legacy)
        tapers = v5c.fit_tapers(train)
        dparents, dcells = fit_d_continuation(train, targets, contexts, qb_probs, marginal)
        bparents, bcells, _ = marginal.fit_marginal_continuation(train, targets, forecast_baselines)

        def bexp(e, b):
            return sum((DISCOUNT ** i) * marginal.expected_marginal(mu, sd, b[e.position]) for i, (mu, sd) in enumerate(zip(e.means, e.sds, strict=True)))

        def bterm(e, b):
            return (DISCOUNT ** 3) * marginal.expected_marginal(e.means[2], e.sds[2], b[e.position])

        def cexp(e, b):
            return sum((DISCOUNT ** i) * c2_expected(mu, sd, b[e.position], marginal) for i, (mu, sd) in enumerate(zip(e.means, e.sds, strict=True)))

        def cterm(e, b):
            return (DISCOUNT ** 3) * c2_expected(e.means[2], e.sds[2], b[e.position], marginal)

        cparents, ccells = fit_generic_continuation(train, targets, forecast_baselines, cexp, cterm)
        inc_train = [marginal.incumbent_raw(e, forecast_pools, forecast_econ, fitted, tapers, legacy, v5c) for e in train]
        inc_scale = marginal.scale_fit(inc_train, [targets[id(e)] for e in train])
        for e in test:
            a = marginal.incumbent_raw(e, forecast_pools, forecast_econ, fitted, tapers, legacy, v5c) * inc_scale
            b = bexp(e, forecast_baselines[e.season]) + bterm(e, forecast_baselines[e.season]) * bcells.get((e.position, age_band(e.position, e.age)), bparents[e.position])
            c = cexp(e, forecast_baselines[e.season]) + cterm(e, forecast_baselines[e.season]) * ccells.get((e.position, age_band(e.position, e.age)), cparents[e.position])
            d, probs = d_predict(e, contexts, qb_probs, marginal, dparents, dcells)
            boundaries = contexts[e.season][0]
            current = state_for_points(e.means[0], boundaries[e.position])
            nxt = panel_by.get((e.player_id, e.season + 1))
            actual = None if nxt is None else state_for_points(nxt.points, boundaries[e.position])
            rows.append({
                "season": holdout,
                "player_id": e.player_id,
                "position": e.position,
                "age": e.age,
                "experience": e.experience,
                "target": targets[id(e)],
                "A": a,
                "B": b,
                "C": c,
                "D": d,
                "current_state": current,
                "state_probs_y2": probs[2],
                "state_probs_y3": probs[3],
                "actual_state_y2": actual,
                "mean_sd": mean(e.sds),
            })
    sd75 = quantile([r["mean_sd"] for r in rows], 0.75)
    weak = []
    for r in rows:
        ci = state_index(r["current_state"])
        up = sum(p for s, p in r["state_probs_y2"].items() if state_index(s) > ci)
        if r["mean_sd"] >= sd75 and up < 0.25:
            weak.append(r)
    result = {
        "rows": rows,
        "metrics": {k: metrics(rows, k) for k in ("A", "B", "C", "D")},
        "state_calibration": state_calibration(rows),
        "generic_uncertainty_control": {
            "n": len(weak),
            "D_mean": mean(r["D"] for r in weak),
            "target_mean": mean(r["target"] for r in weak),
            "D_mae": mean(abs(r["D"] - r["target"]) for r in weak),
        },
    }
    result["fold_wins_D_vs_A"] = sum(
        1
        for s in set(r["season"] for r in rows)
        if mean(abs(r["D"] - r["target"]) for r in rows if r["season"] == s)
        < mean(abs(r["A"] - r["target"]) for r in rows if r["season"] == s)
    )
    return result, contexts, targets


def fit_pedigree_delta(rows, examples, legacy):
    by = {(e.season, e.player_id): e for e in examples}
    pairs = [(r, by[(r["season"], r["player_id"])]) for r in rows if (r["season"], r["player_id"]) in by]
    if not pairs:
        return {"retain": False}
    train = [e for _, e in pairs]
    anchors = legacy.position_anchors(train)
    x = [legacy.forecast_vector(e, anchors) for e in train]
    coef = legacy.solve_ridge(x, [e.pedigree for e in train])
    feats, residuals = [], []
    for r, e in pairs:
        feats.append(e.pedigree - legacy.dot(legacy.forecast_vector(e, anchors), coef))
        residuals.append(r["target"] - r["D"])
    den = sum(f * f for f in feats)
    beta = sum(f * y for f, y in zip(feats, residuals, strict=True)) / den if den > 1e-9 else 0.0
    mae0 = mean(abs(y) for y in residuals)
    mae1 = mean(abs(y - beta * f) for y, f in zip(residuals, feats, strict=True))
    return {"coefficient": beta, "base_mae": mae0, "with_residual_mae": mae1, "retain": mae1 < mae0 * 0.995}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--model-a-rows", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    legacy = load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"), "state_d_legacy")
    v5c = load_module(Path(__file__).with_name("run_fundamental_intrinsic_v5c_calibration.py"), "state_d_v5c")
    parity = load_module(Path(__file__).with_name("run_fundamental_intrinsic_production_parity.py"), "state_d_parity")
    marginal = load_module(Path(__file__).with_name("run_intrinsic_marginal_franchise_challenge.py"), "state_d_marginal")

    examples, forecast_econ = parity.build_examples(panel_path=args.career_panel, model_rows_path=args.model_a_rows, qb_results_path=args.qb_results, legacy=legacy)
    panel = legacy.load_rows(args.career_panel)
    qb_probs = parity.load_qb_probabilities(args.qb_results)
    forecast_pools, forecast_baselines, _ = marginal.contexts_from_forecasts(parity, args.model_a_rows)
    _actual_pools, actual_baselines = marginal.contexts_from_actual(panel)

    evaluation, _contexts, _targets = evaluate(examples, panel, forecast_pools, forecast_baselines, forecast_econ, actual_baselines, qb_probs, legacy, v5c, marginal)
    pedigree = fit_pedigree_delta(evaluation["rows"], examples, legacy)
    rows = evaluation.pop("rows")

    payload = {
        "model_version": MODEL_VERSION,
        "definition": "discounted expected neutral-format marginal contribution integrated over explicit career-state probabilities; generic forecast SD does not create cross-state upside",
        "example_count": len(examples),
        "state_names": STATE_NAMES,
        "state_boundary_method": "five positive football-production states learned by 1D k-means on log1p PIT production plus explicit out state; thresholds refit chronologically",
        "transition_method": "position x age-band x current-state empirical transitions with Jeffreys smoothing and hierarchical backoff; QB starter+ mass constrained by governed QB meaningful-starter Y2/Y3 probability where available",
        "validation": evaluation,
        "pedigree": pedigree,
        "leakage": {"market": False, "league_market": False, "transactions": False, "owner": False, "team_roster": False, "team_replacement": False},
    }
    (args.output_dir / "explicit_state_validation_rows.json").write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    (args.output_dir / "intrinsic_explicit_state_challenge.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"metrics": evaluation["metrics"], "state_calibration": evaluation["state_calibration"], "pedigree": pedigree, "fold_wins_D_vs_A": evaluation["fold_wins_D_vs_A"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import statistics
import sys
import time
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import Position

DISCOUNT = 0.85
REALIZED_HORIZON = 6
MIN_TRAIN = 400
MIN_CELL = 40
POSITIONS = ("QB", "RB", "WR", "TE")
POS_ENUM = tuple(Position(p) for p in POSITIONS)
TEAM_COUNT = 12
DIRECT = {Position.QB: 1, Position.RB: 2, Position.WR: 3, Position.TE: 1}
FLEX = 1
SUPERFLEX = 1
NORMAL = statistics.NormalDist()
ZNODES = tuple(NORMAL.inv_cdf((i + 0.5) / 41) for i in range(41))
MODEL_VERSION = "intrinsic-format-normalized-marginal-franchise-challenger-v1"


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
    return sum(xs) / len(xs) if xs else math.nan


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


def corr(xs, ys):
    if len(xs) < 2:
        return math.nan
    mx, my = mean(xs), mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return sum(x*y for x, y in zip(dx, dy, strict=True)) / den if den > 1e-12 else 0.0


def age_band(position: str, age: float | None) -> str:
    if age is None:
        return "unknown"
    if position == "QB":
        return "young" if age <= 25 else ("prime" if age <= 31 else "aging")
    return "young" if age <= 23 else ("prime" if age <= 27 else "aging")


def relevance(value: float, pool: tuple[float, ...], demand: int) -> float:
    if value <= 0 or demand <= 0 or not pool:
        return 0.0
    greater = len(pool) - bisect_right(pool, value)
    return min(1.0, demand / (1 + greater))


def slot_layers(
    pools: dict[Position, tuple[float, ...]],
    *,
    team_count: int = TEAM_COUNT,
    direct: dict[Position, int] = DIRECT,
    flex: int = FLEX,
    superflex: int = SUPERFLEX,
):
    remaining = {p: list(sorted((max(0.0, float(v)) for v in pools.get(p, ())), reverse=True)) for p in POS_ENUM}
    cursor = {p: 0 for p in POS_ENUM}
    layers: list[dict[str, object]] = []

    def take(p: Position):
        i = cursor[p]
        vals = remaining[p]
        if i >= len(vals) or vals[i] <= 0:
            return None
        cursor[p] += 1
        return vals[i]

    for p in POS_ENUM:
        for slot_index in range(max(0, int(direct.get(p, 0)))):
            vals = [v for _ in range(team_count) if (v := take(p)) is not None]
            if vals:
                layers.append({"name": f"{p.value}{slot_index+1}", "eligible": (p.value,), "values": tuple(vals)})

    def take_best(eligible):
        choices = []
        for p in eligible:
            i = cursor[p]
            vals = remaining[p]
            if i < len(vals) and vals[i] > 0:
                choices.append((vals[i], p.value, p))
        if not choices:
            return None
        _, _, p = max(choices)
        value = take(p)
        return (p, value)

    for slot_index in range(max(0, flex)):
        vals = []
        for _ in range(team_count):
            item = take_best((Position.RB, Position.WR, Position.TE))
            if item is None:
                break
            vals.append(item[1])
        if vals:
            layers.append({"name": f"FLEX{slot_index+1}", "eligible": ("RB", "WR", "TE"), "values": tuple(vals)})

    for slot_index in range(max(0, superflex)):
        vals = []
        for _ in range(team_count):
            item = take_best(POS_ENUM)
            if item is None:
                break
            vals.append(item[1])
        if vals:
            layers.append({"name": f"SF{slot_index+1}", "eligible": POSITIONS, "values": tuple(vals)})
    return tuple(layers)


def weakest_slot_distribution(layers, position: str):
    eligible = [tuple(float(v) for v in layer["values"]) for layer in layers if position in layer["eligible"]]
    if not eligible:
        return ((0.0, 1.0),)
    support = sorted(set(v for layer in eligible for v in layer))
    prev_cdf = 0.0
    pmf = []
    for x in support:
        survival = 1.0
        for layer in eligible:
            cdf = sum(v <= x for v in layer) / len(layer)
            survival *= (1.0 - cdf)
        cdf_min = 1.0 - survival
        mass = max(0.0, cdf_min - prev_cdf)
        if mass > 1e-12:
            pmf.append((x, mass))
        prev_cdf = cdf_min
    total = sum(p for _, p in pmf)
    if total < 1.0 - 1e-9:
        pmf.append((support[-1], 1.0 - total))
    norm = sum(p for _, p in pmf)
    return tuple((b, p / norm) for b, p in pmf)


def baselines_from_pools(pools, **kwargs):
    layers = slot_layers(pools, **kwargs)
    return {p: weakest_slot_distribution(layers, p) for p in POSITIONS}, layers


def marginal_at_x(x: float, baseline) -> float:
    value = max(0.0, x)
    return sum(prob * max(0.0, value - b) for b, prob in baseline)


def expected_marginal(mu: float, sd: float, baseline) -> float:
    mu, sd = max(0.0, mu), max(0.0, sd)
    if sd <= 1e-9:
        return marginal_at_x(mu, baseline)
    return mean(marginal_at_x(max(0.0, mu + sd*z), baseline) for z in ZNODES)


def contexts_from_forecasts(parity, path: Path):
    _model, raw = parity.load_model_a(path)
    pools_by_season = {}
    baselines = {}
    layers = {}
    for season, pools in raw.items():
        canon = {p: tuple(sorted(max(0.0, float(v)) for v in pools.get(p, ()))) for p in POS_ENUM}
        pools_by_season[season] = canon
        baselines[season], layers[season] = baselines_from_pools(canon)
    return pools_by_season, baselines, layers


def contexts_from_actual(panel):
    raw = defaultdict(lambda: defaultdict(list))
    for r in panel:
        raw[r.season][Position(r.position)].append(max(0.0, r.points))
    pools_by_season = {}
    baselines = {}
    for season, pools in raw.items():
        canon = {p: tuple(sorted(max(0.0, float(v)) for v in pools.get(p, ()))) for p in POS_ENUM}
        pools_by_season[season] = canon
        baselines[season], _ = baselines_from_pools(canon)
    return pools_by_season, baselines


def realized_marginal_target(e, panel_by_key, actual_baselines):
    total = 0.0
    for offset in range(REALIZED_HORIZON):
        season = e.season + offset
        row = panel_by_key.get((e.player_id, season))
        if row is None or row.points <= 0 or season not in actual_baselines:
            continue
        total += (DISCOUNT ** offset) * marginal_at_x(row.points, actual_baselines[season][e.position])
    return total


def explicit_challenger(e, baseline):
    return sum((DISCOUNT ** i) * expected_marginal(mu, sd, baseline[e.position]) for i, (mu, sd) in enumerate(zip(e.means, e.sds, strict=True)))


def terminal_driver(e, baseline):
    return (DISCOUNT ** 3) * expected_marginal(e.means[2], e.sds[2], baseline[e.position])


def fit_marginal_continuation(training, targets, baselines):
    parents = {}
    cells = {}
    counts = {}
    for pos in POSITIONS:
        subset = [e for e in training if e.season in baselines and e.position == pos]
        xs = [terminal_driver(e, baselines[e.season]) for e in subset]
        ys = [max(0.0, targets[id(e)] - explicit_challenger(e, baselines[e.season])) for e in subset]
        den = sum(x*x for x in xs)
        parents[pos] = max(0.0, sum(x*y for x, y in zip(xs, ys, strict=True)) / den) if den > 1e-9 else 0.0
        for band in ("young", "prime", "aging"):
            vals = [e for e in subset if age_band(pos, e.age) == band]
            x = [terminal_driver(e, baselines[e.season]) for e in vals]
            y = [max(0.0, targets[id(e)] - explicit_challenger(e, baselines[e.season])) for e in vals]
            den2 = sum(v*v for v in x)
            raw = max(0.0, sum(a*b for a, b in zip(x, y, strict=True)) / den2) if den2 > 1e-9 else parents[pos]
            n = len(vals)
            w = n / (n + 100.0) if n >= MIN_CELL else 0.0
            cells[(pos, band)] = w * raw + (1.0 - w) * parents[pos]
            counts[f"{pos}:{band}"] = n
    return parents, cells, counts


def continuation_factor(e, parents, cells):
    return cells.get((e.position, age_band(e.position, e.age)), parents[e.position])


def challenger_base(e, baselines, parents, cells):
    return explicit_challenger(e, baselines[e.season]) + terminal_driver(e, baselines[e.season]) * continuation_factor(e, parents, cells)


def fit_pedigree(training, targets, baselines, parents, cells, legacy):
    anchors = legacy.position_anchors(training)
    X0 = [legacy.forecast_vector(e, anchors) for e in training]
    residualizer = legacy.solve_ridge(X0, [e.pedigree for e in training])
    feats = [e.pedigree - legacy.dot(legacy.forecast_vector(e, anchors), residualizer) for e in training]
    residuals = [targets[id(e)] - challenger_base(e, baselines, parents, cells) for e in training]
    den = sum(f*f for f in feats)
    coeff = sum(f*r for f, r in zip(feats, residuals, strict=True)) / den if den > 1e-9 else 0.0
    return anchors, residualizer, coeff


def pedigree_adjustment(e, anchors, residualizer, coeff, legacy):
    f = e.pedigree - legacy.dot(legacy.forecast_vector(e, anchors), residualizer)
    return coeff * f


def incumbent_raw(e, forecast_pools, forecast_econ, fitted, tapers, legacy, v5c):
    _base, residual, _repaired = v5c.new_predict(e, fitted, tapers, legacy)
    pool = forecast_pools[e.season][Position(e.position)]
    demand = forecast_econ[e.season][Position(e.position)].selected_starters
    cf = v5c.factor(e, tapers)
    plain = sum((DISCOUNT ** i) * max(0.0, m) for i, m in enumerate(e.means))
    plain += (DISCOUNT ** 3) * max(0.0, e.means[2]) * cf
    relevant = sum((DISCOUNT ** i) * max(0.0, m) * relevance(max(0.0, m), pool, demand) for i, m in enumerate(e.means))
    relevant += (DISCOUNT ** 3) * max(0.0, e.means[2]) * relevance(max(0.0, e.means[2]), pool, demand) * cf
    ratio = residual / plain if plain > 1e-9 else 0.0
    return max(0.0, relevant * (1.0 + ratio))


def scale_fit(xs, ys):
    den = sum(x*x for x in xs)
    return max(0.0, sum(x*y for x, y in zip(xs, ys, strict=True)) / den) if den > 1e-9 else 1.0


def evaluate(examples, forecast_pools, baselines, forecast_econ, targets, legacy, v5c):
    rows = []
    seasons = sorted({e.season for e in examples})
    for holdout in seasons:
        train = [e for e in examples if e.season <= holdout - REALIZED_HORIZON and e.season in baselines]
        test = [e for e in examples if e.season == holdout and e.season in baselines]
        if len(train) < MIN_TRAIN or not test:
            continue
        fitted = v5c.old_fit(train, legacy)
        tapers = v5c.fit_tapers(train)
        parents, cells, _ = fit_marginal_continuation(train, targets, baselines)
        anchors, residualizer, ped_coeff = fit_pedigree(train, targets, baselines, parents, cells, legacy)
        inc_train = [incumbent_raw(e, forecast_pools, forecast_econ, fitted, tapers, legacy, v5c) for e in train]
        inc_scale = scale_fit(inc_train, [targets[id(e)] for e in train])
        for e in test:
            target = targets[id(e)]
            inc = incumbent_raw(e, forecast_pools, forecast_econ, fitted, tapers, legacy, v5c) * inc_scale
            base = challenger_base(e, baselines, parents, cells)
            ped = max(0.0, base + pedigree_adjustment(e, anchors, residualizer, ped_coeff, legacy))
            rows.append({"season": holdout, "position": e.position, "age": e.age, "experience": e.experience,
                         "realized_total": e.realized, "target": target, "incumbent": inc,
                         "challenger_no_pedigree": base, "challenger_pedigree": ped})
    return rows


def metrics(rows, key):
    folds = defaultdict(list)
    positions = defaultdict(list)
    for r in rows:
        err = abs(r[key] - r["target"])
        folds[r["season"]].append(err)
        positions[r["position"]].append(err)
    q90 = quantile([r["target"] for r in rows], .90)
    q25 = quantile([r["target"] for r in rows], .25)
    groups = {
        "young": [r for r in rows if age_band(r["position"], r["age"]) == "young"],
        "prime": [r for r in rows if age_band(r["position"], r["age"]) == "prime"],
        "aging": [r for r in rows if age_band(r["position"], r["age"]) == "aging"],
        "elite": [r for r in rows if r["target"] >= q90],
        "fringe": [r for r in rows if r["target"] <= q25],
    }
    return {
        "n": len(rows),
        "mae": mean(abs(r[key] - r["target"]) for r in rows),
        "correlation_to_realized_marginal": corr([r[key] for r in rows], [r["target"] for r in rows]),
        "correlation_to_discounted_realized_production": corr([r[key] for r in rows], [r["realized_total"] for r in rows]),
        "position_mae": {p: mean(v) for p, v in positions.items()},
        "group_mae": {g: mean(abs(r[key]-r["target"]) for r in vals) for g, vals in groups.items()},
        "fold_mae": {str(s): mean(v) for s, v in folds.items()},
    }


def compare_metrics(rows):
    out = {k: metrics(rows, k) for k in ("incumbent", "challenger_no_pedigree", "challenger_pedigree")}
    for key in ("challenger_no_pedigree", "challenger_pedigree"):
        common = sorted(set(out[key]["fold_mae"]) & set(out["incumbent"]["fold_mae"]))
        out[key]["fold_wins_vs_incumbent"] = sum(out[key]["fold_mae"][s] < out["incumbent"]["fold_mae"][s] for s in common)
        out[key]["folds"] = len(common)
    common = sorted(set(out["challenger_pedigree"]["fold_mae"]) & set(out["challenger_no_pedigree"]["fold_mae"]))
    out["challenger_pedigree"]["fold_wins_vs_no_pedigree"] = sum(
        out["challenger_pedigree"]["fold_mae"][s] < out["challenger_no_pedigree"]["fold_mae"][s] for s in common
    )
    return out


def synthetic(latest_baselines, latest_pools, latest_econ, tapers, marginal_parents, marginal_cells, v5c):
    profiles = [
        ("elite_young_qb", "QB", 24, (360, 380, 390)),
        ("solid_starting_qb", "QB", 29, (285, 270, 255)),
        ("elite_young_rb", "RB", 23, (330, 305, 275)),
        ("elite_young_wr", "WR", 23, (285, 305, 315)),
        ("elite_young_te", "TE", 23, (235, 250, 260)),
        ("aging_productive_rb", "RB", 31, (260, 195, 125)),
        ("developmental_wr", "WR", 22, (105, 155, 205)),
        ("fringe_player", "WR", 27, (45, 35, 25)),
    ]
    rows = []
    for name, pos, age, means in profiles:
        p = Position(pos)
        demand = latest_econ[p].selected_starters
        pool = latest_pools[p]
        cf = tapers.get((pos, v5c.age_band(pos, age)), tapers.get(pos, 0.0))
        inc = sum((DISCOUNT ** i) * m * relevance(m, pool, demand) for i, m in enumerate(means))
        inc += (DISCOUNT ** 3) * means[2] * relevance(means[2], pool, demand) * cf
        mcf = marginal_cells.get((pos, age_band(pos, age)), marginal_parents[pos])
        chal = sum((DISCOUNT ** i) * marginal_at_x(m, latest_baselines[pos]) for i, m in enumerate(means))
        chal += (DISCOUNT ** 3) * marginal_at_x(means[2], latest_baselines[pos]) * mcf
        rows.append({"profile": name, "position": pos, "incumbent_raw_no_pedigree": inc, "challenger_raw_no_pedigree": chal})
    return rows


def timing_test(latest_baseline):
    paths = {"A": (250, 250, 250, 150), "B": (160, 185, 210, 295), "C": (400, 200, 100, 50)}
    return {name: sum((DISCOUNT ** i) * marginal_at_x(v, latest_baseline) for i, v in enumerate(path)) for name, path in paths.items()}


def monte_carlo_equivalence(layers, analytic, runs=3000):
    rng = random.Random(20260914)
    result = {}
    for pos in POSITIONS:
        eligible = [list(layer["values"]) for layer in layers if pos in layer["eligible"]]
        if not eligible:
            continue
        team_count = min(len(v) for v in eligible)
        mins = []
        for _ in range(runs):
            shuffled = []
            for vals in eligible:
                arr = vals[:]
                rng.shuffle(arr)
                shuffled.append(arr)
            mins.extend(min(layer[i] for layer in shuffled) for i in range(team_count))
        grid = [quantile([v for layer in eligible for v in layer], p) for p in (.25, .5, .75, .9, .97)]
        diffs = []
        for x in grid:
            mc = mean(max(0.0, x-b) for b in mins)
            an = marginal_at_x(x, analytic[pos])
            diffs.append(abs(mc-an))
        result[pos] = {"runs": runs, "max_abs_curve_difference": max(diffs), "mean_abs_curve_difference": mean(diffs)}
    return result


def format_sensitivity(latest_pools):
    scenarios = {
        "1QB_1TE": dict(team_count=12, direct=DIRECT, flex=1, superflex=0),
        "SF_1TE": dict(team_count=12, direct=DIRECT, flex=1, superflex=1),
        "SF_2TE": dict(team_count=12, direct={**DIRECT, Position.TE: 2}, flex=1, superflex=1),
        "10team_SF": dict(team_count=10, direct=DIRECT, flex=1, superflex=1),
        "14team_SF": dict(team_count=14, direct=DIRECT, flex=1, superflex=1),
    }
    probes = {
        "QB": quantile(latest_pools[Position.QB], .90),
        "RB": quantile(latest_pools[Position.RB], .90),
        "WR": quantile(latest_pools[Position.WR], .90),
        "TE": quantile(latest_pools[Position.TE], .90),
    }
    out = {}
    for name, cfg in scenarios.items():
        base, _ = baselines_from_pools(latest_pools, **cfg)
        out[name] = {p: marginal_at_x(probes[p], base[p]) for p in POSITIONS}
    scaled = dict(latest_pools)
    scaled[Position.TE] = tuple(v * 1.15 for v in latest_pools[Position.TE])
    tep_base, _ = baselines_from_pools(scaled, team_count=12, direct=DIRECT, flex=1, superflex=1)
    out["TEP_conceptual_15pct_TE_point_uplift"] = {"TE": marginal_at_x(probes["TE"] * 1.15, tep_base["TE"])}
    return out


def performance(latest_examples, baselines, pools, econ, fitted, tapers, legacy, v5c, parents, cells):
    sample = latest_examples[0]
    n = 500
    t0 = time.perf_counter()
    for _ in range(n):
        challenger_base(sample, baselines, parents, cells)
    one_chal = (time.perf_counter() - t0) / n
    t0 = time.perf_counter()
    for _ in range(n):
        incumbent_raw(sample, pools, econ, fitted, tapers, legacy, v5c)
    one_inc = (time.perf_counter() - t0) / n
    t0 = time.perf_counter()
    for e in latest_examples:
        challenger_base(e, baselines, parents, cells)
    pool_chal = time.perf_counter() - t0
    t0 = time.perf_counter()
    for e in latest_examples:
        incumbent_raw(e, pools, econ, fitted, tapers, legacy, v5c)
    pool_inc = time.perf_counter() - t0
    return {
        "latest_pool_n": len(latest_examples),
        "one_player_seconds": {"incumbent": one_inc, "challenger": one_chal},
        "full_latest_pool_seconds": {"incumbent": pool_inc, "challenger": pool_chal},
        "note": "neutral baseline distributions are precomputed once per format/season; no production Monte Carlo is required",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--model-a-rows", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    parity = load_module(Path(__file__).with_name("run_fundamental_intrinsic_production_parity.py"), "marginal_parity")
    legacy = load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"), "marginal_legacy")
    v5c = load_module(Path(__file__).with_name("run_fundamental_intrinsic_v5c_calibration.py"), "marginal_v5c")
    structural = load_module(Path(__file__).with_name("run_intrinsic_structural_audit_fast.py"), "marginal_structural")

    examples, _ = parity.build_examples(panel_path=args.career_panel, model_rows_path=args.model_a_rows, qb_results_path=args.qb_results, legacy=legacy)
    forecast_pools, forecast_baselines, forecast_layers = contexts_from_forecasts(parity, args.model_a_rows)
    forecast_econ = {}
    for season, pools in forecast_pools.items():
        _, economics = structural.context_for_pools({season: pools})
        forecast_econ[season] = economics[season]
    panel = legacy.load_rows(args.career_panel)
    panel_by_key = {(r.player_id, r.season): r for r in panel}
    _, actual_baselines = contexts_from_actual(panel)
    targets = {id(e): realized_marginal_target(e, panel_by_key, actual_baselines) for e in examples}

    rows = evaluate(examples, forecast_pools, forecast_baselines, forecast_econ, targets, legacy, v5c)
    validation = compare_metrics(rows)

    full_fitted = v5c.old_fit(examples, legacy)
    full_tapers = v5c.fit_tapers(examples)
    marginal_parents, marginal_cells, marginal_counts = fit_marginal_continuation(examples, targets, forecast_baselines)
    anchors, residualizer, ped_coeff = fit_pedigree(examples, targets, forecast_baselines, marginal_parents, marginal_cells, legacy)

    latest = max(forecast_pools)
    latest_examples = [e for e in examples if e.season == latest]
    synthetic_rows = synthetic(forecast_baselines[latest], forecast_pools[latest], forecast_econ[latest], full_tapers, marginal_parents, marginal_cells, v5c)
    mc = monte_carlo_equivalence(forecast_layers[latest], forecast_baselines[latest])
    perf = performance(latest_examples, forecast_baselines, forecast_pools, forecast_econ, full_fitted, full_tapers, legacy, v5c, marginal_parents, marginal_cells)

    payload = {
        "model_version": MODEL_VERSION,
        "incumbent": "PR #138 discounted expected career production times deterministic nonlinear starter relevance, plus governed continuation and residual pedigree",
        "challenger": "expected discounted improvement over a neutral franchise's weakest eligible starting slot, integrated over the governed Forecast distribution; neutral slot baselines derive only from league format and format-wide production supply",
        "neutral_baseline": {
            "method": "analytic weakest-eligible-slot distribution",
            "construction": "optimize format-wide direct/FLEX/SUPERFLEX starter layers; treat neutral franchises as exchangeable assignments within each layer; derive the minimum eligible starter distribution from empirical layer CDFs",
            "monte_carlo_equivalence": mc,
        },
        "historical_validation": validation,
        "pedigree": {
            "coefficient_full_sample": ped_coeff,
            "fold_wins_vs_no_pedigree": validation["challenger_pedigree"]["fold_wins_vs_no_pedigree"],
            "mae_no_pedigree": validation["challenger_no_pedigree"]["mae"],
            "mae_with_pedigree": validation["challenger_pedigree"]["mae"],
            "retention_rule": "retain only if chronological improvement is material and broadly non-harmful",
        },
        "continuation": {"parent": marginal_parents, "state_cells": {f"{k[0]}:{k[1]}": v for k, v in marginal_cells.items()}, "cell_counts": marginal_counts},
        "synthetic_perfect_forecast": synthetic_rows,
        "timing_test_WR": timing_test(forecast_baselines[latest]["WR"]),
        "format_sensitivity": format_sensitivity(forecast_pools[latest]),
        "performance": perf,
        "independence": {
            "broad_market": False, "league_market": False, "actual_trade_prices": False,
            "owner_behavior": False, "team_roster": False, "team_need": False,
            "team_specific_replacement": False, "acceptance_behavior": False,
        },
        "te_premium_scoring_plumbing_resolved": False,
        "te_premium_note": "conceptual format response tested; exact reception-aware TE-premium Forecast scoring remains a separate upstream integration issue by management instruction",
        "example_count": len(examples),
        "holdout_rows": len(rows),
        "season_range": [min(e.season for e in examples), max(e.season for e in examples)],
    }
    out = args.output_dir / "intrinsic_marginal_franchise_challenge.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

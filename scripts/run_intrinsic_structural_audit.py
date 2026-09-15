from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import Position
from fsffl.value.intrinsic_economics import structural_position_economics

DISCOUNT = 0.85
REALIZED_HORIZON = 6
POSITIONS = ("QB", "RB", "WR", "TE")
NON_QB = ("RB", "WR", "TE")
MIN_TRAIN = 400
MIN_CELL = 40
TEAM_COUNT = 12
DIRECT = {Position.QB: 1, Position.RB: 2, Position.WR: 3, Position.TE: 1}
FLEX = 1
SUPERFLEX = 1
NORMAL = statistics.NormalDist()


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


def q(values, p: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo, hi = int(math.floor(z)), int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    f = z - lo
    return xs[lo] * (1.0 - f) + xs[hi] * f


def age_band(age: float | None) -> str:
    if age is None:
        return "unknown"
    if age <= 23:
        return "<=23"
    if age <= 26:
        return "24-26"
    if age <= 29:
        return "27-29"
    if age <= 32:
        return "30-32"
    return "33+"


def production_quartile(value: float, pool: list[float]) -> int:
    if not pool:
        return 1
    pct = sum(1 for x in pool if x <= value) / len(pool)
    return min(4, max(1, int(min(0.999999, pct) * 4) + 1))


def growth_counts(pairs):
    valid = [(a, b) for a, b in pairs if a > 0]
    n = len(valid)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "any_growth": sum(b > a for a, b in valid) / n,
        "growth_10": sum(b >= a * 1.10 for a, b in valid) / n,
        "growth_20": sum(b >= a * 1.20 for a, b in valid) / n,
        "growth_30": sum(b >= a * 1.30 for a, b in valid) / n,
    }


def structural_counts(pools: dict[Position, list[float]]):
    return structural_position_economics(
        team_count=TEAM_COUNT,
        direct_slots=DIRECT,
        flex_slots=FLEX,
        superflex_slots=SUPERFLEX,
        forecast_means=pools,
    )


def rank_relevance(value: float, pool: list[float], demand: int) -> float:
    if value <= 0 or demand <= 0 or not pool:
        return 0.0
    rank = 1 + sum(1 for x in pool if x > value)
    return min(1.0, demand / max(1, rank))


def expected_rank_relevant(mean_value: float, stddev: float, pool: list[float], demand: int, nodes: int = 41) -> float:
    if mean_value <= 0 and stddev <= 0:
        return 0.0
    if stddev <= 1e-9:
        return max(0.0, mean_value) * rank_relevance(max(0.0, mean_value), pool, demand)
    total = 0.0
    for i in range(nodes):
        z = NORMAL.inv_cdf((i + 0.5) / nodes)
        value = max(0.0, mean_value + stddev * z)
        total += value * rank_relevance(value, pool, demand)
    return total / nodes


def explicit_plain(example, continuation_factor: float) -> float:
    first3 = sum((DISCOUNT ** i) * max(0.0, m) for i, m in enumerate(example.means))
    tail = (DISCOUNT ** 3) * max(0.0, example.means[2]) * continuation_factor
    return first3 + tail


def explicit_structural(example, continuation_factor: float, pool: list[float], demand: int, *, distributional: bool) -> float:
    total = 0.0
    for i, (m, sd) in enumerate(zip(example.means, example.sds, strict=True)):
        if distributional:
            contribution = expected_rank_relevant(max(0.0, m), max(0.0, sd), pool, demand)
        else:
            contribution = max(0.0, m) * rank_relevance(max(0.0, m), pool, demand)
        total += (DISCOUNT ** i) * contribution
    y3 = max(0.0, example.means[2])
    y3sd = max(0.0, example.sds[2])
    tail_base = expected_rank_relevant(y3, y3sd, pool, demand) if distributional else y3 * rank_relevance(y3, pool, demand)
    total += (DISCOUNT ** 3) * tail_base * continuation_factor
    return total


def fit_scale(preds, targets):
    denominator = sum(x * x for x in preds)
    if denominator <= 1e-9:
        return 1.0
    return max(0.0, sum(x * y for x, y in zip(preds, targets, strict=True)) / denominator)


def actual_pools(panel):
    pools = defaultdict(lambda: defaultdict(list))
    for row in panel:
        pools[row.season][Position(row.position)].append(max(0.0, row.points))
    return pools


def actual_structural_target(example, panel_by_key, actual_by_season):
    total = 0.0
    for offset in range(REALIZED_HORIZON):
        season = example.season + offset
        row = panel_by_key.get((example.player_id, season))
        if row is None or row.points <= 0:
            continue
        pools = actual_by_season.get(season)
        if not pools:
            continue
        economics = structural_counts(pools)
        pos = Position(example.position)
        demand = economics[pos].selected_starters
        sorted_pool = sorted(pools[pos], reverse=True)
        rank = 1 + sum(1 for x in sorted_pool if x > row.points)
        if rank <= demand:
            total += (DISCOUNT ** offset) * row.points
    return total


def evaluate_challengers(examples, pools_by_season, panel_by_key, actual_by_season, legacy, v5c):
    rows = []
    for holdout in sorted({e.season for e in examples}):
        train = [e for e in examples if e.season <= holdout - REALIZED_HORIZON]
        test = [e for e in examples if e.season == holdout]
        if len(train) < MIN_TRAIN or not test:
            continue
        fitted = v5c.old_fit(train, legacy)
        tapers = v5c.fit_tapers(train)

        def features(e):
            base, residual, repaired = v5c.new_predict(e, fitted, tapers, legacy)
            position = Position(e.position)
            economics = structural_counts(pools_by_season[e.season])
            pool = list(pools_by_season[e.season][position])
            demand = economics[position].selected_starters
            cf = v5c.factor(e, tapers)
            plain = max(1e-9, explicit_plain(e, cf))
            deterministic = explicit_structural(e, cf, pool, demand, distributional=False)
            distributional = explicit_structural(e, cf, pool, demand, distributional=True)
            residual_share = residual / plain
            b = max(0.0, deterministic * (1.0 + residual_share))
            c = max(0.0, distributional * (1.0 + residual_share))
            a = max(0.0, repaired * economics[position].relative_pressure)
            target = actual_structural_target(e, panel_by_key, actual_by_season)
            return a, b, c, target

        train_features = [features(e) for e in train if e.season in pools_by_season]
        scales = []
        for idx in range(3):
            scales.append(fit_scale([x[idx] for x in train_features], [x[3] for x in train_features]))
        for e in test:
            if e.season not in pools_by_season:
                continue
            a, b, c, target = features(e)
            preds = [a * scales[0], b * scales[1], c * scales[2]]
            rows.append({
                "season": holdout,
                "position": e.position,
                "age": e.age,
                "experience": e.experience,
                "target": target,
                "A": preds[0],
                "B": preds[1],
                "C": preds[2],
            })
    out = {}
    for key in ("A", "B", "C"):
        errors = [abs(r[key] - r["target"]) for r in rows]
        folds = defaultdict(list)
        by_position = defaultdict(list)
        for r in rows:
            folds[r["season"]].append(abs(r[key] - r["target"]))
            by_position[r["position"]].append(abs(r[key] - r["target"]))
        young = [r for r in rows if r["age"] is not None and r["age"] <= 24]
        aging = [r for r in rows if r["age"] is not None and r["age"] >= 30]
        targets = [r["target"] for r in rows]
        elite_cut = q(targets, 0.90)
        elite = [r for r in rows if r["target"] >= elite_cut]
        out[key] = {
            "n": len(rows),
            "mae": mean(errors),
            "fold_mae": {str(season): mean(vals) for season, vals in folds.items()},
            "position_mae": {p: mean(vals) for p, vals in by_position.items()},
            "young_mae": mean(abs(r[key] - r["target"]) for r in young),
            "aging_mae": mean(abs(r[key] - r["target"]) for r in aging),
            "elite_tail_mae": mean(abs(r[key] - r["target"]) for r in elite),
        }
    for key in ("B", "C"):
        common = sorted(set(out[key]["fold_mae"]) & set(out["A"]["fold_mae"]))
        out[key]["fold_wins_vs_A"] = sum(out[key]["fold_mae"][f] < out["A"]["fold_mae"][f] for f in common)
        out[key]["folds"] = len(common)
    return out


def fit_growth_cells(training, pools_by_season, panel_by_key):
    parent = defaultdict(list)
    cells = defaultdict(list)
    for e in training:
        if e.position not in NON_QB or e.age is None or e.season not in pools_by_season:
            continue
        y1 = max(0.0, e.means[0])
        next_row = panel_by_key.get((e.player_id, e.season + 1))
        y2_actual = next_row.points if next_row is not None else 0.0
        quart = production_quartile(y1, list(pools_by_season[e.season][Position(e.position)]))
        parent[(e.position, age_band(e.age))].append((y1, y2_actual))
        cells[(e.position, age_band(e.age), quart)].append((y1, y2_actual))

    def slope(rows):
        denominator = sum(x * x for x, _y in rows)
        return max(0.0, sum(x * y for x, y in rows) / denominator) if denominator > 1e-9 else 0.0

    parent_slope = {k: slope(v) for k, v in parent.items()}
    fitted = {}
    counts = {}
    for key, vals in cells.items():
        counts[str(key)] = len(vals)
        p = parent_slope[(key[0], key[1])]
        if len(vals) < MIN_CELL:
            fitted[key] = p
            continue
        raw = slope(vals)
        weight = len(vals) / (len(vals) + 100.0)
        fitted[key] = weight * raw + (1.0 - weight) * p
    return parent_slope, fitted, counts


def growth_repair_validation(examples, pools_by_season, panel_by_key):
    rows = []
    for holdout in sorted({e.season for e in examples}):
        train = [e for e in examples if e.season <= holdout - 1]
        test = [e for e in examples if e.season == holdout and e.position in NON_QB and e.age is not None]
        if len(train) < MIN_TRAIN or not test:
            continue
        parent, cells, _counts = fit_growth_cells(train, pools_by_season, panel_by_key)
        for e in test:
            if e.season not in pools_by_season:
                continue
            y1 = max(0.0, e.means[0])
            actual = panel_by_key.get((e.player_id, e.season + 1))
            target = actual.points if actual is not None else 0.0
            current = max(0.0, e.means[1])
            quart = production_quartile(y1, list(pools_by_season[e.season][Position(e.position)]))
            challenger = y1 * cells.get((e.position, age_band(e.age), quart), parent.get((e.position, age_band(e.age)), 1.0))
            rows.append({"season": holdout, "position": e.position, "age": e.age, "current": current, "challenger": challenger, "target": target, "y1": y1, "quartile": quart})
    result = {}
    for key in ("current", "challenger"):
        folds = defaultdict(list)
        positions = defaultdict(list)
        for r in rows:
            err = abs(r[key] - r["target"])
            folds[r["season"]].append(err)
            positions[r["position"]].append(err)
        result[key] = {
            "mae": mean(abs(r[key] - r["target"]) for r in rows),
            "position_mae": {p: mean(v) for p, v in positions.items()},
            "fold_mae": {str(s): mean(v) for s, v in folds.items()},
        }
    common = sorted(set(result["current"]["fold_mae"]) & set(result["challenger"]["fold_mae"]))
    result["challenger"]["fold_wins"] = sum(result["challenger"]["fold_mae"][s] < result["current"]["fold_mae"][s] for s in common)
    result["challenger"]["folds"] = len(common)
    result["growth_frequency"] = {
        "predicted_current_y2_vs_y1": growth_counts((r["y1"], r["current"]) for r in rows),
        "predicted_challenger_y2_vs_y1": growth_counts((r["y1"], r["challenger"]) for r in rows),
        "realized_y2_vs_y1": growth_counts((r["y1"], r["target"]) for r in rows),
    }
    return result


def growth_diagnostics(examples, panel_by_key):
    result = {}
    for position in POSITIONS:
        subset = [e for e in examples if e.position == position]
        result[position] = {
            "forecast_y2_vs_y1": growth_counts((e.means[0], e.means[1]) for e in subset),
            "forecast_y3_vs_y2": growth_counts((e.means[1], e.means[2]) for e in subset),
            "realized_y2_vs_y1": growth_counts((e.means[0], panel_by_key.get((e.player_id, e.season + 1)).points if panel_by_key.get((e.player_id, e.season + 1)) else 0.0) for e in subset),
            "realized_y3_vs_y2": growth_counts((panel_by_key.get((e.player_id, e.season + 1)).points if panel_by_key.get((e.player_id, e.season + 1)) else 0.0, panel_by_key.get((e.player_id, e.season + 2)).points if panel_by_key.get((e.player_id, e.season + 2)) else 0.0) for e in subset),
        }
    return result


def synthetic_test(pools_by_season, structural_by_season):
    season = max(pools_by_season)
    pools = pools_by_season[season]
    economics = structural_by_season[season]
    profiles = [
        ("elite_young_qb", Position.QB, (360, 380, 390), (35, 45, 50)),
        ("solid_starting_qb", Position.QB, (285, 270, 255), (45, 55, 65)),
        ("elite_young_rb", Position.RB, (330, 305, 275), (55, 65, 75)),
        ("elite_young_wr", Position.WR, (285, 305, 315), (45, 55, 65)),
        ("elite_young_te", Position.TE, (235, 250, 260), (40, 50, 60)),
        ("aging_productive_rb", Position.RB, (260, 195, 125), (45, 55, 60)),
        ("developmental_wr", Position.WR, (105, 155, 205), (70, 85, 95)),
        ("fringe_depth", Position.WR, (45, 35, 25), (30, 30, 30)),
    ]
    rows = []
    for name, pos, means, sds in profiles:
        current_plain = sum((DISCOUNT ** i) * means[i] for i in range(3)) * economics[pos].relative_pressure
        demand = economics[pos].selected_starters
        pool = list(pools[pos])
        det = sum((DISCOUNT ** i) * means[i] * rank_relevance(means[i], pool, demand) for i in range(3))
        dist = sum((DISCOUNT ** i) * expected_rank_relevant(means[i], sds[i], pool, demand) for i in range(3))
        rows.append({"profile": name, "position": pos.value, "current_A": current_plain, "deterministic_B": det, "distributional_C": dist})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--model-a-rows", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    parity = load_module(Path(__file__).with_name("run_fundamental_intrinsic_production_parity.py"), "structural_audit_parity")
    legacy = load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"), "structural_audit_legacy")
    v5c = load_module(Path(__file__).with_name("run_fundamental_intrinsic_v5c_calibration.py"), "structural_audit_v5c")

    examples, structural = parity.build_examples(panel_path=args.career_panel, model_rows_path=args.model_a_rows, qb_results_path=args.qb_results, legacy=legacy)
    _model, pools = parity.load_model_a(args.model_a_rows)
    panel = legacy.load_rows(args.career_panel)
    panel_by_key = {(row.player_id, row.season): row for row in panel}
    actual_by_season = actual_pools(panel)

    payload = {
        "example_count": len(examples),
        "season_range": [min(e.season for e in examples), max(e.season for e in examples)],
        "current_equation": "discounted Y1-Y3 expected fantasy points + fitted continuation + residual pedigree, then multiplied by one position-wide structural pressure factor; uncertainty propagated to stddev but not mean value",
        "growth_diagnostics": growth_diagnostics(examples, panel_by_key),
        "growth_repair_validation": growth_repair_validation(examples, pools, panel_by_key),
        "structural_challengers": evaluate_challengers(examples, pools, panel_by_key, actual_by_season, legacy, v5c),
        "synthetic_perfect_forecast_test": synthetic_test(pools, structural),
        "challenger_definitions": {
            "A": "incumbent repaired career production times one uniform position pressure factor",
            "B": "deterministic rank-relevance: league starter demand / production-supply rank, capped at 1; no position multiplier",
            "C": "distributional rank-relevance: expected production integrated over the Forecast distribution against the same league-derived rank relevance curve",
        },
        "independence": {
            "market_inputs_used": False,
            "league_market_inputs_used": False,
            "team_utility_inputs_used": False,
            "owner_inputs_used": False,
            "transaction_inputs_used": False,
            "replacement_surplus_inputs_used": False,
        },
    }
    out = args.output_dir / "intrinsic_structural_audit.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

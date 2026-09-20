from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
from bisect import bisect_right
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
ZNODES = tuple(NORMAL.inv_cdf((i + 0.5) / 31) for i in range(31))


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


def quantile(values, p: float) -> float:
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


def context_for_pools(pools_by_season):
    ordered = {}
    economics = {}
    for season, pools in pools_by_season.items():
        canonical = {p: tuple(sorted(max(0.0, float(v)) for v in pools.get(p, ()))) for p in (Position.QB, Position.RB, Position.WR, Position.TE)}
        ordered[season] = canonical
        economics[season] = structural_position_economics(
            team_count=TEAM_COUNT,
            direct_slots=DIRECT,
            flex_slots=FLEX,
            superflex_slots=SUPERFLEX,
            forecast_means=canonical,
        )
    return ordered, economics


def quartile(value: float, pool: tuple[float, ...]) -> int:
    if not pool:
        return 1
    pct = bisect_right(pool, value) / len(pool)
    return min(4, max(1, int(min(0.999999, pct) * 4) + 1))


def relevance(value: float, pool: tuple[float, ...], demand: int) -> float:
    if value <= 0 or demand <= 0 or not pool:
        return 0.0
    greater = len(pool) - bisect_right(pool, value)
    rank = 1 + greater
    return min(1.0, demand / rank)


def expected_relevant(mu: float, sd: float, pool: tuple[float, ...], demand: int) -> float:
    if sd <= 1e-9:
        x = max(0.0, mu)
        return x * relevance(x, pool, demand)
    total = 0.0
    for z in ZNODES:
        x = max(0.0, mu + sd * z)
        total += x * relevance(x, pool, demand)
    return total / len(ZNODES)


def growth_counts(pairs):
    valid = [(a, b) for a, b in pairs if a > 0]
    n = len(valid)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "any_growth": sum(b > a for a, b in valid) / n,
        "growth_10": sum(b >= 1.10 * a for a, b in valid) / n,
        "growth_20": sum(b >= 1.20 * a for a, b in valid) / n,
        "growth_30": sum(b >= 1.30 * a for a, b in valid) / n,
    }


def actual_pool_context(panel):
    raw = defaultdict(lambda: defaultdict(list))
    for row in panel:
        raw[row.season][Position(row.position)].append(max(0.0, row.points))
    return context_for_pools(raw)


def actual_target(example, panel_by_key, actual_pools, actual_economics):
    total = 0.0
    for offset in range(REALIZED_HORIZON):
        season = example.season + offset
        row = panel_by_key.get((example.player_id, season))
        if row is None or row.points <= 0 or season not in actual_pools:
            continue
        pos = Position(example.position)
        pool = actual_pools[season][pos]
        demand = actual_economics[season][pos].selected_starters
        rank = 1 + (len(pool) - bisect_right(pool, row.points))
        if rank <= demand:
            total += (DISCOUNT ** offset) * row.points
    return total


def plain_explicit(e, cf):
    return sum((DISCOUNT ** i) * max(0.0, m) for i, m in enumerate(e.means)) + (DISCOUNT ** 3) * max(0.0, e.means[2]) * cf


def structural_explicit(e, cf, pool, demand, distributional: bool):
    total = 0.0
    for i, (mu, sd) in enumerate(zip(e.means, e.sds, strict=True)):
        x = expected_relevant(mu, sd, pool, demand) if distributional else max(0.0, mu) * relevance(max(0.0, mu), pool, demand)
        total += (DISCOUNT ** i) * x
    y3 = expected_relevant(e.means[2], e.sds[2], pool, demand) if distributional else max(0.0, e.means[2]) * relevance(max(0.0, e.means[2]), pool, demand)
    return total + (DISCOUNT ** 3) * y3 * cf


def scale_fit(xs, ys):
    d = sum(x * x for x in xs)
    return max(0.0, sum(x * y for x, y in zip(xs, ys, strict=True)) / d) if d > 1e-9 else 1.0


def structural_validation(examples, forecast_pools, forecast_econ, panel_by_key, actual_pools, actual_econ, legacy, v5c):
    rows = []
    targets = {id(e): actual_target(e, panel_by_key, actual_pools, actual_econ) for e in examples}
    seasons = sorted({e.season for e in examples})
    for holdout in seasons:
        train = [e for e in examples if e.season <= holdout - REALIZED_HORIZON and e.season in forecast_pools]
        test = [e for e in examples if e.season == holdout and e.season in forecast_pools]
        if len(train) < MIN_TRAIN or not test:
            continue
        fitted = v5c.old_fit(train, legacy)
        tapers = v5c.fit_tapers(train)

        def feat(e):
            _base, residual, repaired = v5c.new_predict(e, fitted, tapers, legacy)
            pos = Position(e.position)
            econ = forecast_econ[e.season][pos]
            pool = forecast_pools[e.season][pos]
            cf = v5c.factor(e, tapers)
            plain = max(1e-9, plain_explicit(e, cf))
            residual_ratio = residual / plain
            bcore = structural_explicit(e, cf, pool, econ.selected_starters, False)
            ccore = structural_explicit(e, cf, pool, econ.selected_starters, True)
            return (
                max(0.0, repaired * econ.relative_pressure),
                max(0.0, bcore * (1.0 + residual_ratio)),
                max(0.0, ccore * (1.0 + residual_ratio)),
                targets[id(e)],
            )

        tf = [feat(e) for e in train]
        scales = [scale_fit([r[i] for r in tf], [r[3] for r in tf]) for i in range(3)]
        for e in test:
            a, b, c, target = feat(e)
            rows.append({"season": holdout, "position": e.position, "age": e.age, "target": target, "A": a * scales[0], "B": b * scales[1], "C": c * scales[2]})

    output = {}
    for key in ("A", "B", "C"):
        folds = defaultdict(list)
        pos = defaultdict(list)
        for r in rows:
            err = abs(r[key] - r["target"])
            folds[r["season"]].append(err)
            pos[r["position"]].append(err)
        target_cut = quantile([r["target"] for r in rows], 0.90)
        groups = {
            "young": [r for r in rows if r["age"] is not None and r["age"] <= 24],
            "aging": [r for r in rows if r["age"] is not None and r["age"] >= 30],
            "elite_tail": [r for r in rows if r["target"] >= target_cut],
        }
        output[key] = {
            "n": len(rows),
            "mae": mean(abs(r[key] - r["target"]) for r in rows),
            "position_mae": {p: mean(v) for p, v in pos.items()},
            "fold_mae": {str(s): mean(v) for s, v in folds.items()},
            **{f"{name}_mae": mean(abs(r[key] - r["target"]) for r in vals) for name, vals in groups.items()},
        }
    for key in ("B", "C"):
        common = sorted(set(output[key]["fold_mae"]) & set(output["A"]["fold_mae"]))
        output[key]["fold_wins_vs_A"] = sum(output[key]["fold_mae"][s] < output["A"]["fold_mae"][s] for s in common)
        output[key]["folds"] = len(common)
    return output


def fit_growth(training, forecast_pools, panel_by_key):
    parents = defaultdict(list)
    cells = defaultdict(list)
    for e in training:
        if e.position not in NON_QB or e.age is None or e.season not in forecast_pools:
            continue
        y1 = max(0.0, e.means[0])
        actual = panel_by_key.get((e.player_id, e.season + 1))
        y2 = actual.points if actual is not None else 0.0
        qtile = quartile(y1, forecast_pools[e.season][Position(e.position)])
        parents[(e.position, age_band(e.age))].append((y1, y2))
        cells[(e.position, age_band(e.age), qtile)].append((y1, y2))

    def slope(rows):
        d = sum(x * x for x, _ in rows)
        return max(0.0, sum(x * y for x, y in rows) / d) if d > 1e-9 else 0.0

    parent = {k: slope(v) for k, v in parents.items()}
    fitted = {}
    counts = {}
    for key, vals in cells.items():
        p = parent[(key[0], key[1])]
        counts["|".join(map(str, key))] = len(vals)
        if len(vals) < MIN_CELL:
            fitted[key] = p
        else:
            raw = slope(vals)
            w = len(vals) / (len(vals) + 100.0)
            fitted[key] = w * raw + (1.0 - w) * p
    return parent, fitted, counts


def growth_validation(examples, forecast_pools, panel_by_key):
    rows = []
    seasons = sorted({e.season for e in examples})
    for holdout in seasons:
        train = [e for e in examples if e.season <= holdout - 1]
        test = [e for e in examples if e.season == holdout and e.position in NON_QB and e.age is not None and e.season in forecast_pools]
        if len(train) < MIN_TRAIN or not test:
            continue
        parent, cells, _ = fit_growth(train, forecast_pools, panel_by_key)
        for e in test:
            y1 = max(0.0, e.means[0])
            actual = panel_by_key.get((e.player_id, e.season + 1))
            target = actual.points if actual is not None else 0.0
            qtile = quartile(y1, forecast_pools[e.season][Position(e.position)])
            challenger = y1 * cells.get((e.position, age_band(e.age), qtile), parent.get((e.position, age_band(e.age)), 1.0))
            rows.append({"season": holdout, "position": e.position, "age": e.age, "quartile": qtile, "y1": y1, "current": max(0.0, e.means[1]), "challenger": challenger, "target": target})
    out = {}
    for key in ("current", "challenger"):
        folds = defaultdict(list)
        positions = defaultdict(list)
        for r in rows:
            err = abs(r[key] - r["target"])
            folds[r["season"]].append(err)
            positions[r["position"]].append(err)
        out[key] = {"mae": mean(abs(r[key] - r["target"]) for r in rows), "position_mae": {p: mean(v) for p, v in positions.items()}, "fold_mae": {str(s): mean(v) for s, v in folds.items()}}
    common = sorted(set(out["current"]["fold_mae"]) & set(out["challenger"]["fold_mae"]))
    out["challenger"]["fold_wins_vs_current"] = sum(out["challenger"]["fold_mae"][s] < out["current"]["fold_mae"][s] for s in common)
    out["challenger"]["folds"] = len(common)
    out["growth_frequency"] = {
        "current": growth_counts((r["y1"], r["current"]) for r in rows),
        "challenger": growth_counts((r["y1"], r["challenger"]) for r in rows),
        "realized": growth_counts((r["y1"], r["target"]) for r in rows),
    }
    return out


def growth_diagnostics(examples, panel_by_key):
    out = {}
    for p in POSITIONS:
        subset = [e for e in examples if e.position == p]
        out[p] = {
            "forecast_y2_vs_y1": growth_counts((e.means[0], e.means[1]) for e in subset),
            "forecast_y3_vs_y2": growth_counts((e.means[1], e.means[2]) for e in subset),
            "realized_next_vs_y1_forecast": growth_counts((e.means[0], panel_by_key.get((e.player_id, e.season + 1)).points if panel_by_key.get((e.player_id, e.season + 1)) else 0.0) for e in subset),
        }
    return out


def synthetic(forecast_pools, forecast_econ):
    season = max(forecast_pools)
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
        econ = forecast_econ[season][pos]
        pool = forecast_pools[season][pos]
        a = sum((DISCOUNT ** i) * means[i] for i in range(3)) * econ.relative_pressure
        b = sum((DISCOUNT ** i) * means[i] * relevance(means[i], pool, econ.selected_starters) for i in range(3))
        c = sum((DISCOUNT ** i) * expected_relevant(means[i], sds[i], pool, econ.selected_starters) for i in range(3))
        rows.append({"profile": name, "position": pos.value, "A_current": a, "B_rank_relevance": b, "C_distributional_relevance": c})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--model-a-rows", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    parity = load_module(Path(__file__).with_name("run_fundamental_intrinsic_production_parity.py"), "structural_fast_parity")
    legacy = load_module(Path(__file__).with_name("run_fundamental_intrinsic_residual_calibration.py"), "structural_fast_legacy")
    v5c = load_module(Path(__file__).with_name("run_fundamental_intrinsic_v5c_calibration.py"), "structural_fast_v5c")
    examples, _ = parity.build_examples(panel_path=args.career_panel, model_rows_path=args.model_a_rows, qb_results_path=args.qb_results, legacy=legacy)
    _model, raw_pools = parity.load_model_a(args.model_a_rows)
    forecast_pools, forecast_econ = context_for_pools(raw_pools)
    panel = legacy.load_rows(args.career_panel)
    panel_by_key = {(r.player_id, r.season): r for r in panel}
    actual_pools, actual_econ = actual_pool_context(panel)

    payload = {
        "example_count": len(examples),
        "season_range": [min(e.season for e in examples), max(e.season for e in examples)],
        "current_equation": "discounted expected Y1-Y3 fantasy production + fitted continuation + residual pedigree, multiplied by one uniform position-wide pressure factor; stddev is reported but does not change mean Intrinsic",
        "growth_diagnostics": growth_diagnostics(examples, panel_by_key),
        "growth_repair_validation": growth_validation(examples, forecast_pools, panel_by_key),
        "structural_challengers": structural_validation(examples, forecast_pools, forecast_econ, panel_by_key, actual_pools, actual_econ, legacy, v5c),
        "synthetic_perfect_forecast_test": synthetic(forecast_pools, forecast_econ),
        "challenger_definitions": {
            "A": "incumbent: repaired career production times one uniform position pressure factor",
            "B": "deterministic nonlinear starter relevance: min(1, league starter demand / production-supply rank), no uniform position multiplier",
            "C": "distributional starter relevance: integrate Forecast mean/std distribution through the same league-rule-derived relevance curve; no upside bonus",
        },
        "independence": {"market": False, "league_market": False, "team_utility": False, "owner": False, "transactions": False, "replacement_surplus": False},
    }
    path = args.output_dir / "intrinsic_structural_audit.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import json
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

POSITIONS = ("QB", "RB", "WR", "TE")
DISCOUNT = 0.85
FORECAST_HORIZON = 3
REALIZED_HORIZON = 6
MIN_PREHISTORY_SEASONS = 5
MIN_TRAIN_EXAMPLES = 400
RIDGE = 1e-6
EPS = 1e-9
FACTOR_NAMES = ("experience", "survival", "pedigree")
MODEL_VERSION = "fundamental-intrinsic-residual-calibration-v1"
FORECAST_BASELINE_VERSION = "fundamental-intrinsic-pit-career-baseline-v1"


@dataclass(frozen=True)
class PanelRow:
    player_id: str
    season: int
    position: str
    points: float
    age: int | None
    experience: int
    rookie: bool
    percentile: float
    draft_pick: int | None


@dataclass(frozen=True)
class State:
    player_id: str
    position: str
    mean: float
    sd: float
    age: int | None
    experience: int
    percentile: float


@dataclass(frozen=True)
class Example:
    season: int
    player_id: str
    position: str
    age: int | None
    experience: int
    pedigree: float
    survival: float
    means: tuple[float, float, float]
    sds: tuple[float, float, float]
    realized: float


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def q(values: list[float], quantile: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    p = quantile * (len(xs) - 1)
    lo, hi = int(math.floor(p)), int(math.ceil(p))
    if lo == hi:
        return xs[lo]
    f = p - lo
    return xs[lo] * (1.0 - f) + xs[hi] * f


def mean(values) -> float:
    xs = list(values)
    return sum(xs) / len(xs) if xs else math.nan


def load_rows(path: Path) -> list[PanelRow]:
    rows: list[PanelRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            if raw["position"] not in POSITIONS:
                continue
            points = float(raw["fantasy_points"])
            if points <= 0:
                continue
            draft_raw = (raw.get("draft_pick") or "").strip()
            rows.append(
                PanelRow(
                    player_id=raw["player_id"],
                    season=int(raw["season"]),
                    position=raw["position"],
                    points=points,
                    age=int(raw["age_year_floor"]) if raw.get("age_year_floor") else None,
                    experience=int(raw["experience_years"]),
                    rookie=(raw.get("is_rookie_cohort") or "").lower() in {"true", "1", "yes", "t"},
                    percentile=float(raw["prior_production_percentile"]),
                    draft_pick=int(draft_raw) if draft_raw else None,
                )
            )
    return rows


def pedigree_score(draft_pick: int | None) -> float:
    if draft_pick is None or draft_pick <= 0:
        return 0.0
    capped = min(260, draft_pick)
    return max(0.0, 1.0 - math.log1p(capped) / math.log1p(260.0))


class FoldCalibration:
    def __init__(self, rows: list[PanelRow], target_season: int, rc):
        self.training = [row for row in rows if row.season <= target_season - 2]
        self.parent: dict[str, dict[str, object]] = {}
        self.cells: dict[tuple[object, ...], dict[str, object]] = {}
        rc_rows = [
            rc.Row(
                player_id=r.player_id,
                season=r.season,
                position=r.position,
                current=r.points,
                nxt=0.0,
                survived=False,
                age=r.age,
                experience=r.experience,
                rookie=r.rookie,
                production_quartile=min(4, max(1, int(r.percentile * 4) + 1)),
            )
            for r in []
        ]
        # Re-read the transition outcomes from the panel through the canonical rc loader shape.
        self.rc_training = []
        raw_by_key = {(r.player_id, r.season): r for r in rows}
        for r in self.training:
            nxt = raw_by_key.get((r.player_id, r.season + 1))
            self.rc_training.append(
                rc.Row(
                    player_id=r.player_id,
                    season=r.season,
                    position=r.position,
                    current=r.points,
                    nxt=nxt.points if nxt is not None else 0.0,
                    survived=nxt is not None,
                    age=r.age,
                    experience=r.experience,
                    rookie=r.rookie,
                    production_quartile=min(4, max(1, int(r.percentile * 4) + 1)),
                )
            )
        for pos in POSITIONS:
            fitted = rc.calibrate_position(self.rc_training, pos)
            if not fitted:
                continue
            self.parent[pos] = fitted[0]
            for item in fitted[1:]:
                key = (
                    pos,
                    item["age_years"] if item["age_years"] != "" else None,
                    int(item["experience_years"]),
                    int(item["prior_production_quartile"]),
                    str(item["is_rookie_cohort"]).lower() == "true",
                )
                self.cells[key] = item

    def supported(self) -> bool:
        seasons = {row.season for row in self.training}
        return len(seasons) >= MIN_PREHISTORY_SEASONS and all(pos in self.parent for pos in POSITIONS)

    def transition(self, state: State, *, rookie: bool = False) -> dict[str, float]:
        quartile = min(4, max(1, int(state.percentile * 4) + 1))
        item = self.cells.get((state.position, state.age, state.experience, quartile, rookie), self.parent[state.position])
        return {
            "multiplier": float(item["conditional_production_multiplier"]),
            "survival": float(item["survival_probability"]),
            "dispersion": float(item["conditional_multiplier_stddev"]),
            "multiplier_se": float(item["conditional_multiplier_standard_error"]),
            "survival_se": float(item["survival_standard_error"]),
        }


def assign_percentiles(states: list[State]) -> list[State]:
    by_pos: dict[str, list[State]] = defaultdict(list)
    for state in states:
        by_pos[state.position].append(state)
    result: list[State] = []
    for items in by_pos.values():
        ordered = sorted(items, key=lambda s: (s.mean, s.player_id))
        pct = {s.player_id: (i + 0.5) / len(ordered) for i, s in enumerate(ordered)}
        result.extend(State(s.player_id, s.position, s.mean, s.sd, s.age, s.experience, pct[s.player_id]) for s in items)
    return result


def forecast_one(state: State, calibration: FoldCalibration) -> tuple[State, float]:
    e = calibration.transition(state, rookie=state.experience == 0)
    conditional = state.mean * e["multiplier"]
    nxt_mean = e["survival"] * conditional
    conditional_sd = state.mean * e["dispersion"]
    variance = (
        e["survival"] * conditional_sd**2
        + e["survival"] * (1.0 - e["survival"]) * conditional**2
        + (state.mean * e["multiplier_se"] * e["survival"]) ** 2
        + (conditional * e["survival_se"]) ** 2
    )
    return (
        State(
            player_id=state.player_id,
            position=state.position,
            mean=max(0.0, nxt_mean),
            sd=math.sqrt(max(0.0, variance)),
            age=None if state.age is None else state.age + 1,
            experience=state.experience + 1,
            percentile=state.percentile,
        ),
        e["survival"],
    )


def build_examples(rows: list[PanelRow], rc) -> list[Example]:
    by_season: dict[int, list[PanelRow]] = defaultdict(list)
    by_key = {(r.player_id, r.season): r for r in rows}
    for row in rows:
        by_season[row.season].append(row)
    min_season, max_season = min(by_season), max(by_season)
    examples: list[Example] = []
    for target in range(min_season + 1, max_season - REALIZED_HORIZON + 2):
        calibration = FoldCalibration(rows, target, rc)
        if not calibration.supported():
            continue
        prior = by_season.get(target - 1, [])
        current = [State(r.player_id, r.position, r.points, 0.0, r.age, r.experience, r.percentile) for r in prior]
        paths: list[dict[str, State]] = []
        source_survival: dict[str, float] = {}
        for offset in range(FORECAST_HORIZON):
            next_states: list[State] = []
            for state in current:
                nxt, survival = forecast_one(state, calibration)
                next_states.append(nxt)
                if offset == 0:
                    source_survival[state.player_id] = survival
            current = assign_percentiles(next_states)
            paths.append({s.player_id: s for s in current})
        prior_map = {r.player_id: r for r in prior}
        for player_id, y1 in paths[0].items():
            if player_id not in paths[1] or player_id not in paths[2] or player_id not in prior_map:
                continue
            p = prior_map[player_id]
            realized = 0.0
            for offset in range(REALIZED_HORIZON):
                actual = by_key.get((player_id, target + offset))
                realized += (DISCOUNT**offset) * (actual.points if actual is not None else 0.0)
            ys = (paths[0][player_id], paths[1][player_id], paths[2][player_id])
            examples.append(
                Example(
                    season=target,
                    player_id=player_id,
                    position=y1.position,
                    age=y1.age,
                    experience=p.experience + 1,
                    pedigree=pedigree_score(p.draft_pick),
                    survival=source_survival.get(player_id, 0.0),
                    means=tuple(s.mean for s in ys),
                    sds=tuple(s.sd for s in ys),
                    realized=realized,
                )
            )
    return examples


def solve_ridge(X: list[list[float]], y: list[float], ridge: float = RIDGE) -> list[float]:
    if not X:
        return []
    p = len(X[0])
    A = [[sum(row[i] * row[j] for row in X) for j in range(p)] for i in range(p)]
    b = [sum(row[i] * target for row, target in zip(X, y)) for i in range(p)]
    for i in range(1, p):
        A[i][i] += ridge
    for i in range(p):
        pivot = max(range(i, p), key=lambda k: abs(A[k][i]))
        A[i], A[pivot] = A[pivot], A[i]
        b[i], b[pivot] = b[pivot], b[i]
        if abs(A[i][i]) < 1e-12:
            A[i][i] = 1e-12
        div = A[i][i]
        A[i] = [v / div for v in A[i]]
        b[i] /= div
        for k in range(p):
            if k == i:
                continue
            factor = A[k][i]
            A[k] = [v - factor * w for v, w in zip(A[k], A[i])]
            b[k] -= factor * b[i]
    return b


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def position_anchors(training: list[Example]) -> dict[str, float]:
    anchors = {}
    for pos in POSITIONS:
        values = [e.realized for e in training if e.position == pos]
        anchors[pos] = max(1.0, q(values, 0.90))
    return anchors


def forecast_vector(e: Example, anchors: dict[str, float]) -> list[float]:
    a = anchors[e.position]
    pos = [1.0 if e.position == p else 0.0 for p in POSITIONS[1:]]
    return [1.0, *(m / a for m in e.means), *(s / a for s in e.sds), *pos]


def factor_value(e: Example, name: str) -> float:
    if name == "experience":
        return min(15.0, max(0.0, float(e.experience))) / 15.0
    if name == "survival":
        return e.survival
    if name == "pedigree":
        return e.pedigree
    raise KeyError(name)


def normalized_three_year(e: Example, anchors: dict[str, float]) -> float:
    a = anchors[e.position]
    return 100.0 * sum((DISCOUNT**i) * m for i, m in enumerate(e.means)) / a


def normalized_target(e: Example, anchors: dict[str, float]) -> float:
    return 100.0 * e.realized / anchors[e.position]


def fit_continuation(training: list[Example], anchors: dict[str, float]) -> dict[str, float]:
    output = {}
    for pos in POSITIONS:
        subset = [e for e in training if e.position == pos]
        xs = [100.0 * (DISCOUNT**FORECAST_HORIZON) * e.means[2] / anchors[pos] for e in subset]
        ys = [max(0.0, normalized_target(e, anchors) - normalized_three_year(e, anchors)) for e in subset]
        denom = sum(x * x for x in xs)
        output[pos] = max(0.0, sum(x * y for x, y in zip(xs, ys)) / denom) if denom > EPS else 0.0
    return output


def baseline_value(e: Example, anchors: dict[str, float], continuation: dict[str, float]) -> float:
    y3_terminal = 100.0 * (DISCOUNT**FORECAST_HORIZON) * e.means[2] / anchors[e.position]
    return normalized_three_year(e, anchors) + continuation[e.position] * y3_terminal


def fit_factor_residualizers(training: list[Example], anchors: dict[str, float], factors: tuple[str, ...]) -> dict[str, list[float]]:
    X = [forecast_vector(e, anchors) for e in training]
    return {name: solve_ridge(X, [factor_value(e, name) for e in training]) for name in factors}


def residualized_factor(e: Example, name: str, anchors: dict[str, float], coeffs: dict[str, list[float]]) -> float:
    return factor_value(e, name) - dot(forecast_vector(e, anchors), coeffs[name])


def fit_residual_model(
    training: list[Example], anchors: dict[str, float], continuation: dict[str, float], factors: tuple[str, ...]
) -> tuple[dict[str, list[float]], list[float]]:
    if not factors:
        return {}, [0.0]
    residualizers = fit_factor_residualizers(training, anchors, factors)
    X = [[1.0, *(residualized_factor(e, name, anchors, residualizers) for name in factors)] for e in training]
    y = [normalized_target(e, anchors) - baseline_value(e, anchors, continuation) for e in training]
    return residualizers, solve_ridge(X, y, ridge=1e-4)


def predict(
    e: Example,
    anchors: dict[str, float],
    continuation: dict[str, float],
    factors: tuple[str, ...],
    residualizers: dict[str, list[float]],
    residual_coeffs: list[float],
) -> tuple[float, float, float]:
    base = baseline_value(e, anchors, continuation)
    if not factors:
        return base, 0.0, base
    residual = residual_coeffs[0] + sum(
        residual_coeffs[i + 1] * residualized_factor(e, name, anchors, residualizers)
        for i, name in enumerate(factors)
    )
    final = max(0.0, base + residual)
    return base, residual, final


def evaluate_bundle(examples: list[Example], factors: tuple[str, ...]) -> dict[str, object]:
    seasons = sorted({e.season for e in examples})
    rows = []
    for holdout_season in seasons:
        training = [e for e in examples if e.season <= holdout_season - REALIZED_HORIZON]
        holdout = [e for e in examples if e.season == holdout_season]
        if len(training) < MIN_TRAIN_EXAMPLES or not holdout:
            continue
        anchors = position_anchors(training)
        continuation = fit_continuation(training, anchors)
        residualizers, coeffs = fit_residual_model(training, anchors, continuation, factors)
        for e in holdout:
            base, residual, final = predict(e, anchors, continuation, factors, residualizers, coeffs)
            target = normalized_target(e, anchors)
            rows.append({
                "season": e.season,
                "player_id": e.player_id,
                "position": e.position,
                "base": base,
                "residual": residual,
                "final": final,
                "target": target,
                "base_error": abs(base - target),
                "final_error": abs(final - target),
            })
    if not rows:
        return {"factors": factors, "n": 0, "mae_gain": 0.0, "fold_win_rate": 0.0, "position_gain": {}}
    base_mae = mean(r["base_error"] for r in rows)
    final_mae = mean(r["final_error"] for r in rows)
    by_fold: dict[int, list[dict[str, object]]] = defaultdict(list)
    by_pos: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_fold[int(row["season"])].append(row)
        by_pos[str(row["position"])].append(row)
    fold_wins = []
    for vals in by_fold.values():
        fold_wins.append(mean(v["final_error"] for v in vals) < mean(v["base_error"] for v in vals))
    pos_gain = {}
    for pos in POSITIONS:
        vals = by_pos.get(pos, [])
        if vals:
            bm = mean(v["base_error"] for v in vals)
            fm = mean(v["final_error"] for v in vals)
            pos_gain[pos] = (bm - fm) / bm if bm > EPS else 0.0
    # Tail diagnostics: top decile by baseline within position-season.
    tail = []
    groups: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[(int(row["season"]), str(row["position"]))].append(row)
    for vals in groups.values():
        cutoff = q([float(v["base"]) for v in vals], 0.90)
        tail.extend(v for v in vals if float(v["base"]) >= cutoff)
    tail_base = mean(v["base_error"] for v in tail) if tail else math.nan
    tail_final = mean(v["final_error"] for v in tail) if tail else math.nan
    return {
        "factors": list(factors),
        "n": len(rows),
        "base_mae": base_mae,
        "final_mae": final_mae,
        "mae_gain": (base_mae - final_mae) / base_mae if base_mae > EPS else 0.0,
        "folds": len(by_fold),
        "fold_win_rate": mean(fold_wins),
        "position_gain": pos_gain,
        "tail_mae_gain": (tail_base - tail_final) / tail_base if tail and tail_base > EPS else 0.0,
    }


def choose_bundle(results: list[dict[str, object]]) -> dict[str, object]:
    def qualifies(r: dict[str, object]) -> bool:
        pos = list(r.get("position_gain", {}).values())
        return (
            int(r.get("n", 0)) > 0
            and float(r.get("mae_gain", 0.0)) >= 0.005
            and float(r.get("fold_win_rate", 0.0)) >= 0.65
            and float(r.get("tail_mae_gain", -1.0)) >= -0.01
            and pos
            and min(pos) >= -0.01
            and sum(v > 0 for v in pos) >= 3
        )
    qualified = [r for r in results if qualifies(r)]
    if not qualified:
        return min(results, key=lambda r: float(r.get("final_mae", math.inf)))
    return min(qualified, key=lambda r: (len(r["factors"]), -float(r["mae_gain"]), -float(r["fold_win_rate"])))


def fit_final(examples: list[Example], factors: tuple[str, ...]) -> dict[str, object]:
    anchors = position_anchors(examples)
    continuation = fit_continuation(examples, anchors)
    residualizers, coeffs = fit_residual_model(examples, anchors, continuation, factors)
    values = []
    residuals = []
    for e in examples:
        base, residual, final = predict(e, anchors, continuation, factors, residualizers, coeffs)
        values.append(final)
        residuals.append(residual)
    display_quantiles = {str(p): q(values, p) for p in (0.10, 0.25, 0.50, 0.75, 0.90, 0.97, 0.99)}
    return {
        "position_anchors": anchors,
        "continuation_coefficients": continuation,
        "factor_residualizers": residualizers,
        "residual_coefficients": coeffs,
        "display_raw_quantiles": display_quantiles,
        "raw_value_min": min(values),
        "raw_value_max": max(values),
        "residual_mean": mean(residuals),
        "residual_sd": statistics.pstdev(residuals) if len(residuals) > 1 else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rc = load_module(Path(__file__).with_name("run_career_calibration.py"), "fundamental_intrinsic_career_calibration")
    rows = load_rows(args.career_panel)
    examples = build_examples(rows, rc)
    if len(examples) < 1000:
        raise SystemExit(f"insufficient PIT examples: {len(examples)}")

    bundles: list[tuple[str, ...]] = [()]
    for size in range(1, len(FACTOR_NAMES) + 1):
        bundles.extend(itertools.combinations(FACTOR_NAMES, size))
    results = [evaluate_bundle(examples, bundle) for bundle in bundles]
    selected = choose_bundle(results)
    selected_factors = tuple(selected["factors"])
    final = fit_final(examples, selected_factors)

    payload = {
        "model_version": MODEL_VERSION,
        "forecast_baseline_version": FORECAST_BASELINE_VERSION,
        "discount_factor": DISCOUNT,
        "forecast_horizon": FORECAST_HORIZON,
        "realized_validation_horizon": REALIZED_HORIZON,
        "target": "discounted realized football production; no market, replacement, Team Utility, or owner inputs",
        "conditioning_features": ["Y1/Y2/Y3 means", "Y1/Y2/Y3 uncertainty", "position"],
        "candidate_residual_factors": list(FACTOR_NAMES),
        "bundle_results": results,
        "selected_bundle": selected,
        "final_parameters": final,
        "example_count": len(examples),
        "season_range": [min(e.season for e in examples), max(e.season for e in examples)],
        "pedigree_definition": "1-log1p(min(draft_pick,260))/log1p(260); undrafted/missing=0",
        "anti_double_counting": "Each selected factor is residualized against the full six-dimensional Y1/Y2/Y3 Forecast mean/uncertainty vector plus position before its Value coefficient is fitted.",
        "market_inputs_used": False,
        "replacement_inputs_used": False,
        "team_utility_inputs_used": False,
    }
    (args.output_dir / "fundamental_intrinsic_residual_calibration.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    report = [
        "# Fundamental Intrinsic residual calibration",
        "",
        f"Model: `{MODEL_VERSION}`",
        f"PIT examples: **{len(examples)}** ({payload['season_range'][0]}-{payload['season_range'][1]})",
        "",
        "The target is six-season discounted realized football production. Broad Market, League Market, replacement surplus, roster need, Team Utility and owner behavior are excluded.",
        "",
        "Every candidate fundamental factor is first residualized against Y1/Y2/Y3 Forecast means, Y1/Y2/Y3 Forecast uncertainty, and position. The Value regression therefore receives only information not linearly explained by the governed Forecast distribution.",
        "",
        "| Residual bundle | N | MAE gain | Fold win rate | Tail MAE gain | Position gains |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for result in results:
        report.append(
            f"| {','.join(result['factors']) or 'none'} | {result['n']} | {result.get('mae_gain',0):.2%} | {result.get('fold_win_rate',0):.1%} | {result.get('tail_mae_gain',0):.2%} | {json.dumps(result.get('position_gain',{}), sort_keys=True)} |"
        )
    report += [
        "",
        f"Selected parsimonious bundle: **{','.join(selected_factors) or 'none'}**.",
        "",
        "## Frozen production parameters",
        "",
        "```json",
        json.dumps(final, indent=2, sort_keys=True),
        "```",
    ]
    (args.output_dir / "fundamental_intrinsic_residual_calibration.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print((args.output_dir / "fundamental_intrinsic_residual_calibration.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

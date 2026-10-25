from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Iterable

POSITIONS = ("QB", "RB", "WR", "TE")
HORIZON = 3
ANNUAL_WEIGHTS = (1.0, 0.85, 0.70)
MIN_PREHISTORY_SEASONS = 5
MIN_POSITION_ROWS = 100
MIN_POSITION_SURVIVORS = 50
TARGET_COVERAGE = 0.80
MATERIAL_MAE_IMPROVEMENT = 0.05
DISAGREEMENT_GAP = 0.20
MARKET_INCREMENTAL_GAIN = 0.02
PRIMARY_CONTEXT = "12t_sf_2rb_3wr_1te_1flex"
CONTEXTS = {
    PRIMARY_CONTEXT: {
        "team_count": 12,
        "required": {"QB": 1, "RB": 2, "WR": 3, "TE": 1},
        "flex": 1,
        "superflex": 1,
    },
    "12t_1qb_2rb_3wr_1te_1flex": {
        "team_count": 12,
        "required": {"QB": 1, "RB": 2, "WR": 3, "TE": 1},
        "flex": 1,
        "superflex": 0,
    },
}
REPLACEMENT_CANDIDATES = (
    "starter_threshold",
    "marginal_lineup_opportunity",
    "first_rostered_replacement",
    "replacement_pool_quantile",
)


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
class EvalRow:
    player_id: str
    position: str
    season: int
    model_a: float
    model_a_sd: float
    affine_feature: float
    realized: float
    age: int | None
    experience: int
    market: float | None = None


def mean(xs: Iterable[float]) -> float:
    values = list(xs)
    return sum(values) / len(values) if values else math.nan


def corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return math.nan
    xb, yb = mean(xs), mean(ys)
    xx = sum((x - xb) ** 2 for x in xs)
    yy = sum((y - yb) ** 2 for y in ys)
    if xx == 0 or yy == 0:
        return 0.0
    return sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / math.sqrt(xx * yy)


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def percentiles(values: list[float]) -> list[float]:
    rs = ranks(values)
    return [r / (len(values) - 1) if len(values) > 1 else 0.5 for r in rs]


def load_calibration_module():
    path = Path(__file__).with_name("run_career_calibration.py")
    spec = importlib.util.spec_from_file_location("pr131_career_calibration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing career calibration script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_rows(path: Path, rc):
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            current = float(raw["fantasy_points"])
            if current <= 0 or raw["position"] not in POSITIONS:
                continue
            pct = float(raw["prior_production_percentile"])
            rows.append(
                rc.Row(
                    player_id=raw["player_id"],
                    season=int(raw["season"]),
                    position=raw["position"],
                    current=current,
                    nxt=float(raw["next_fantasy_points"]),
                    survived=raw["survived_next_season"].strip().lower() in {"true", "1", "t", "yes"},
                    age=int(raw["age_year_floor"]) if raw.get("age_year_floor") else None,
                    experience=int(raw["experience_years"]),
                    rookie=raw["is_rookie_cohort"].strip().lower() in {"true", "1", "t", "yes"},
                    production_quartile=min(4, max(1, int(pct * 4) + 1)),
                )
            )
    return rows


class FoldCalibration:
    def __init__(self, rows, target_season: int, rc):
        self.target_season = target_season
        # Preseason T may use only transitions whose next-season outcome is already
        # known: source transition rows through T-2 (outcome through T-1).
        self.training = [row for row in rows if row.season <= target_season - 2]
        self.evidence = {}
        self.parent = {}
        self.cells = {}
        for pos in POSITIONS:
            fitted = rc.calibrate_position(self.training, pos)
            self.evidence[pos] = fitted
            if fitted:
                self.parent[pos] = fitted[0]
                for item in fitted[1:]:
                    key = (
                        item["age_years"] if item["age_years"] != "" else None,
                        int(item["experience_years"]),
                        int(item["prior_production_quartile"]),
                        str(item["is_rookie_cohort"]).lower() == "true",
                    )
                    self.cells[(pos, *key)] = item

    def supported(self) -> bool:
        seasons = {row.season for row in self.training}
        if len(seasons) < MIN_PREHISTORY_SEASONS:
            return False
        for pos in POSITIONS:
            parent = self.parent.get(pos)
            if not parent:
                return False
            if int(parent["sample_size"]) < MIN_POSITION_ROWS:
                return False
            if int(parent["survivor_sample_size"]) < MIN_POSITION_SURVIVORS:
                return False
        return True

    def transition(self, state: State, *, rookie: bool = False) -> dict[str, float]:
        q = min(4, max(1, int(state.percentile * 4) + 1))
        item = self.cells.get((state.position, state.age, state.experience, q, rookie))
        if item is None:
            item = self.parent[state.position]
        return {
            "multiplier": float(item["conditional_production_multiplier"]),
            "survival": float(item["survival_probability"]),
            "dispersion": float(item["conditional_multiplier_stddev"]),
            "multiplier_se": float(item["conditional_multiplier_standard_error"]),
            "survival_se": float(item["survival_standard_error"]),
        }


def assign_percentiles(states: list[State]) -> list[State]:
    result = []
    by_pos = defaultdict(list)
    for state in states:
        by_pos[state.position].append(state)
    for items in by_pos.values():
        ordered = sorted(items, key=lambda s: (s.mean, s.player_id))
        n = len(ordered)
        pct = {s.player_id: (i + 0.5) / n for i, s in enumerate(ordered)}
        result.extend(replace(s, percentile=pct[s.player_id]) for s in items)
    return result


def forecast_one(state: State, calibration: FoldCalibration) -> State:
    e = calibration.transition(state)
    conditional = state.mean * e["multiplier"]
    next_mean = e["survival"] * conditional
    conditional_sd = state.mean * e["dispersion"]
    variance = (
        e["survival"] * conditional_sd**2
        + e["survival"] * (1 - e["survival"]) * conditional**2
        + (state.mean * e["multiplier_se"] * e["survival"]) ** 2
        + (conditional * e["survival_se"]) ** 2
    )
    return State(
        player_id=state.player_id,
        position=state.position,
        mean=max(0.0, next_mean),
        sd=math.sqrt(max(0.0, variance)),
        age=None if state.age is None else state.age + 1,
        experience=state.experience + 1,
        percentile=state.percentile,
    )


def forecast_paths(rows, season: int, rc):
    calibration = FoldCalibration(rows, season, rc)
    if not calibration.supported():
        return calibration, {}
    prior = [row for row in rows if row.season == season - 1]
    current = [
        State(row.player_id, row.position, row.current, 0.0, row.age, row.experience, (row.production_quartile - 0.5) / 4)
        for row in prior
    ]
    paths = {}
    for offset in range(HORIZON):
        current = assign_percentiles([forecast_one(state, calibration) for state in current])
        paths[offset] = current
    return calibration, paths


def required_counts(context: dict[str, object]) -> dict[str, int]:
    team_count = int(context["team_count"])
    required = context["required"]
    return {pos: team_count * int(required[pos]) for pos in POSITIONS}


def optimized_starters(states: list[State], context: dict[str, object]) -> set[str]:
    counts = required_counts(context)
    selected = set()
    for pos in POSITIONS:
        items = sorted((s for s in states if s.position == pos), key=lambda s: (-s.mean, s.player_id))
        selected.update(s.player_id for s in items[: counts[pos]])
    flex_slots = int(context["team_count"]) * int(context["flex"])
    flex = sorted(
        (s for s in states if s.player_id not in selected and s.position in {"RB", "WR", "TE"}),
        key=lambda s: (-s.mean, s.player_id),
    )
    selected.update(s.player_id for s in flex[:flex_slots])
    sf_slots = int(context["team_count"]) * int(context["superflex"])
    sf = sorted((s for s in states if s.player_id not in selected), key=lambda s: (-s.mean, s.player_id))
    selected.update(s.player_id for s in sf[:sf_slots])
    return selected


def replacement_levels(states: list[State], context_id: str, candidate: str):
    context = CONTEXTS[context_id]
    counts = required_counts(context)
    starters = optimized_starters(states, context)
    result = {}
    for pos in POSITIONS:
        items = sorted((s for s in states if s.position == pos), key=lambda s: (-s.mean, s.player_id))
        if not items:
            result[pos] = (0.0, 0.0)
            continue
        selected = [s for s in items if s.player_id in starters]
        if candidate == "starter_threshold":
            chosen = items[min(len(items) - 1, max(0, counts[pos] - 1))]
        elif candidate == "marginal_lineup_opportunity":
            chosen = selected[-1] if selected else items[min(len(items) - 1, counts[pos] - 1)]
        elif candidate == "first_rostered_replacement":
            chosen = items[min(len(items) - 1, len(selected))]
        elif candidate == "replacement_pool_quantile":
            pool = sorted((s for s in items if s.player_id not in starters), key=lambda s: (s.mean, s.player_id))
            chosen = pool[min(len(pool) - 1, round(0.75 * (len(pool) - 1)))] if pool else items[-1]
        else:
            raise ValueError(candidate)
        result[pos] = (chosen.mean, chosen.sd)
    return result


def actual_states(rows, season: int) -> list[State]:
    return [
        State(row.player_id, row.position, row.current, 0.0, row.age, row.experience, (row.production_quartile - 0.5) / 4)
        for row in rows if row.season == season
    ]


def evaluate_fold(rows, season: int, context_id: str, candidate: str, rc):
    calibration, paths = forecast_paths(rows, season, rc)
    if not paths:
        return calibration, [], []
    forecast_rep = {o: replacement_levels(paths[o], context_id, candidate) for o in range(HORIZON)}
    realized_rep = {o: replacement_levels(actual_states(rows, season + o), context_id, candidate) for o in range(HORIZON)}
    actual = {o: {r.player_id: r for r in rows if r.season == season + o} for o in range(HORIZON)}
    path = {o: {s.player_id: s for s in paths[o]} for o in range(HORIZON)}
    prior = {r.player_id: r for r in rows if r.season == season - 1}
    evaluations = []
    details = []
    for player_id, first in path[0].items():
        if player_id not in prior:
            continue
        model_a = 0.0
        model_var = 0.0
        realized = 0.0
        for offset, weight in enumerate(ANNUAL_WEIGHTS):
            state = path[offset][player_id]
            rep_mean, rep_sd = forecast_rep[offset][state.position]
            model_a += weight * max(0.0, state.mean - rep_mean)
            if state.mean > rep_mean:
                model_var += weight**2 * (state.sd**2 + rep_sd**2)
            actual_row = actual[offset].get(player_id)
            actual_points = actual_row.current if actual_row is not None else 0.0
            realized_replacement = realized_rep[offset][state.position][0]
            realized += weight * max(0.0, actual_points - realized_replacement)
            details.append({
                "fold_id": f"preseason-{season}",
                "target_season": season,
                "as_of": f"{season}-08-31T23:59:59+00:00",
                "evidence_cutoff": f"{season-1}-12-31T23:59:59+00:00",
                "asset_id": player_id,
                "position": state.position,
                "league_context_id": context_id,
                "replacement_candidate": candidate,
                "season_offset": offset,
                "forecast_model_version": f"pr131-fold-career-{season}",
                "player_forecast_mean": state.mean,
                "player_forecast_stddev": state.sd,
                "replacement_forecast_mean": rep_mean,
                "replacement_forecast_stddev": rep_sd,
                "realized_player_points": actual_points,
                "realized_replacement_points": realized_replacement,
                "annual_weight": weight,
                "provenance": "career_transition_panel.csv; calibration rows season<=target-2",
            })
        p = prior[player_id]
        evaluations.append(EvalRow(
            player_id=player_id,
            position=first.position,
            season=season,
            model_a=model_a,
            model_a_sd=math.sqrt(max(0.0, model_var)),
            affine_feature=first.mean,
            realized=realized,
            age=first.age,
            experience=p.experience + 1,
        ))
    return calibration, evaluations, details


def fit_affine(rows: list[EvalRow]):
    xs = [r.affine_feature for r in rows]
    ys = [r.realized for r in rows]
    xb, yb = mean(xs), mean(ys)
    denom = sum((x - xb) ** 2 for x in xs)
    slope = max(0.0, sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / denom) if denom else 0.0
    intercept = yb - slope * xb
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sd = statistics.stdev(residuals) if len(residuals) > 1 else 0.0
    return intercept, slope, sd


def fold_metrics(rows: list[EvalRow], affine):
    intercept, slope, residual_sd = affine
    a_errors, c_errors = [], []
    a_covered = c_covered = 0
    z = 1.2815515655446004
    for row in rows:
        affine_pred = intercept + slope * row.affine_feature
        a_errors.append(row.model_a - row.realized)
        c_errors.append(affine_pred - row.realized)
        if row.model_a - z * row.model_a_sd <= row.realized <= row.model_a + z * row.model_a_sd:
            a_covered += 1
        if affine_pred - z * residual_sd <= row.realized <= affine_pred + z * residual_sd:
            c_covered += 1
    a_mae = mean(abs(e) for e in a_errors)
    c_mae = mean(abs(e) for e in c_errors)
    return {
        "n": len(rows),
        "model_a_mae": a_mae,
        "affine_mae": c_mae,
        "model_a_rmse": math.sqrt(mean(e * e for e in a_errors)),
        "affine_rmse": math.sqrt(mean(e * e for e in c_errors)),
        "model_a_bias": mean(a_errors),
        "affine_bias": mean(c_errors),
        "model_a_coverage": a_covered / len(rows),
        "affine_coverage": c_covered / len(rows),
        "mae_improvement": (c_mae - a_mae) / c_mae if c_mae else 0.0,
    }


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def market_crosswalk(repo: Path) -> dict[str, str]:
    path = repo / "files" / "db_playerids.csv"
    if not path.exists():
        return {}
    mapping = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            gsis = (row.get("gsis_id") or "").strip()
            fp = (row.get("fantasypros_id") or "").strip()
            if gsis and fp and gsis.upper() != "NA" and fp.upper() != "NA":
                mapping[gsis] = fp
    return mapping


def market_snapshot(repo: Path, cutoff: date, context_id: str) -> dict[str, float]:
    commits = [x for x in git(repo, "log", f"--before={cutoff.isoformat()}T23:59:59Z", "--format=%H", "--", "files/values.csv").splitlines() if x]
    value_col = "value_2qb" if "sf" in context_id else "value_1qb"
    for commit in commits[:80]:
        try:
            text = git(repo, "show", f"{commit}:files/values.csv")
        except subprocess.CalledProcessError:
            continue
        reader = csv.DictReader(text.splitlines())
        rows = list(reader)
        fields = set(reader.fieldnames or ())
        if not rows or not {"fp_id", value_col}.issubset(fields):
            continue
        observed_dates = []
        for row in rows:
            raw = (row.get("scrape_date") or "").strip()
            if raw:
                try:
                    observed_dates.append(date.fromisoformat(raw[:10]))
                except ValueError:
                    pass
        if observed_dates and max(observed_dates) > cutoff:
            continue
        out = {}
        for row in rows:
            fp = (row.get("fp_id") or "").strip()
            value = (row.get(value_col) or "").strip()
            if not fp or fp.upper() == "NA" or not value or value.upper() == "NA":
                continue
            try:
                out[fp] = float(value)
            except ValueError:
                pass
        if out:
            return out
    return {}


def attach_market(rows: list[EvalRow], snapshot: dict[str, float], crosswalk: dict[str, str]) -> list[EvalRow]:
    return [replace(row, market=snapshot.get(crosswalk.get(row.player_id, ""))) for row in rows]


def solve_ols(data: list[EvalRow], include_market: bool):
    p = 3 if include_market else 2
    X, y = [], []
    for row in data:
        if include_market and row.market is None:
            continue
        x = [1.0, row.model_a]
        if include_market:
            x.append(float(row.market))
        X.append(x)
        y.append(row.realized)
    if len(X) < max(10, p + 2):
        return None
    A = [[sum(x[i] * x[j] for x in X) for j in range(p)] for i in range(p)]
    b = [sum(x[i] * yy for x, yy in zip(X, y)) for i in range(p)]
    for i in range(p):
        pivot = max(range(i, p), key=lambda k: abs(A[k][i]))
        A[i], A[pivot] = A[pivot], A[i]
        b[i], b[pivot] = b[pivot], b[i]
        if abs(A[i][i]) < 1e-10:
            return None
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


def market_diagnostics(rows: list[EvalRow], prior_rows: list[EvalRow]):
    usable = [r for r in rows if r.market is not None]
    if len(usable) < 10:
        return {"available": False, "n": len(usable)}
    intrinsic = [r.model_a for r in usable]
    market = [float(r.market) for r in usable]
    ip = percentiles(intrinsic)
    mp = percentiles(market)
    i_sd = statistics.pstdev(intrinsic) or 1.0
    m_sd = statistics.pstdev(market) or 1.0
    i_mean, m_mean = mean(intrinsic), mean(market)
    result = {
        "available": True,
        "n": len(usable),
        "pearson": corr(intrinsic, market),
        "spearman": corr(ranks(intrinsic), ranks(market)),
        "mean_absolute_standardized_residual": mean(abs((i - i_mean) / i_sd - (m - m_mean) / m_sd) for i, m in zip(intrinsic, market)),
        "material_disagreement_rate": mean(1.0 if abs(i - m) >= DISAGREEMENT_GAP else 0.0 for i, m in zip(ip, mp)),
        "market_incremental_mae_gain": None,
        "market_adds_incremental_information": None,
    }
    train = [r for r in prior_rows if r.market is not None]
    base = solve_ols(train, False)
    plus = solve_ols(train, True)
    if base and plus:
        base_mae = mean(abs((base[0] + base[1] * r.model_a) - r.realized) for r in usable)
        plus_mae = mean(abs((plus[0] + plus[1] * r.model_a + plus[2] * float(r.market)) - r.realized) for r in usable)
        gain = (base_mae - plus_mae) / base_mae if base_mae else 0.0
        result["market_incremental_mae_gain"] = gain
        result["market_adds_incremental_information"] = gain >= MARKET_INCREMENTAL_GAIN
    return result


def context_shift(rows, season: int, candidate: str, rc):
    _, sf, _ = evaluate_fold(rows, season, PRIMARY_CONTEXT, candidate, rc)
    _, one, _ = evaluate_fold(rows, season, "12t_1qb_2rb_3wr_1te_1flex", candidate, rc)
    one_by = {r.player_id: r for r in one}
    qb, non = [], []
    for row in sf:
        other = one_by.get(row.player_id)
        if other:
            (qb if row.position == "QB" else non).append(row.model_a - other.model_a)
    return {"n": len(qb) + len(non), "qb_relative_gain": mean(qb) if qb else 0.0, "non_qb_relative_gain": mean(non) if non else 0.0}


def scenario_checks(rows: list[EvalRow], fold_rows: dict[int, list[EvalRow]], scarcity: dict[str, float]):
    checks = {}
    rbs = [r for r in rows if r.position == "RB" and r.age is not None]
    pairs = []
    for young in rbs:
        for old in rbs:
            if old.age is None or young.age is None or old.age - young.age < 4:
                continue
            denom = max(young.affine_feature, old.affine_feature)
            if denom > 0 and abs(young.affine_feature - old.affine_feature) / denom <= 0.10:
                pairs.append((young, old))
    accuracy = mean(1.0 if (y.model_a > o.model_a) == (y.realized > o.realized) else 0.0 for y, o in pairs) if pairs else 0.0
    checks["aging_rb_vs_young_rb"] = {"n": len(pairs), "directional_accuracy": accuracy, "pass": bool(pairs) and accuracy >= 0.55}

    def cohort(name: str, subset: list[EvalRow]):
        signal = corr(ranks([r.model_a for r in subset]), ranks([r.realized for r in subset])) if len(subset) >= 10 else math.nan
        checks[name] = {"n": len(subset), "rank_signal_correlation": signal, "pass": len(subset) >= 10 and signal > 0.25}

    qbs = [r for r in rows if r.position == "QB"]
    threshold = sorted(r.affine_feature for r in qbs)[int(0.75 * (len(qbs) - 1))] if qbs else math.inf
    cohort("elite_qb_longevity", [r for r in qbs if r.affine_feature >= threshold and (r.age or 0) <= 33])
    cohort("developing_wr", [r for r in rows if r.position == "WR" and r.age is not None and r.age <= 25 and r.experience <= 3])
    cohort("developing_te", [r for r in rows if r.position == "TE" and r.age is not None and r.age <= 26 and r.experience <= 3])
    checks["position_scarcity_shift"] = {
        **scarcity,
        "pass": scarcity["qb_relative_gain"] > 0 and abs(scarcity["non_qb_relative_gain"]) < abs(scarcity["qb_relative_gain"]),
    }

    changes = []
    seasons = sorted(fold_rows)
    for a, b in zip(seasons, seasons[1:]):
        if b != a + 1:
            continue
        prior = {r.player_id: r for r in fold_rows[a]}
        for nxt in fold_rows[b]:
            old = prior.get(nxt.player_id)
            if old is None:
                continue
            mc = nxt.model_a - old.model_a
            rc = nxt.realized - old.realized
            if abs(mc) > 1e-9 or abs(rc) > 1e-9:
                changes.append((mc, rc))
    direction = mean(1.0 if (m > 0) == (r > 0) else 0.0 for m, r in changes) if changes else 0.0
    change_corr = corr([m for m, _ in changes], [r for _, r in changes]) if len(changes) >= 2 else math.nan
    checks["expected_appreciation_decline"] = {
        "n": len(changes), "directional_accuracy": direction, "change_correlation": change_corr,
        "pass": bool(changes) and direction >= 0.55 and math.isfinite(change_corr) and change_corr > 0.10,
    }
    return checks


def write_csv(path: Path, rows: list[dict[str, object]]):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--dynastyprocess-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rc = load_calibration_module()
    rows = load_rows(args.career_panel, rc)
    max_panel_season = max(r.season for r in rows)
    max_target = max_panel_season - (HORIZON - 1)
    supported = []
    calibrations = {}
    for season in range(min(r.season for r in rows) + 1, max_target + 1):
        calibration = FoldCalibration(rows, season, rc)
        if calibration.supported():
            supported.append(season)
            calibrations[season] = calibration
    if len(supported) < 2:
        raise SystemExit(f"insufficient chronological folds: {supported}")

    calibration_rows = []
    for season in supported:
        calibration = calibrations[season]
        for pos in POSITIONS:
            parent = calibration.parent[pos]
            calibration_rows.append({
                "fold_id": f"preseason-{season}", "target_season": season,
                "as_of": f"{season}-08-31T23:59:59+00:00",
                "evidence_cutoff": f"{season-1}-12-31T23:59:59+00:00",
                "position": pos, "training_transition_rows": parent["sample_size"],
                "training_survivors": parent["survivor_sample_size"],
                "parent_multiplier": parent["conditional_production_multiplier"],
                "parent_survival_probability": parent["survival_probability"],
                "multiplier_standard_error": parent["conditional_multiplier_standard_error"],
                "survival_standard_error": parent["survival_standard_error"],
                "minimum_prehistory_seasons": MIN_PREHISTORY_SEASONS,
            })
    write_csv(args.output_dir / "fold_forecast_calibration.csv", calibration_rows)

    crosswalk = market_crosswalk(args.dynastyprocess_repo)
    all_results = {}
    aggregates = {}
    fold_rows_by_candidate = {}
    all_detail_rows = []
    for candidate in REPLACEMENT_CANDIDATES:
        prior_rows = []
        fold_rows_by_candidate[candidate] = {}
        fold_results = []
        for season in supported:
            _, holdout, details = evaluate_fold(rows, season, PRIMARY_CONTEXT, candidate, rc)
            snapshot = market_snapshot(args.dynastyprocess_repo, date(season, 8, 31), PRIMARY_CONTEXT)
            holdout = attach_market(holdout, snapshot, crosswalk)
            fold_rows_by_candidate[candidate][season] = holdout
            all_detail_rows.extend(details)
            if prior_rows:
                affine = fit_affine(prior_rows)
                fold_results.append({
                    "season": season,
                    "affine_fit": {"intercept": affine[0], "slope": affine[1], "residual_sd": affine[2]},
                    "metrics": fold_metrics(holdout, affine),
                    "market": market_diagnostics(holdout, prior_rows),
                })
            prior_rows.extend(holdout)
        n = sum(f["metrics"]["n"] for f in fold_results)
        def wavg(key: str):
            return sum(f["metrics"][key] * f["metrics"]["n"] for f in fold_results) / n if n else math.nan
        aggregate = {
            "holdout_folds": len(fold_results), "n": n,
            "model_a_mae": wavg("model_a_mae"), "affine_mae": wavg("affine_mae"),
            "model_a_rmse": wavg("model_a_rmse"), "affine_rmse": wavg("affine_rmse"),
            "model_a_coverage": wavg("model_a_coverage"), "affine_coverage": wavg("affine_coverage"),
        }
        aggregate["mae_improvement"] = (aggregate["affine_mae"] - aggregate["model_a_mae"]) / aggregate["affine_mae"] if aggregate["affine_mae"] else 0.0
        aggregate["coverage_error"] = abs(aggregate["model_a_coverage"] - TARGET_COVERAGE)
        aggregates[candidate] = aggregate
        all_results[candidate] = {"aggregate": aggregate, "folds": fold_results}

    write_csv(args.output_dir / "model_a_point_in_time_rows.csv", all_detail_rows)

    best = min(REPLACEMENT_CANDIDATES, key=lambda c: aggregates[c]["model_a_mae"])
    winners = []
    for season in supported[1:]:
        fold_scores = []
        for candidate in REPLACEMENT_CANDIDATES:
            fold = next((f for f in all_results[candidate]["folds"] if f["season"] == season), None)
            if fold:
                fold_scores.append((fold["metrics"]["model_a_mae"], candidate))
        if fold_scores:
            winners.append(min(fold_scores)[1])
    winner_counts = Counter(winners)
    stability = winner_counts[best] / len(winners) if winners else 0.0

    best_rows = [r for season in supported[1:] for r in fold_rows_by_candidate[best].get(season, [])]
    scenarios = scenario_checks(best_rows, fold_rows_by_candidate[best], context_shift(rows, supported[-1], best, rc))
    scenario_passes = sum(bool(v.get("pass")) for v in scenarios.values())
    economic_pass_rate = scenario_passes / len(scenarios)

    market_folds = [f["market"] for f in all_results[best]["folds"] if f["market"].get("available")]
    market_summary = {"available_folds": len(market_folds)}
    if market_folds:
        for key in ("pearson", "spearman", "mean_absolute_standardized_residual", "material_disagreement_rate"):
            market_summary[key] = mean(float(f[key]) for f in market_folds)
        gains = [f["market_incremental_mae_gain"] for f in market_folds if f.get("market_incremental_mae_gain") is not None]
        market_summary["market_incremental_mae_gain"] = mean(gains) if gains else None
        flags = [f["market_adds_incremental_information"] for f in market_folds if f.get("market_adds_incremental_information") is not None]
        market_summary["market_adds_incremental_information_rate"] = mean(1.0 if flag else 0.0 for flag in flags) if flags else None

    agg = aggregates[best]
    material = agg["mae_improvement"] >= MATERIAL_MAE_IMPROVEMENT
    stable = stability >= 0.60
    uncertainty_ok = agg["coverage_error"] <= 0.10
    market_independent = bool(market_folds) and market_summary.get("spearman", 1.0) < 0.98 and market_summary.get("material_disagreement_rate", 0.0) >= 0.10
    enough_folds = agg["holdout_folds"] >= 5
    promotion = material and stable and uncertainty_ok and economic_pass_rate >= 5 / 6 and market_independent and enough_folds

    ordered = sorted(best_rows, key=lambda r: r.model_a)
    decile = max(1, len(ordered) // 10)
    top_resid = mean(r.realized - r.model_a for r in ordered[-decile:]) if ordered else 0.0
    middle = ordered[len(ordered) // 3: 2 * len(ordered) // 3]
    mid_resid = mean(r.realized - r.model_a for r in middle) if middle else 0.0
    residual_gap = abs(top_resid - mid_resid)
    model_b_specific = None
    if agg["holdout_folds"] >= 5 and residual_gap > 0.25 * agg["model_a_mae"]:
        model_b_specific = "bounded nonlinear surplus transformation (persistent elite-tail residual structure)"

    conclusions = {
        "best_replacement": best,
        "replacement_winner_stability": stability,
        "replacement_winner_counts": dict(winner_counts),
        "model_a_materially_outperforms_affine": material,
        "model_a_mae_improvement": agg["mae_improvement"],
        "economic_scenario_pass_rate": economic_pass_rate,
        "uncertainty_calibration_ok": uncertainty_ok,
        "market_independence_ok": market_independent,
        "production_promotion_justified": promotion,
        "model_b_complexity_justified": model_b_specific is not None,
        "model_b_specific_complexity": model_b_specific,
        "top_vs_middle_residual_gap": residual_gap,
    }
    payload = {
        "study_version": "pr131-model-a-benchmark-v1",
        "research_only": True,
        "fold_definition": {
            "supported_target_seasons": supported,
            "affine_holdout_seasons": supported[1:],
            "minimum_prehistory_seasons": MIN_PREHISTORY_SEASONS,
            "minimum_position_rows": MIN_POSITION_ROWS,
            "minimum_position_survivors": MIN_POSITION_SURVIVORS,
            "horizon_seasons": HORIZON,
            "annual_weights": ANNUAL_WEIGHTS,
            "forecast_cutoff_rule": "target T uses transition rows season<=T-2; outcomes known through T-1",
            "terminal_fold_rule": "all three realized seasons must exist in the extracted panel",
        },
        "limitations": [
            "Historical Forecast universe starts from prior-season NFL producers; incoming rookies with no prior NFL season are excluded rather than hindsight-backfilled.",
            "Time weights are fixed transparent research weights; time preference is not estimated.",
            "Historical market values are diagnostics only and never Model A inputs or targets.",
        ],
        "replacement_candidates": aggregates,
        "best_candidate": all_results[best],
        "market_independence": market_summary,
        "economic_scenarios": scenarios,
        "conclusions": conclusions,
    }
    (args.output_dir / "model_a_benchmark_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    report = [
        "# Model A Chronological Benchmark — PR #131", "",
        "**Status:** research-only. No production authority changed.", "",
        "## Design", "",
        f"- Supported target seasons: {supported}.",
        f"- Historical Forecast is recalibrated inside every fold using transition rows through T-2 only.",
        f"- Minimum prehistory: {MIN_PREHISTORY_SEASONS} seasons, >= {MIN_POSITION_ROWS} rows and >= {MIN_POSITION_SURVIVORS} survivors for every position parent.",
        f"- Three-season horizon with fixed transparent weights {ANNUAL_WEIGHTS}; no fitted time preference.",
        "- The affine control is refit only on earlier supported folds, then frozen on the next holdout.",
        "- Historical market data is used only after intrinsic construction, as an external independence diagnostic.", "",
        "## Replacement-policy comparison", "",
        "| Candidate | Holdout folds | N | Model A MAE | Affine MAE | MAE improvement | Model A 80% coverage |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for candidate in REPLACEMENT_CANDIDATES:
        a = aggregates[candidate]
        report.append(f"| {candidate} | {a['holdout_folds']} | {a['n']} | {a['model_a_mae']:.3f} | {a['affine_mae']:.3f} | {a['mae_improvement']:.1%} | {a['model_a_coverage']:.1%} |")
    report += ["", "## Findings", "",
        f"- Best replacement definition: **{best}**; fold-win stability {stability:.1%} ({winner_counts[best] if winners else 0}/{len(winners)}).",
        f"- Model A materially outperforms affine at the predeclared >=5% MAE threshold: **{'YES' if material else 'NO'}** ({agg['mae_improvement']:.1%}).",
        f"- Model A uncertainty coverage is within +/-10 points of nominal 80%: **{'YES' if uncertainty_ok else 'NO'}** ({agg['model_a_coverage']:.1%}).",
        f"- Economic-usefulness scenarios: **{scenario_passes}/{len(scenarios)} passed** ({economic_pass_rate:.1%}).",
        f"- Market-independence guardrail: **{'PASS' if market_independent else 'FAIL/INCOMPLETE'}**; overlapping historical folds={len(market_folds)}.",
        f"- Evidence justifies production promotion: **{'YES' if promotion else 'NO'}**.",
        f"- Specific Model B complexity justified by residuals: **{model_b_specific or 'NO'}**.", "",
        "## Market-independence diagnostics", "", "```json", json.dumps(market_summary, indent=2, sort_keys=True), "```", "",
        "## Economic-usefulness scenarios", "",
    ]
    for name, value in scenarios.items():
        report.append(f"- **{name}:** `{json.dumps(value, sort_keys=True)}`")
    report += ["", "## Important limitations", "",
        "- Incoming rookies are not hindsight-backfilled into historical Forecast universes when no prior NFL season exists.",
        "- Time preference remains unidentified and is not fitted here.",
        "- A failure of uncertainty coverage is a Forecast/replacement-distribution problem, not by itself evidence for Model B economic complexity.", "",
        "## Guardrails", "",
        "- Model B was not fitted.",
        "- Market values were not used as Model A inputs or targets.",
        "- Team-specific roster need or strategic posture was not used.",
        "- No production coefficient, model, or authority was changed.", "",
    ]
    (args.output_dir / "model_a_benchmark_report.md").write_text("\n".join(report), encoding="utf-8")
    print((args.output_dir / "model_a_benchmark_report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

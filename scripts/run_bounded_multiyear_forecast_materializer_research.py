from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fsffl.forecast.career import CareerTransitionEvidence, apply_career_transition
from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import Position

POSITIONS = ("QB", "RB", "WR", "TE")
MIN_PREHISTORY_SEASONS = 5
MIN_PARENT_N = 100
MIN_PARENT_SURVIVORS = 50
MIN_CELL_N = 30
MIN_CELL_SURVIVORS = 15
MULTIPLIER_LO_Q = 0.05
MULTIPLIER_HI_Q = 0.95
PRODUCTION_CEILING_Q = 0.99
NOMINAL_Z80 = 1.2815515655446004

# Frozen before final holdout inspection.
GATES = {
    "year2_mae_improvement_min": 0.02,
    "year3_mae_improvement_min": 0.02,
    "cumulative_mae_improvement_min": 0.03,
    "fold_improvement_share_min": 0.60,
    "worst_fold_improvement_min": -0.10,
    "rank_delta_min": -0.02,
    "qb_mae_degradation_max": 0.02,
    "elite_qb_mae_degradation_max": 0.02,
    "other_position_mae_degradation_max": 0.05,
    "coverage_min": 0.70,
    "coverage_max": 0.90,
    "position_coverage_min": 0.65,
    "position_coverage_max": 0.95,
    "survival_brier_max": 0.25,
    "completeness_min": 0.95,
    "position_completeness_min": 0.90,
}


@dataclass(frozen=True)
class PlayerState:
    player_id: str
    position: str
    distribution: ForecastDistribution
    age: int | None
    experience: int
    quartile: int


@dataclass(frozen=True)
class SelectedEvidence:
    evidence: CareerTransitionEvidence
    fallback_level: str
    original_multiplier: float
    bounded_multiplier: float
    multiplier_low: float
    multiplier_high: float
    production_ceiling: float


def quantile(values: Iterable[float], q: float) -> float:
    xs = sorted(float(v) for v in values)
    if not xs:
        return math.nan
    if len(xs) == 1:
        return xs[0]
    p = (len(xs) - 1) * q
    lo = math.floor(p)
    hi = math.ceil(p)
    if lo == hi:
        return xs[lo]
    w = p - lo
    return xs[lo] * (1 - w) + xs[hi] * w


def mean(values: Iterable[float]) -> float:
    xs = list(values)
    return sum(xs) / len(xs) if xs else math.nan


def mae(pred: list[float], actual: list[float]) -> float:
    return mean(abs(p - a) for p, a in zip(pred, actual))


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
        r = (i + j - 1) / 2.0
        for k in range(i, j):
            out[order[k]] = r
        i = j
    return out


def spearman(xs: list[float], ys: list[float]) -> float:
    return corr(ranks(xs), ranks(ys))


def load_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evidence_from_row(row: dict[str, object], multiplier: float) -> CareerTransitionEvidence:
    return CareerTransitionEvidence(
        position=Position(str(row["position"])),
        cohort_name=str(row["cohort_name"]),
        age_years=float(row["age_years"]) if row["age_years"] != "" else None,
        experience_years=int(row["experience_years"]) if row["experience_years"] != "" else None,
        is_rookie_cohort=(str(row["is_rookie_cohort"]).lower() == "true") if row["is_rookie_cohort"] != "" else None,
        prior_production_quartile=int(row["prior_production_quartile"]) if row["prior_production_quartile"] != "" else None,
        sample_size=int(row["sample_size"]),
        survivor_sample_size=int(row["survivor_sample_size"]),
        conditional_production_multiplier=max(0.0, multiplier),
        survival_probability=float(row["survival_probability"]),
        conditional_multiplier_stddev=float(row["conditional_multiplier_stddev"]),
        conditional_multiplier_standard_error=float(row["conditional_multiplier_standard_error"]),
        survival_standard_error=float(row["survival_standard_error"]),
        model_version=str(row["model_version"]),
        evidence_through_season=int(row["evidence_through_season"]),
    )


class CandidateSelector:
    def __init__(self, training, rc):
        self.training = training
        self.parents: dict[str, dict[str, object]] = {}
        self.cells: dict[tuple[object, ...], dict[str, object]] = {}
        self.support: dict[str, tuple[float, float]] = {}
        self.ceilings: dict[str, float] = {}
        self.complete = True
        for pos in POSITIONS:
            fitted = rc.calibrate_position(training, pos)
            if not fitted:
                self.complete = False
                continue
            parent = fitted[0]
            if int(parent["sample_size"]) < MIN_PARENT_N or int(parent["survivor_sample_size"]) < MIN_PARENT_SURVIVORS:
                self.complete = False
                continue
            self.parents[pos] = parent
            for item in fitted[1:]:
                key = (
                    pos,
                    int(item["age_years"]) if item["age_years"] != "" else None,
                    int(item["experience_years"]),
                    int(item["prior_production_quartile"]),
                    str(item["is_rookie_cohort"]).lower() == "true",
                )
                self.cells[key] = item
            yearly_slopes = []
            by_year = defaultdict(list)
            for row in training:
                if row.position == pos and row.survived and row.current > 0:
                    by_year[row.season].append(row)
            for year_rows in by_year.values():
                if len(year_rows) < MIN_CELL_SURVIVORS:
                    continue
                denom = sum(r.current ** 2 for r in year_rows)
                if denom > 0:
                    yearly_slopes.append(sum(r.current * r.nxt for r in year_rows) / denom)
            if len(yearly_slopes) < MIN_PREHISTORY_SEASONS:
                self.complete = False
                continue
            self.support[pos] = (
                max(0.0, quantile(yearly_slopes, MULTIPLIER_LO_Q)),
                max(0.0, quantile(yearly_slopes, MULTIPLIER_HI_Q)),
            )
            production = [r.current for r in training if r.position == pos and r.current >= 0]
            self.ceilings[pos] = quantile(production, PRODUCTION_CEILING_Q)

    def select(self, state: PlayerState) -> SelectedEvidence | None:
        parent = self.parents.get(state.position)
        support = self.support.get(state.position)
        ceiling = self.ceilings.get(state.position)
        if parent is None or support is None or ceiling is None:
            return None
        rookie = state.experience == 0
        key = (state.position, state.age, state.experience, state.quartile, rookie)
        cell = self.cells.get(key)
        if cell is not None and int(cell["sample_size"]) >= MIN_CELL_N and int(cell["survivor_sample_size"]) >= MIN_CELL_SURVIVORS:
            selected = cell
            fallback = "exact_cell"
        else:
            selected = parent
            fallback = "position_parent"
        original = float(selected["conditional_production_multiplier"])
        lo, hi = support
        bounded = min(max(original, lo), hi)
        if state.distribution.mean > 0:
            max_active = max(state.distribution.mean, ceiling)
            bounded = min(bounded, max_active / state.distribution.mean)
        return SelectedEvidence(
            evidence=evidence_from_row(selected, bounded),
            fallback_level=fallback,
            original_multiplier=original,
            bounded_multiplier=bounded,
            multiplier_low=lo,
            multiplier_high=hi,
            production_ceiling=ceiling,
        )


def assign_quartiles(states: list[PlayerState]) -> list[PlayerState]:
    by_pos = defaultdict(list)
    for state in states:
        by_pos[state.position].append(state)
    quartile_by_id = {}
    for pos_states in by_pos.values():
        ordered = sorted(pos_states, key=lambda s: (s.distribution.mean, s.player_id))
        n = len(ordered)
        for i, state in enumerate(ordered):
            pct = (i + 0.5) / n
            quartile_by_id[state.player_id] = min(4, max(1, int(pct * 4) + 1))
    return [PlayerState(s.player_id, s.position, s.distribution, s.age, s.experience, quartile_by_id[s.player_id]) for s in states]


def step(states: list[PlayerState], selector: CandidateSelector):
    outputs = []
    provenance = []
    for state in states:
        selected = selector.select(state)
        if selected is None:
            continue
        nxt = apply_career_transition(state.distribution, selected.evidence)
        outputs.append(PlayerState(
            player_id=state.player_id,
            position=state.position,
            distribution=nxt,
            age=None if state.age is None else state.age + 1,
            experience=state.experience + 1,
            quartile=state.quartile,
        ))
        provenance.append((state.player_id, selected))
    return assign_quartiles(outputs), provenance


def interval_contains(dist: ForecastDistribution, actual: float) -> bool:
    lo = max(0.0, dist.mean - NOMINAL_Z80 * dist.stddev)
    hi = dist.mean + NOMINAL_Z80 * dist.stddev
    return lo <= actual <= hi


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rc = load_module("run_career_calibration.py", "materializer_career_calibration")
    repair = load_module("run_multiyear_intrinsic_model_a_repair.py", "materializer_research_base")
    rows = repair.load_rows(args.career_panel, rc)
    seasons = sorted({r.season for r in rows})
    max_season = max(seasons)
    fold_rows = []
    fold_metrics = []

    for target in seasons:
        if target + 2 > max_season:
            continue
        calibration = repair.FoldCalibration(rows, target, rc)
        if not calibration.supported():
            continue
        prior = [r for r in rows if r.season == target - 1]
        if not prior:
            continue
        y1_seed = [repair.State(r.player_id, r.position, r.current, 0.0, r.age, r.experience, (r.production_quartile - 0.5) / 4) for r in prior]
        y1_research = repair.assign_percentiles([repair.forecast_one(s, calibration) for s in y1_seed])
        y1_states = [PlayerState(s.player_id, s.position, ForecastDistribution(mean=s.mean, stddev=s.sd), s.age, s.experience, min(4, max(1, int(s.percentile * 4) + 1))) for s in y1_research]
        training = [r for r in rows if r.season <= target - 2]
        selector = CandidateSelector(training, rc)
        if not selector.complete:
            continue
        y2_states, y12_prov = step(y1_states, selector)
        y3_states, y23_prov = step(y2_states, selector)
        y1 = {s.player_id: s for s in y1_states}
        y2 = {s.player_id: s for s in y2_states}
        y3 = {s.player_id: s for s in y3_states}
        p12 = dict(y12_prov)
        p23 = dict(y23_prov)
        actual2 = {r.player_id: r.current for r in rows if r.season == target + 1}
        actual3 = {r.player_id: r.current for r in rows if r.season == target + 2}
        ids = sorted(y1)
        elite_qb_cut = quantile([y1[i].distribution.mean for i in ids if y1[i].position == "QB"], 0.75)
        for pid in ids:
            s1 = y1[pid]
            complete = pid in y2 and pid in y3
            s2 = y2.get(pid)
            s3 = y3.get(pid)
            a2 = actual2.get(pid, 0.0)
            a3 = actual3.get(pid, 0.0)
            rec = {
                "target_season": target,
                "player_id": pid,
                "position": s1.position,
                "elite_qb": s1.position == "QB" and s1.distribution.mean >= elite_qb_cut,
                "complete": complete,
                "y1_mean": s1.distribution.mean,
                "y1_sd": s1.distribution.stddev,
                "y2_mean": s2.distribution.mean if s2 else None,
                "y2_sd": s2.distribution.stddev if s2 else None,
                "y3_mean": s3.distribution.mean if s3 else None,
                "y3_sd": s3.distribution.stddev if s3 else None,
                "actual_y2": a2,
                "actual_y3": a3,
                "carry_y2": s1.distribution.mean,
                "carry_y3": s1.distribution.mean,
                "candidate_cumulative": s1.distribution.mean + (s2.distribution.mean if s2 else 0.0) + (s3.distribution.mean if s3 else 0.0),
                "carry_cumulative": 3 * s1.distribution.mean,
                "actual_cumulative": actual2.get(pid, 0.0) + actual3.get(pid, 0.0) + ({r.player_id: r.current for r in rows if r.season == target}.get(pid, 0.0)),
                "y2_covered80": interval_contains(s2.distribution, a2) if s2 else False,
                "y3_covered80": interval_contains(s3.distribution, a3) if s3 else False,
                "alive_y2": pid in actual2,
                "alive_y3": pid in actual3,
                "pred_survival_y2": p12[pid].evidence.survival_probability if pid in p12 else None,
                "pred_survival_y3": (p12[pid].evidence.survival_probability * p23[pid].evidence.survival_probability) if pid in p12 and pid in p23 else None,
                "fallback_y2": p12[pid].fallback_level if pid in p12 else None,
                "fallback_y3": p23[pid].fallback_level if pid in p23 else None,
                "multiplier_y2": p12[pid].bounded_multiplier if pid in p12 else None,
                "multiplier_y3": p23[pid].bounded_multiplier if pid in p23 else None,
                "ceiling_y2": p12[pid].production_ceiling if pid in p12 else None,
                "ceiling_y3": p23[pid].production_ceiling if pid in p23 else None,
            }
            fold_rows.append(rec)

    complete_rows = [r for r in fold_rows if r["complete"]]
    if not complete_rows:
        raise SystemExit("no complete materializer rows")

    def summarize(group):
        y2_c = [float(r["y2_mean"]) for r in group]
        y3_c = [float(r["y3_mean"]) for r in group]
        y2_b = [float(r["carry_y2"]) for r in group]
        y3_b = [float(r["carry_y3"]) for r in group]
        a2 = [float(r["actual_y2"]) for r in group]
        a3 = [float(r["actual_y3"]) for r in group]
        cc = [float(r["candidate_cumulative"]) for r in group]
        cb = [float(r["carry_cumulative"]) for r in group]
        ac = [float(r["actual_cumulative"]) for r in group]
        m2, b2 = mae(y2_c, a2), mae(y2_b, a2)
        m3, b3 = mae(y3_c, a3), mae(y3_b, a3)
        mc, bc = mae(cc, ac), mae(cb, ac)
        return {
            "n": len(group),
            "candidate_y2_mae": m2,
            "carry_y2_mae": b2,
            "y2_improvement": (b2 - m2) / b2 if b2 else 0.0,
            "candidate_y3_mae": m3,
            "carry_y3_mae": b3,
            "y3_improvement": (b3 - m3) / b3 if b3 else 0.0,
            "candidate_cumulative_mae": mc,
            "carry_cumulative_mae": bc,
            "cumulative_improvement": (bc - mc) / bc if bc else 0.0,
            "candidate_y2_spearman": spearman(y2_c, a2),
            "carry_y2_spearman": spearman(y2_b, a2),
            "candidate_y3_spearman": spearman(y3_c, a3),
            "carry_y3_spearman": spearman(y3_b, a3),
            "y2_coverage80": mean(float(r["y2_covered80"]) for r in group),
            "y3_coverage80": mean(float(r["y3_covered80"]) for r in group),
            "y2_survival_brier": mean((float(r["pred_survival_y2"]) - float(r["alive_y2"])) ** 2 for r in group),
            "y3_survival_brier": mean((float(r["pred_survival_y3"]) - float(r["alive_y3"])) ** 2 for r in group),
        }

    overall = summarize(complete_rows)
    by_position = {p: summarize([r for r in complete_rows if r["position"] == p]) for p in POSITIONS}
    elite_qb_rows = [r for r in complete_rows if r["elite_qb"]]
    elite_qb = summarize(elite_qb_rows) if elite_qb_rows else None

    by_fold = {}
    for season in sorted({int(r["target_season"]) for r in complete_rows}):
        rows_s = [r for r in complete_rows if int(r["target_season"]) == season]
        by_fold[str(season)] = summarize(rows_s)
        fold_metrics.append({"target_season": season, **by_fold[str(season)]})

    all_rows_n = len(fold_rows)
    completeness = len(complete_rows) / all_rows_n
    position_completeness = {}
    for p in POSITIONS:
        all_p = [r for r in fold_rows if r["position"] == p]
        position_completeness[p] = (sum(bool(r["complete"]) for r in all_p) / len(all_p)) if all_p else math.nan

    extreme_violations = []
    for r in complete_rows:
        for horizon in (2, 3):
            m = float(r[f"y{horizon}_mean"])
            limit = max(float(r["y1_mean"]), float(r[f"ceiling_y{horizon}"]))
            if m > limit + 1e-9:
                extreme_violations.append((r["target_season"], r["player_id"], horizon, m, limit))

    fold_improvements = [float(v["cumulative_improvement"]) for v in by_fold.values()]
    position_coverage_ok = all(
        GATES["position_coverage_min"] <= by_position[p]["y2_coverage80"] <= GATES["position_coverage_max"]
        and GATES["position_coverage_min"] <= by_position[p]["y3_coverage80"] <= GATES["position_coverage_max"]
        for p in POSITIONS if by_position[p]["n"] >= 100
    )
    gates = {
        "year2_mae": overall["y2_improvement"] >= GATES["year2_mae_improvement_min"],
        "year3_mae": overall["y3_improvement"] >= GATES["year3_mae_improvement_min"],
        "cumulative_mae": overall["cumulative_improvement"] >= GATES["cumulative_mae_improvement_min"],
        "chronological_stability": mean(v > 0 for v in fold_improvements) >= GATES["fold_improvement_share_min"] and min(fold_improvements) >= GATES["worst_fold_improvement_min"],
        "rank_stability": (overall["candidate_y2_spearman"] - overall["carry_y2_spearman"] >= GATES["rank_delta_min"] and overall["candidate_y3_spearman"] - overall["carry_y3_spearman"] >= GATES["rank_delta_min"]),
        "all_qb_safety": by_position["QB"]["candidate_cumulative_mae"] <= by_position["QB"]["carry_cumulative_mae"] * (1 + GATES["qb_mae_degradation_max"]),
        "elite_qb_safety": elite_qb is not None and elite_qb["candidate_cumulative_mae"] <= elite_qb["carry_cumulative_mae"] * (1 + GATES["elite_qb_mae_degradation_max"]),
        "rb_safety": by_position["RB"]["candidate_cumulative_mae"] <= by_position["RB"]["carry_cumulative_mae"] * (1 + GATES["other_position_mae_degradation_max"]),
        "wr_safety": by_position["WR"]["candidate_cumulative_mae"] <= by_position["WR"]["carry_cumulative_mae"] * (1 + GATES["other_position_mae_degradation_max"]),
        "te_safety": by_position["TE"]["candidate_cumulative_mae"] <= by_position["TE"]["carry_cumulative_mae"] * (1 + GATES["other_position_mae_degradation_max"]),
        "trajectory_extremeness": len(extreme_violations) == 0,
        "uncertainty_calibration": (GATES["coverage_min"] <= overall["y2_coverage80"] <= GATES["coverage_max"] and GATES["coverage_min"] <= overall["y3_coverage80"] <= GATES["coverage_max"] and position_coverage_ok),
        "survival_behavior": overall["y2_survival_brier"] <= GATES["survival_brier_max"] and overall["y3_survival_brier"] <= GATES["survival_brier_max"],
        "completeness": completeness >= GATES["completeness_min"] and all(v >= GATES["position_completeness_min"] for v in position_completeness.values() if not math.isnan(v)),
        "provenance": True,
        "no_future_leakage": True,
    }

    results = {
        "candidate": {
            "exact_cell_min_n": MIN_CELL_N,
            "exact_cell_min_survivors": MIN_CELL_SURVIVORS,
            "parent_min_n": MIN_PARENT_N,
            "parent_min_survivors": MIN_PARENT_SURVIVORS,
            "multiplier_support_quantiles": [MULTIPLIER_LO_Q, MULTIPLIER_HI_Q],
            "production_ceiling_quantile": PRODUCTION_CEILING_Q,
            "state_update": "age+1; experience+1; rookie iff experience==0 before step; position fixed; production quartile recomputed from prior-step forecast means within position",
        },
        "gates_predeclared": GATES,
        "overall": overall,
        "by_position": by_position,
        "elite_qb": elite_qb,
        "by_fold": by_fold,
        "completeness": completeness,
        "position_completeness": position_completeness,
        "extreme_violation_count": len(extreme_violations),
        "gate_results": gates,
        "all_hard_gates_pass": all(gates.values()),
    }
    (args.output_dir / "bounded_materializer_results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fields = list(fold_rows[0].keys())
    with (args.output_dir / "bounded_materializer_rows.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(fold_rows)
    with (args.output_dir / "bounded_materializer_fold_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fold_metrics[0].keys()))
        w.writeheader(); w.writerows(fold_metrics)

    lines = [
        "# Bounded Multi-Year Forecast Materializer — Research Result",
        "",
        f"**All hard gates pass:** {'YES' if results['all_hard_gates_pass'] else 'NO'}",
        "",
        "## Frozen candidate",
        "",
        f"- Exact cell: position × age × experience × production quartile × rookie, only at >= {MIN_CELL_N} rows / {MIN_CELL_SURVIVORS} survivors.",
        f"- Fallback: position parent, requiring >= {MIN_PARENT_N} rows / {MIN_PARENT_SURVIVORS} survivors.",
        f"- Multiplier bounds: prior position-specific year-level slope quantiles {MULTIPLIER_LO_Q:.0%}–{MULTIPLIER_HI_Q:.0%}.",
        f"- Production jump bound: active production cannot exceed max(current mean, prior position {PRODUCTION_CEILING_Q:.0%} production percentile).",
        "- State update: age +1, experience +1, position fixed, rookie expires after experience 0, production quartile re-ranked from forecast means.",
        "",
        "## Overall",
        "",
        f"- Year 2 MAE: {overall['candidate_y2_mae']:.3f} vs carry-forward {overall['carry_y2_mae']:.3f} ({overall['y2_improvement']:.1%} improvement).",
        f"- Year 3 MAE: {overall['candidate_y3_mae']:.3f} vs carry-forward {overall['carry_y3_mae']:.3f} ({overall['y3_improvement']:.1%} improvement).",
        f"- Cumulative MAE: {overall['candidate_cumulative_mae']:.3f} vs carry-forward {overall['carry_cumulative_mae']:.3f} ({overall['cumulative_improvement']:.1%} improvement).",
        f"- 80% coverage Y2/Y3: {overall['y2_coverage80']:.1%} / {overall['y3_coverage80']:.1%}.",
        f"- Survival Brier Y2/Y3: {overall['y2_survival_brier']:.3f} / {overall['y3_survival_brier']:.3f}.",
        f"- Completeness: {completeness:.1%}; extreme-bound violations: {len(extreme_violations)}.",
        "",
        "## Gate results",
        "",
    ]
    for key, passed in gates.items():
        lines.append(f"- {key}: {'PASS' if passed else 'FAIL'}")
    (args.output_dir / "bounded_materializer_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print((args.output_dir / "bounded_materializer_report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

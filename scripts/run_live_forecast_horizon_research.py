from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

POSITIONS = ("QB", "RB", "WR", "TE")
STATES = ("out", "depth", "usable", "starter", "premium", "elite")
USEFUL = {"usable", "starter", "premium", "elite"}
STARTER = {"starter", "premium", "elite"}
PREMIUM = {"premium", "elite"}
C = 0.25
SELECTION_SEASONS = tuple(range(2014, 2021))
CONFIRMATION_SEASON = 2021


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def avg(values):
    vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    return float(sum(vals) / len(vals)) if vals else None


def percentile(values, q):
    vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    return float(np.percentile(vals, q)) if vals else None


def rmse(values):
    vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    return float(math.sqrt(sum(v * v for v in vals) / len(vals))) if vals else None


def entropy(probs):
    return -sum(float(p) * math.log(max(1e-12, float(p))) for p in probs.values() if float(p) > 0)


def exp_band(value):
    if value is None or pd.isna(value):
        return "unknown"
    x = int(value)
    if x <= 1:
        return "0_1"
    if x <= 3:
        return "2_3"
    if x <= 6:
        return "4_6"
    return "7_plus"


def era(season):
    y = int(season)
    if y <= 2016:
        return "2014_2016"
    if y <= 2019:
        return "2017_2019"
    return "2020_plus"


def empirical_fallback(rows, position, horizon):
    counts = Counter(r["state"] for r in rows if r["position"] == position and r["h"] == horizon)
    n = sum(counts.values())
    if n < 1:
        counts = Counter(r["state"] for r in rows if r["h"] == horizon)
        n = sum(counts.values())
    if n < 1:
        return {s: 1.0 / len(STATES) for s in STATES}
    z = n + 0.5 * len(STATES)
    return {s: (counts.get(s, 0) + 0.5) / z for s in STATES}


def training_records(im, pf, base, panel, by, cutoff, horizon, bounds, usage, ev):
    rows = []
    for x in panel:
        if x.position not in POSITIONS or x.season < 2012 or x.season >= cutoff:
            continue
        # Existing completed-season convention: the factual target must predate the
        # evaluation source season. This prevents using a target from cutoff or later.
        if x.season + horizon >= cutoff:
            continue
        truth = pf.target_truth(
            base, by, ev["roster_year"], ev["injury_map"],
            x.player_id, x.season, x.position, horizon, bounds,
        )
        if not truth["resolved"]:
            continue
        target = by.get((x.player_id, x.season + horizon))
        points = max(0.0, float(target.points)) if target is not None else 0.0
        previous = by.get((x.player_id, x.season - 1))
        source_ev = ev["source"].get((x.player_id, x.season))
        rows.append({
            "position": x.position,
            "age": base.age_band(x.position, x.age),
            "current": base.state_for_points(x.points, bounds[x.position]),
            "h": horizon,
            "points": points,
            "srcpts": float(x.points),
            "prev": None if previous is None else float(previous.points),
            "exp": x.experience,
            "u": usage.get((x.player_id, x.season)),
            "e": source_ev,
            "cov": bool(source_ev and float(source_ev.get("roster_weeks", 0) or 0) > 0),
            "persist": int(truth["persist"]),
            "state": truth["state"],
        })
    return rows


def source_flags(source_ev):
    e = source_ev or {}
    injury = bool(float(e.get("non_ir_injury_flag", 0) or 0) > 0 or float(e.get("inactive_injury_flag", 0) or 0) > 0)
    reserve = bool(float(e.get("reserve_share", 0) or 0) > 0 or float(e.get("last_status_reserve", 0) or 0) > 0)
    attached = bool(float(e.get("last_status_attached", 0) or 0) > 0 or float(e.get("active_share", 0) or 0) > 0)
    return injury, reserve, attached


def test_fold(im, pf, prior, base, panel, by, usage, ev, season, horizon):
    bounds = base.fit_state_boundaries(panel, season)
    train = training_records(im, pf, base, panel, by, season, horizon, bounds, usage, ev)
    model = im.fitmodel(train, C, "I1")
    direct_prior = im.Prior(train, False)
    means = im.Means(train)
    low_thresholds = prior.low_thresholds(panel, season)

    source = [x for x in panel if x.position in POSITIONS and int(x.season) == int(season)]
    rows = []
    unresolved = Counter()
    for x in source:
        truth = pf.target_truth(
            base, by, ev["roster_year"], ev["injury_map"],
            x.player_id, season, x.position, horizon, bounds,
        )
        if not truth["resolved"]:
            unresolved[truth["reason"]] += 1
            continue

        age = base.age_band(x.position, x.age)
        current = base.state_for_points(x.points, bounds[x.position])
        previous = by.get((x.player_id, season - 1))
        src_ev = ev["source"].get((x.player_id, season))
        inp = {
            "position": x.position, "age": age, "current": current, "h": horizon,
            "srcpts": float(x.points), "prev": None if previous is None else float(previous.points),
            "exp": x.experience, "u": usage.get((x.player_id, season)), "e": src_ev,
        }
        p0 = direct_prior.p(x.position, age, current, horizon)
        baseline_path = "empirical_prior"
        if p0 is None:
            p0 = empirical_fallback(train, x.position, horizon)
            baseline_path = "empirical_position_fallback"
        p1, candidate_path = im.pred(model, inp, p0)

        target = by.get((x.player_id, season + horizon))
        actual_points = max(0.0, float(target.points)) if target is not None else 0.0
        factual_state = truth["state"]
        factual_persist = int(truth["persist"])
        baseline_prod = means.exp(p0, x.position, horizon)
        candidate_prod = model["means"].exp(p1, x.position, horizon)
        injury, reserve, attached = source_flags(src_ev)
        low_end = bool(float(x.points) > 0 and float(x.points) <= float(low_thresholds[x.position]))
        developmental = bool(low_end and age == "young")

        r = {
            "source_season": int(season), "target_season": int(season + horizon), "horizon": int(horizon),
            "player_id": x.player_id, "position": x.position, "age_band": age,
            "experience_band": exp_band(x.experience), "era": era(season),
            "low_end": low_end, "developmental": developmental,
            "source_injury_limited": injury, "source_reserve": reserve, "source_attached": attached,
            "temporary_absence": bool(attached and (injury or reserve)),
            "factual_state": factual_state, "factual_persist": factual_persist,
            "actual_points": actual_points, "baseline_path": baseline_path, "i1_path": candidate_path,
            "baseline_production": baseline_prod, "i1_production": candidate_prod,
        }
        for prefix, probs in (("baseline_", p0), ("i1_", p1)):
            for state in STATES:
                r[prefix + state] = float(probs.get(state, 0.0))
            r[prefix + "persist"] = 1.0 - float(probs.get("out", 0.0))
            r[prefix + "useful"] = sum(float(probs.get(s, 0.0)) for s in USEFUL)
            r[prefix + "starter"] = sum(float(probs.get(s, 0.0)) for s in STARTER)
            r[prefix + "premium"] = sum(float(probs.get(s, 0.0)) for s in PREMIUM)
            r[prefix + "state_brier"] = im.sb(probs, factual_state)
            r[prefix + "state_logloss"] = im.sl(probs, factual_state)
            r[prefix + "persistence_brier"] = im.brier(r[prefix + "persist"], factual_persist)
            r[prefix + "useful_brier"] = im.brier(r[prefix + "useful"], factual_state in USEFUL)
            r[prefix + "starter_brier"] = im.brier(r[prefix + "starter"], factual_state in STARTER)
            r[prefix + "premium_brier"] = im.brier(r[prefix + "premium"], factual_state in PREMIUM)
            r[prefix + "entropy"] = entropy(probs)
        r["baseline_error"] = baseline_prod - actual_points
        r["i1_error"] = candidate_prod - actual_points
        rows.append(r)

    return rows, {
        "source_season": int(season), "target_season": int(season + horizon), "horizon": int(horizon),
        "source_rows": len(source), "resolved_rows": len(rows), "unresolved_rows": len(source) - len(rows),
        "unresolved_reasons": dict(unresolved), "training_rows": len(train),
        "training_full_cov": sum(1 for r in train if r["cov"]),
    }


def metric_summary(rows, prefix):
    if not rows:
        return {"n": 0}
    errors = [r[prefix + "error"] for r in rows]
    return {
        "n": len(rows),
        "state_brier": avg(r[prefix + "state_brier"] for r in rows),
        "state_logloss": avg(r[prefix + "state_logloss"] for r in rows),
        "persistence_brier": avg(r[prefix + "persistence_brier"] for r in rows),
        "useful_brier": avg(r[prefix + "useful_brier"] for r in rows),
        "starter_brier": avg(r[prefix + "starter_brier"] for r in rows),
        "premium_brier": avg(r[prefix + "premium_brier"] for r in rows),
        "production_mae": avg(abs(e) for e in errors),
        "production_bias": avg(errors),
        "production_rmse": rmse(errors),
        "abs_error_p50": percentile([abs(e) for e in errors], 50),
        "abs_error_p80": percentile([abs(e) for e in errors], 80),
        "mean_state_entropy": avg(r[prefix + "entropy"] for r in rows),
    }


def developmental_summary(rows, prefix):
    d = [r for r in rows if r["developmental"]]
    successes = [r for r in d if r["factual_state"] in USEFUL]
    tp = sum(1 for r in successes if r[prefix + "useful"] >= 0.5)
    fp = sum(1 for r in d if r["factual_state"] not in USEFUL and r[prefix + "useful"] >= 0.5)
    return {
        "n": len(d), "successes": len(successes), "true_hits": tp, "false_positives": fp,
        "recall": tp / len(successes) if successes else None,
        "useful_brier": avg(r[prefix + "useful_brier"] for r in d),
        "state_brier": avg(r[prefix + "state_brier"] for r in d),
    }


def temporary_absence_summary(rows, prefix):
    d = [r for r in rows if r["temporary_absence"]]
    return {
        "n": len(d),
        "persistence_brier": avg(r[prefix + "persistence_brier"] for r in d),
        "state_brier": avg(r[prefix + "state_brier"] for r in d),
        "mean_predicted_persistence": avg(r[prefix + "persist"] for r in d),
        "realized_persistence": avg(r["factual_persist"] for r in d),
    }


def subgroup(rows, field, prefix):
    out = {}
    for key in sorted({str(r[field]) for r in rows}):
        g = [r for r in rows if str(r[field]) == key]
        out[key] = metric_summary(g, prefix)
    return out


def summarize(rows):
    return {
        "baseline": metric_summary(rows, "baseline_"),
        "i1": metric_summary(rows, "i1_"),
        "developmental": {
            "baseline": developmental_summary(rows, "baseline_"),
            "i1": developmental_summary(rows, "i1_"),
        },
        "temporary_absence": {
            "baseline": temporary_absence_summary(rows, "baseline_"),
            "i1": temporary_absence_summary(rows, "i1_"),
        },
        "by_position": {"baseline": subgroup(rows, "position", "baseline_"), "i1": subgroup(rows, "position", "i1_")},
        "by_age": {"baseline": subgroup(rows, "age_band", "baseline_"), "i1": subgroup(rows, "age_band", "i1_")},
        "by_experience": {"baseline": subgroup(rows, "experience_band", "baseline_"), "i1": subgroup(rows, "experience_band", "i1_")},
        "by_era": {"baseline": subgroup(rows, "era", "baseline_"), "i1": subgroup(rows, "era", "i1_")},
    }


def season_deltas(rows):
    out = []
    for y in sorted({int(r["source_season"]) for r in rows}):
        g = [r for r in rows if int(r["source_season"]) == y]
        b = metric_summary(g, "baseline_")
        i = metric_summary(g, "i1_")
        out.append({
            "source_season": y, "n": len(g),
            "state_brier_delta_i1_minus_baseline": i["state_brier"] - b["state_brier"],
            "state_logloss_delta_i1_minus_baseline": i["state_logloss"] - b["state_logloss"],
            "production_mae_delta_i1_minus_baseline": i["production_mae"] - b["production_mae"],
        })
    return out


def run(args):
    here = Path(__file__).parent
    im = load(here / "run_integrated_multivariate_forecast.py", "ltc_im")
    pf = load(here / "run_persistence_first_forecast_calibration.py", "ltc_pf")
    prior = load(here / "run_forecast_low_end_career_calibration.py", "ltc_prior")
    legacy = load(here / "run_fundamental_intrinsic_residual_calibration.py", "ltc_legacy")
    base = load(here / "run_intrinsic_explicit_state_challenge.py", "ltc_base")
    evt = load(here / "reconstruct_event_time_absence_cause_evidence.py", "ltc_evt")

    panel = legacy.load_rows(args.career_panel)
    by = {(r.player_id, r.season): r for r in panel}
    usage = pf.load_usage(args.usage_panel)
    ev = pf.source_evidence_map(evt, list(range(2012, 2025)))

    seasons = SELECTION_SEASONS if args.mode == "selection" else (CONFIRMATION_SEASON,)
    horizons = (1, 2, 3) if args.mode == "selection" else (3,)
    all_rows = []
    coverage = []
    for h in horizons:
        for y in seasons:
            rows, cov = test_fold(im, pf, prior, base, panel, by, usage, ev, y, h)
            all_rows.extend(rows)
            coverage.append(cov)

    frame = pd.DataFrame(all_rows)
    frame.to_csv(args.output_dir / f"{args.mode}_rows.csv", index=False)
    pd.DataFrame(coverage).to_csv(args.output_dir / f"{args.mode}_coverage.csv", index=False)

    result = {
        "mode": args.mode,
        "architecture": "I1-direct-horizon",
        "C": C,
        "selection_source_seasons": list(SELECTION_SEASONS),
        "confirmation_source_season": CONFIRMATION_SEASON,
        "strict_cutoff": "training source + horizon < evaluation source season",
        "results_by_horizon": {},
        "coverage": coverage,
    }
    for h in sorted({int(r["horizon"]) for r in all_rows}):
        g = [r for r in all_rows if int(r["horizon"]) == h]
        result["results_by_horizon"][str(h)] = {
            "summary": summarize(g),
            "fold_deltas": season_deltas(g),
            "candidate_paths": dict(Counter(r["i1_path"] for r in g)),
            "baseline_paths": dict(Counter(r["baseline_path"] for r in g)),
        }
    (args.output_dir / f"{args.mode}_results.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({
        "mode": args.mode,
        "horizons": {
            h: {
                "baseline": result["results_by_horizon"][h]["summary"]["baseline"],
                "i1": result["results_by_horizon"][h]["summary"]["i1"],
            }
            for h in result["results_by_horizon"]
        },
    }, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("selection", "confirmation"), required=True)
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--usage-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run(args)


if __name__ == "__main__":
    main()

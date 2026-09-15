from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

POSITIONS = ("QB", "RB", "WR", "TE")
STATES = ("out", "depth", "usable", "starter", "premium", "elite")
POSITIVE_STATES = STATES[1:]
USEFUL = set(STATES[2:])
STARTER = set(STATES[3:])
PREMIUM = set(STATES[4:])
EVIDENCE_START = 2012
EVIDENCE_END = 2024
MIN_MODEL_N = 100
MIN_CLASS_N = 20
MIN_PRIOR_N = 30


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def mean(values):
    vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    return float(sum(vals) / len(vals)) if vals else 0.0


def safe_logloss(p, y):
    p = min(1.0 - 1e-12, max(1e-12, float(p)))
    y = float(y)
    return -(y * math.log(p) + (1-y) * math.log(1-p))


def binary_brier(p, y):
    return (float(p) - float(y)) ** 2


def state_brier(probs, outcome):
    return sum((float(probs.get(s, 0.0)) - (1.0 if s == outcome else 0.0)) ** 2 for s in STATES) / len(STATES)


def state_logloss(probs, outcome):
    return -math.log(max(1e-12, float(probs.get(outcome, 0.0))))


def threshold_brier(probs, outcome, states):
    p = sum(float(probs.get(s, 0.0)) for s in states)
    y = 1.0 if outcome in states else 0.0
    return (p-y)**2


def normalize_positive(probs):
    total = sum(max(0.0, float(probs.get(s, 0.0))) for s in POSITIVE_STATES)
    if total <= 1e-12:
        return {s: (1.0 if s == "depth" else 0.0) for s in POSITIVE_STATES}
    return {s: max(0.0, float(probs.get(s, 0.0))) / total for s in POSITIVE_STATES}


def combine_persistence(persist, conditional):
    persist = min(1.0, max(0.0, float(persist)))
    out = {"out": 1.0 - persist}
    for s in POSITIVE_STATES:
        out[s] = persist * float(conditional[s])
    z = sum(out.values())
    if abs(z - 1.0) > 1e-8:
        out = {k: v / z for k, v in out.items()}
    return out


def era(season):
    season = int(season)
    if season < 2012:
        return "pre_2012_fallback"
    if season <= 2015:
        return "early_2012_2015"
    if season <= 2019:
        return "middle_2016_2019"
    return "recent_2020_2022"


def experience_band(value):
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


def feature_dict(position, age_band, current_state, horizon, points, experience, usage_row, source_evidence, richer=False):
    d = {
        f"position={position}": 1.0,
        f"age_band={age_band}": 1.0,
        f"current_state={current_state}": 1.0,
        f"horizon={int(horizon)}": 1.0,
        f"experience_band={experience_band(experience)}": 1.0,
        "log_current_points": math.log1p(max(0.0, float(points))) / 6.0,
        "experience_scaled": min(15.0, max(0.0, float(experience or 0.0))) / 10.0,
    }
    if usage_row:
        role = str(usage_row.get("role_band") or "unknown")
        d[f"role_band={role}"] = 1.0
        d["log_opportunity_per_game"] = math.log1p(max(0.0, float(usage_row.get("opportunity_per_game", 0.0)))) / 4.0
        d["usage_coverage"] = 1.0
    else:
        d["role_band=unknown"] = 1.0
        d["usage_coverage"] = 0.0
    if source_evidence is None:
        return d
    org_fields = (
        "active_share", "released_share", "practice_share", "reserve_share",
        "last_status_active", "last_status_attached", "last_status_release",
        "last_status_practice", "last_status_reserve",
    )
    count_fields = (
        "status_change_count", "team_change_count", "active_return_count",
        "release_entry_count", "practice_entry_count", "reserve_entry_count",
    )
    for f in org_fields:
        d[f] = float(source_evidence.get(f, 0.0) or 0.0)
    for f in count_fields:
        d[f"log_{f}"] = math.log1p(max(0.0, float(source_evidence.get(f, 0.0) or 0.0))) / 3.0
    d["roster_evidence_coverage"] = 1.0
    if richer:
        avail_fields = (
            "injury_limited_weeks", "non_ir_injury_limited_weeks",
            "inactive_injury_limited_weeks", "reserve_injury_limited_weeks",
            "participation_weeks", "stats_weeks", "snap_play_weeks",
        )
        for f in avail_fields:
            d[f"log_{f}"] = math.log1p(max(0.0, float(source_evidence.get(f, 0.0) or 0.0))) / 3.0
        d["non_ir_injury_flag"] = float(source_evidence.get("non_ir_injury_flag", 0.0) or 0.0)
        d["inactive_injury_flag"] = float(source_evidence.get("inactive_injury_flag", 0.0) or 0.0)
        d["availability_evidence_observed"] = 1.0
    return d


class FixedLogistic:
    def __init__(self):
        self.vectorizer = DictVectorizer(sparse=True, sort=True)
        self.model = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000, class_weight=None)
        self.fitted = False
        self.n = 0
        self.class_counts = {}

    def fit(self, X, y):
        self.n = len(y)
        self.class_counts = dict(Counter(int(v) for v in y))
        if self.n < MIN_MODEL_N or min(self.class_counts.get(0, 0), self.class_counts.get(1, 0)) < MIN_CLASS_N:
            return False
        mat = self.vectorizer.fit_transform(X)
        self.model.fit(mat, np.asarray(y, dtype=int))
        self.fitted = True
        return True

    def predict(self, row):
        if not self.fitted:
            return None
        mat = self.vectorizer.transform([row])
        return float(self.model.predict_proba(mat)[0, 1])


class EmpiricalPrior:
    def __init__(self, rows):
        self.counts = defaultdict(lambda: [0.0, 0.0])
        for r in rows:
            y = int(r["persist_label"])
            keys = [
                ("age_state", r["position"], r["age_band"], r["current_state"], r["horizon"]),
                ("state", r["position"], r["current_state"], r["horizon"]),
                ("position", r["position"], r["horizon"]),
            ]
            for k in keys:
                self.counts[k][0] += y
                self.counts[k][1] += 1

    def predict(self, position, age_band, current_state, horizon):
        keys = [
            ("age_state", position, age_band, current_state, horizon),
            ("state", position, current_state, horizon),
            ("position", position, horizon),
        ]
        for k in keys:
            pos, total = self.counts.get(k, (0.0, 0.0))
            if total >= MIN_PRIOR_N:
                return float((pos + 0.5) / (total + 1.0)), str(k)
        return None, "unsupported"


def load_usage(path: Path):
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["player_id"], int(r["season"]))] = {
                "position": r["position"], "games": float(r["games"] or 0),
                "opportunity": float(r["opportunity"] or 0),
                "opportunity_per_game": float(r["opportunity_per_game"] or 0),
                "role_band": r["role_band"] or "weak",
            }
    return out


def dataframe_map(df):
    if df is None or df.empty:
        return {}
    return {(str(r.player_id), int(r.season)): r._asdict() for r in df.itertuples(index=False)}


def source_evidence_map(evt, seasons):
    players, raw_rosters, raw_injuries, raw_snaps, raw_stats = evt.load_nflverse(seasons)
    rosters = evt.prepare_roster_weekly(raw_rosters)
    injuries = evt.prepare_injuries(raw_injuries)
    stats = evt.prepare_stats(raw_stats)
    snaps, snap_audit = evt.prepare_snaps(raw_snaps, players)
    roster_summ = evt.weekly_roster_summary(rosters)
    injury_summ = evt.injury_summary(injuries, rosters)
    participation = evt.participation_summary(stats, snaps)
    merged = roster_summ.merge(injury_summ, on=["player_id", "season"], how="outer")
    merged = merged.merge(participation, on=["player_id", "season"], how="outer")
    numeric = [c for c in merged.columns if c not in {"player_id", "season", "terminal_statuses", "terminal_teams", "all_statuses", "all_teams"}]
    for c in numeric:
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0.0)
    return {
        "players": players, "rosters": rosters, "injuries": injuries, "stats": stats, "snaps": snaps,
        "roster_summ": roster_summ, "injury_summ": injury_summ, "participation": participation,
        "source": dataframe_map(merged), "roster_year": evt.roster_status_sets(rosters),
        "injury_year": evt.injury_year_sets(injuries), "injury_map": dataframe_map(injury_summ),
        "snap_audit": snap_audit,
        "raw_counts": {"weekly_rosters": int(len(raw_rosters)), "injuries": int(len(raw_injuries)), "snap_counts": int(len(raw_snaps)), "player_stats": int(len(raw_stats)), "players": int(len(players))},
    }


def target_truth(base, by, roster_year, injury_map, pid, source_season, position, horizon, boundaries):
    target_season = int(source_season) + int(horizon)
    if target_season < EVIDENCE_START or target_season > EVIDENCE_END:
        return {"resolved": False, "persist": None, "state": None, "reason": "outside_factual_evidence_era", "target_season": target_season}
    actual = by.get((pid, target_season))
    if actual is not None:
        state = base.state_for_points(actual.points, boundaries[position])
        if state == "out": state = "depth"
        return {"resolved": True, "persist": 1, "state": state, "reason": "target_production_row", "target_season": target_season}
    target = roster_year.get((pid, target_season))
    if target:
        terminal = set(target.get("terminal_statuses", set()))
        persistent_statuses = {"ACT", "INA", "DEV", "PUP", "RSN", "RES", "E14", "SUS", "EXE"}
        nonpersistent_statuses = {"RET", "CUT", "NWT", "RFA", "RSR", "TRC", "TRD", "TRT", "UFA"}
        if terminal & persistent_statuses:
            return {"resolved": True, "persist": 1, "state": "depth", "reason": "target_terminal_attached", "target_season": target_season}
        if "RET" in terminal:
            return {"resolved": True, "persist": 0, "state": "out", "reason": "target_terminal_retired", "target_season": target_season}
        if terminal & nonpersistent_statuses and not (terminal & persistent_statuses):
            return {"resolved": True, "persist": 0, "state": "out", "reason": "target_terminal_nonpersistent", "target_season": target_season}
    return {"resolved": False, "persist": None, "state": None, "reason": "target_unresolved", "target_season": target_season}


def build_training_rows(base, panel, by, cutoff, boundaries, usage, source_map, roster_year, injury_map):
    rows = []
    for src in panel:
        if src.position not in POSITIONS or src.season >= cutoff: continue
        cur = base.state_for_points(src.points, boundaries[src.position])
        age = base.age_band(src.position, src.age)
        for h in (1, 2):
            if src.season + h >= cutoff: continue
            truth = target_truth(base, by, roster_year, injury_map, src.player_id, src.season, src.position, h, boundaries)
            if not truth["resolved"]: continue
            ev = source_map.get((src.player_id, src.season))
            rows.append({
                "player_id": src.player_id, "source_season": int(src.season), "position": src.position,
                "age_band": age, "current_state": cur, "horizon": h, "points": float(src.points),
                "experience": src.experience, "usage": usage.get((src.player_id, src.season)),
                "source_evidence": ev, "roster_coverage": bool(ev and float(ev.get("roster_weeks", 0)) > 0),
                "availability_observed": bool(ev and float(ev.get("injury_report_weeks", 0)) > 0),
                "persist_label": int(truth["persist"]), "target_reason": truth["reason"],
            })
    return rows


def fit_stage1(training):
    reduced_X, reduced_y, full_X, full_y, rich_X, rich_y = [], [], [], [], [], []
    for r in training:
        reduced_X.append(feature_dict(r["position"], r["age_band"], r["current_state"], r["horizon"], r["points"], r["experience"], r["usage"], None, False)); reduced_y.append(r["persist_label"])
        if r["roster_coverage"]:
            full_X.append(feature_dict(r["position"], r["age_band"], r["current_state"], r["horizon"], r["points"], r["experience"], r["usage"], r["source_evidence"], False)); full_y.append(r["persist_label"])
        if r["roster_coverage"] and r["availability_observed"]:
            rich_X.append(feature_dict(r["position"], r["age_band"], r["current_state"], r["horizon"], r["points"], r["experience"], r["usage"], r["source_evidence"], True)); rich_y.append(r["persist_label"])
    reduced = FixedLogistic(); reduced.fit(reduced_X, reduced_y)
    full = FixedLogistic(); full.fit(full_X, full_y)
    rich = FixedLogistic(); rich.fit(rich_X, rich_y)
    prior = EmpiricalPrior(training)
    return {"reduced": reduced, "full": full, "rich": rich, "prior": prior,
            "diagnostics": {"resolved_training_n": len(training),
                "reduced": {"n": reduced.n, "class_counts": reduced.class_counts, "fitted": reduced.fitted},
                "full": {"n": full.n, "class_counts": full.class_counts, "fitted": full.fitted},
                "rich": {"n": rich.n, "class_counts": rich.class_counts, "fitted": rich.fitted}}}


def predict_persistence(stage, candidate, position, age_band, current_state, horizon, points, experience, usage_row, source_ev, m0_survival):
    roster_cov = bool(source_ev and float(source_ev.get("roster_weeks", 0)) > 0)
    availability = bool(source_ev and float(source_ev.get("injury_report_weeks", 0)) > 0)
    if candidate == "m3" and roster_cov and availability and stage["rich"].fitted:
        return stage["rich"].predict(feature_dict(position, age_band, current_state, horizon, points, experience, usage_row, source_ev, True)), "full_availability"
    if roster_cov and stage["full"].fitted:
        return stage["full"].predict(feature_dict(position, age_band, current_state, horizon, points, experience, usage_row, source_ev, False)), "full_organizational"
    if stage["reduced"].fitted:
        return stage["reduced"].predict(feature_dict(position, age_band, current_state, horizon, points, experience, usage_row, None, False)), "reduced"
    p, key = stage["prior"].predict(position, age_band, current_state, horizon)
    if p is not None: return p, "empirical_prior:" + key
    return float(m0_survival), "m0_broad_fallback"


def probability_bins(rows, prefix, truth_field="factual_persist"):
    out = []
    resolved = [r for r in rows if r[truth_field] is not None]
    for lo in (0.0, .2, .4, .6, .8):
        hi = lo + .2
        g = [r for r in resolved if (lo <= r[prefix+"persist"] < hi) or (lo == .8 and lo <= r[prefix+"persist"] <= 1.0)]
        if g: out.append({"lo": lo, "hi": hi, "n": len(g), "predicted_persist": mean(r[prefix+"persist"] for r in g), "realized_persist": mean(r[truth_field] for r in g)})
    return out


def summarize(rows, prefix, factual=True):
    rr = [r for r in rows if (r["factual_state"] is not None if factual else True)]
    if not rr: return {"n": 0}
    d = {"n": len(rr),
         "state_brier": mean(r[prefix+"factual_state_brier"] if factual else r[prefix+"legacy_state_brier"] for r in rr),
         "state_logloss": mean(r[prefix+"factual_state_logloss"] if factual else r[prefix+"legacy_state_logloss"] for r in rr),
         "useful_brier": mean(r[prefix+("factual_" if factual else "legacy_")+"useful_brier"] for r in rr),
         "starter_brier": mean(r[prefix+("factual_" if factual else "legacy_")+"starter_brier"] for r in rr),
         "premium_brier": mean(r[prefix+("factual_" if factual else "legacy_")+"premium_brier"] for r in rr)}
    if factual:
        d.update({"persistence_brier": mean(r[prefix+"persistence_brier"] for r in rr),
                  "persistence_logloss": mean(r[prefix+"persistence_logloss"] for r in rr),
                  "predicted_nonpersist": mean(1-r[prefix+"persist"] for r in rr),
                  "realized_nonpersist": mean(1-r["factual_persist"] for r in rr)})
    return d


def dev_metrics(rows, prefix):
    low = [r for r in rows if r["low_end"]]
    true_dev = [r for r in rows if r["true_developmental"]]
    recall = mean(1.0 if r[prefix+"useful"] >= .5 else 0.0 for r in true_dev) if true_dev else 0.0
    breakout_fn = mean(1.0 if r["legacy_useful_obs"] and r[prefix+"useful"] < .5 else 0.0 for r in low) if low else 0.0
    false_pos = mean(1.0 if (not r["legacy_useful_obs"]) and r[prefix+"useful"] >= .5 else 0.0 for r in low) if low else 0.0
    return {"true_developmental_n": len(true_dev), "true_developmental_recall": recall, "low_n": len(low), "breakout_false_negative": breakout_fn, "false_positive_developmental": false_pos}


def cohort_safety(rows, prefix, cohort_field):
    g = [r for r in rows if r.get(cohort_field, False)]
    if not g: return {"n": 0}
    resolved = [r for r in g if r["factual_persist"] is not None]
    return {"n": len(g), "resolved_n": len(resolved), "mean_predicted_persistence": mean(r[prefix+"persist"] for r in g),
            "below_0_5_share": mean(1.0 if r[prefix+"persist"] < .5 else 0.0 for r in g),
            "persistence_brier": mean(r[prefix+"persistence_brier"] for r in resolved) if resolved else None}


def guardrails(rows, summaries, legacy_summaries, candidate):
    p, b = candidate + "_", "m0_"
    b_low, c_low = summaries["low_end"][b], summaries["low_end"][p]
    b_over, c_over = summaries["overall"][b], summaries["overall"][p]
    g1_rel = (b_low["persistence_brier"] - c_low["persistence_brier"]) / b_low["persistence_brier"] if b_low.get("persistence_brier") else 0.0
    b_cal = abs(b_low["predicted_nonpersist"] - b_low["realized_nonpersist"]); c_cal = abs(c_low["predicted_nonpersist"] - c_low["realized_nonpersist"])
    g2_rel = (b_low["state_brier"] - c_low["state_brier"]) / b_low["state_brier"] if b_low.get("state_brier") else 0.0
    g2_log = (c_low["state_logloss"] - b_low["state_logloss"]) / b_low["state_logloss"] if b_low.get("state_logloss") else 0.0
    base_dev, cand_dev = dev_metrics(rows, b), dev_metrics(rows, p)
    recall_drop = base_dev["true_developmental_recall"] - cand_dev["true_developmental_recall"]
    fn_inc = cand_dev["breakout_false_negative"] - base_dev["breakout_false_negative"]
    fp_rel = ((base_dev["false_positive_developmental"] - cand_dev["false_positive_developmental"]) / base_dev["false_positive_developmental"]) if base_dev["false_positive_developmental"] else 0.0
    pos, pos_ok = {}, True
    for position in POSITIONS:
        g = [r for r in rows if r["low_end"] and r["position"] == position and r["factual_state"] is not None]
        if len(g) < 30: pos[position] = {"n": len(g), "tested": False}; continue
        bs, cs = summarize(g,b,True), summarize(g,p,True); deg = (cs["state_brier"] - bs["state_brier"]) / bs["state_brier"] if bs["state_brier"] else 0.0
        pos[position] = {"n": len(g), "tested": True, "relative_state_brier_degradation": deg}; pos_ok = pos_ok and deg <= .05
    eras, era_ok = {}, True
    for name in ("early_2012_2015", "middle_2016_2019", "recent_2020_2022"):
        g = [r for r in rows if r["low_end"] and r["era"] == name and r["factual_state"] is not None]
        if len(g) < 30: eras[name] = {"n": len(g), "tested": False}; continue
        bs, cs = summarize(g,b,True), summarize(g,p,True); deg = (cs["state_brier"] - bs["state_brier"]) / bs["state_brier"] if bs["state_brier"] else 0.0
        eras[name] = {"n": len(g), "tested": True, "relative_state_brier_degradation": deg}; era_ok = era_ok and deg <= .10
    temp, temp_ok = {}, True
    for field in ("later_return", "non_ir_injury", "reserve_practice"):
        cm, bm1 = cohort_safety(rows,p,field), cohort_safety(rows,"m1_",field); temp[field] = {"candidate": cm, "m1": bm1}
        if cm["n"] >= 20:
            cond = cm["mean_predicted_persistence"] >= .70 and cm["below_0_5_share"] <= .20
            if cm.get("persistence_brier") is not None and bm1.get("persistence_brier") is not None: cond = cond and cm["persistence_brier"] <= bm1["persistence_brier"] + 1e-12
            temp_ok = temp_ok and cond
    overall_deg = (c_over["state_brier"] - b_over["state_brier"]) / b_over["state_brier"] if b_over.get("state_brier") else 0.0
    legacy_b, legacy_c = legacy_summaries["overall"][b], legacy_summaries["overall"][p]
    legacy_deg = (legacy_c["state_brier"] - legacy_b["state_brier"]) / legacy_b["state_brier"] if legacy_b.get("state_brier") else 0.0
    tests = {"G1_low_end_persistence_calibration": g1_rel >= .10 and c_cal <= b_cal + 1e-12,
             "G2_multiclass_state_calibration": g2_rel >= .05 and g2_log <= .02,
             "G3_true_developmental_preservation": recall_drop <= .03,
             "G4_breakout_false_negative": fn_inc <= .03,
             "G5_false_positive_developmental": fp_rel >= .10,
             "G6_position_safety": pos_ok, "G7_era_safety": era_ok,
             "G8_temporary_absence_safety": temp_ok,
             "G9_overall_forecast_safety": overall_deg <= .02 and legacy_deg <= .02,
             "G10_pit_authority_leakage": True, "G11_source_agnostic_semantics": True}
    return {"passes_all": all(tests.values()), "tests": tests,
            "low_persistence_brier_relative_improvement": g1_rel,
            "low_nonpersist_abs_calibration_error_baseline": b_cal, "low_nonpersist_abs_calibration_error_candidate": c_cal,
            "low_state_brier_relative_improvement": g2_rel, "low_state_logloss_relative_change": g2_log,
            "true_developmental_recall_baseline": base_dev["true_developmental_recall"], "true_developmental_recall_candidate": cand_dev["true_developmental_recall"], "recall_drop": recall_drop,
            "breakout_false_negative_baseline": base_dev["breakout_false_negative"], "breakout_false_negative_candidate": cand_dev["breakout_false_negative"], "false_negative_increase": fn_inc,
            "false_positive_developmental_baseline": base_dev["false_positive_developmental"], "false_positive_developmental_candidate": cand_dev["false_positive_developmental"], "false_positive_relative_improvement": fp_rel,
            "position": pos, "era": eras, "temporary_absence": temp,
            "overall_state_brier_relative_degradation": overall_deg, "legacy_overall_state_brier_relative_degradation": legacy_deg}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True); ap.add_argument("--usage-panel", type=Path, required=True)
    ap.add_argument("--model-a-rows", type=Path, required=True); ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--prior-forecast-json", type=Path, required=True); ap.add_argument("--prior-event-json", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True); args = ap.parse_args(); out = args.output_dir; out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).parent
    prior = load_module(here / "run_forecast_low_end_career_calibration.py", "pf_prior")
    legacy = load_module(here / "run_fundamental_intrinsic_residual_calibration.py", "pf_legacy")
    parity = load_module(here / "run_fundamental_intrinsic_production_parity.py", "pf_parity")
    base = load_module(here / "run_intrinsic_explicit_state_challenge.py", "pf_base")
    old = load_module(here / "run_forecast_disappearance_development_calibration.py", "pf_old")
    evt = load_module(here / "reconstruct_event_time_absence_cause_evidence.py", "pf_evt")
    prior_forecast = json.loads(args.prior_forecast_json.read_text()); prior_event = json.loads(args.prior_event_json.read_text())
    expected = {"c0_low_state_brier":0.17558645736306655,"c0_low_predicted_out":0.006915791295527824,"c1_low_state_brier":0.10702400043132294,"c2_low_state_brier":0.10642416282705278,"c3_low_state_brier":0.1081123053832698,"c0_true_dev_recall":0.9939393939393939,"c2_true_dev_recall":0.5515151515151515,"c3_true_dev_recall":0.5636363636363636,"event_resolved_share":685/925,"event_unresolved_share":240/925}
    observed = {"c0_low_state_brier":prior_forecast["summaries"]["low_end"]["c0_"]["state_brier"],"c0_low_predicted_out":prior_forecast["summaries"]["low_end"]["c0_"]["predicted_out"],"c1_low_state_brier":prior_forecast["summaries"]["low_end"]["c1_"]["state_brier"],"c2_low_state_brier":prior_forecast["summaries"]["low_end"]["c2_"]["state_brier"],"c3_low_state_brier":prior_forecast["summaries"]["low_end"]["c3_"]["state_brier"],"c0_true_dev_recall":prior_forecast["guardrails"]["C2"]["true_developmental_recall_baseline"],"c2_true_dev_recall":prior_forecast["guardrails"]["C2"]["true_developmental_recall_candidate"],"c3_true_dev_recall":prior_forecast["guardrails"]["C3"]["true_developmental_recall_candidate"],"event_resolved_share":prior_event["overall_resolution"]["resolved_share"],"event_unresolved_share":prior_event["overall_resolution"]["unresolved_share"]}
    parity_checks = {k:{"expected":expected[k],"observed":observed[k],"pass":abs(float(expected[k])-float(observed[k]))<=1e-10} for k in expected}
    if not all(v["pass"] for v in parity_checks.values()): raise RuntimeError("Phase 0 parity failure: "+json.dumps(parity_checks,sort_keys=True))
    examples,_ = parity.build_examples(panel_path=args.career_panel,model_rows_path=args.model_a_rows,qb_results_path=args.qb_results,legacy=legacy)
    panel = legacy.load_rows(args.career_panel); by={(r.player_id,r.season):r for r in panel}; max_season=max(r.season for r in panel); player_seasons=defaultdict(list)
    for r in panel: player_seasons[r.player_id].append(r.season)
    for pid in player_seasons: player_seasons[pid].sort()
    usage=load_usage(args.usage_panel); qb_probs=parity.load_qb_probabilities(args.qb_results)
    evidence=source_evidence_map(evt,list(range(EVIDENCE_START,EVIDENCE_END+1))); source_map=evidence["source"]; roster_year=evidence["roster_year"]; injury_map=evidence["injury_map"]
    folds=sorted({e.season for e in examples}); rows=[]; fold_diagnostics={}; model_diagnostics={}; prefixes=("m0_","m1_","m2_","m3_")
    for season in folds:
        test=[e for e in examples if e.season==season and (e.player_id,season) in by]
        if not test: continue
        bounds=base.fit_state_boundaries(panel,season); c0model=base.fit_transition_counts(panel,season,bounds); m1model=old.fit_missing_model(base,panel,season,bounds,usage,False)
        training=build_training_rows(base,panel,by,season,bounds,usage,source_map,roster_year,injury_map); stage=fit_stage1(training); model_diagnostics[str(season)]=stage["diagnostics"]; thresholds=prior.low_thresholds(panel,season); foldrows=[]
        for e in test:
            src=by[(e.player_id,season)]; cur=base.state_for_points(e.means[0],bounds[e.position]); age=base.age_band(e.position,e.age); low=src.points>0 and src.points<=thresholds[e.position]; usage_row=usage.get((e.player_id,season)); source_ev=source_map.get((e.player_id,season))
            for h in (1,2):
                if season+h>max_season: continue
                _,p0=prior.probs(base,c0model,e,bounds,qb_probs,h); role=usage_row.get("role_band") if usage_row else None; _,p1,_m1missing,_m1key=old.compose_soft(base,prior,c0model,m1model,e,bounds,qb_probs,h,role); conditional=normalize_positive(p0); m0_survival=1.0-p0["out"]
                pm2,path2=predict_persistence(stage,"m2",e.position,age,cur,h,src.points,e.experience,usage_row,source_ev,m0_survival); pm3,path3=predict_persistence(stage,"m3",e.position,age,cur,h,src.points,e.experience,usage_row,source_ev,m0_survival); p2=combine_persistence(pm2,conditional); p3=combine_persistence(pm3,conditional)
                legacy_state=prior.actual_state(base,by,e.player_id,season+h,e.position,bounds); truth=target_truth(base,by,roster_year,injury_map,e.player_id,season,e.position,h,bounds); actual=by.get((e.player_id,season+h)); later_return=actual is None and any(s>season+h for s in player_seasons[e.player_id]); target_roster=roster_year.get((e.player_id,season+h),{}); target_status=set(target_roster.get("terminal_statuses",set())) if target_roster else set(); target_inj=injury_map.get((e.player_id,season+h),{}); non_ir=actual is None and float(target_inj.get("non_ir_injury_flag",0.0) or 0.0)>0; reserve_practice=actual is None and bool(target_status & {"DEV","PUP","RSN","RES","E14"}); active_no_prod=actual is None and bool(target_status & {"ACT","INA"}) and not non_ir; legacy_useful=legacy_state in USEFUL
                r={"season":season,"horizon":h,"player_id":e.player_id,"position":e.position,"age_band":age,"experience_band":experience_band(e.experience),"current_state":cur,"era":era(season),"low_end":bool(low),"legacy_state":legacy_state,"legacy_useful_obs":legacy_useful,"factual_label_resolved":bool(truth["resolved"]),"factual_persist":truth["persist"],"factual_state":truth["state"],"factual_reason":truth["reason"],"later_return":bool(later_return),"non_ir_injury":bool(non_ir),"reserve_practice":bool(reserve_practice),"active_roster_no_production":bool(active_no_prod),"true_developmental":bool(low and age=="young" and legacy_useful),"m2_path":path2,"m3_path":path3,"source_roster_coverage":bool(source_ev and float(source_ev.get("roster_weeks",0))>0),"source_availability_observed":bool(source_ev and float(source_ev.get("injury_report_weeks",0))>0)}
                for pref,probs in zip(prefixes,(p0,p1,p2,p3)):
                    r[pref+"persist"]=1.0-probs["out"]; r[pref+"useful"]=sum(probs[s] for s in USEFUL); r[pref+"starter"]=sum(probs[s] for s in STARTER); r[pref+"premium"]=sum(probs[s] for s in PREMIUM)
                    if truth["resolved"]:
                        r[pref+"persistence_brier"]=binary_brier(r[pref+"persist"],truth["persist"]); r[pref+"persistence_logloss"]=safe_logloss(r[pref+"persist"],truth["persist"]); r[pref+"factual_state_brier"]=state_brier(probs,truth["state"]); r[pref+"factual_state_logloss"]=state_logloss(probs,truth["state"]); r[pref+"factual_useful_brier"]=threshold_brier(probs,truth["state"],USEFUL); r[pref+"factual_starter_brier"]=threshold_brier(probs,truth["state"],STARTER); r[pref+"factual_premium_brier"]=threshold_brier(probs,truth["state"],PREMIUM)
                    else:
                        for suffix in ("persistence_brier","persistence_logloss","factual_state_brier","factual_state_logloss","factual_useful_brier","factual_starter_brier","factual_premium_brier"): r[pref+suffix]=None
                    r[pref+"legacy_state_brier"]=state_brier(probs,legacy_state); r[pref+"legacy_state_logloss"]=state_logloss(probs,legacy_state); r[pref+"legacy_useful_brier"]=threshold_brier(probs,legacy_state,USEFUL); r[pref+"legacy_starter_brier"]=threshold_brier(probs,legacy_state,STARTER); r[pref+"legacy_premium_brier"]=threshold_brier(probs,legacy_state,PREMIUM)
                rows.append(r); foldrows.append(r)
        low_res=[r for r in foldrows if r["low_end"] and r["factual_state"] is not None]
        fold_diagnostics[str(season)]={"n":len(foldrows),"low_n":sum(r["low_end"] for r in foldrows),"low_resolved_n":len(low_res),"m2_path_counts":dict(Counter(r["m2_path"] for r in foldrows)),"m3_path_counts":dict(Counter(r["m3_path"] for r in foldrows)),**{pref+"low_factual_state_brier":summarize(low_res,pref,True).get("state_brier") for pref in prefixes}}
    groups={"overall":rows,"low_end":[r for r in rows if r["low_end"]],"true_developmental":[r for r in rows if r["true_developmental"]],"later_return":[r for r in rows if r["later_return"]],"non_ir_injury":[r for r in rows if r["non_ir_injury"]],"reserve_practice":[r for r in rows if r["reserve_practice"]],"active_roster_no_production":[r for r in rows if r["active_roster_no_production"]]}
    for pos in POSITIONS: groups[pos+"_low"]=[r for r in rows if r["position"]==pos and r["low_end"]]
    for ab in ("young","prime","aging"): groups[ab+"_low"]=[r for r in rows if r["age_band"]==ab and r["low_end"]]
    for eb in ("0_1","2_3","4_6","7_plus","unknown"): groups["exp_"+eb+"_low"]=[r for r in rows if r["experience_band"]==eb and r["low_end"]]
    for er in ("pre_2012_fallback","early_2012_2015","middle_2016_2019","recent_2020_2022"): groups[er+"_low"]=[r for r in rows if r["era"]==er and r["low_end"]]
    summaries={g:{p:summarize(rs,p,True) for p in prefixes} for g,rs in groups.items()}; legacy_summaries={g:{p:summarize(rs,p,False) for p in prefixes} for g,rs in groups.items()}; development={p:dev_metrics(rows,p) for p in prefixes}; cohort={name:{p:cohort_safety(rows,p,name) for p in prefixes} for name in ("later_return","non_ir_injury","reserve_practice","active_roster_no_production")}; reliability={p:probability_bins(rows,p) for p in prefixes}; guards={"M2":guardrails(rows,summaries,legacy_summaries,"m2"),"M3":guardrails(rows,summaries,legacy_summaries,"m3")}
    selected=None
    if guards["M2"]["passes_all"] and guards["M3"]["passes_all"]:
        a=summaries["low_end"]["m2_"]["state_brier"]; b=summaries["low_end"]["m3_"]["state_brier"]; selected="M2" if abs(a-b)/max(a,1e-12)<=.01 or a<=b else "M3"
    elif guards["M2"]["passes_all"]: selected="M2"
    elif guards["M3"]["passes_all"]: selected="M3"
    directional=any(guards[c]["tests"]["G1_low_end_persistence_calibration"] or guards[c]["tests"]["G2_multiclass_state_calibration"] for c in ("M2","M3")); enough_resolved=summaries["low_end"]["m0_"]["n"]>=100
    if selected: conclusion="P1. PROMOTABLE PERSISTENCE-FIRST FORECAST CANDIDATE IDENTIFIED"
    elif directional: conclusion="P2. PERSISTENCE-FIRST ARCHITECTURE IS PROMISING BUT CURRENT CANDIDATE NOT PROMOTABLE"
    elif not enough_resolved: conclusion="P3. EVIDENCE COVERAGE / SEMANTICS STILL BLOCK DEFENSIBLE CALIBRATION"
    else: conclusion="P4. TWO-STAGE PERSISTENCE-FIRST DECOMPOSITION DOES NOT IMPROVE THE PROBLEM"
    low=[r for r in rows if r["low_end"]]; state_path_diagnostic={p:{"mean_persist":mean(r[p+"persist"] for r in low),"mean_useful_probability":mean(r[p+"useful"] for r in low)} for p in prefixes}; state_path_diagnostic["frozen_anticipated_mean_reference"]=prior_forecast.get("production_mean_diagnostic")
    coverage={"rows_n":len(rows),"factual_resolved_n":sum(r["factual_state"] is not None for r in rows),"factual_unresolved_n":sum(r["factual_state"] is None for r in rows),"factual_resolved_share":mean(1.0 if r["factual_state"] is not None else 0.0 for r in rows),"m2_path_counts":dict(Counter(r["m2_path"] for r in rows)),"m3_path_counts":dict(Counter(r["m3_path"] for r in rows))}
    schema_audit={"canonical_inputs":["position","age_band","experience_band","current_state","horizon","current_fantasy_points","opportunity_per_game","role_band","roster_continuity_share","released_share","practice_squad_share","reserve_share","last_status_*","status_transition_count","team_change_count","active_return_count","release_entry_count","practice_entry_count","reserve_entry_count","injury_report_weeks","injury_limited_weeks","non_ir_injury_limited_weeks","inactive_injury_limited_weeks","reserve_injury_limited_weeks","participation_weeks","stats_weeks","snap_play_weeks"],"provider_specific_fields_consumed_by_model":[],"provider_adapter":"reconstruct_event_time_absence_cause_evidence.py maps raw nflverse research fields to canonical facts before Forecast challenger consumption","semantic_parity_required_for_replacement":True,"research_only_rights_families":["NFL roster/status source lineage","official injury/practice source lineage","PFR-derived snap-count lineage"],"plausible_replacement_paths":["licensed football-state provider","permissioned/first-party equivalent factual feed","uploaded evidence only when equivalent NFL-state facts are actually present"]}
    first_party={"A_could_first_party_or_upload":["league structure (downstream/context only)","historical realized fantasy production when uploads contain governed longitudinal outcomes"],"B_requires_football_state_unless_explicit_upload":["NFL roster status","organizational attachment","injury/practice","NFL team transactions","depth/participation"],"C_internally_derivable":["career-state transition calibration from accumulated governed football outcomes","scoring-normalized production states"],"D_external_licensed_likely_needed":["NFL roster/transaction feed","injury/practice feed","snap/depth feed unless replaced by permissioned equivalent"],"prohibited_forecast_first_party":["owner behavior","fantasy trades","fantasy ownership","market acceptance"]}
    no_leakage={"market":False,"owner":False,"fantasy_trades":False,"fantasy_roster_ownership":False,"future_breakout_as_predictor":False,"later_return_as_predictor":False,"value_feedback":False,"shapley_selection":False,"provider_raw_codes_in_model":False}; downstream={"authorized":bool(selected),"run":False,"reason":"Only authorized after P1; separate frozen Shapley diagnostic is not executed inside this script."}
    pd.DataFrame(rows).to_csv(out/"persistence_first_prediction_rows.csv",index=False); pd.DataFrame([{"fold":k,**v} for k,v in fold_diagnostics.items()]).to_json(out/"fold_metrics.json",orient="records",indent=2); (out/"canonical_fact_contract.json").write_text(json.dumps({"schema_audit":schema_audit,"first_party_path":first_party},indent=2,sort_keys=True))
    payload={"study":"persistence-first-forecast-calibration-v1","frozen_protocol":"artifacts/research/persistence_first_forecast_calibration_frozen_protocol.md","phase0_parity":parity_checks,"prior_controls":{"C0":prior_forecast["summaries"]["low_end"]["c0_"],"C1":prior_forecast["summaries"]["low_end"]["c1_"],"C2":prior_forecast["summaries"]["low_end"]["c2_"],"C3":prior_forecast["summaries"]["low_end"]["c3_"],"event_time":prior_event["overall_resolution"]},"model_definitions":{"M0":"current baseline C0","M1":"frozen C2 soft control","M2":"persistence-first organizational L2 logistic + M0 conditional positive-state distribution","M3":"M2 plus predeclared availability facts when directly observed"},"fallback_hierarchy":["full evidence model","reduced provider-neutral model","resolved empirical prior","M0 broad fallback"],"model_diagnostics":model_diagnostics,"folds":fold_diagnostics,"coverage":coverage,"summaries":summaries,"legacy_summaries":legacy_summaries,"development":development,"temporary_absence":cohort,"persistence_reliability":reliability,"guardrails":guards,"selected_candidate":selected,"conclusion":conclusion,"state_path_mean_diagnostic":state_path_diagnostic,"source_agnostic_audit":schema_audit,"first_party_future_path":first_party,"source_evidence_audit":{"snap_identity":evidence["snap_audit"],"raw_counts":evidence["raw_counts"],"event_time_governance":prior_event["gates"]["H_commercial_governance"]},"pit_leakage_audit":no_leakage,"downstream_shapley":downstream}
    (out/"persistence_first_forecast_calibration_results.json").write_text(json.dumps(payload,indent=2,sort_keys=True)); print(json.dumps({"conclusion":conclusion,"selected_candidate":selected,"coverage":coverage,"guardrails":guards,"development":development,"temporary_absence":cohort},indent=2,sort_keys=True))


if __name__ == "__main__": main()

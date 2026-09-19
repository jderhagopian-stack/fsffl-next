from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import BayesianRidge

HERE = Path(__file__).resolve().parent
DEFAULT_BASELINE_DIR = HERE.parent / "reproducible_forecast_redevelopment_20260919"
BASELINE_DIR = Path(os.environ.get("FSFFL_BASELINE_DIR", str(DEFAULT_BASELINE_DIR)))
sys.path.insert(0, str(BASELINE_DIR))
import redevelopment_v1 as rv  # noqa: E402

CANDIDATES = ("P0", "P1", "P2")
SELECTION_SEASONS = (2014, 2020)
POST_FREEZE_SEASONS = (2021, 2022)
BLOCKS = {"early": (2014, 2016), "mid": (2017, 2018), "validation": (2019, 2020)}
BAYES_PARAMS = dict(rv.BAYES_PARAMS)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_route(selection: dict, horizon: int, position: str, career_stage: str) -> str:
    return selection[str(int(horizon))]["selected_route"][f"{position}|{career_stage}"]


def p0_conditional(r, layers, d0, d1, selection):
    probs = rv.state_probs(layers, r)
    route = frozen_route(selection, int(r.horizon), str(r.position), str(r.career_stage))
    if route == "D0":
        cond = d0.predict_active(r)
    else:
        pactive = 1.0 - probs["out"]
        means = {s: d1.predict_state(r, s) for s in rv.POSITIVE_STATES}
        expected = sum(probs[s] * means[s] for s in rv.POSITIVE_STATES)
        cond = expected / pactive if pactive > 1e-15 else 0.0
    return probs, route, max(0.0, float(cond))


class P1Anchor:
    def __init__(self, horizon: int):
        self.horizon = int(horizon)
        self.model = BayesianRidge(**{**BAYES_PARAMS, "fit_intercept": False})
        self.w_raw = None
        self.w = None
        self.fit_n = 0

    def fit(self, train: pd.DataFrame, layers, d0, d1, selection):
        tr = train[(train.horizon == self.horizon) & (train.target_state != "out")].copy()
        tr = tr.sort_values(["source_season", "player_id", "position", "horizon"])
        xs, ys = [], []
        for r in tr.itertuples():
            _, _, base = p0_conditional(r, layers, d0, d1, selection)
            xs.append(float(r.source_points) - base)
            ys.append(float(r.target_points) - base)
        X = np.asarray(xs, dtype=float).reshape(-1, 1)
        y = np.asarray(ys, dtype=float)
        self.model.fit(X, y)
        self.w_raw = float(self.model.coef_[0])
        self.w = float(np.clip(self.w_raw, 0.0, 1.0))
        self.fit_n = int(len(tr))
        return self

    def predict(self, source_points: float, p0_cond: float) -> float:
        return max(0.0, float(p0_cond) + self.w * (float(source_points) - float(p0_cond)))

    def package(self):
        return {
            "horizon": self.horizon, "fit_n": self.fit_n, "w_raw": self.w_raw, "w": self.w,
            "bayes_params": {**BAYES_PARAMS, "fit_intercept": False},
            "alpha_": float(self.model.alpha_), "lambda_": float(self.model.lambda_),
        }


class P2RetentionModel:
    def __init__(self, route_kind: str, horizon: int):
        self.route_kind = str(route_kind)
        self.horizon = int(horizon)
        self.helper = rv.ProductionModel(self.route_kind, self.horizon)
        self.vec = DictVectorizer(sort=True)
        self.model = BayesianRidge(**BAYES_PARAMS)
        self.fit_n = 0

    def fit(self, train: pd.DataFrame):
        tr = train[(train.horizon == self.horizon) & (train.target_state != "out")].copy()
        tr = tr.sort_values(["source_season", "player_id", "position", "horizon"])
        if len(tr) < 100:
            raise RuntimeError("insufficient P2 training rows")
        self.helper._fit_scalers(tr)
        X = [self.helper._features(r) for r in tr.itertuples()]
        y = np.log1p(tr.target_points.to_numpy(float)) - np.log1p(tr.source_points.to_numpy(float))
        self.model.fit(self.vec.fit_transform(X).toarray(), y)
        self.fit_n = int(len(tr))
        return self

    def _delta(self, r, state=None) -> float:
        feat = self.helper._features(r, state) if self.route_kind == "D1" else self.helper._features(r)
        return float(self.model.predict(self.vec.transform([feat]).toarray())[0])

    def predict_active(self, r) -> float:
        if self.route_kind != "D0":
            raise ValueError("D0 route required")
        delta = self._delta(r)
        return max(0.0, math.expm1(math.log1p(max(0.0, float(r.source_points))) + delta))

    def predict_state(self, r, state: str) -> float:
        if self.route_kind != "D1":
            raise ValueError("D1 route required")
        delta = self._delta(r, state)
        return max(0.0, math.expm1(math.log1p(max(0.0, float(r.source_points))) + delta))

    def package(self):
        return {
            "route_kind": self.route_kind, "horizon": self.horizon, "fit_n": self.fit_n,
            "bayes_params": BAYES_PARAMS,
            "scalers": {k: v.package() for k, v in self.helper.scalers.items()},
            "features": self.vec.get_feature_names_out().tolist(),
            "coef": self.model.coef_.tolist(), "intercept": float(self.model.intercept_),
            "alpha_": float(self.model.alpha_), "lambda_": float(self.model.lambda_),
        }


def training_sets(rows: pd.DataFrame, source_season: int, horizon: int):
    t, h = int(source_season), int(horizon)
    if h == 2:
        state_train = rows[
            (rows.source_season < t)
            & (rows.source_season + rows.horizon <= t - 1)
            & (rows.horizon.isin([1, 2]))
        ].copy()
        prod_train = rows[
            (rows.source_season < t)
            & (rows.source_season + 2 <= t - 1)
            & (rows.horizon == 2)
        ].copy()
    else:
        state_train = rows[
            (rows.source_season < t)
            & (rows.source_season + 3 <= t - 1)
            & (rows.horizon == 3)
        ].copy()
        prod_train = state_train.copy()
    return state_train, prod_train


def fit_fold(rows: pd.DataFrame, source_season: int, horizon: int, selection: dict):
    state_train, prod_train = training_sets(rows, source_season, horizon)
    layers = rv.fit_state_layers(state_train, horizon)
    d0, d1 = rv.fit_candidates(prod_train, horizon)
    p1 = P1Anchor(horizon).fit(prod_train, layers, d0, d1, selection)
    needed = sorted({
        frozen_route(selection, horizon, p, cs)
        for p in rv.POSITIONS for cs in ("developmental", "established", "veteran")
    })
    p2 = {route: P2RetentionModel(route, horizon).fit(prod_train) for route in needed}
    return layers, d0, d1, p1, p2, {
        "source_season": int(source_season), "horizon": int(horizon),
        "state_train_n": int(len(state_train)), "prod_train_n": int(len(prod_train)),
        "P1": p1.package(), "P2": {k: v.package() for k, v in p2.items()}
    }


def predict_test_row(r, layers, d0, d1, p1, p2, selection):
    probs, route, p0_cond = p0_conditional(r, layers, d0, d1, selection)
    pactive = 1.0 - probs["out"]
    p0_uncond = pactive * p0_cond

    p1_cond = p1.predict(float(r.source_points), p0_cond)
    p1_uncond = pactive * p1_cond

    model = p2[route]
    if route == "D0":
        p2_cond = model.predict_active(r)
    else:
        state_means = {s: model.predict_state(r, s) for s in rv.POSITIVE_STATES}
        p2_uncond_tmp = sum(probs[s] * state_means[s] for s in rv.POSITIVE_STATES)
        p2_cond = p2_uncond_tmp / pactive if pactive > 1e-15 else 0.0
    p2_uncond = pactive * p2_cond

    rec = {
        "source_season": int(r.source_season), "player_id": str(r.player_id), "position": str(r.position),
        "horizon": int(r.horizon), "age": float(r.age), "experience": int(r.experience),
        "career_stage": str(r.career_stage), "age_band": str(r.age_band),
        "source_state": str(r.source_state), "source_points": float(r.source_points),
        "source_percentile": float(r.source_percentile), "target_points": float(r.target_points),
        "target_state": str(r.target_state), "target_active": int(r.target_state != "out"),
        "role_loss": None if pd.isna(r.role_loss) else int(r.role_loss),
        "deep_collapse": int(r.deep_collapse), "top10": int(r.top10), "top5": int(r.top5),
        "age_le25": int(r.age_le25), "prime_established": int(r.prime_established),
        "route": route, "p_active": float(pactive),
        "P0_cond": float(p0_cond), "P0_uncond": float(p0_uncond),
        "P1_cond": float(p1_cond), "P1_uncond": float(p1_uncond),
        "P2_cond": float(p2_cond), "P2_uncond": float(p2_uncond),
    }
    for s in rv.STATES:
        rec[f"p_{s}"] = float(probs[s])
    return rec


def rolling_predictions(rows: pd.DataFrame, selection: dict, seasons=range(2014, 2023)):
    records, fitlog = [], []
    for t in seasons:
        for h in (2, 3):
            test = rows[(rows.source_season == t) & (rows.horizon == h)].copy()
            if test.empty:
                continue
            layers, d0, d1, p1, p2, log = fit_fold(rows, t, h, selection)
            for r in test.itertuples():
                records.append(predict_test_row(r, layers, d0, d1, p1, p2, selection))
            fitlog.append(log)
    return pd.DataFrame(records), fitlog


def control_parity(pred: pd.DataFrame, durable: pd.DataFrame, tol=1e-8):
    d = durable.copy()
    selection_cols = ["source_season", "player_id", "position", "horizon"]
    d["route"] = [
        "D1" if np.isclose(float(r.pred_D1), float(r.pred_D1)) else "D1"
        for r in d.itertuples()
    ]
    # Durable control conditional / unconditional from the already-frozen route will be reconstructed from route cells.
    # Caller adds durable route and values before this function.
    m = pred.merge(
        d[selection_cols + ["durable_P0_cond", "durable_P0_uncond", "p_active"]],
        on=selection_cols, how="outer", suffixes=("_new", "_old"), indicator=True
    )
    both = m[m["_merge"] == "both"].copy()
    dc = np.abs(both.P0_cond - both.durable_P0_cond)
    du = np.abs(both.P0_uncond - both.durable_P0_uncond)
    dp = np.abs(both.p_active_new - both.p_active_old)
    out = {
        "rows_new": int(len(pred)), "rows_durable": int(len(d)), "matched": int(len(both)),
        "left_only": int((m["_merge"] == "left_only").sum()), "right_only": int((m["_merge"] == "right_only").sum()),
        "max_conditional_diff": float(dc.max()) if len(dc) else None,
        "max_unconditional_diff": float(du.max()) if len(du) else None,
        "max_active_probability_diff": float(dp.max()) if len(dp) else None,
        "tolerance": float(tol)
    }
    out["pass"] = (
        out["left_only"] == 0 and out["right_only"] == 0
        and out["max_conditional_diff"] <= tol
        and out["max_unconditional_diff"] <= tol
        and out["max_active_probability_diff"] <= tol
    )
    return out


def block_name(season: int):
    for name, (lo, hi) in BLOCKS.items():
        if lo <= int(season) <= hi:
            return name
    return "post_freeze"


def eval_metrics(g: pd.DataFrame, candidate: str):
    cond_col, uncond_col = f"{candidate}_cond", f"{candidate}_uncond"
    all_err = g[uncond_col] - g.target_points
    active = g[g.target_active == 1].copy()
    cond_err = active[cond_col] - active.target_points
    ret = active[active.source_points > 0].copy()
    ret_bias = (ret[cond_col] / ret.source_points - ret.target_points / ret.source_points)
    return {
        "n": int(len(g)), "active_n": int(len(active)),
        "unconditional_mae": float(np.abs(all_err).mean()), "unconditional_bias": float(all_err.mean()),
        "conditional_mae": float(np.abs(cond_err).mean()) if len(active) else None,
        "conditional_bias": float(cond_err.mean()) if len(active) else None,
        "retention_bias": float(ret_bias.mean()) if len(ret) else None,
        "absolute_retention_bias": float(abs(ret_bias.mean())) if len(ret) else None,
        "underprediction_share_active": float((cond_err < 0).mean()) if len(active) else None,
    }


def scorecard(pred: pd.DataFrame):
    selection = pred[pred.source_season.between(*SELECTION_SEASONS)].copy()
    rows = []
    cohort_defs = {
        "all": lambda x: pd.Series(True, index=x.index),
        "top10": lambda x: x.source_percentile >= 0.90,
        "top5": lambda x: x.source_percentile >= 0.95,
        "young_top10": lambda x: (x.source_percentile >= 0.90) & (x.age <= 25),
        "age_le25": lambda x: x.age <= 25,
        "developmental": lambda x: x.career_stage == "developmental",
        "prime_established": lambda x: x.prime_established == 1,
        "veteran": lambda x: x.career_stage == "veteran",
        "role_loss": lambda x: x.role_loss == 1,
        "non_role_loss": lambda x: ~(x.role_loss == 1),
        "deep_collapse": lambda x: x.deep_collapse == 1,
    }
    for h in (2, 3):
        hh = selection[selection.horizon == h].copy()
        scopes = [("aggregate", "all", hh)]
        for b, (lo, hi) in BLOCKS.items():
            scopes.append(("block", b, hh[hh.source_season.between(lo, hi)]))
        for p in rv.POSITIONS:
            scopes.append(("position", p, hh[hh.position == p]))
        for cname, func in cohort_defs.items():
            scopes.append(("cohort", cname, hh[func(hh)]))
        for scope_type, scope, gg in scopes:
            if len(gg) == 0:
                continue
            for cand in CANDIDATES:
                m = eval_metrics(gg, cand)
                rows.append({"horizon": h, "scope_type": scope_type, "scope": scope, "candidate": cand, **m})
    return pd.DataFrame(rows)


def retention_by_decile(pred: pd.DataFrame):
    x = pred[pred.source_season.between(*SELECTION_SEASONS) & (pred.target_active == 1) & (pred.source_points > 0)].copy()
    x["source_decile"] = np.minimum(10, np.floor(x.source_percentile * 10).astype(int) + 1)
    rows = []
    for h in (2, 3):
        hh = x[x.horizon == h]
        for pos_scope, gg0 in [("ALL", hh)] + [(p, hh[hh.position == p]) for p in rv.POSITIONS]:
            for dec, gg in gg0.groupby("source_decile"):
                rec = {"horizon": h, "position_scope": pos_scope, "source_decile": int(dec), "n": int(len(gg)),
                       "mean_source_points": float(gg.source_points.mean()),
                       "realized_retention": float((gg.target_points / gg.source_points).mean())}
                for cand in CANDIDATES:
                    rec[f"{cand}_pred_retention"] = float((gg[f"{cand}_cond"] / gg.source_points).mean())
                rows.append(rec)
    return pd.DataFrame(rows)


def get_metric(sc, h, scope_type, scope, cand, metric):
    r = sc[
        (sc.horizon == h) & (sc.scope_type == scope_type) & (sc.scope == scope) & (sc.candidate == cand)
    ]
    if len(r) != 1:
        raise RuntimeError(f"metric row not unique: {h} {scope_type} {scope} {cand}")
    return float(r.iloc[0][metric])


def selection_decision(sc: pd.DataFrame):
    decision = {"candidates": {}}
    for cand in ("P1", "P2"):
        detail = {"rules": {}, "pass": True}
        # Step 1 aggregate top5
        top5_improvements = {}
        for h in (2, 3):
            p0 = get_metric(sc, h, "cohort", "top5", "P0", "absolute_retention_bias")
            cc = get_metric(sc, h, "cohort", "top5", cand, "absolute_retention_bias")
            top5_improvements[str(h)] = p0 - cc
        r1a = all(v >= 0.01 for v in top5_improvements.values())
        detail["rules"]["top5_aggregate_improvement_ge_0p01_each_horizon"] = {
            "pass": r1a, "improvement": top5_improvements
        }
        detail["pass"] &= r1a

        block_results, improved_count, all_guard = [], 0, True
        for h in (2, 3):
            for b in BLOCKS:
                p0 = get_metric(sc, h, "block", b, "P0", "absolute_retention_bias")
                cc = get_metric(sc, h, "block", b, cand, "absolute_retention_bias")
                imp = p0 - cc
                improved_count += int(imp > 0)
                all_guard &= (imp >= -0.01)
                block_results.append({"horizon": h, "block": b, "improvement": imp})
        r1b = improved_count >= 5 and all_guard
        detail["rules"]["top5_chronology_5of6_and_no_worse_than_0p01"] = {
            "pass": r1b, "improved_cells": improved_count, "cells": block_results
        }
        detail["pass"] &= r1b

        top10_guard = {}
        r1c = True
        for h in (2, 3):
            p0 = get_metric(sc, h, "cohort", "top10", "P0", "absolute_retention_bias")
            cc = get_metric(sc, h, "cohort", "top10", cand, "absolute_retention_bias")
            change = cc - p0
            top10_guard[str(h)] = change
            r1c &= change <= 0.01
        detail["rules"]["top10_abs_retention_bias_guard"] = {"pass": r1c, "candidate_minus_P0": top10_guard}
        detail["pass"] &= r1c

        young = {}
        r2 = True
        for h in (2, 3):
            rb0 = get_metric(sc, h, "cohort", "young_top10", "P0", "absolute_retention_bias")
            rbc = get_metric(sc, h, "cohort", "young_top10", cand, "absolute_retention_bias")
            m0 = get_metric(sc, h, "cohort", "young_top10", "P0", "conditional_mae")
            mc = get_metric(sc, h, "cohort", "young_top10", cand, "conditional_mae")
            d0 = get_metric(sc, h, "cohort", "developmental", "P0", "unconditional_mae")
            dc = get_metric(sc, h, "cohort", "developmental", cand, "unconditional_mae")
            young[str(h)] = {"abs_ret_bias_change": rbc-rb0, "cond_mae_change": mc-m0, "developmental_uncond_mae_change": dc-d0}
            r2 &= (rbc-rb0 <= 0.01 and mc-m0 <= 1.0 and dc-d0 <= 0.75)
        detail["rules"]["young_developmental_guardrails"] = {"pass": r2, "changes": young}
        detail["pass"] &= r2

        broad = {"aggregate": {}, "blocks": [], "positions": []}
        r3 = True
        for h in (2, 3):
            u0 = get_metric(sc, h, "aggregate", "all", "P0", "unconditional_mae")
            uc = get_metric(sc, h, "aggregate", "all", cand, "unconditional_mae")
            c0 = get_metric(sc, h, "aggregate", "all", "P0", "conditional_mae")
            cc = get_metric(sc, h, "aggregate", "all", cand, "conditional_mae")
            broad["aggregate"][str(h)] = {"unconditional_mae_change": uc-u0, "conditional_mae_change": cc-c0}
            r3 &= (uc-u0 <= 0.50 and cc-c0 <= 0.50)
            for b in BLOCKS:
                b0 = get_metric(sc, h, "block", b, "P0", "unconditional_mae")
                bc = get_metric(sc, h, "block", b, cand, "unconditional_mae")
                ch = bc-b0
                broad["blocks"].append({"horizon": h, "block": b, "unconditional_mae_change": ch})
                r3 &= ch <= 1.0
            for p in rv.POSITIONS:
                p0 = get_metric(sc, h, "position", p, "P0", "unconditional_mae")
                pc = get_metric(sc, h, "position", p, cand, "unconditional_mae")
                ch = pc-p0
                broad["positions"].append({"horizon": h, "position": p, "unconditional_mae_change": ch})
                r3 &= ch <= 1.0
        detail["rules"]["broad_accuracy_guardrails"] = {"pass": r3, **broad}
        detail["pass"] &= r3

        mean_gain = float(np.mean(list(top5_improvements.values())))
        r4 = mean_gain >= 0.01
        detail["rules"]["mean_top5_abs_retention_bias_reduction_ge_0p01"] = {"pass": r4, "mean_improvement": mean_gain}
        detail["pass"] &= r4
        decision["candidates"][cand] = detail

    passing = [c for c, d in decision["candidates"].items() if d["pass"]]
    decision["passing"] = passing
    if not passing:
        decision["winner"] = None
        decision["outcome_if_stop_now"] = "B"
        return decision
    if len(passing) == 1:
        decision["winner"] = passing[0]
        return decision

    def top5_sum(c):
        return sum(get_metric(sc, h, "cohort", "top5", c, "absolute_retention_bias") for h in (2,3))
    def uncond_sum(c):
        return sum(get_metric(sc, h, "aggregate", "all", c, "unconditional_mae") for h in (2,3))
    s1, s2 = top5_sum("P1"), top5_sum("P2")
    u1, u2 = uncond_sum("P1"), uncond_sum("P2")
    if abs(s1-s2) <= 0.005 and abs(u1-u2) <= 0.25:
        winner = "P1"
        reason = "predeclared simplicity tiebreak"
    else:
        winner = min(passing, key=top5_sum)
        reason = "lower summed absolute top5 retention bias"
    decision["winner"] = winner
    decision["winner_reason"] = reason
    decision["tiebreak_values"] = {"P1_top5_sum": s1, "P2_top5_sum": s2, "P1_uncond_sum": u1, "P2_uncond_sum": u2}
    return decision


def attach_durable_control(durable: pd.DataFrame, selection: dict):
    d = durable.copy()
    routes = [
        frozen_route(selection, int(r.horizon), str(r.position), str(r.career_stage))
        for r in d.itertuples()
    ]
    d["durable_route"] = routes
    d["durable_P0_cond"] = np.where(
        d.durable_route == "D1",
        d.pred_D1 / d.p_active.clip(lower=1e-15),
        d.active_D0
    )
    d["durable_P0_uncond"] = np.where(d.durable_route == "D1", d.pred_D1, d.pred_D0)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--q3", required=True)
    ap.add_argument("--selection", required=True)
    ap.add_argument("--durable-control", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(args.panel)
    q3 = pd.read_csv(args.q3)
    selection = json.loads(Path(args.selection).read_text())
    durable = pd.read_csv(args.durable_control)

    rows = rv.build_rows(panel, 2023)
    parity = rv.parity_check(rows, q3)
    if not parity["pass"]:
        raise SystemExit("governed source reconstruction parity failure")

    pred, fitlog = rolling_predictions(rows, selection, range(2014, 2023))
    durable = attach_durable_control(durable, selection)
    control = control_parity(pred, durable, tol=1e-8)
    (out / "P0_CONTROL_PARITY.json").write_text(json.dumps(control, indent=2) + "\n")
    if not control["pass"]:
        raise SystemExit("P0 durable control parity failure")

    sc = scorecard(pred)
    dec = retention_by_decile(pred)
    decision = selection_decision(sc)

    pred.to_csv(out / "HISTORICAL_CANDIDATE_PREDICTIONS.csv", index=False)
    sc.to_csv(out / "HISTORICAL_CANDIDATE_SCORECARD.csv", index=False)
    dec.to_csv(out / "RETENTION_DECILE_CALIBRATION.csv", index=False)
    (out / "FIT_LOG.json").write_text(json.dumps(fitlog, indent=2) + "\n")
    (out / "HISTORICAL_SELECTION_DECISION.json").write_text(json.dumps(decision, indent=2) + "\n")

    post = pred[pred.source_season.between(*POST_FREEZE_SEASONS)].copy()
    post_sc = []
    for h in (2,3):
        hh = post[post.horizon == h]
        for cand in CANDIDATES:
            post_sc.append({"horizon": h, "candidate": cand, **eval_metrics(hh, cand)})
    (out / "POST_FREEZE_REPLICATION_SCORECARD.json").write_text(json.dumps(post_sc, indent=2) + "\n")

    manifest = {
        "schema_version": "fsffl-conditional-production-historical-run-v1",
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__},
        "inputs": {
            "panel_sha256": sha256_file(args.panel), "q3_sha256": sha256_file(args.q3),
            "selection_sha256": sha256_file(args.selection), "durable_control_sha256": sha256_file(args.durable_control),
            "implementation_sha256": sha256_file(Path(__file__))
        },
        "rows": int(len(pred)), "fitlog_entries": int(len(fitlog)),
        "selection_window": [2014,2020], "post_freeze_window":[2021,2022],
        "P0_control_parity": control, "winner": decision.get("winner"),
        "candidate_fit_cycles": {"P0_D0_D1_fold_pairs": len(fitlog), "P1_anchor_fits": len(fitlog), "P2_model_fits": int(sum(len(x["P2"]) for x in fitlog))},
        "current_board_used": False, "current_player_tuning_actions": 0
    }
    (out / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"control": control, "decision": decision, "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()

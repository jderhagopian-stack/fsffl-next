from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import BayesianRidge, LogisticRegression

POSITIONS = ("QB", "RB", "WR", "TE")
STATES = ("out", "depth", "usable", "starter", "premium", "elite")
POSITIVE_STATES = STATES[1:]
STATE_RANK = {s: i for i, s in enumerate(STATES)}
THRESHOLDS = (("useful", 2), ("starter", 3), ("premium", 4), ("elite", 5))
LOGIT_C = 0.25
LOGIT_SEED = 20260915
BOOTSTRAP_SEED = 20260919
REPLAY_PROB_TOL = 1e-10
REPLAY_POINT_TOL = 1e-8
BLOCKS = {"early": (2014, 2016), "mid": (2017, 2018), "validation": (2019, 2020)}
STATE_LAYER_ROUTE = {"QB": "A2+C+D", "RB": "A2+D", "WR": "A2+D", "TE": "A2+D"}

BAYES_PARAMS = dict(
    max_iter=300,
    tol=1e-6,
    alpha_1=1e-6,
    alpha_2=1e-6,
    lambda_1=1e-6,
    lambda_2=1e-6,
    compute_score=False,
    fit_intercept=True,
    copy_X=True,
    verbose=False,
)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def json_sha(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def quantile(values: Iterable[float], p: float) -> float:
    xs = sorted(float(x) for x in values)
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo, hi = int(math.floor(z)), int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    f = z - lo
    return xs[lo] * (1 - f) + xs[hi] * f


def fit_state_boundaries(values: Iterable[float], k: int = 5, iterations: int = 60):
    xs = sorted(math.log1p(max(0.0, float(x))) for x in values if x > 0)
    if len(xs) < k:
        c = sum(xs) / len(xs) if xs else 0.0
        centers = [c] * k
    else:
        centers = [quantile(xs, (i + 0.5) / k) for i in range(k)]
    for _ in range(iterations):
        groups = [[] for _ in range(k)]
        for x in xs:
            j = min(range(k), key=lambda q: abs(x - centers[q]))
            groups[j].append(x)
        new = [sum(g) / len(g) if g else centers[i] for i, g in enumerate(groups)]
        new.sort()
        if max(abs(a - b) for a, b in zip(new, centers)) < 1e-9:
            centers = new
            break
        centers = new
    raw = [max(0.0, math.expm1(x)) for x in centers]
    return tuple(raw), tuple((raw[i] + raw[i + 1]) / 2 for i in range(k - 1))


def state_for_points(points: float, boundaries) -> str:
    if points <= 0:
        return "out"
    idx = 0
    thresholds = boundaries[1]
    while idx < len(thresholds) and points > thresholds[idx]:
        idx += 1
    return POSITIVE_STATES[idx]


def coarse_age_band(position: str, age: float) -> str:
    if not np.isfinite(age):
        return "unknown"
    if position == "QB":
        return "young" if age <= 25 else ("prime" if age <= 31 else "aging")
    return "young" if age <= 23 else ("prime" if age <= 27 else "aging")


def exp_band(exp: int) -> str:
    exp = int(exp)
    if exp <= 1:
        return "0_1"
    if exp <= 3:
        return "2_3"
    if exp <= 6:
        return "4_6"
    return "7_plus"


def career_stage(exp: int) -> str:
    exp = int(exp)
    if exp <= 3:
        return "developmental"
    if exp <= 8:
        return "established"
    return "veteran"


def build_rows(panel: pd.DataFrame, max_source_season: int = 2023) -> pd.DataFrame:
    df = panel.copy()
    df = df[df.position.isin(POSITIONS)].copy()
    df["season"] = df.season.astype(int)
    df["fantasy_points"] = pd.to_numeric(df.fantasy_points, errors="coerce").fillna(0.0)
    df["age_years"] = pd.to_numeric(df.age_years, errors="coerce")
    df["experience_years"] = pd.to_numeric(df.experience_years, errors="coerce").fillna(0).astype(int)
    df["role_band"] = df.role_band.fillna("unknown")
    df["opportunity_per_game"] = pd.to_numeric(df.opportunity_per_game, errors="coerce")
    df["games"] = pd.to_numeric(df.games, errors="coerce")
    df = df.sort_values(["season", "player_id", "position"]).reset_index(drop=True)
    by_season = {int(s): g.copy() for s, g in df.groupby("season")}
    key = {(str(r.player_id), int(r.season)): r for r in df.itertuples(index=False)}
    source_info = {}
    age_state_info = {}
    cutoff_bounds = {}

    for t in range(2004, max_source_season + 1):
        prior = df[df.season < t]
        cur = by_season.get(t)
        if prior.empty or cur is None:
            continue
        bounds = {}
        state_stats = {}
        age_state_stats = {}
        for p in POSITIONS:
            vals = prior.loc[(prior.position == p) & (prior.fantasy_points > 0), "fantasy_points"].tolist()
            if len(vals) < 20:
                continue
            b = fit_state_boundaries(vals)
            bounds[p] = b
            pp = prior[prior.position == p].copy()
            pp["state"] = [state_for_points(v, b) for v in pp.fantasy_points]
            pp["age_band_tmp"] = [coarse_age_band(p, float(a)) for a in pp.age_years]
            for st, g in pp.groupby("state"):
                a = g.fantasy_points.to_numpy(float)
                mu = float(a.mean())
                sd = float(a.std(ddof=1)) if len(a) > 1 else 0.0
                if sd < 1e-6:
                    sd = max(1.0, abs(mu) * 0.25)
                state_stats[(p, st)] = (len(a), mu, sd)
            for (ab, st), g in pp.groupby(["age_band_tmp", "state"]):
                a = g.fantasy_points.to_numpy(float)
                mu = float(a.mean())
                sd = float(a.std(ddof=1)) if len(a) > 1 else 0.0
                if sd < 1e-6:
                    sd = max(1.0, abs(mu) * 0.25)
                age_state_stats[(p, ab, st)] = (len(a), mu, sd)
        cutoff_bounds[t] = bounds
        for r in cur.itertuples(index=False):
            p = str(r.position)
            if p not in bounds:
                continue
            points = float(r.fantasy_points)
            st = state_for_points(points, bounds[p])
            base = state_stats.get((p, st))
            if base is None or base[0] < 10:
                continue
            _, mu, sd = base
            age = float(r.age_years) if np.isfinite(r.age_years) else np.nan
            ab = coarse_age_band(p, age)
            ast = age_state_stats.get((p, ab, st))
            if ast is not None and ast[0] >= 10:
                _, amu, asd = ast
            else:
                amu, asd = mu, sd
            source_info[(str(r.player_id), t)] = {
                "position": p,
                "source_state": st,
                "source_points": points,
                "current_resid_z": (points - mu) / sd,
                "current_age_state_resid_z": (points - amu) / asd,
                "age": age,
                "age_band": ab,
                "experience": int(r.experience_years),
                "source_role_band": str(r.role_band),
                "games": float(r.games) if np.isfinite(r.games) else np.nan,
                "opportunity_per_game": float(r.opportunity_per_game) if np.isfinite(r.opportunity_per_game) else np.nan,
            }
            age_state_info[(str(r.player_id), t)] = (points - amu) / asd

    rows = []
    max_data_season = int(df.season.max())
    for t in range(2005, min(max_source_season, max_data_season) + 1):
        bounds = cutoff_bounds.get(t, {})
        for r in by_season.get(t, pd.DataFrame()).itertuples(index=False):
            pid = str(r.player_id)
            src = source_info.get((pid, t))
            if src is None:
                continue
            p = src["position"]
            prior_row = key.get((pid, t - 1))
            prior1_points = None
            if prior_row is not None and str(prior_row.position) == p:
                prior1_points = float(prior_row.fantasy_points)
            prior_age1 = age_state_info.get((pid, t - 1), np.nan)
            prior_age2 = age_state_info.get((pid, t - 2), np.nan)
            prior2_cov = int(np.isfinite(prior_age1) and np.isfinite(prior_age2))
            prior2_mean = float((prior_age1 + prior_age2) / 2) if prior2_cov else np.nan
            prior2_gap = float(abs(prior_age1 - prior_age2)) if prior2_cov else np.nan
            for h in (1, 2, 3):
                if t + h > max_data_season:
                    continue
                tr = key.get((pid, t + h))
                present = tr is not None and str(tr.position) == p
                target_points = float(tr.fantasy_points) if present else 0.0
                target_state = state_for_points(target_points, bounds[p]) if present else "out"
                target_role = str(tr.role_band) if present else "missing"
                role_loss = np.nan
                if present and src["source_role_band"] == "established" and target_role in ("weak", "established"):
                    role_loss = float(target_role == "weak")
                rows.append({
                    "source_season": t, "player_id": pid, "position": p, "horizon": h,
                    "age": src["age"], "age_band": src["age_band"], "experience": src["experience"],
                    "career_stage": career_stage(src["experience"]), "source_state": src["source_state"],
                    "source_points": src["source_points"], "current_resid_z": src["current_resid_z"],
                    "current_age_state_resid_z": src["current_age_state_resid_z"],
                    "prior_age_state_resid_z": prior_age1,
                    "prior2_mean_age_state_z": prior2_mean, "prior2_gap_age_state_z": prior2_gap,
                    "prior2_coverage": prior2_cov, "prior1_points": prior1_points,
                    "prior1_coverage": int(prior1_points is not None),
                    "source_role_band": src["source_role_band"], "games": src["games"],
                    "opportunity_per_game": src["opportunity_per_game"],
                    "target_present": int(present), "target_points": target_points, "target_state": target_state,
                    "target_role_band": target_role, "role_loss": role_loss,
                })
    ev = pd.DataFrame(rows)
    ev = ev[ev.source_state != "out"].copy()
    unique = ev[ev.horizon == 1][["source_season", "player_id", "position", "source_state", "source_points"]].copy()
    unique["source_percentile"] = np.nan
    unique["state_percentile"] = np.nan
    for _, idx in unique.groupby(["source_season", "position"]).groups.items():
        v = unique.loc[idx, "source_points"]
        unique.loc[idx, "source_percentile"] = (v.rank(method="average") - 0.5) / len(v)
    for _, idx in unique.groupby(["source_season", "position", "source_state"]).groups.items():
        v = unique.loc[idx, "source_points"]
        unique.loc[idx, "state_percentile"] = (v.rank(method="average") - 0.5) / len(v)
    ev = ev.merge(unique[["source_season", "player_id", "source_percentile", "state_percentile"]],
                  on=["source_season", "player_id"], how="left")
    ev["deep_collapse"] = (ev.target_points <= 0.25 * ev.source_points).astype(int)
    ev["top10"] = (ev.source_percentile >= 0.90).astype(int)
    ev["top5"] = (ev.source_percentile >= 0.95).astype(int)
    ev["age_le25"] = (ev.age <= 25).astype(int)
    ev["prime_established"] = ((ev.career_stage == "established") & (ev.age_band == "prime")).astype(int)
    return ev.sort_values(["source_season", "player_id", "position", "horizon"]).reset_index(drop=True)


def parity_check(rebuilt: pd.DataFrame, q3: pd.DataFrame) -> dict:
    a = rebuilt[rebuilt.source_season <= 2022].copy()
    b = q3[q3.source_state != "out"].copy()
    keys = ["source_season", "player_id", "position", "horizon"]
    keep = keys + ["source_state", "source_points", "target_points", "target_state",
                   "current_age_state_resid_z", "prior_age_state_resid_z"]
    m = a[keep].merge(b[keep], on=keys, suffixes=("_new", "_old"), how="outer", indicator=True)
    both = m[m["_merge"] == "both"].copy()
    def mdiff(col):
        x = pd.to_numeric(both[f"{col}_new"], errors="coerce")
        y = pd.to_numeric(both[f"{col}_old"], errors="coerce")
        d = np.abs(x - y)
        return float(np.nanmax(d.to_numpy())) if np.isfinite(d).any() else 0.0
    out = {
        "rebuilt_rows": int(len(a)), "governed_rows": int(len(b)),
        "matched_rows": int(len(both)),
        "left_only": int((m["_merge"] == "left_only").sum()),
        "right_only": int((m["_merge"] == "right_only").sum()),
        "source_state_mismatch": int((both.source_state_new != both.source_state_old).sum()),
        "target_state_mismatch": int((both.target_state_new.replace({"missing":"out"}) != both.target_state_old.replace({"missing":"out"})).sum()),
        "max_source_points_diff": mdiff("source_points"),
        "max_target_points_diff": mdiff("target_points"),
        "max_current_age_state_resid_z_diff": mdiff("current_age_state_resid_z"),
        "max_prior_age_state_resid_z_diff": mdiff("prior_age_state_resid_z"),
    }
    out["pass"] = (
        out["left_only"] == 0 and out["right_only"] == 0 and out["source_state_mismatch"] == 0
        and out["target_state_mismatch"] == 0 and out["max_source_points_diff"] <= 1e-12
        and out["max_target_points_diff"] <= 1e-12
        and out["max_current_age_state_resid_z_diff"] <= 1e-10
        and out["max_prior_age_state_resid_z_diff"] <= 1e-10
    )
    return out


def prob_features(r, *, age_mode: str, add_c: bool, add_d: bool) -> dict:
    p = str(r.position); h = int(r.horizon); exp = int(r.experience)
    d = {f"p={p}":1, f"s={r.source_state}":1, f"h={h}":1, f"e={exp_band(exp)}":1,
         "exp":min(15.0,max(0.0,float(exp)))/10.0}
    if age_mode == "coarse":
        d[f"a={r.age_band}"] = 1
    elif age_mode == "a2":
        age = float(r.age); ref = 31.0 if p == "QB" else 27.0
        d[f"age_exact_{p}"] = (age-ref)/5.0
        if p == "QB":
            d["age_late_QB"] = max(0.0, age-37.0)/5.0
        else:
            d[f"age_late_{p}"] = max(0.0, age-31.0)/5.0
            if p == "TE":
                d["age_young_TE"] = max(0.0,24.0-age)/5.0
    cur = max(0.0,float(r.source_points))
    prior = None if not int(r.prior1_coverage) else max(0.0,float(r.prior1_points))
    pv = 0.0 if prior is None else prior
    d.update({"lp":math.log1p(cur)/6.0, "lprev":math.log1p(pv)/6.0,
              "dpts":max(-2.0,min(2.0,(cur-pv)/100.0)), "prev_cov":0 if prior is None else 1})
    role = str(r.source_role_band) if pd.notna(r.source_role_band) else "unknown"
    if role in ("weak","established") and pd.notna(r.opportunity_per_game) and pd.notna(r.games):
        d[f"role={role}"]=1; d["u_cov"]=1
        d["lopg"]=math.log1p(max(0.0,float(r.opportunity_per_game)))/4.0
        d["lg"]=math.log1p(max(0.0,float(r.games)))/3.0
    else:
        d.update({"role=unknown":1,"u_cov":0,"lopg":0.0,"lg":0.0})
    d.update({"r_cov":0,"i_cov":0,"part_cov":0})
    if add_c:
        mem = r.prior_age_state_resid_z
        supported = (p=="QB" and r.age_band in ("prime","aging"))
        if supported:
            key = f"mem_{p}_{r.age_band}_h{h}"
            if pd.notna(mem):
                d[key]=float(mem); d[key+"_cov"]=1
            else:
                d[key]=0.0; d[key+"_cov"]=0
    if add_d and pd.notna(r.state_percentile):
        pct=float(r.state_percentile)
        d[f"pct_{p}"]=(pct-0.5)*2.0
        if r.source_state in ("premium","elite"):
            d[f"hi_{p}_{r.source_state}"]=max(0.0,(pct-0.8)/0.2)
            d[f"lo_{p}_{r.source_state}"]=max(0.0,(0.2-pct)/0.2)
    return d


class BinModel:
    def __init__(self):
        self.vec=DictVectorizer(sort=True)
        self.model=LogisticRegression(C=LOGIT_C,solver="lbfgs",max_iter=2000,random_state=LOGIT_SEED)
        self.ok=False
    def fit(self, feats, y):
        y=np.asarray(y,dtype=int)
        counts=np.bincount(y,minlength=2)
        if len(y)>=100 and counts.min()>=15:
            self.model.fit(self.vec.fit_transform(feats),y); self.ok=True
        return self
    def prob(self, feat):
        if not self.ok:
            raise RuntimeError("unavailable binary state model")
        return float(self.model.predict_proba(self.vec.transform([feat]))[0,1])
    def package(self):
        return {
            "ok":self.ok, "features":self.vec.get_feature_names_out().tolist(),
            "coef":self.model.coef_.ravel().tolist(), "intercept":self.model.intercept_.ravel().tolist(),
            "classes":self.model.classes_.tolist(), "params":{"C":LOGIT_C,"solver":"lbfgs","max_iter":2000,"random_state":LOGIT_SEED}
        }


class ProbLayer:
    def __init__(self, add_c: bool):
        self.add_c=add_c
        self.persist=BinModel()
        self.ordered={name:BinModel() for name,_ in THRESHOLDS}
    def fit(self, train: pd.DataFrame):
        pf=[prob_features(r,age_mode="a2",add_c=self.add_c,add_d=False) for r in train.itertuples()]
        self.persist.fit(pf,(train.target_state!="out").astype(int).tolist())
        pos=train[train.target_state!="out"].copy()
        of=[prob_features(r,age_mode="coarse",add_c=self.add_c,add_d=True) for r in pos.itertuples()]
        for name,rank in THRESHOLDS:
            self.ordered[name].fit(of,[1 if STATE_RANK[s]>=rank else 0 for s in pos.target_state])
        return self
    def predict(self,r):
        p=self.persist.prob(prob_features(r,age_mode="a2",add_c=self.add_c,add_d=False))
        feat=prob_features(r,age_mode="coarse",add_c=self.add_c,add_d=True)
        cum=[]; last=1.0
        for name,_ in THRESHOLDS:
            q=self.ordered[name].prob(feat)
            q=min(last,max(0.0,min(1.0,q))); cum.append(q); last=q
        useful,starter,premium,elite=cum
        cond={"depth":1-useful,"usable":useful-starter,"starter":starter-premium,"premium":premium-elite,"elite":elite}
        out={"out":1-p}; out.update({s:p*cond[s] for s in POSITIVE_STATES})
        z=sum(out.values())
        return {s:out[s]/z for s in STATES}
    def package(self):
        return {"add_c":self.add_c,"persistence":self.persist.package(),"ordered":{k:v.package() for k,v in self.ordered.items()}}


@dataclass
class Scaler:
    mean: float
    sd: float
    @classmethod
    def fit(cls, x):
        a=np.asarray(x,dtype=float); a=a[np.isfinite(a)]
        mean=float(a.mean()) if len(a) else 0.0
        sd=float(a.std(ddof=0)) if len(a) else 1.0
        if sd<1e-12: sd=1.0
        return cls(mean,sd)
    def z(self,x):
        return (float(x)-self.mean)/self.sd
    def package(self):
        return {"mean":self.mean,"sd":self.sd}


class ProductionModel:
    def __init__(self, candidate: str, horizon: int):
        self.candidate=candidate; self.horizon=int(horizon)
        self.vec=DictVectorizer(sort=True)
        self.model=BayesianRidge(**BAYES_PARAMS)
        self.scalers={}
        self.fit_n=0
    def _fit_scalers(self, train):
        raw={
            "source_log":np.log1p(train.source_points.to_numpy(float)),
            "source_pct":train.source_percentile.to_numpy(float),
            "age":train.age.to_numpy(float),
            "experience":np.minimum(train.experience.to_numpy(float),15.0),
        }
        for k,v in raw.items(): self.scalers[k]=Scaler.fit(v)
        cov=train[train.prior1_coverage==1]
        self.scalers["prior1_log"]=Scaler.fit(np.log1p(cov.prior1_points.to_numpy(float))) if len(cov) else Scaler(0.0,1.0)
        if self.candidate=="D1":
            c2=train[train.prior2_coverage==1]
            self.scalers["prior2_mean"]=Scaler.fit(c2.prior2_mean_age_state_z.to_numpy(float)) if len(c2) else Scaler(0.0,1.0)
            self.scalers["prior2_gap"]=Scaler.fit(c2.prior2_gap_age_state_z.to_numpy(float)) if len(c2) else Scaler(0.0,1.0)
    def _features(self,r,future_state=None):
        vals={
            "source_log":self.scalers["source_log"].z(math.log1p(max(0.0,float(r.source_points)))),
            "source_pct":self.scalers["source_pct"].z(float(r.source_percentile)),
            "age":self.scalers["age"].z(float(r.age)),
            "experience":self.scalers["experience"].z(min(float(r.experience),15.0)),
            "prior1_log": self.scalers["prior1_log"].z(math.log1p(max(0.0,float(r.prior1_points)))) if int(r.prior1_coverage) else 0.0,
        }
        d={f"p={r.position}":1,f"src={r.source_state}":1,"prior1_cov":int(r.prior1_coverage)}
        for k,v in vals.items():
            d[k]=v; d[f"{k}@p={r.position}"]=v
        if self.candidate=="D1":
            if future_state is None: future_state=str(r.target_state)
            d[f"future={future_state}"]=1
            d[f"pstate={r.position}|{future_state}"]=1
            d[f"source_log@future={future_state}"]=vals["source_log"]
            d[f"source_pct@future={future_state}"]=vals["source_pct"]
            if int(r.prior2_coverage):
                m=self.scalers["prior2_mean"].z(float(r.prior2_mean_age_state_z))
                g=self.scalers["prior2_gap"].z(float(r.prior2_gap_age_state_z))
            else:
                m=g=0.0
            d["prior2_cov"]=int(r.prior2_coverage); d["prior2_mean_z"]=m; d["prior2_gap_z"]=g
            d[f"prior2_mean_z@p={r.position}"]=m; d[f"prior2_gap_z@p={r.position}"]=g
        return d
    def fit(self, train):
        tr=train[(train.horizon==self.horizon)&(train.target_state!="out")].copy()
        tr=tr.sort_values(["source_season","player_id","position","horizon"])
        if len(tr)<100: raise RuntimeError("insufficient production training rows")
        self._fit_scalers(tr)
        X=[self._features(r) for r in tr.itertuples()]
        self.model.fit(self.vec.fit_transform(X),tr.target_points.to_numpy(float))
        self.fit_n=len(tr)
        return self
    def predict_active(self,r):
        if self.candidate!="D0": raise ValueError("D0 only")
        return max(0.0,float(self.model.predict(self.vec.transform([self._features(r)]))[0]))
    def predict_state(self,r,state):
        if self.candidate!="D1": raise ValueError("D1 only")
        return max(0.0,float(self.model.predict(self.vec.transform([self._features(r,state)]))[0]))
    def package(self):
        return {
            "candidate":self.candidate,"horizon":self.horizon,"fit_n":self.fit_n,
            "bayes_params":BAYES_PARAMS,"scalers":{k:v.package() for k,v in self.scalers.items()},
            "features":self.vec.get_feature_names_out().tolist(),"coef":self.model.coef_.tolist(),
            "intercept":float(self.model.intercept_), "alpha_":float(self.model.alpha_),"lambda_":float(self.model.lambda_),
            "sigma_diag":np.diag(self.model.sigma_).tolist()
        }


def fit_state_layers(train, horizon):
    if horizon==2:
        st=train[train.horizon.isin([1,2])].copy()
    else:
        st=train[train.horizon==3].copy()
    return {"qb":ProbLayer(add_c=True).fit(st), "nonqb":ProbLayer(add_c=False).fit(st)}


def state_probs(layers,r):
    return (layers["qb"] if r.position=="QB" else layers["nonqb"]).predict(r)


def fit_candidates(train,horizon):
    return ProductionModel("D0",horizon).fit(train), ProductionModel("D1",horizon).fit(train)


def predict_row(r,layers,d0,d1):
    probs=state_probs(layers,r)
    active=d0.predict_active(r)
    p_active=1-probs["out"]
    d0_pts=p_active*active
    means={s:d1.predict_state(r,s) for s in POSITIVE_STATES}
    d1_pts=sum(probs[s]*means[s] for s in POSITIVE_STATES)
    rec={
        "source_season":int(r.source_season),"player_id":str(r.player_id),"position":str(r.position),
        "horizon":int(r.horizon),"age":float(r.age),"experience":int(r.experience),
        "career_stage":str(r.career_stage),"source_state":str(r.source_state),
        "source_points":float(r.source_points),"source_percentile":float(r.source_percentile),
        "target_points":float(r.target_points),"target_state":str(r.target_state),
        "target_present":int(r.target_present),"role_loss":None if pd.isna(r.role_loss) else int(r.role_loss),
        "deep_collapse":int(r.deep_collapse),"top10":int(r.top10),"top5":int(r.top5),
        "age_le25":int(r.age_le25),"prime_established":int(r.prime_established),
        "p_active":float(p_active),"pred_D0":float(d0_pts),"pred_D1":float(d1_pts),
        "active_D0":float(active),
    }
    for s in STATES: rec[f"p_{s}"]=float(probs[s])
    for s in POSITIVE_STATES: rec[f"d1_mean_{s}"]=float(means[s])
    return rec


def rolling_predictions(rows: pd.DataFrame, seasons=range(2014,2023)):
    allrec=[]
    fitlog=[]
    for t in seasons:
        for h in (2,3):
            if h==2:
                train=rows[(rows.source_season<t)&(rows.source_season+rows.horizon<=t-1)&(rows.horizon.isin([1,2]))].copy()
                prod_train=rows[(rows.source_season<t)&(rows.source_season+2<=t-1)&(rows.horizon==2)].copy()
            else:
                train=rows[(rows.source_season<t)&(rows.source_season+3<=t-1)&(rows.horizon==3)].copy()
                prod_train=train.copy()
            test=rows[(rows.source_season==t)&(rows.horizon==h)].copy()
            if test.empty: continue
            layers=fit_state_layers(train,h)
            d0,d1=fit_candidates(prod_train,h)
            for r in test.itertuples():
                allrec.append(predict_row(r,layers,d0,d1))
            fitlog.append({"source_season":t,"horizon":h,"state_train_n":len(train),
                           "prod_train_n":len(prod_train),"d0_fit_n":d0.fit_n,"d1_fit_n":d1.fit_n})
    return pd.DataFrame(allrec),fitlog


def mae_bias(g,pred):
    e=g[pred]-g.target_points
    return {"n":int(len(g)),"mae":float(np.abs(e).mean()),"bias":float(e.mean()),
            "over_rate":float((e>0).mean()),"under_rate":float((e<0).mean())}


def paired_gain(g,a="pred_D0",b="pred_D1"):
    return float((np.abs(g[a]-g.target_points)-np.abs(g[b]-g.target_points)).mean())


def bootstrap_gain(g,a="pred_D0",b="pred_D1",reps=5000,seed=BOOTSTRAP_SEED):
    d=(np.abs(g[a]-g.target_points)-np.abs(g[b]-g.target_points)).to_numpy(float)
    seasons=g.source_season.astype(str).to_numpy(); players=g.player_id.astype(str).to_numpy()
    us=np.unique(seasons); up=np.unique(players); rng=np.random.default_rng(seed); vals=[]
    si={v:i for i,v in enumerate(us)}; pi={v:i for i,v in enumerate(up)}
    sidx=np.array([si[x] for x in seasons]); pidx=np.array([pi[x] for x in players])
    for _ in range(reps):
        ws=rng.exponential(1.0,len(us)); wp=rng.exponential(1.0,len(up)); w=ws[sidx]*wp[pidx]
        vals.append(float(np.sum(w*d)/np.sum(w)))
    q=np.quantile(vals,[0.025,0.975])
    return {"mean_gain":float(d.mean()),"ci95":[float(q[0]),float(q[1])],"reps":reps,"seed":seed}


def block_mask(df,name):
    lo,hi=BLOCKS[name]
    return df.source_season.between(lo,hi)


def route_selection(pred: pd.DataFrame):
    selection={}
    for h in (2,3):
        x=pred[(pred.horizon==h)&pred.source_season.between(2014,2020)].copy()
        blocks={b:paired_gain(x[block_mask(x,b)]) for b in BLOCKS}
        universal="D1" if all(v>0 for v in blocks.values()) else "D0"
        posroute={}
        posevidence={}
        for p in POSITIONS:
            g=x[x.position==p]
            counts={b:int(len(g[block_mask(g,b)])) for b in BLOCKS}
            seasons=int(g.source_season.nunique())
            gains={b:paired_gain(g[block_mask(g,b)]) if counts[b] else None for b in BLOCKS}
            eligible=all(counts[b]>=20 for b in BLOCKS) and seasons>=4
            use=eligible and all(gains[b] is not None and gains[b]>0 for b in BLOCKS)
            posroute[p]="D1" if use else "D0"
            posevidence[p]={"counts":counts,"seasons":seasons,"gains":gains,"eligible":eligible}
        x["pred_position_route"]=[r.pred_D1 if posroute[r.position]=="D1" else r.pred_D0 for r in x.itertuples()]
        basecol="pred_D1" if universal=="D1" else "pred_D0"
        pos_agg={b:float((np.abs(x.loc[block_mask(x,b),basecol]-x.loc[block_mask(x,b),"target_points"])-
                          np.abs(x.loc[block_mask(x,b),"pred_position_route"]-x.loc[block_mask(x,b),"target_points"])).mean()) for b in BLOCKS}
        pos_advance=all(v>=0 for v in pos_agg.values()) and any(v>0 for v in pos_agg.values())
        if not pos_advance:
            posroute={p:universal for p in POSITIONS}

        careerroute={}
        carevidence={}
        for p in POSITIONS:
            for cs in ("developmental","established","veteran"):
                g=x[(x.position==p)&(x.career_stage==cs)]
                counts={b:int(len(g[block_mask(g,b)])) for b in BLOCKS}
                seasons=int(g.source_season.nunique())
                gains={b:paired_gain(g[block_mask(g,b)]) if counts[b] else None for b in BLOCKS}
                eligible=all(counts[b]>=20 for b in BLOCKS) and seasons>=4
                use=eligible and all(gains[b] is not None and gains[b]>0 for b in BLOCKS)
                careerroute[f"{p}|{cs}"]="D1" if use else "D0"
                carevidence[f"{p}|{cs}"]={"counts":counts,"seasons":seasons,"gains":gains,"eligible":eligible}
        def pp(r):
            return r.pred_D1 if posroute[r.position]=="D1" else r.pred_D0
        def pc(r):
            return r.pred_D1 if careerroute[f"{r.position}|{r.career_stage}"]=="D1" else r.pred_D0
        x["pred_pos"]= [pp(r) for r in x.itertuples()]
        x["pred_career"]=[pc(r) for r in x.itertuples()]
        car_agg={b:float((np.abs(x.loc[block_mask(x,b),"pred_pos"]-x.loc[block_mask(x,b),"target_points"])-
                          np.abs(x.loc[block_mask(x,b),"pred_career"]-x.loc[block_mask(x,b),"target_points"])).mean()) for b in BLOCKS}
        car_advance=all(v>=0 for v in car_agg.values()) and any(v>0 for v in car_agg.values())
        effective_tie=all(abs(v)<0.05 for v in car_agg.values())
        if not car_advance or effective_tie:
            final_kind="position" if pos_advance else "universal"
            final_route={f"{p}|{cs}":posroute[p] for p in POSITIONS for cs in ("developmental","established","veteran")}
        else:
            final_kind="position_x_career"
            final_route=careerroute
        selection[str(h)]={
            "universal_evidence":blocks,"universal":universal,
            "position_evidence":posevidence,"position_aggregate_gain_vs_universal":pos_agg,
            "position_advance":pos_advance,"position_route":posroute,
            "career_evidence":carevidence,"career_aggregate_gain_vs_position":car_agg,
            "career_advance":car_advance,"career_effective_tie":effective_tie,
            "selected_kind":final_kind,"selected_route":final_route
        }
    return selection


def routed_pred(r,sel):
    c=sel[str(int(r.horizon))]["selected_route"][f"{r.position}|{r.career_stage}"]
    return r.pred_D1 if c=="D1" else r.pred_D0


def scorecard(pred,selection):
    out={"overall":{},"chronological":{},"cohorts":{},"uncertainty":{},"state_calibration":{}}
    for h in (2,3):
        x=pred[(pred.horizon==h)&pred.source_season.between(2014,2020)].copy()
        x["pred_route"]=[routed_pred(r,selection) for r in x.itertuples()]
        out["overall"][str(h)]={c:mae_bias(x,c) for c in ("pred_D0","pred_D1","pred_route")}
        out["uncertainty"][str(h)]={
            "D0_to_D1":bootstrap_gain(x),
            "D0_to_route":bootstrap_gain(x,a="pred_D0",b="pred_route")
        }
        out["chronological"][str(h)]={}
        for b in BLOCKS:
            g=x[block_mask(x,b)]
            out["chronological"][str(h)][b]={c:mae_bias(g,c) for c in ("pred_D0","pred_D1","pred_route")}
        cohorts={
            "top10":x.top10==1,"top5":x.top5==1,"age_le25":x.age_le25==1,
            "developmental":x.career_stage=="developmental","established":x.career_stage=="established",
            "veteran":x.career_stage=="veteran","prime_established":x.prime_established==1,
            "role_loss":x.role_loss==1,"deep_collapse":x.deep_collapse==1
        }
        out["cohorts"][str(h)]={}
        for name,mask in cohorts.items():
            g=x[mask]
            out["cohorts"][str(h)][name]={c:mae_bias(g,c) for c in ("pred_D0","pred_D1","pred_route")} if len(g) else {"n":0}
        y=(x.target_state!="out").astype(float).to_numpy()
        pa=x.p_active.to_numpy(float); eps=1e-12
        probs=x[[f"p_{s}" for s in STATES]].to_numpy(float)
        Y=np.zeros_like(probs)
        for i,s in enumerate(x.target_state): Y[i,STATE_RANK[s]]=1
        out["state_calibration"][str(h)]={
            "persistence_brier":float(np.mean((pa-y)**2)),
            "persistence_logloss":float(-np.mean(y*np.log(np.clip(pa,eps,1-eps))+(1-y)*np.log(np.clip(1-pa,eps,1-eps)))),
            "state_brier":float(np.mean(np.sum((probs-Y)**2,axis=1))),
            "state_logloss":float(-np.mean(np.log(np.clip(probs[np.arange(len(x)),[STATE_RANK[s] for s in x.target_state]],eps,1))))
        }
    return out


def final_fit(rows,selection):
    pkg={"schema_version":"fsffl-redeveloped-forecast-fit-v1","selection":selection,
         "environment":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"sklearn":sklearn.__version__},
         "horizons":{}}
    for h,maxs in ((2,2023),(3,2022)):
        if h==2:
            state_train=rows[(rows.source_season<=maxs)&(rows.horizon.isin([1,2]))&(rows.source_season+rows.horizon<=2025)].copy()
            prod_train=rows[(rows.source_season<=maxs)&(rows.horizon==2)&(rows.source_season+2<=2025)].copy()
        else:
            state_train=rows[(rows.source_season<=maxs)&(rows.horizon==3)&(rows.source_season+3<=2025)].copy()
            prod_train=state_train.copy()
        layers=fit_state_layers(state_train,h); d0,d1=fit_candidates(prod_train,h)
        pkg["horizons"][str(h)]={
            "max_source_season":maxs,"state_train_n":int(len(state_train)),"prod_train_n":int(len(prod_train)),
            "state_qb":layers["qb"].package(),"state_nonqb":layers["nonqb"].package(),
            "D0":d0.package(),"D1":d1.package()
        }
    return pkg


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=["parity","historical","final-fit"])
    ap.add_argument("--panel",required=True); ap.add_argument("--q3",required=True)
    ap.add_argument("--outdir",required=True); ap.add_argument("--selection")
    args=ap.parse_args()
    out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)
    panel=pd.read_csv(args.panel); q3=pd.read_csv(args.q3)
    rows=build_rows(panel,2023)
    parity=parity_check(rows,q3)
    (out/"SOURCE_RECONSTRUCTION_PARITY.json").write_text(json.dumps(parity,indent=2,allow_nan=False))
    if not parity["pass"]:
        raise SystemExit("source reconstruction parity failure")
    if args.mode=="parity":
        print(json.dumps(parity,indent=2)); return
    if args.mode=="historical":
        pred,fitlog=rolling_predictions(rows,range(2014,2023))
        sel=route_selection(pred)
        sc=scorecard(pred,sel)
        pred.to_csv(out/"historical_predictions.csv",index=False)
        (out/"FIT_LOG.json").write_text(json.dumps(fitlog,indent=2,allow_nan=False))
        (out/"ROUTING_SELECTION.json").write_text(json.dumps(sel,indent=2,allow_nan=False))
        (out/"HISTORICAL_SCORECARD.json").write_text(json.dumps(sc,indent=2,allow_nan=False))
        print(json.dumps({"parity":parity,"selection":sel,"scorecard":sc},indent=2)); return
    if args.mode=="final-fit":
        if not args.selection: raise SystemExit("--selection required")
        sel=json.loads(Path(args.selection).read_text())
        pkg=final_fit(rows,sel)
        raw=json.dumps(pkg,indent=2,sort_keys=True,allow_nan=False)+"\n"
        (out/"FINAL_FITTED_PACKAGE.json").write_text(raw)
        print(json.dumps({"package_sha256":hashlib.sha256(raw.encode()).hexdigest(),
                          "horizons":{k:{"state_train_n":v["state_train_n"],"prod_train_n":v["prod_train_n"]} for k,v in pkg["horizons"].items()}},indent=2))

if __name__=="__main__":
    main()

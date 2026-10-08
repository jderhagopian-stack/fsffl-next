from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

POSITIONS = ("QB", "RB", "WR", "TE")
DEV_SEASONS = tuple(range(2005, 2017))
HOLDOUT_SEASONS = tuple(range(2017, 2023))
MIN_CELL_N = 30
MIN_CELL_SURVIVORS = 15
MIN_PARENT_N = 100
MIN_PARENT_SURVIVORS = 50
FAMILY_MIN_OVERALL_GAIN = 0.005
FAMILY_MIN_QB_GAIN = 0.01
FAMILY_MAX_POSITION_HARM = 0.03
Y2_GAIN_GATE = 0.02
CUMULATIVE_GAIN_GATE = 0.03
FOLD_WIN_GATE = 0.60
MAX_FOLD_HARM = 0.10
QB_CARRY_TOLERANCE = 0.02
ELITE_QB_BOUNDED_GAIN = 0.10
NON_QB_HARM_TOLERANCE = 0.05
SURVIVAL_BRIER_GATE = 0.25
UNCERTAINTY_LOW = 0.70
UNCERTAINTY_HIGH = 0.90
Z80 = 1.2815515655446004

FAMILIES = {
    "pedigree": ("draft_pick_pct", "undrafted"),
    "availability": ("games_pct", "games_mean_2"),
    "role": ("opportunity_pct", "role_mean_2", "role_vol_2", "qb_established_starter_seasons"),
    "efficiency": ("efficiency",),
    "qb_mobility": ("qb_rush_share",),
}

STATS_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_{season}.csv"
PLAYERS_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"


@dataclass(frozen=True)
class Row:
    player_id: str
    season: int
    position: str
    current: float
    nxt: float
    survived: bool
    age: int | None
    experience: int
    percentile: float
    features: dict[str, float]


@dataclass(frozen=True)
class State:
    player_id: str
    position: str
    mean: float
    sd: float
    age: int | None
    experience: int
    percentile: float
    features: dict[str, float]


def safe_float(value, default=0.0):
    try:
        if value in (None, "", "NA", "NaN", "nan"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def rank_percentiles(values: list[float]) -> list[float]:
    if not values:
        return []
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = (i + j - 1) / 2.0
        for k in range(i, j):
            ranks[order[k]] = r
        i = j
    n = len(values)
    return [(r + 0.5) / n for r in ranks]


def download(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "FSFFL-NEXT-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as src, path.open("wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
    return path


def load_player_metadata(cache: Path) -> dict[str, dict[str, float]]:
    path = download(PLAYERS_URL, cache / "players.csv")
    out = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            pid = raw.get("gsis_id") or raw.get("player_id") or ""
            if not pid:
                continue
            pick = safe_float(raw.get("draft_number") or raw.get("draft_pick") or raw.get("draft_overall"), 0.0)
            rnd = safe_float(raw.get("draft_round"), 0.0)
            undrafted = 1.0 if pick <= 0 and rnd <= 0 else 0.0
            if pick <= 0 and rnd > 0:
                pick = min(260.0, (rnd - 1.0) * 32.0 + 16.0)
            pick_pct = 0.0 if undrafted else max(0.0, min(1.0, 1.0 - (pick - 1.0) / 259.0))
            out[pid] = {"draft_pick_pct": pick_pct, "undrafted": undrafted}
    return out


def load_season_stats(seasons: list[int], cache: Path) -> dict[tuple[str, int], dict[str, float]]:
    records: dict[tuple[str, int], dict[str, float]] = {}
    by_pos_season: dict[tuple[int, str], list[tuple[str, float]]] = defaultdict(list)
    season_max_games: dict[int, float] = defaultdict(float)
    for season in seasons:
        path = download(STATS_URL.format(season=season), cache / f"stats_player_reg_{season}.csv")
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                pid = raw.get("player_id") or raw.get("gsis_id") or ""
                pos = raw.get("position") or raw.get("position_group") or ""
                if not pid or pos not in POSITIONS:
                    continue
                games = safe_float(raw.get("games"), 0.0)
                attempts = safe_float(raw.get("attempts"), 0.0)
                carries = safe_float(raw.get("carries"), 0.0)
                targets = safe_float(raw.get("targets"), 0.0)
                pass_yards = safe_float(raw.get("passing_yards"), 0.0)
                rush_yards = safe_float(raw.get("rushing_yards"), 0.0)
                rec_yards = safe_float(raw.get("receiving_yards"), 0.0)
                if pos == "QB":
                    opp = attempts
                elif pos == "RB":
                    opp = carries + targets
                else:
                    opp = targets
                if games <= 0 and opp > 0:
                    games = 1.0
                rec = {
                    "games": games,
                    "attempts": attempts,
                    "carries": carries,
                    "targets": targets,
                    "passing_yards": pass_yards,
                    "rushing_yards": rush_yards,
                    "receiving_yards": rec_yards,
                    "opportunity": opp,
                    "position": pos,
                }
                records[(pid, season)] = rec
                by_pos_season[(season, pos)].append((pid, opp))
                season_max_games[season] = max(season_max_games[season], games)
    for (season, pos), items in by_pos_season.items():
        pcts = rank_percentiles([v for _, v in items])
        for (pid, _), pct in zip(items, pcts):
            records[(pid, season)]["opportunity_pct"] = pct
    for (pid, season), rec in records.items():
        max_games = season_max_games.get(season, 0.0)
        rec["games_pct"] = rec["games"] / max_games if max_games > 0 else 0.0
    return records


def build_features(panel_path: Path, cache: Path, output_dir: Path) -> list[Row]:
    base = []
    with panel_path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            pos = raw["position"]
            cur = safe_float(raw["fantasy_points"])
            if pos not in POSITIONS or cur <= 0:
                continue
            base.append(raw)
    seasons = sorted({int(r["season"]) for r in base})
    stats = load_season_stats(seasons, cache)
    players = load_player_metadata(cache)

    historical_role: dict[str, list[tuple[int, float, float, bool]]] = defaultdict(list)
    features_by_key: dict[tuple[str, int], dict[str, float]] = {}
    by_season_pos: dict[tuple[int, str], list[tuple[str, float]]] = defaultdict(list)

    for raw in sorted(base, key=lambda r: (int(r["season"]), r["player_id"])):
        pid = raw["player_id"]
        season = int(raw["season"])
        pos = raw["position"]
        rec = stats.get((pid, season), {})
        opp_pct = safe_float(rec.get("opportunity_pct"), 0.0)
        games_pct = safe_float(rec.get("games_pct"), 0.0)
        history = historical_role[pid]
        prior = [x for x in history if x[0] < season]
        recent = prior[-1:] if prior else []
        role_mean_2 = statistics.mean([opp_pct] + [x[1] for x in recent]) if recent else opp_pct
        games_mean_2 = statistics.mean([games_pct] + [x[2] for x in recent]) if recent else games_pct
        role_vol_2 = abs(opp_pct - recent[-1][1]) if recent else 0.0
        if pos == "QB":
            ranked = sorted(
                ((k[0], v.get("attempts", 0.0)) for k, v in stats.items() if k[1] == season and v.get("position") == "QB"),
                key=lambda x: (-x[1], x[0]),
            )
            top32 = {p for p, _ in ranked[:32]}
            established_now = pid in top32 and safe_float(rec.get("attempts")) > 0
        else:
            established_now = False
        established_count = sum(1 for _, _, _, est in prior if est) + (1 if established_now else 0)
        opportunity = max(1.0, safe_float(rec.get("opportunity"), 0.0))
        current_points = safe_float(raw["fantasy_points"])
        efficiency = current_points / opportunity
        pass_yards = safe_float(rec.get("passing_yards"), 0.0)
        rush_yards = safe_float(rec.get("rushing_yards"), 0.0)
        qb_rush_share = rush_yards / (abs(pass_yards) + abs(rush_yards)) if pos == "QB" and (pass_yards or rush_yards) else 0.0
        meta = players.get(pid, {"draft_pick_pct": 0.0, "undrafted": 1.0})
        feat = {
            "draft_pick_pct": meta["draft_pick_pct"],
            "undrafted": meta["undrafted"],
            "games_pct": games_pct,
            "games_mean_2": games_mean_2,
            "opportunity_pct": opp_pct,
            "role_mean_2": role_mean_2,
            "role_vol_2": role_vol_2,
            "efficiency": efficiency,
            "qb_rush_share": qb_rush_share,
            "qb_established_starter_seasons": float(established_count),
        }
        features_by_key[(pid, season)] = feat
        historical_role[pid].append((season, opp_pct, games_pct, established_now))
        by_season_pos[(season, pos)].append((pid, current_points))

    percentile_by_key = {}
    for (season, pos), items in by_season_pos.items():
        pcts = rank_percentiles([v for _, v in items])
        for (pid, _), pct in zip(items, pcts):
            percentile_by_key[(pid, season)] = pct

    rows = []
    for raw in base:
        pid = raw["player_id"]
        season = int(raw["season"])
        feat = features_by_key.get((pid, season))
        if feat is None:
            continue
        rows.append(Row(
            player_id=pid,
            season=season,
            position=raw["position"],
            current=safe_float(raw["fantasy_points"]),
            nxt=safe_float(raw["next_fantasy_points"]),
            survived=str(raw["survived_next_season"]).strip().lower() in {"true", "1", "t", "yes"},
            age=int(raw["age_year_floor"]) if raw.get("age_year_floor") not in (None, "") else None,
            experience=int(float(raw["experience_years"])),
            percentile=percentile_by_key.get((pid, season), safe_float(raw.get("prior_production_percentile"), 0.5)),
            features=feat,
        ))

    derived = output_dir / "career_persistence_derived_features.csv"
    with derived.open("w", newline="", encoding="utf-8") as handle:
        fields = ["player_id", "season", "position"] + sorted(next(iter(features_by_key.values())).keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"player_id": row.player_id, "season": row.season, "position": row.position, **row.features})
    return rows


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    idx = (len(arr) - 1) * q
    lo = int(math.floor(idx)); hi = int(math.ceil(idx))
    if lo == hi:
        return arr[lo]
    return arr[lo] * (hi - idx) + arr[hi] * (idx - lo)


class Calibration:
    def __init__(self, training: list[Row], features: tuple[str, ...]):
        self.training = training
        self.features = features
        self.parent = {}
        self.cells = {}
        self.bounds = {}
        self.ceilings = {}
        self.scalers = {}
        self.prod_beta = {}
        self.surv_beta = {}
        for pos in POSITIONS:
            rs = [r for r in training if r.position == pos]
            surv = [r for r in rs if r.survived and r.current > 0]
            multipliers = [r.nxt / r.current for r in surv]
            self.bounds[pos] = (percentile(multipliers, 0.05), percentile(multipliers, 0.95)) if multipliers else (0.0, 2.0)
            self.ceilings[pos] = percentile([r.current for r in rs], 0.99)
            self.parent[pos] = self._fit_evidence(rs)
            groups = defaultdict(list)
            for r in rs:
                q = min(4, max(1, int(r.percentile * 4) + 1))
                groups[(r.age, r.experience, q, r.experience == 0)].append(r)
            for key, gr in groups.items():
                ev = self._fit_evidence(gr)
                if ev["n"] >= MIN_CELL_N and ev["survivors"] >= MIN_CELL_SURVIVORS:
                    self.cells[(pos, *key)] = ev
            self._fit_enrichment(pos, rs)

    def _fit_evidence(self, rs: list[Row]):
        surv = [r for r in rs if r.survived and r.current > 0]
        mult = [r.nxt / r.current for r in surv]
        p = sum(r.survived for r in rs) / len(rs) if rs else 0.0
        m = statistics.mean(mult) if mult else 1.0
        sd = statistics.pstdev(mult) if len(mult) > 1 else 0.0
        return {"n": len(rs), "survivors": len(surv), "survival": p, "multiplier": m, "dispersion": sd}

    def evidence(self, row_or_state):
        pos = row_or_state.position
        q = min(4, max(1, int(row_or_state.percentile * 4) + 1))
        key = (pos, row_or_state.age, row_or_state.experience, q, row_or_state.experience == 0)
        ev = self.cells.get(key)
        parent = self.parent.get(pos, {"n": 0, "survivors": 0, "survival": 0.0, "multiplier": 1.0, "dispersion": 0.0})
        if ev is None:
            ev = parent
        return ev

    def _x(self, features: dict[str, float], pos: str) -> np.ndarray:
        means, sds = self.scalers[pos]
        vals = []
        for i, name in enumerate(self.features):
            raw = float(features.get(name, 0.0))
            vals.append((raw - means[i]) / sds[i] if sds[i] > 1e-9 else 0.0)
        return np.array([1.0, *vals], dtype=float)

    def _fit_enrichment(self, pos: str, rs: list[Row]):
        if not self.features:
            self.scalers[pos] = ([], [])
            self.prod_beta[pos] = np.zeros(1)
            self.surv_beta[pos] = np.zeros(1)
            return
        means = [statistics.mean([r.features.get(f, 0.0) for r in rs]) if rs else 0.0 for f in self.features]
        sds = [statistics.pstdev([r.features.get(f, 0.0) for r in rs]) if len(rs) > 1 else 1.0 for f in self.features]
        self.scalers[pos] = (means, sds)
        Xp=[]; yp=[]; Xs=[]; ys=[]
        for r in rs:
            ev = self.evidence(r)
            x = self._x(r.features, pos)
            Xs.append(x); ys.append((1.0 if r.survived else 0.0) - ev["survival"])
            if r.survived and r.current > 0:
                Xp.append(x); yp.append(r.nxt / r.current - ev["multiplier"])
        self.prod_beta[pos] = np.linalg.lstsq(np.vstack(Xp), np.array(yp), rcond=None)[0] if len(Xp) >= len(self.features)+5 else np.zeros(len(self.features)+1)
        self.surv_beta[pos] = np.linalg.lstsq(np.vstack(Xs), np.array(ys), rcond=None)[0] if len(Xs) >= len(self.features)+5 else np.zeros(len(self.features)+1)

    def predict_params(self, state: State, enriched: bool):
        ev = self.evidence(state)
        multiplier = ev["multiplier"]
        survival = ev["survival"]
        if enriched and self.features:
            x = self._x(state.features, state.position)
            multiplier += float(x @ self.prod_beta[state.position])
            survival += float(x @ self.surv_beta[state.position])
        lo, hi = self.bounds[state.position]
        multiplier = max(lo, min(hi, multiplier))
        survival = max(0.0, min(1.0, survival))
        return multiplier, survival, ev["dispersion"]


def assign_percentiles(states: list[State]) -> list[State]:
    out=[]
    by_pos=defaultdict(list)
    for s in states: by_pos[s.position].append(s)
    for pos, items in by_pos.items():
        pcts=rank_percentiles([s.mean for s in items])
        out.extend(replace(s, percentile=p) for s,p in zip(items,pcts))
    return out


def step(state: State, cal: Calibration, enriched: bool) -> State:
    mult, survival, dispersion = cal.predict_params(state, enriched)
    conditional = state.mean * mult
    ceiling = max(state.mean, cal.ceilings[state.position])
    conditional = max(0.0, min(ceiling, conditional))
    next_mean = survival * conditional
    conditional_sd = state.mean * dispersion
    var = survival * conditional_sd**2 + survival * (1.0-survival) * conditional**2 + (survival*mult*state.sd)**2
    return State(state.player_id, state.position, next_mean, math.sqrt(max(0.0,var)), None if state.age is None else state.age+1, state.experience+1, state.percentile, state.features)


def realized_map(rows: list[Row]) -> dict[tuple[str,int], float]:
    return {(r.player_id,r.season): r.current for r in rows}


def fold_predictions(rows: list[Row], source_season: int, features: tuple[str,...], enriched: bool):
    training=[r for r in rows if r.season <= source_season-1]
    cal=Calibration(training, features)
    source=[r for r in rows if r.season == source_season]
    states=[State(r.player_id,r.position,r.current,0.0,r.age,r.experience,r.percentile,r.features) for r in source]
    states=assign_percentiles(states)
    y2=assign_percentiles([step(s,cal,enriched) for s in states])
    y3=assign_percentiles([step(s,cal,enriched) for s in y2])
    return cal, states, y2, y3


def mae(items):
    return statistics.mean([abs(a-b) for a,b in items]) if items else math.nan


def brier(items):
    return statistics.mean([(p-y)**2 for p,y in items]) if items else math.nan


def evaluate(rows: list[Row], seasons: tuple[int,...], features: tuple[str,...], enriched: bool):
    realized=realized_map(rows)
    totals=defaultdict(list); pos=defaultdict(lambda:defaultdict(list)); fold_metrics=[]
    coverage={"y2":[],"y3":[]}; survival_items={"y2":[],"y3":[]}; explosion=0
    elite_items=[]
    for season in seasons:
        cal, source, y2, y3=fold_predictions(rows,season,features,enriched)
        byid2={s.player_id:s for s in y2}; byid3={s.player_id:s for s in y3}; src={s.player_id:s for s in source}
        fold_pairs=[]
        qb_source=sorted([s for s in source if s.position=="QB"], key=lambda s:(s.mean,s.player_id))
        elite_cut=percentile([s.mean for s in qb_source],0.75) if qb_source else math.inf
        for pid,s0 in src.items():
            s2=byid2.get(pid); s3=byid3.get(pid)
            if s2 is None or s3 is None: continue
            r2=realized.get((pid,season+1),0.0); r3=realized.get((pid,season+2),0.0)
            pairs=[(s2.mean,r2),(s3.mean,r3)]
            totals["y2"].append(pairs[0]); totals["y3"].append(pairs[1]); totals["cum"].append((s2.mean+s3.mean,r2+r3));
            pos[s0.position]["y2"].append(pairs[0]); pos[s0.position]["y3"].append(pairs[1]); pos[s0.position]["cum"].append((s2.mean+s3.mean,r2+r3))
            fold_pairs.append((s2.mean+s3.mean,r2+r3))
            if s0.position=="QB" and s0.mean>=elite_cut: elite_items.append((s2.mean+s3.mean,r2+r3))
            coverage["y2"].append(abs(r2-s2.mean) <= Z80*s2.sd if s2.sd>0 else r2==s2.mean)
            coverage["y3"].append(abs(r3-s3.mean) <= Z80*s3.sd if s3.sd>0 else r3==s3.mean)
            # Survival here is probability of any next-season production; use expected-state decomposition p ~= mean/conditional.
            m2,p2,_=cal.predict_params(s0,enriched); m3,p3,_=cal.predict_params(s2,enriched)
            survival_items["y2"].append((p2,1.0 if r2>0 else 0.0)); survival_items["y3"].append((p3,1.0 if r3>0 else 0.0))
            if s2.mean>max(s0.mean,cal.ceilings[s0.position])+1e-9 or s3.mean>max(s2.mean,cal.ceilings[s0.position])+1e-9: explosion+=1
        fold_metrics.append({"season":season,"cumulative_mae":mae(fold_pairs),"n":len(fold_pairs)})
    return {
        "n":len(totals["y2"]),
        "y2_mae":mae(totals["y2"]),"y3_mae":mae(totals["y3"]),"cumulative_mae":mae(totals["cum"]),
        "positions":{p:{h:mae(pos[p][h]) for h in ("y2","y3","cum")} for p in POSITIONS},
        "elite_qb_cumulative_mae":mae(elite_items),"elite_qb_n":len(elite_items),
        "coverage_y2":statistics.mean(coverage["y2"]) if coverage["y2"] else math.nan,
        "coverage_y3":statistics.mean(coverage["y3"]) if coverage["y3"] else math.nan,
        "survival_brier_y2":brier(survival_items["y2"]),"survival_brier_y3":brier(survival_items["y3"]),
        "explosions":explosion,"folds":fold_metrics,
    }


def evaluate_carry(rows: list[Row], seasons: tuple[int,...]):
    realized=realized_map(rows); totals=defaultdict(list); pos=defaultdict(lambda:defaultdict(list)); elite=[]; folds=[]
    for season in seasons:
        source=[r for r in rows if r.season==season]
        qbcut=percentile([r.current for r in source if r.position=="QB"],0.75)
        fp=[]
        for r in source:
            y2=realized.get((r.player_id,season+1),0.0); y3=realized.get((r.player_id,season+2),0.0)
            totals["y2"].append((r.current,y2)); totals["y3"].append((r.current,y3)); totals["cum"].append((2*r.current,y2+y3));
            pos[r.position]["y2"].append((r.current,y2)); pos[r.position]["y3"].append((r.current,y3)); pos[r.position]["cum"].append((2*r.current,y2+y3)); fp.append((2*r.current,y2+y3))
            if r.position=="QB" and r.current>=qbcut: elite.append((2*r.current,y2+y3))
        folds.append({"season":season,"cumulative_mae":mae(fp),"n":len(fp)})
    return {"n":len(totals["y2"]),"y2_mae":mae(totals["y2"]),"y3_mae":mae(totals["y3"]),"cumulative_mae":mae(totals["cum"]),"positions":{p:{h:mae(pos[p][h]) for h in ("y2","y3","cum")} for p in POSITIONS},"elite_qb_cumulative_mae":mae(elite),"elite_qb_n":len(elite),"folds":folds}


def rel_gain(base,cand): return (base-cand)/base if base and math.isfinite(base) else math.nan


def select_families(rows: list[Row]):
    base=evaluate(rows,DEV_SEASONS,(),False)
    accepted=[]; diagnostics={}
    for fam,names in FAMILIES.items():
        cand=evaluate(rows,DEV_SEASONS,names,True)
        overall=rel_gain(base["cumulative_mae"],cand["cumulative_mae"])
        qb=rel_gain(base["positions"]["QB"]["cum"],cand["positions"]["QB"]["cum"])
        harms=[]
        for p in POSITIONS:
            b=base["positions"][p]["cum"]; c=cand["positions"][p]["cum"]
            harms.append((c-b)/b if b else 0.0)
        useful=(overall>=FAMILY_MIN_OVERALL_GAIN or qb>=FAMILY_MIN_QB_GAIN) and max(harms)<=FAMILY_MAX_POSITION_HARM
        diagnostics[fam]={"features":names,"overall_cumulative_gain":overall,"qb_cumulative_gain":qb,"max_position_harm":max(harms),"accepted":useful}
        if useful: accepted.append(fam)
    selected=[]
    for fam in accepted:
        for f in FAMILIES[fam]:
            if f not in selected: selected.append(f)
    return tuple(selected),diagnostics,base


def acceptance(carry,bounded,enriched):
    fold_b={x["season"]:x["cumulative_mae"] for x in bounded["folds"]}; fold_e={x["season"]:x["cumulative_mae"] for x in enriched["folds"]}
    wins=[s for s in fold_b if fold_e[s]<fold_b[s]]
    worst=min(((fold_b[s]-fold_e[s])/fold_b[s] for s in fold_b),default=0.0)
    gates={
        "y2_materially_better_than_bounded":rel_gain(bounded["y2_mae"],enriched["y2_mae"])>=Y2_GAIN_GATE,
        "y2_materially_better_than_carry":rel_gain(carry["y2_mae"],enriched["y2_mae"])>=Y2_GAIN_GATE,
        "y3_not_degraded_vs_bounded":enriched["y3_mae"]<=bounded["y3_mae"]*1.01,
        "cumulative_better_than_bounded":rel_gain(bounded["cumulative_mae"],enriched["cumulative_mae"])>=CUMULATIVE_GAIN_GATE,
        "cumulative_better_than_carry":rel_gain(carry["cumulative_mae"],enriched["cumulative_mae"])>=CUMULATIVE_GAIN_GATE,
        "fold_stability":len(wins)/len(fold_b)>=FOLD_WIN_GATE if fold_b else False,
        "worst_fold_guardrail":worst>=-MAX_FOLD_HARM,
        "all_qb_not_materially_worse_than_carry":enriched["positions"]["QB"]["cum"]<=carry["positions"]["QB"]["cum"]*(1+QB_CARRY_TOLERANCE),
        "elite_qb_substantially_better_than_bounded":rel_gain(bounded["elite_qb_cumulative_mae"],enriched["elite_qb_cumulative_mae"])>=ELITE_QB_BOUNDED_GAIN,
        "rb_wr_te_safety":all(enriched["positions"][p]["cum"]<=bounded["positions"][p]["cum"]*(1+NON_QB_HARM_TOLERANCE) for p in ("RB","WR","TE")),
        "uncertainty_y2":UNCERTAINTY_LOW<=enriched["coverage_y2"]<=UNCERTAINTY_HIGH,
        "uncertainty_y3":UNCERTAINTY_LOW<=enriched["coverage_y3"]<=UNCERTAINTY_HIGH,
        "survival_y2":enriched["survival_brier_y2"]<=SURVIVAL_BRIER_GATE and enriched["survival_brier_y2"]<bounded["survival_brier_y2"],
        "survival_y3":enriched["survival_brier_y3"]<=SURVIVAL_BRIER_GATE and enriched["survival_brier_y3"]<bounded["survival_brier_y3"],
        "trajectory_safety":enriched["explosions"]==0,
    }
    return gates,{"fold_win_rate":len(wins)/len(fold_b) if fold_b else 0.0,"worst_fold_relative_improvement":worst}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--career-panel",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True); args=ap.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True); cache=args.output_dir/"career-persistence-cache"
    t0=time.perf_counter(); rows=build_features(args.career_panel,cache,args.output_dir); preprocess=time.perf_counter()-t0
    selected,feature_diag,dev_base=select_families(rows)
    holdout_carry=evaluate_carry(rows,HOLDOUT_SEASONS)
    holdout_bounded=evaluate(rows,HOLDOUT_SEASONS,(),False)
    holdout_enriched=evaluate(rows,HOLDOUT_SEASONS,selected,True)
    gates,stability=acceptance(holdout_carry,holdout_bounded,holdout_enriched)
    derived=args.output_dir/"career_persistence_derived_features.csv"
    t1=time.perf_counter();
    with derived.open("rb") as h: h.read()
    read_latency=time.perf_counter()-t1
    result={
        "status":"PASS" if all(gates.values()) else "FAIL",
        "selected_features":selected,"feature_family_diagnostics":feature_diag,
        "development_baseline":dev_base,"holdout_carry":holdout_carry,"holdout_bounded":holdout_bounded,"holdout_enriched":holdout_enriched,
        "gates":gates,"stability":stability,
        "operations":{"derived_rows":len(rows),"derived_bytes":derived.stat().st_size,"preprocess_seconds":preprocess,"full_table_read_seconds":read_latency,"refresh_cadence":"annual/offline; current-season role refresh may be scheduled after final regular-season stats","live_path":"precomputed compact derived features + versioned coefficients; no raw historical scan"},
        "provenance":{"stats":"nflverse player regular-season stats, CC-BY-4.0 family; direct release files","players":"nflverse players release; derived draft metadata","career_panel":"existing governed PR131 historical panel","contracts":"rejected from v2: historical point-in-time contract reconstruction not required and source terms/provenance are more complex","depth_charts":"rejected from v2: historical source changed after 2024 and long-horizon PIT comparability is weaker","injury_detail":"rejected from v2: availability captured by games played; detailed historical injury provenance/sparsity not needed","starts":"not used directly: stable cross-era player starts field not present in chosen nflverse seasonal source; QB role proxied by top-32 pass-attempt seasons"},
    }
    (args.output_dir/"career_persistence_results.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    lines=["# Career Persistence Feature Layer Research Result","",f"**Decision:** {'PROMOTE ENRICHED FORECAST' if result['status']=='PASS' else 'DO NOT PROMOTE'}","",f"Selected features: {', '.join(selected) if selected else 'none'}.","",f"Derived rows: {len(rows):,}; size: {derived.stat().st_size/1024:.1f} KiB; preprocessing: {preprocess:.2f}s; full-table local read: {read_latency*1000:.2f} ms.","","## Holdout metrics","",f"- Carry: Y2 {holdout_carry['y2_mae']:.3f}, Y3 {holdout_carry['y3_mae']:.3f}, cumulative {holdout_carry['cumulative_mae']:.3f}.",f"- Bounded: Y2 {holdout_bounded['y2_mae']:.3f}, Y3 {holdout_bounded['y3_mae']:.3f}, cumulative {holdout_bounded['cumulative_mae']:.3f}.",f"- Enriched: Y2 {holdout_enriched['y2_mae']:.3f}, Y3 {holdout_enriched['y3_mae']:.3f}, cumulative {holdout_enriched['cumulative_mae']:.3f}.","",f"- QB cumulative: carry {holdout_carry['positions']['QB']['cum']:.3f}; bounded {holdout_bounded['positions']['QB']['cum']:.3f}; enriched {holdout_enriched['positions']['QB']['cum']:.3f}.",f"- Elite-QB cumulative: carry {holdout_carry['elite_qb_cumulative_mae']:.3f}; bounded {holdout_bounded['elite_qb_cumulative_mae']:.3f}; enriched {holdout_enriched['elite_qb_cumulative_mae']:.3f}.",f"- Survival Brier Y2/Y3: {holdout_enriched['survival_brier_y2']:.4f} / {holdout_enriched['survival_brier_y3']:.4f}.",f"- Nominal-80% coverage Y2/Y3: {holdout_enriched['coverage_y2']:.3f} / {holdout_enriched['coverage_y3']:.3f}.",f"- Fold win rate vs bounded: {stability['fold_win_rate']:.3f}.","","## Gates",""]
    lines += [f"- {'PASS' if v else 'FAIL'} — {k}" for k,v in gates.items()]
    lines += ["","## Feature-family selection (development folds only)",""]+[f"- {k}: {'accepted' if v['accepted'] else 'rejected'}; cumulative gain {v['overall_cumulative_gain']:.3%}; QB gain {v['qb_cumulative_gain']:.3%}; max positional harm {v['max_position_harm']:.3%}." for k,v in feature_diag.items()]
    (args.output_dir/"career_persistence_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"selected":selected,"gates":gates,"holdout":{"carry":holdout_carry,"bounded":holdout_bounded,"enriched":holdout_enriched},"operations":result["operations"]},indent=2))

if __name__=="__main__": main()

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import urllib.request
from collections import defaultdict
from pathlib import Path

POS=("QB","RB","WR","TE")
SEASONS=(2021,2022,2023,2024,2025)
HOLDOUT=(2023,2024,2025)
CUTOFFS=tuple(range(0,18))
NFL_GAMES=17.0
Z90=1.6448536269514722
MATERIALITY_FRACTION=0.10
ELIGIBLE_OBSERVED_TIERS=("history_plus_current","history_only","current_only","cold_start")
IDENTITY_LIGHT_RULE="eligible only when canonical offensive position is known/non-conflicting and the matching position/cutoff cold-start population is eligible; uses tier-agnostic position bound"
DATA={
2021:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2021.csv","41915fb49238902ad1f129ebf0405b11a1e710454ae0fe8f7b3e4f9145875f48"),
2022:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2022.csv","ad426c3fe5bf1cc30c3f137fdfe96d054e19d400879ee4413129da49fa7b54be"),
2023:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2023.csv","f19cb71a5de0dce7fd09376026237c9ee9d5a93fe13815a2ea3ec2d37204cb17"),
2024:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2024.csv","3ddc45a84f759aa348ce465ae001752c530575455717657cdfe1f8abfcdb4759"),
2025:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv","e5e0615b3d96a3eaebfaee91e55afb4a4e7fe0caf057454177bcd7d6ad4bcfc2"),
}

def num(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else 0.0
    except Exception:
        return 0.0

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()

def fetch(year:int,cache:Path)->Path:
    cache.mkdir(parents=True,exist_ok=True)
    url,want=DATA[year]
    path=cache/f"stats_player_week_{year}.csv"
    if not path.exists() or digest(path)!=want:
        req=urllib.request.Request(url,headers={"User-Agent":"fsffl-next-research/1.0"})
        with urllib.request.urlopen(req,timeout=180) as response,path.open("wb") as f:
            while True:
                block=response.read(1048576)
                if not block: break
                f.write(block)
    got=digest(path)
    if got!=want:
        raise RuntimeError(f"hash mismatch {year}: {got} != {want}")
    return path

def exact_lost(row,cols):
    parts=("sack_fumbles_lost","rushing_fumbles_lost","receiving_fumbles_lost")
    if all(x in cols for x in parts):
        return sum(num(row.get(x)) for x in parts),"+".join(parts)
    if "fumbles_lost" in cols:
        return num(row.get("fumbles_lost")),"fumbles_lost"
    raise RuntimeError("exact FUMBLES_LOST unavailable")

def opportunity(row,pos):
    sacks=num(row.get("sacks_suffered")) if "sacks_suffered" in row else num(row.get("sacks"))
    if pos=="QB":
        return num(row.get("attempts"))+sacks+num(row.get("carries"))
    return num(row.get("carries"))+num(row.get("receptions"))

def load_season(year:int,cache:Path):
    path=fetch(year,cache)
    players={}
    team_weeks=set()
    semantics=None
    with path.open(newline="",encoding="utf-8") as f:
        rd=csv.DictReader(f); cols=set(rd.fieldnames or [])
        for row in rd:
            if (row.get("season_type") or "REG").upper() not in ("REG","REGULAR"):
                continue
            pos=(row.get("position") or row.get("position_group") or "").upper()
            if pos not in POS: continue
            pid=(row.get("player_id") or row.get("gsis_id") or "").strip()
            if not pid: continue
            week=int(num(row.get("week")))
            if not 1<=week<=18: continue
            team=(row.get("recent_team") or row.get("team") or "").strip()
            if team: team_weeks.add((team,week))
            lost,sem=exact_lost(row,cols)
            semantics=semantics or sem
            if semantics!=sem: raise RuntimeError("inconsistent exact semantics")
            x=players.setdefault((pid,pos),{"weeks":{},"name":row.get("player_display_name") or row.get("player_name") or ""})
            w=x["weeks"].setdefault(week,{"lost":0.0,"opp":0.0})
            w["lost"]+=lost;w["opp"]+=opportunity(row,pos)
    if len({team for team,_ in team_weeks})!=32:
        raise RuntimeError(f"{year}: cannot reconstruct 32-team schedule state")
    rows=[]
    for (pid,pos),x in players.items():
        weeks=x["weeks"]
        rows.append({
            "season":year,"pid":pid,"pos":pos,"name":x["name"],"weeks":weeks,
            "games":len(weeks),"opp":sum(w["opp"] for w in weeks.values()),
            "lost":sum(w["lost"] for w in weeks.values()),
        })
    return rows,team_weeks,{"season":year,"sha256":digest(path),"exact_semantics":semantics,"player_rows":len(rows)}

def history_player_stats(rows_by,year):
    d=defaultdict(lambda:{"games":0,"opp":0.0})
    for y in sorted(rows_by):
        if y>=year: continue
        for r in rows_by[y]:
            x=d[r["pid"]];x["games"]+=r["games"];x["opp"]+=r["opp"]
    return d

def structural_remaining(team_weeks,cutoff):
    if cutoff==0:return NFL_GAMES
    completed=sum(1 for _team,w in team_weeks if w<=cutoff)/32.0
    remain=NFL_GAMES-completed
    if remain<=0:raise RuntimeError(f"cutoff {cutoff}: no remaining regular-season denominator")
    return remain

def target(row,team_weeks,cutoff):
    remain=structural_remaining(team_weeks,cutoff)
    future=sum(v["lost"] for w,v in row["weeks"].items() if w>cutoff)
    return NFL_GAMES*future/remain

def tier(row,prior,cutoff):
    current_games=sum(1 for w in row["weeks"] if w<=cutoff)
    current_opp=sum(v["opp"] for w,v in row["weeks"].items() if w<=cutoff)
    hist=bool(prior and prior["games"])
    cur=bool(current_games or current_opp)
    if hist and cur:return "history_plus_current"
    if hist:return "history_only"
    if cur:return "current_only"
    return "cold_start"

def training_bound(rows_by,team_weeks_by,target_year,cutoff,pos):
    values=[]
    for y in sorted(rows_by):
        if y>=target_year:continue
        values += [target(r,team_weeks_by[y],cutoff) for r in rows_by[y] if r["pos"]==pos]
    if not values:raise RuntimeError("materiality bound has no historical support")
    return {
        "n":len(values),
        "event_bound":max(values),
        "mean":statistics.mean(values),
        "sd":statistics.stdev(values) if len(values)>1 else 0.0,
        "expected_nonparametric_next_draw_coverage":len(values)/(len(values)+1.0),
    }

def writecsv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8");return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--cache-dir",type=Path,default=Path("/tmp/fumbles-lifecycle-cache"))
    ap.add_argument("--rolling-table",type=Path,required=True)
    ap.add_argument("--league-rules",type=Path,required=True)
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)

    rows_by={};team_weeks_by={};lineage=[]
    for y in SEASONS:
        rows,tw,meta=load_season(y,args.cache_dir)
        rows_by[y]=rows;team_weeks_by[y]=tw;lineage.append(meta)

    rolling=json.loads(args.rolling_table.read_text())
    rules=json.loads(args.league_rules.read_text())
    fum_points=None
    for r in rules.get("scoring",[]):
        if r.get("stat")=="fum_lost":
            fum_points=float(r.get("points",0.0));break
    if fum_points is None or fum_points==0:
        raise RuntimeError("league rules must score fum_lost")

    # Historical annual pseudo-rollover validation. Bound is frozen as the
    # prior-season, position-wide historical maximum. It is intentionally
    # independent of player identity/evidence tier.
    heldout=[]
    for year in HOLDOUT:
        prior=history_player_stats(rows_by,year)
        for cutoff in CUTOFFS:
            for pos in POS:
                b=training_bound(rows_by,team_weeks_by,year,cutoff,pos)
                actual_rows=[]
                for row in rows_by[year]:
                    if row["pos"]!=pos:continue
                    t=tier(row,prior.get(row["pid"]),cutoff)
                    actual_rows.append((t,target(row,team_weeks_by[year],cutoff)))
                for label in ("ALL",)+ELIGIBLE_OBSERVED_TIERS:
                    vals=[v for t,v in actual_rows if label=="ALL" or t==label]
                    if not vals:continue
                    heldout.append({
                        "target_year":year,"cutoff":cutoff,"position":pos,"tier":label,
                        "n":len(vals),"training_n":b["n"],"event_bound":b["event_bound"],
                        "max_actual":max(vals),
                        "coverage":sum(v<=b["event_bound"] for v in vals)/len(vals),
                        "exceedances":sum(v>b["event_bound"] for v in vals),
                        "expected_nonparametric_next_draw_coverage":b["expected_nonparametric_next_draw_coverage"],
                    })

    # The first all-population validation exposed one unsupported cell:
    # QB cold-start at Week 13 (8/9, 88.9%). Later QB cold-start samples are
    # even smaller. Do not inflate the bound after seeing that result. Fail
    # closed for the contiguous QB cold-start/identity-light suffix 13-17.
    def tier_eligible(cutoff, pos, tier):
        if tier=="cold_start" and pos=="QB" and cutoff>=13:
            return False
        return True

    # Every eligible observed fallback tier must have >=90% pooled historical
    # coverage at every cutoff/position where it appears.
    pooled=defaultdict(list)
    for row in heldout:
        if row["tier"]=="ALL":continue
        pooled[(row["cutoff"],row["position"],row["tier"])].append(row)
    pooled_rows=[];failures=[]
    for (cutoff,pos,t),parts in sorted(pooled.items()):
        n=sum(int(x["n"]) for x in parts)
        ex=sum(int(x["exceedances"]) for x in parts)
        cov=(n-ex)/n if n else 1.0
        eligible=tier_eligible(cutoff,pos,t)
        rec={"cutoff":cutoff,"position":pos,"tier":t,"n":n,"exceedances":ex,"coverage":cov,"eligible_for_fallback":eligible,"passes_90":cov>=0.90}
        pooled_rows.append(rec)
        if eligible and cov<0.90:failures.append(rec)

    # 2026 production/fallback bound. For Week 2..17, never narrow the
    # previously frozen P1-affected bound: take max(prior bound, all-pop
    # historical maximum). Week 0/1 use omission-only lifecycle and the
    # position-wide historical maximum.
    production=[]
    for cutoff in CUTOFFS:
        for pos in POS:
            b=training_bound(rows_by,team_weeks_by,2026,cutoff,pos)
            old=None
            if cutoff>=2:
                old=float(rolling["cutoffs"][str(cutoff)]["materiality_event_bound_90"][pos])
            event_bound=max(b["event_bound"],old or 0.0)
            score_bound=abs(fum_points)*event_bound
            minimum_sd=score_bound/(MATERIALITY_FRACTION*Z90)
            production.append({
                "target_season":2026,"cutoff":cutoff,"position":pos,
                "historical_training_n":b["n"],
                "historical_max_season_equivalent_events":b["event_bound"],
                "previous_primary_population_bound":old,
                "fallback_event_bound":event_bound,
                "expected_nonparametric_next_draw_coverage":b["expected_nonparametric_next_draw_coverage"],
                "league_points_per_event":fum_points,
                "score_impact_bound":score_bound,
                "minimum_supported_fp_stddev_for_non_material":minimum_sd,
                "eligible_observed_tiers":";".join(ELIGIBLE_OBSERVED_TIERS),
                "cold_start_fallback_eligible":tier_eligible(cutoff,pos,"cold_start"),
                "identity_light_fallback_eligible":tier_eligible(cutoff,pos,"cold_start"),
                "identity_light_rule":IDENTITY_LIGHT_RULE,
            })

    # Early-season focused validation.
    early=[r for r in pooled_rows if r["cutoff"] in (0,1)]
    early_fail=[r for r in early if not r["passes_90"]]

    # These are governed acceptance gates, not report-only diagnostics.
    # A workflow that writes passes=false but exits 0 would be an unsafe false
    # success for the Implementation handoff.
    if failures:
        raise RuntimeError(
            "eligible FUMBLES_LOST fallback population failed 90% coverage gate: "
            + json.dumps(failures, sort_keys=True)
        )
    if early_fail:
        raise RuntimeError(
            "FUMBLES_LOST Week-0/1 lifecycle population gate failed: "
            + json.dumps(early_fail, sort_keys=True)
        )

    result={
        "study":"FUMBLES_LOST materiality population + season-start lifecycle",
        "rolling_model_reopened":False,
        "week2_to_17_table_changed":False,
        "fallback_bound":{
            "formula":"max(position-wide historical maximum season-equivalent target from all completed prior seasons, previously frozen rolling primary-population bound when cutoff>=2)",
            "tier_conditioning":False,
            "observed_tiers_eligible":list(ELIGIBLE_OBSERVED_TIERS),
            "identity_light":IDENTITY_LIGHT_RULE,
            "restriction":"QB cold-start and identity-light fail closed at cutoffs 13-17; all other observed tiers/cutoffs remain eligible subject to the runtime materiality inequality",
            "unknown_or_conflicting_position":"FAIL_CLOSED",
            "minimum_empirical_coverage_gate":0.90,
            "pooled_position_cutoff_tier_failures":failures,
            "passes":not failures,
        },
        "season_start":{
            "week0":"no first-party point estimate; explicit omission; NON_MATERIAL_PARTIAL only if frozen bound test passes",
            "week1":"no first-party point estimate; explicit omission; NON_MATERIAL_PARTIAL only if frozen bound test passes",
            "week2_transition":"enter already-supported Week-2 rolling model; if unavailable, use corrected fallback gate",
            "early_population_failures":early_fail,
            "passes":not early_fail,
        },
        "annual_rollover":{
            "mode":"deterministic annual refresh plus minimal governed freeze",
            "target_year_Y_inputs":"completed governed exact weekly seasons through Y-1 only",
            "position_rates":"recompute cumulative exact lost-fumble/opportunity and opportunity/game rates through Y-1",
            "player_role_priors":"recompute cumulative prior player opportunity/game sufficient statistics through Y-1",
            "calibration":"for each cutoff 2..17 rerun same global train-only ratio across pseudo-current seasons 2022..Y-1; no family search",
            "uncertainty":"for each position/cutoff c, new_floor=max(prior_floor[p,c], max newly completed held-out residual RMSE[p,k] for every k<=c); preserves monotone prefix floor",
            "materiality":"carry prior fallback bound and take max with newly available all-pop position historical maximum at cutoff 0..17",
            "freeze_required_before_point_authority":True,
            "on_gate_or_source_failure":"no automatic point authority; explicit omission + materiality gate where supported; otherwise fail closed",
        },
        "lineage":lineage,
        "guards":{
            "silent_zero":False,
            "full_coverage_claim":False,
            "named_player_tuning":False,
            "future_leakage":False,
            "broader_forecast_search":False,
        }
    }

    writecsv(args.output_dir/"MATERIALITY_HELDOUT_BY_POPULATION.csv",heldout)
    writecsv(args.output_dir/"MATERIALITY_POOLED_POPULATION_GATES.csv",pooled_rows)
    writecsv(args.output_dir/"FALLBACK_PRODUCTION_BOUNDS_2026.csv",production)
    (args.output_dir/"LIFECYCLE_VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

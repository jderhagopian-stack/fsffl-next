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
OOT=(2023,2024,2025)
CUTOFFS=tuple(range(2,18))
NFL_GAMES=17.0
ROLE_PRIOR_GAMES=4.0
Z80=1.2815515655446004
Z90=1.6448536269514722
MATERIALITY_FRACTION=0.10

DATA={
2021:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2021.csv","41915fb49238902ad1f129ebf0405b11a1e710454ae0fe8f7b3e4f9145875f48"),
2022:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2022.csv","ad426c3fe5bf1cc30c3f137fdfe96d054e19d400879ee4413129da49fa7b54be"),
2023:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2023.csv","f19cb71a5de0dce7fd09376026237c9ee9d5a93fe13815a2ea3ec2d37204cb17"),
2024:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2024.csv","3ddc45a84f759aa348ce465ae001752c530575455717657cdfe1f8abfcdb4759"),
2025:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv","e5e0615b3d96a3eaebfaee91e55afb4a4e7fe0caf057454177bcd7d6ad4bcfc2"),
}
ACCEPTED_WEEK2_FLOORS={
 "QB":1.7266303753562966,
 "RB":0.7375205714435535,
 "WR":0.4424922528480551,
 "TE":0.4524060195836409,
}
ACCEPTED_COLD_FLOOR=0.789918699230448
ACCEPTED_WEEK2={
 "rmse":0.8105091976152538,
 "mae":0.48684391295520824,
 "bias":0.05088409116369245,
 "zero_gap":0.0347225013054242,
}
GATES={
 "max_abs_bias":0.15,
 "max_zero_gap":0.05,
 "max_pooled_rmse_vs_zero":1.0,
 "max_year_rmse_vs_zero":1.10,
}

def num(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else 0.0
    except Exception:
        return 0.0

def digest(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):
            h.update(b)
    return h.hexdigest()

def fetch(year:int,cache:Path)->Path:
    cache.mkdir(parents=True,exist_ok=True)
    url,want=DATA[year]
    p=cache/f"stats_player_week_{year}.csv"
    if not p.exists() or digest(p)!=want:
        req=urllib.request.Request(url,headers={"User-Agent":"fsffl-next-research/1.0"})
        with urllib.request.urlopen(req,timeout=180) as r,p.open("wb") as f:
            while True:
                b=r.read(1048576)
                if not b: break
                f.write(b)
    got=digest(p)
    if got!=want:
        raise RuntimeError(f"hash mismatch {year}: {got} != {want}")
    return p

def lost(row,cols):
    cc=("sack_fumbles_lost","rushing_fumbles_lost","receiving_fumbles_lost")
    if all(x in cols for x in cc):
        return sum(num(row.get(x)) for x in cc),"+".join(cc)
    if "fumbles_lost" in cols:
        return num(row.get("fumbles_lost")),"fumbles_lost"
    raise RuntimeError("exact FUMBLES_LOST field/components unavailable")

def opp(row,pos):
    sacks=num(row.get("sacks_suffered")) if "sacks_suffered" in row else num(row.get("sacks"))
    if pos=="QB":
        return num(row.get("attempts"))+sacks+num(row.get("carries"))
    return num(row.get("carries"))+num(row.get("receptions"))

def load_season(year:int,cache:Path):
    p=fetch(year,cache)
    players={}
    team_weeks=set()
    sem=None
    with p.open(newline="",encoding="utf-8") as f:
        rd=csv.DictReader(f)
        cols=set(rd.fieldnames or [])
        for r in rd:
            if (r.get("season_type") or "REG").upper() not in ("REG","REGULAR"):
                continue
            pos=(r.get("position") or r.get("position_group") or "").upper()
            if pos not in POS:
                continue
            pid=(r.get("player_id") or r.get("gsis_id") or "").strip()
            if not pid:
                continue
            week=int(num(r.get("week")))
            if week<1 or week>18:
                continue
            team=(r.get("recent_team") or r.get("team") or "").strip()
            if team:
                team_weeks.add((team,week))
            fl,s=lost(r,cols)
            sem=sem or s
            if sem!=s:
                raise RuntimeError("inconsistent exact lost-fumble semantics")
            key=(pid,pos)
            x=players.setdefault(key,{"weeks":{}, "name":r.get("player_display_name") or r.get("player_name") or ""})
            w=x["weeks"].setdefault(week,{"opp":0.0,"fl":0.0,"team":team})
            w["opp"]+=opp(r,pos);w["fl"]+=fl
            if team:
                w["team"]=team
    teams=sorted({t for t,_w in team_weeks})
    if len(teams)!=32:
        raise RuntimeError(f"{year}: expected 32 teams inferred from exact weekly data, got {len(teams)}")
    rows=[]
    for (pid,pos),x in players.items():
        full_weeks=sorted(x["weeks"])
        rows.append({
            "season":year,"pid":pid,"pos":pos,"name":x["name"],
            "weeks":x["weeks"],
            "games":len(full_weeks),
            "opp":sum(x["weeks"][w]["opp"] for w in full_weeks),
            "fl":sum(x["weeks"][w]["fl"] for w in full_weeks),
        })
    meta={"season":year,"sha256":digest(p),"url":DATA[year][0],"player_rows":len(rows),"exact_semantics":sem,"teams":len(teams)}
    return rows,team_weeks,meta

def hist(rows_by,year):
    return [r for y in sorted(rows_by) if y<year for r in rows_by[y]]

def position_stats(train):
    d=defaultdict(lambda:{"fl":0.0,"opp":0.0,"games":0})
    for r in train:
        x=d[r["pos"]];x["fl"]+=r["fl"];x["opp"]+=r["opp"];x["games"]+=r["games"]
    out={}
    for p in POS:
        x=d[p]
        out[p]={
            "fl_po":x["fl"]/x["opp"] if x["opp"] else 0.0,
            "opp_pg":x["opp"]/x["games"] if x["games"] else 0.0,
        }
    return out

def player_stats(train):
    d=defaultdict(lambda:{"opp":0.0,"games":0})
    for r in train:
        x=d[r["pid"]];x["opp"]+=r["opp"];x["games"]+=r["games"]
    return d

def cutoff_row(r,cutoff):
    weeks=r["weeks"]
    early=[w for w in weeks if w<=cutoff]
    late=[w for w in weeks if w>cutoff]
    return {
        **{k:r[k] for k in ("season","pid","pos","name","games","opp","fl")},
        "cutoff":cutoff,
        "current_games":len(early),
        "current_opp":sum(weeks[w]["opp"] for w in early),
        "future_fl":sum(weeks[w]["fl"] for w in late),
    }

def avg_remaining_games(team_weeks,cutoff):
    completed=sum(1 for _team,w in team_weeks if w<=cutoff)
    avg_completed=completed/32.0
    rem=NFL_GAMES-avg_completed
    if rem<=0:
        raise RuntimeError(f"cutoff {cutoff} has no structural games remaining")
    return rem

def tier(r,h):
    a=bool(h and h["games"])
    b=bool(r["current_games"] or r["current_opp"])
    return "history_plus_current" if a and b else "history_only" if a else "current_only" if b else "cold_start"

def role(r,h,ps):
    prior=(h["opp"]/h["games"]) if h and h["games"] else ps["opp_pg"]
    if r["current_games"]:
        return (r["current_opp"]+ROLE_PRIOR_GAMES*prior)/(r["current_games"]+ROLE_PRIOR_GAMES)
    return prior

def actual_target(r,rem):
    return NFL_GAMES*r["future_fl"]/rem

def raw_predictions(rows_by,team_weeks_by,year,cutoff):
    tr=hist(rows_by,year)
    ps=position_stats(tr)
    ph=player_stats(tr)
    rem=avg_remaining_games(team_weeks_by[year],cutoff)
    out=[]
    for base in rows_by[year]:
        r=cutoff_row(base,cutoff)
        h=ph.get(r["pid"])
        ro=role(r,h,ps[r["pos"]])
        out.append({
            **r,
            "tier":tier(r,h),
            "remaining_games_structural_avg":rem,
            "raw":NFL_GAMES*ro*ps[r["pos"]]["fl_po"],
            "actual":actual_target(r,rem),
        })
    return out

def calibration_scale(rows_by,team_weeks_by,year,cutoff):
    pred=0.0;actual=0.0
    for t in range(2022,year):
        for r in raw_predictions(rows_by,team_weeks_by,t,cutoff):
            if r["tier"]=="cold_start":
                continue
            pred+=r["raw"];actual+=r["actual"]
    return actual/pred if pred>0 else 1.0

def predictions(rows_by,team_weeks_by,year,cutoff):
    scale=calibration_scale(rows_by,team_weeks_by,year,cutoff)
    out=[]
    for r in raw_predictions(rows_by,team_weeks_by,year,cutoff):
        out.append({**r,"scale":scale,"pred":max(0.0,scale*r["raw"])})
    return out

def pct(values,q):
    vals=sorted(float(x) for x in values)
    if not vals:return 0.0
    z=(len(vals)-1)*q;lo=math.floor(z);hi=math.ceil(z)
    return vals[lo] if lo==hi else vals[lo]*(hi-z)+vals[hi]*(z-lo)

def ranks(values):
    order=sorted(range(len(values)),key=lambda i:values[i])
    out=[0.0]*len(values);i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]:j+=1
        rr=(i+j-1)/2+1
        for k in range(i,j):out[order[k]]=rr
        i=j
    return out

def spear(x,y):
    if len(x)<2:return 0.0
    a,b=ranks(x),ranks(y);ma=statistics.mean(a);mb=statistics.mean(b)
    num=sum((u-ma)*(v-mb) for u,v in zip(a,b))
    da=math.sqrt(sum((u-ma)**2 for u in a));db=math.sqrt(sum((v-mb)**2 for v in b))
    return num/(da*db) if da and db else 0.0

def metrics(rows):
    if not rows:return {"n":0}
    e=[r["pred"]-r["actual"] for r in rows]
    p=[r["pred"] for r in rows];a=[r["actual"] for r in rows]
    actual_zero=[1.0 if r["future_fl"]==0 else 0.0 for r in rows]
    lambdas=[r["pred"]*r["remaining_games_structural_avg"]/NFL_GAMES for r in rows]
    pred_zero=[math.exp(-max(0.0,x)) for x in lambdas]
    return {
        "n":len(rows),
        "mae":statistics.mean(abs(x) for x in e),
        "rmse":math.sqrt(statistics.mean(x*x for x in e)),
        "bias":statistics.mean(e),
        "spearman":spear(p,a),
        "actual_zero_rate":statistics.mean(actual_zero),
        "pred_zero_rate":statistics.mean(pred_zero),
        "zero_gap":abs(statistics.mean(actual_zero)-statistics.mean(pred_zero)),
        "zero_brier":statistics.mean((u-v)**2 for u,v in zip(pred_zero,actual_zero)),
        "actual_p90":pct(a,.90),"pred_p90":pct(p,.90),
        "actual_p95":pct(a,.95),"pred_p95":pct(p,.95),
        "actual_p99":pct(a,.99),"pred_p99":pct(p,.99),
    }

def primary(rows):
    return [r for r in rows if r["tier"]!="cold_start"]

def coverage(rows,floor,z):
    if not rows:return 0.0
    ok=0
    for r in rows:
        sd=max(math.sqrt(max(0.0,r["pred"])),floor)
        lo=max(0.0,r["pred"]-z*sd);hi=r["pred"]+z*sd
        ok+= lo<=r["actual"]<=hi
    return ok/len(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--cache-dir",type=Path,default=Path("/tmp/fumbles-rolling-cache"))
    ap.add_argument("--league-rules",type=Path,required=True)
    args=ap.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)

    rows_by={};team_weeks_by={};lineage=[]
    for y in SEASONS:
        rows,tw,meta=load_season(y,args.cache_dir)
        rows_by[y]=rows;team_weeks_by[y]=tw;lineage.append(meta)

    all_by_cutoff={}
    metric_rows=[]
    season_rows=[]
    pos_rows=[]
    scale_rows=[]
    gate_rows=[]
    raw_pos_rmse={p:{} for p in POS}

    for c in CUTOFFS:
        allrows=[]
        zeros=[]
        for y in OOT:
            rr=predictions(rows_by,team_weeks_by,y,c)
            pp=primary(rr)
            allrows.extend(pp)
            z=[{**r,"pred":0.0} for r in pp]
            zeros.extend(z)
            m=metrics(pp);zm=metrics(z)
            season_rows.append({"cutoff":c,"season":y,"model":"rolling","position":"ALL",**m})
            season_rows.append({"cutoff":c,"season":y,"model":"zero_omission","position":"ALL",**zm})
            for p in POS:
                pm=metrics([r for r in pp if r["pos"]==p])
                pz=metrics([{**r,"pred":0.0} for r in pp if r["pos"]==p])
                pos_rows.append({"cutoff":c,"season":y,"model":"rolling","position":p,**pm})
                pos_rows.append({"cutoff":c,"season":y,"model":"zero_omission","position":p,**pz})
            scale_rows.append({"target_year":y,"cutoff":c,"calibration_scalar":calibration_scale(rows_by,team_weeks_by,y,c),"training_pseudo_current_seasons":";".join(str(t) for t in range(2022,y))})
        all_by_cutoff[c]=allrows
        m=metrics(allrows);zm=metrics(zeros)
        metric_rows.append({"cutoff":c,"season":"COMBINED","model":"rolling","position":"ALL",**m})
        metric_rows.append({"cutoff":c,"season":"COMBINED","model":"zero_omission","position":"ALL",**zm})
        reasons=[]
        if m["rmse"]>GATES["max_pooled_rmse_vs_zero"]*zm["rmse"]:reasons.append("pooled_rmse_vs_zero")
        if abs(m["bias"])>GATES["max_abs_bias"]:reasons.append("bias")
        if m["zero_gap"]>GATES["max_zero_gap"]:reasons.append("zero_calibration")
        for y in OOT:
            my=next(x for x in season_rows if x["cutoff"]==c and x["season"]==y and x["model"]=="rolling" and x["position"]=="ALL")
            zy=next(x for x in season_rows if x["cutoff"]==c and x["season"]==y and x["model"]=="zero_omission" and x["position"]=="ALL")
            if my["rmse"]>GATES["max_year_rmse_vs_zero"]*zy["rmse"]:reasons.append(f"{y}_rmse_stability")
        gate_rows.append({"cutoff":c,"passes":not reasons,"reasons":";".join(reasons),"rolling_rmse":m["rmse"],"zero_rmse":zm["rmse"],"bias":m["bias"],"zero_gap":m["zero_gap"]})
        for p in POS:
            pr=[r for r in allrows if r["pos"]==p]
            pm=metrics(pr)
            raw_pos_rmse[p][c]=pm["rmse"]
            pos_rows.append({"cutoff":c,"season":"COMBINED","model":"rolling","position":p,**pm})
        scale_rows.append({"target_year":2026,"cutoff":c,"calibration_scalar":calibration_scale(rows_by,team_weeks_by,2026,c),"training_pseudo_current_seasons":"2022;2023;2024;2025"})

    # Exact Week-2 reproduction guard.
    w2=next(x for x in metric_rows if x["cutoff"]==2 and x["model"]=="rolling")
    for k,want in ACCEPTED_WEEK2.items():
        if abs(float(w2[k])-want)>1e-10:
            raise RuntimeError(f"Week-2 accepted model reproduction failed for {k}: {w2[k]} != {want}")

    # Smallest monotone empirical safety floor.
    floor_rows=[]
    rolling_floor={}
    for p in POS:
        cur=ACCEPTED_WEEK2_FLOORS[p]
        for c in CUTOFFS:
            cur=max(cur,raw_pos_rmse[p][c])
            rolling_floor[(p,c)]=cur
            rr=[r for r in all_by_cutoff[c] if r["pos"]==p]
            floor_rows.append({
                "position":p,"cutoff":c,
                "accepted_week2_floor":ACCEPTED_WEEK2_FLOORS[p],
                "oot_residual_rmse_at_cutoff":raw_pos_rmse[p][c],
                "rolling_floor":cur,
                "coverage80":coverage(rr,cur,Z80),
                "coverage90":coverage(rr,cur,Z90),
                "n":len(rr),
            })

    # Production/reference position rates are frozen historical 2021-2025 sufficient statistics.
    prod_ps=position_stats(hist(rows_by,2026))
    scoring=json.loads(args.league_rules.read_text())
    fum_points=None
    for row in scoring.get("scoring",[]):
        if row.get("stat")=="fum_lost":
            fum_points=float(row.get("points",0.0))
            break
    if fum_points is None or fum_points==0:
        raise RuntimeError("connected league rules do not score fum_lost")

    impact_rows=[]
    for c in CUTOFFS:
        scale26=calibration_scale(rows_by,team_weeks_by,2026,c)
        for p in POS:
            rr=[r for r in all_by_cutoff[c] if r["pos"]==p]
            empirical_p99=pct([r["actual"] for r in rr],.99)
            ref_mean=scale26*NFL_GAMES*prod_ps[p]["opp_pg"]*prod_ps[p]["fl_po"]
            floor=rolling_floor[(p,c)]
            event_bound=max(empirical_p99,ref_mean+Z90*floor)
            score_bound=abs(fum_points)*event_bound
            required_sd=score_bound/(MATERIALITY_FRACTION*Z90)
            impact_rows.append({
                "position":p,"cutoff":c,
                "production_calibration_scalar":scale26,
                "position_reference_mean_events":ref_mean,
                "rolling_position_stddev_floor":floor,
                "empirical_oot_p99_season_equivalent_events":empirical_p99,
                "event_bound_90":event_bound,
                "league_points_per_event":fum_points,
                "score_impact_bound_90":score_bound,
                "materiality_fraction":MATERIALITY_FRACTION,
                "minimum_supported_fp_stddev_to_be_non_material":required_sd,
            })

    # Determine frozen-contract disposition.
    passing=[int(r["cutoff"]) for r in gate_rows if r["passes"]]
    failing=[int(r["cutoff"]) for r in gate_rows if not r["passes"]]
    all_later=all(c in passing for c in range(3,18))
    prefix=2
    for c in range(3,18):
        row=next(x for x in gate_rows if x["cutoff"]==c)
        if row["passes"]:prefix=c
        else:break
    noncontiguous=any(c in passing for c in range(prefix+2,18)) if prefix<17 else False
    if all_later:
        disposition="rolling_week2_through_week17_supported"
        supported_end=17
    elif prefix>=3 and not noncontiguous:
        disposition="contiguous_prefix_supported_then_materiality_fallback"
        supported_end=prefix
    else:
        disposition="management_gate_noncontiguous_or_early_failure"
        supported_end=prefix

    def writecsv(name,rows):
        p=args.output_dir/name
        if not rows:p.write_text("");return
        with p.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

    writecsv("ROLLING_CUTOFF_METRICS.csv",metric_rows+season_rows+pos_rows)
    writecsv("ROLLING_GATE_RESULTS.csv",gate_rows)
    writecsv("ROLLING_CALIBRATION_SCALARS.csv",scale_rows)
    writecsv("ROLLING_UNCERTAINTY.csv",floor_rows)
    writecsv("MATERIALITY_IMPACT_BOUNDS.csv",impact_rows)

    result={
        "study":"rolling first-party exact FUMBLES_LOST authority",
        "frozen_protocol":"artifacts/research/fumbles_lost_rolling_authority_20260929/PROTOCOL_FROZEN.md",
        "target_semantics":"exact lost fumbles only",
        "opportunity_semantics":{"QB":"attempts+sacks_suffered+carries","RB_WR_TE":"carries+receptions"},
        "cutoffs":list(CUTOFFS),
        "oot_seasons":list(OOT),
        "week2_reproduction":{k:w2[k] for k in ACCEPTED_WEEK2},
        "gates":GATES,
        "passing_cutoffs":passing,
        "failing_cutoffs":failing,
        "supported_through_cutoff":supported_end,
        "disposition":disposition,
        "uncertainty":{
            "formula":"max(sqrt(mean), monotone rolling position OOT floor)",
            "cold_start_floor":ACCEPTED_COLD_FLOOR,
            "nonzero":True,
        },
        "materiality":{
            "rule":"impact_bound_90 <= 0.10 * 1.645 * supported_fantasy_point_stddev",
            "fraction":MATERIALITY_FRACTION,
            "coordinate_bound":"max(empirical OOT p99 actual target, position reference mean + 1.645 * rolling floor)",
            "silent_zero_forbidden":True,
            "full_coverage_claim_forbidden":True,
        },
        "lineage":lineage,
        "guards":{
            "new_forecast_family_search":False,
            "named_2026_player_tuning":False,
            "total_fumbles_proxy":False,
            "future_leakage":False,
            "y2_y3_changed":False,
            "y4_y7_changed":False,
            "k_dst_changed":False,
            "intrinsic_semantics_changed":False,
            "runtime_architecture_changed":False,
        }
    }
    (args.output_dir/"ROLLING_VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

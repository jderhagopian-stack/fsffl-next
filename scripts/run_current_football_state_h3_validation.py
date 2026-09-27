from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from fsffl.forecast.integrated_i1 import (
    I1ForecastInput,
    I1TrainingRow,
    IntegratedI1Model,
    STATE_NAMES,
)
from fsffl.state.models import Position

OUT=Path("artifacts/research/current_football_state_h3_20260926")
POSITIONS=("QB","RB","WR","TE")
HORIZONS=(1,2,3)
HOLDOUTS=(2018,2019,2020,2021)
POSITIVE_STATES=tuple(s for s in STATE_NAMES if s!="out")
RELEASE_STATUSES={"CUT","NWT","RFA","RSR","TRC","TRD","TRT","UFA"}
ATTACHED_STATUSES={"ACT","INA"}
PRACTICE_STATUSES={"DEV"}
RESERVE_STATUSES={"RES","E14","PUP","RSN"}
SUSP_STATUSES={"SUS","EXE"}
RETIRED_STATUSES={"RET"}

def load_module(path: Path,name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def mean(xs):
    a=[float(x) for x in xs if x is not None and np.isfinite(float(x))]
    return float(np.mean(a)) if a else float("nan")

def brier(p,y): return (float(p)-float(y))**2
def logloss(p,y):
    p=min(.999999,max(.000001,float(p))); y=float(y)
    return -(y*math.log(p)+(1-y)*math.log(1-p))
def state_brier(probs,actual):
    return float(np.mean([(float(probs[s])-(1.0 if s==actual else 0.0))**2 for s in STATE_NAMES]))

def conditional_points(result):
    p=max(1e-12,float(result.persistence_probability))
    return sum(float(result.probabilities[s])/p*float(result.state_means[s]) for s in POSITIVE_STATES)

def dataframe_map(frame):
    if frame is None or frame.empty: return {}
    return {(str(r.player_id),int(r.season)):r._asdict() for r in frame.itertuples(index=False)}

def event_evidence(evt,seasons):
    players, raw_rosters, raw_injuries, raw_snaps, raw_stats=evt.load_nflverse(seasons)
    rosters=evt.prepare_roster_weekly(raw_rosters)
    injuries=evt.prepare_injuries(raw_injuries)
    stats_keys=evt.prepare_stats(raw_stats)
    snaps,snap_audit=evt.prepare_snaps(raw_snaps,players)
    roster_summ=evt.weekly_roster_summary(rosters)
    injury_summ=evt.injury_summary(injuries,rosters)
    participation=evt.participation_summary(stats_keys,snaps)
    merged=roster_summ.merge(injury_summ,on=["player_id","season"],how="outer")
    merged=merged.merge(participation,on=["player_id","season"],how="outer")
    numeric=[c for c in merged.columns if c not in {"player_id","season","terminal_statuses","terminal_teams","all_statuses","all_teams"}]
    for c in numeric: merged[c]=pd.to_numeric(merged[c],errors="coerce").fillna(0.0)
    return {
        "players":players,"raw_rosters":raw_rosters,"raw_injuries":raw_injuries,
        "raw_snaps":raw_snaps,"raw_stats":raw_stats,
        "rosters":rosters,"injuries":injuries,"stats_keys":stats_keys,"snaps":snaps,
        "roster_summ":roster_summ,"injury_summ":injury_summ,"participation":participation,
        "source":dataframe_map(merged),"roster_year":evt.roster_status_sets(rosters),
        "injury_year":evt.injury_year_sets(injuries),"injury_map":dataframe_map(injury_summ),
        "snap_audit":snap_audit,
    }

def mask_raw(raw,mode):
    raw=dict(raw or {})
    if mode=="full": return raw
    if mode=="continuity":
        for k in (
            "injury_report_weeks","injury_limited_weeks","non_ir_injury_limited_weeks",
            "inactive_injury_limited_weeks","reserve_injury_limited_weeks",
            "non_ir_injury_flag","inactive_injury_flag",
            "participation_weeks","stats_weeks","snap_play_weeks",
        ): raw[k]=0
        return raw
    if mode=="reduced":
        return {}
    raise KeyError(mode)

def build_canonical(validator,pid,position,age,experience,current_points,prior_points,usage,raw,mode):
    return validator.canonical_evidence(
        pid,Position(position),age,experience,current_points,prior_points,usage,mask_raw(raw,mode)
    )

def make_record(validator,base,pf,panel,by,usage,ev,src,h,bounds,mode):
    truth=pf.target_truth(base,by,ev["roster_year"],ev["injury_map"],src.player_id,src.season,src.position,h,bounds)
    if not truth["resolved"]: return None
    target=by.get((src.player_id,src.season+h))
    target_points=max(0.0,float(target.points)) if target is not None else 0.0
    prior=by.get((src.player_id,src.season-1))
    prior_points=None if prior is None else max(0.0,float(prior.points))
    current_state=base.state_for_points(src.points,bounds[src.position])
    band=base.age_band(src.position,src.age)
    raw=ev["source"].get((src.player_id,src.season))
    evidence=build_canonical(
        validator,src.player_id,src.position,src.age,src.experience,float(src.points),
        prior_points,usage.get((src.player_id,src.season)),raw,mode
    )
    return I1TrainingRow(
        position=Position(src.position),age_band=band,current_state=current_state,horizon=h,
        target_state=truth["state"],target_points=target_points,current_points=max(0.0,float(src.points)),
        prior_points=prior_points,experience_years=int(src.experience) if src.experience is not None else None,
        evidence=evidence,
    )

def build_training(validator,base,pf,panel,by,usage,ev,holdout,horizons,mode,bounds):
    rows=[]
    for src in panel:
        if src.position not in POSITIONS or src.season<2012 or src.season>=holdout: continue
        for h in horizons:
            if src.season+h>=holdout: continue
            r=make_record(validator,base,pf,panel,by,usage,ev,src,h,bounds,mode)
            if r is not None: rows.append(r)
    return rows

def event_flags(ev,pid,season):
    raw=ev["source"].get((pid,season),{}) or {}
    ry=ev["roster_year"].get((pid,season),{}) or {}
    terminal=set(ry.get("terminal_statuses",set()) or set())
    allst=set(ry.get("statuses",set()) or set())
    flags={
        "any_event":False,
        "any_injury":float(raw.get("injury_limited_weeks",0) or 0)>0,
        "non_ir_injury":float(raw.get("non_ir_injury_limited_weeks",0) or 0)>0,
        "reserve_injury":float(raw.get("reserve_injury_limited_weeks",0) or 0)>0,
        "team_change":float(raw.get("team_change_count",0) or 0)>0,
        "release_cut":float(raw.get("release_entry_count",0) or 0)>0 or bool(terminal&RELEASE_STATUSES),
        "active_return":float(raw.get("active_return_count",0) or 0)>0,
        "practice_reserve":float(raw.get("practice_entry_count",0) or 0)>0 or float(raw.get("reserve_entry_count",0) or 0)>0,
        "suspension_exempt":float(raw.get("suspension_entry_count",0) or 0)>0 or bool(allst&SUSP_STATUSES),
        "retired":bool(allst&RETIRED_STATUSES) or bool(terminal&RETIRED_STATUSES),
    }
    flags["any_event"]=any(v for k,v in flags.items() if k!="any_event")
    return flags

def evaluate_oot(validator,base,pf,panel,usage,ev):
    by={(r.player_id,int(r.season)):r for r in panel}
    rows=[]; fitdiag=[]
    for T in HOLDOUTS:
        bounds=base.fit_state_boundaries(panel,T)
        train12_full=build_training(validator,base,pf,panel,by,usage,ev,T,(1,2),"full",bounds)
        train12_cont=build_training(validator,base,pf,panel,by,usage,ev,T,(1,2),"continuity",bounds)
        train3_full=build_training(validator,base,pf,panel,by,usage,ev,T,(3,),"full",bounds)
        train3_cont=build_training(validator,base,pf,panel,by,usage,ev,T,(3,),"continuity",bounds)
        models={
            "full12":IntegratedI1Model(train12_full),"cont12":IntegratedI1Model(train12_cont),
            "full3":IntegratedI1Model(train3_full),"cont3":IntegratedI1Model(train3_cont),
        }
        fitdiag.append({"holdout":T,"train_h12":len(train12_full),"train_h3":len(train3_full)})
        test=[r for r in panel if int(r.season)==T and r.position in POSITIONS]
        for src in test:
            prior=by.get((src.player_id,T-1)); prior_points=None if prior is None else max(0.0,float(prior.points))
            state=base.state_for_points(src.points,bounds[src.position]); band=base.age_band(src.position,src.age)
            raw=ev["source"].get((src.player_id,T),{}) or {}
            flags=event_flags(ev,src.player_id,T)
            for h in HORIZONS:
                truth=pf.target_truth(base,by,ev["roster_year"],ev["injury_map"],src.player_id,T,src.position,h,bounds)
                if not truth["resolved"]: continue
                actual=by.get((src.player_id,T+h)); actual_points=max(0.0,float(actual.points)) if actual is not None else 0.0
                model_full=models["full3" if h==3 else "full12"]; model_cont=models["cont3" if h==3 else "cont12"]
                inputs={}
                for mode in ("reduced","continuity","full"):
                    evidence=build_canonical(
                        validator,src.player_id,src.position,src.age,src.experience,float(src.points),
                        prior_points,usage.get((src.player_id,T)),raw,mode
                    )
                    inputs[mode]=I1ForecastInput(
                        position=Position(src.position),age_band=band,current_state=state,horizon=h,
                        current_points=max(0.0,float(src.points)),prior_points=prior_points,
                        experience_years=int(src.experience) if src.experience is not None else None,
                        evidence=evidence,
                    )
                results={}
                try:
                    # Reduced path is the full model's reduced submodel.
                    results["reduced"]=model_full.predict(inputs["reduced"])
                    results["continuity"]=model_cont.predict(inputs["continuity"])
                    results["full"]=model_full.predict(inputs["full"])
                except ValueError:
                    continue
                for path,res in results.items():
                    rec={
                        "holdout":T,"player_id":src.player_id,"position":src.position,"horizon":h,
                        "age_band":band,"path":path,"actual_state":truth["state"],
                        "actual_persist":int(truth["persist"]),"actual_points":actual_points,
                        "pred_persist":float(res.persistence_probability),
                        "pred_points":float(res.anticipated_points),
                        "pred_conditional_points":float(conditional_points(res)),
                        "persistence_brier":brier(res.persistence_probability,truth["persist"]),
                        "persistence_logloss":logloss(res.persistence_probability,truth["persist"]),
                        "state_brier":state_brier(res.probabilities,truth["state"]),
                        "point_abs_error":abs(float(res.anticipated_points)-actual_points),
                        "point_bias":float(res.anticipated_points)-actual_points,
                        "conditional_point_abs_error":abs(float(conditional_points(res))-actual_points) if truth["persist"] else np.nan,
                        "evidence_path":res.evidence_path,
                    }
                    rec.update(flags); rows.append(rec)
    return pd.DataFrame(rows),pd.DataFrame(fitdiag)

def metric_summary(g):
    return {
        "n":int(len(g)),
        "persistence_brier":float(g.persistence_brier.mean()),
        "persistence_logloss":float(g.persistence_logloss.mean()),
        "state_brier":float(g.state_brier.mean()),
        "point_mae":float(g.point_abs_error.mean()),
        "point_bias":float(g.point_bias.mean()),
        "conditional_point_mae":float(g.conditional_point_abs_error.dropna().mean()) if g.conditional_point_abs_error.notna().any() else np.nan,
        "realized_persistence":float(g.actual_persist.mean()),
        "predicted_persistence":float(g.pred_persist.mean()),
    }

def summarize_oot(rows):
    out=[]
    for keys,g in rows.groupby(["path","horizon","position"]):
        path,h,pos=keys; out.append({"path":path,"horizon":h,"position":pos,**metric_summary(g)})
    for keys,g in rows.groupby(["path","horizon"]):
        path,h=keys; out.append({"path":path,"horizon":h,"position":"ALL",**metric_summary(g)})
    return pd.DataFrame(out)

def cohort_summary(rows):
    cohorts=["any_event","any_injury","non_ir_injury","reserve_injury","team_change","release_cut","active_return","practice_reserve","suspension_exempt","retired"]
    out=[]
    for cohort in cohorts:
        x=rows[rows[cohort].astype(bool)]
        for keys,g in x.groupby(["path","horizon"]):
            path,h=keys
            out.append({"cohort":cohort,"path":path,"horizon":h,"position":"ALL",**metric_summary(g)})
        for keys,g in x.groupby(["path","horizon","position"]):
            path,h,pos=keys
            if len(g)>=10: out.append({"cohort":cohort,"path":path,"horizon":h,"position":pos,**metric_summary(g)})
    return pd.DataFrame(out)

def fold_deltas(rows):
    out=[]
    for h in HORIZONS:
        for T in HOLDOUTS:
            g=rows[(rows.horizon==h)&(rows.holdout==T)]
            if g.empty: continue
            m={p:metric_summary(g[g.path==p]) for p in ("reduced","continuity","full")}
            for child,parent,family in (("continuity","reduced","organizational"),("full","continuity","availability_participation"),("full","reduced","all_event")):
                if not m[child]["n"] or not m[parent]["n"]: continue
                out.append({
                    "holdout":T,"horizon":h,"family":family,
                    "child":child,"parent":parent,"n":m[child]["n"],
                    "persistence_brier_rel":m[child]["persistence_brier"]/m[parent]["persistence_brier"]-1,
                    "state_brier_rel":m[child]["state_brier"]/m[parent]["state_brier"]-1,
                    "point_mae_rel":m[child]["point_mae"]/m[parent]["point_mae"]-1,
                    "conditional_point_mae_rel":m[child]["conditional_point_mae"]/m[parent]["conditional_point_mae"]-1 if np.isfinite(m[parent]["conditional_point_mae"]) and m[parent]["conditional_point_mae"]>0 else np.nan,
                })
    return pd.DataFrame(out)

def build_weekly(raw_stats):
    x=raw_stats.copy()
    pcol="position_group" if "position_group" in x.columns else "position"
    x=x[x[pcol].astype(str).isin(POSITIONS)].copy()
    x["position"]=x[pcol].astype(str)
    x["player_id"]=x["player_id"].astype(str)
    x["season"]=pd.to_numeric(x["season"],errors="coerce").astype("Int64")
    x["week"]=pd.to_numeric(x["week"],errors="coerce").astype("Int64")
    x=x[x.season.notna()&x.week.notna()&(x.week<=18)].copy()
    x["season"]=x.season.astype(int); x["week"]=x.week.astype(int)
    fcol="fantasy_points" if "fantasy_points" in x.columns else "fantasyPoints"
    x["fantasy_points"]=pd.to_numeric(x[fcol],errors="coerce").fillna(0.0)
    for c in ("attempts","carries","targets"):
        if c not in x.columns: x[c]=0.0
        x[c]=pd.to_numeric(x[c],errors="coerce").fillna(0.0)
    x["opportunity"]=np.where(x.position=="QB",x.attempts,np.where(x.position=="RB",x.carries+x.targets,x.targets))
    return x[["player_id","season","week","position","fantasy_points","opportunity"]].drop_duplicates(["player_id","season","week"])

def injury_family(text):
    t=str(text or "").lower()
    groups={
        "lower_leg_foot":["ankle","foot","toe","achilles","calf","shin"],
        "knee":["knee","acl","mcl","meniscus"],
        "hamstring_groin":["hamstring","groin","quad","thigh"],
        "shoulder_arm":["shoulder","elbow","arm","wrist","hand","finger"],
        "concussion_head":["concussion","head"],
        "back_core":["back","abdomen","abdominal","rib","hip","oblique"],
    }
    for k,words in groups.items():
        if any(w in t for w in words): return k
    return "other_or_unknown"

def injury_episodes(evt,ev,panel,base,pf,weekly):
    injuries=ev["injuries"]; rosters=ev["rosters"]
    by={(r.player_id,int(r.season)):r for r in panel}
    bounds_cache={s:base.fit_state_boundaries(panel,s+1) for s in range(2012,2025)}
    weekly_groups={(str(pid),int(season)):g.sort_values("week") for (pid,season),g in weekly.groupby(["player_id","season"])}
    limited=injuries[injuries._official_limitation].copy()
    episode_rows=[]
    for (pid,season),g in limited.groupby(["player_id","season"]):
        weeks=sorted(set(int(w) for w in g.week))
        starts=[]; prev=None
        for w in weeks:
            if prev is None or w>prev+1: starts.append(w)
            prev=w
        wstats=weekly_groups.get((str(pid),int(season)))
        if wstats is None or wstats.empty: continue
        for start in starts:
            pre=wstats[wstats.week<start].tail(3)
            if len(pre)<3: continue
            block=[w for w in weeks if w>=start]
            end=start
            for w in block:
                if w<=end+1: end=max(end,w)
                else: break
            erows=g[g.week==start]
            reports="|".join(erows._report.astype(str)); practices="|".join(erows._practice.astype(str))
            text="|".join(erows._injury_text.astype(str))
            rweek=rosters[(rosters.player_id==str(pid))&(rosters.season==int(season))&(rosters.week==start)]
            sts=set(rweek._status.astype(str))
            desc="|".join(rweek._desc.astype(str))
            reserve=bool(sts&RESERVE_STATUSES) or ("INJURED" in desc and "RESERVE" in desc)
            if reserve: severity="reserve_ir_pup_nfi"
            elif "out" in reports or "doubtful" in reports or ("INA" in sts): severity="doubtful_out"
            else: severity="limited_questionable"
            post=wstats[wstats.week>=start].head(3)
            return_week=int(post.iloc[0].week) if len(post) else None
            post3=post
            pre_ppg=float(pre.fantasy_points.mean()); post_ppg=float(post3.fantasy_points.mean()) if len(post3) else np.nan
            pre_opp=float(pre.opportunity.mean()); post_opp=float(post3.opportunity.mean()) if len(post3) else np.nan
            future=wstats[wstats.week>=start]
            roster_future=rosters[(rosters.player_id==str(pid))&(rosters.season==int(season))&(rosters.week>=start)]
            denom=max(1,int(roster_future.week.nunique()) if len(roster_future) else 18-start+1)
            avail=float(future.week.nunique()/denom)
            recur=any(w>return_week for w in weeks) if return_week is not None else False
            bounds=bounds_cache[int(season)]
            dur={}
            for hh in (1,2):
                t=pf.target_truth(base,by,ev["roster_year"],ev["injury_map"],str(pid),int(season),str(wstats.iloc[0].position),hh,bounds)
                target=by.get((str(pid),int(season)+hh))
                dur[f"y{hh+1}_resolved"]=bool(t["resolved"])
                dur[f"y{hh+1}_persist"]=int(t["persist"]) if t["resolved"] else np.nan
                dur[f"y{hh+1}_points"]=float(target.points) if target is not None else (0.0 if t["resolved"] else np.nan)
            episode_rows.append({
                "player_id":str(pid),"season":int(season),"position":str(wstats.iloc[0].position),
                "event_week":start,"episode_end_week":end,"severity":severity,"injury_family":injury_family(text),
                "injury_text":text,"pre_games":len(pre),"post_games":len(post3),
                "games_to_return":np.nan if return_week is None else max(0,return_week-start),
                "remaining_roster_week_participation_share":avail,
                "pre_ppg":pre_ppg,"post_return_ppg":post_ppg,
                "post_return_ppg_ratio":post_ppg/pre_ppg if pre_ppg>1e-9 and np.isfinite(post_ppg) else np.nan,
                "pre_opportunity":pre_opp,"post_return_opportunity":post_opp,
                "post_return_opportunity_ratio":post_opp/pre_opp if pre_opp>1e-9 and np.isfinite(post_opp) else np.nan,
                "recurrence_after_return":bool(recur),
                **dur
            })
    return pd.DataFrame(episode_rows)

def episode_summary(eps):
    out=[]
    if eps.empty: return pd.DataFrame()
    for dims in [("severity",),("severity","position"),("injury_family",)]:
        for keys,g in eps.groupby(list(dims)):
            if not isinstance(keys,tuple): keys=(keys,)
            row={d:str(v) for d,v in zip(dims,keys)}
            row.update({
                "n":int(len(g)),
                "median_games_to_return":float(g.games_to_return.median()) if g.games_to_return.notna().any() else np.nan,
                "mean_remaining_participation_share":float(g.remaining_roster_week_participation_share.mean()),
                "median_post_return_ppg_ratio":float(g.post_return_ppg_ratio.median()) if g.post_return_ppg_ratio.notna().any() else np.nan,
                "median_post_return_opportunity_ratio":float(g.post_return_opportunity_ratio.median()) if g.post_return_opportunity_ratio.notna().any() else np.nan,
                "recurrence_share":float(g.recurrence_after_return.mean()),
                "y2_persist_share":float(g.loc[g.y2_resolved,"y2_persist"].mean()) if g.y2_resolved.any() else np.nan,
                "y3_persist_share":float(g.loc[g.y3_resolved,"y3_persist"].mean()) if g.y3_resolved.any() else np.nan,
            })
            out.append(row)
    return pd.DataFrame(out)

def noninjury_events(ev,weekly,panel,base,pf):
    rosters=ev["rosters"]; by={(r.player_id,int(r.season)):r for r in panel}
    weekly_groups={(str(pid),int(season)):g.sort_values("week") for (pid,season),g in weekly.groupby(["player_id","season"])}
    bounds_cache={s:base.fit_state_boundaries(panel,s+1) for s in range(2012,2025)}
    durability_cache={}
    events=[]
    def durability(pid,season,pos):
        key=(pid,season,pos)
        if key in durability_cache: return durability_cache[key]
        bounds=bounds_cache[season]; dur={}
        for hh in (1,2):
            t=pf.target_truth(base,by,ev["roster_year"],ev["injury_map"],pid,season,pos,hh,bounds)
            target=by.get((pid,season+hh))
            dur[f"y{hh+1}_resolved"]=bool(t["resolved"])
            dur[f"y{hh+1}_persist"]=int(t["persist"]) if t["resolved"] else np.nan
            dur[f"y{hh+1}_points"]=float(target.points) if target is not None else (0.0 if t["resolved"] else np.nan)
        durability_cache[key]=dur
        return dur
    def add(pid,season,pos,week,etype,source):
        w=weekly_groups.get((pid,season),pd.DataFrame())
        pre=w[w.week<week].tail(3); post=w[w.week>=week].head(3)
        preopp=float(pre.opportunity.mean()) if len(pre) else np.nan; postopp=float(post.opportunity.mean()) if len(post) else np.nan
        preppg=float(pre.fantasy_points.mean()) if len(pre) else np.nan; postppg=float(post.fantasy_points.mean()) if len(post) else np.nan
        dur=durability(pid,season,pos)
        events.append({
            "player_id":pid,"season":season,"position":pos,"event_week":week,"event_type":etype,"source":source,
            "pre_opportunity":preopp,"post_opportunity":postopp,
            "post_opportunity_ratio":postopp/preopp if np.isfinite(preopp) and preopp>1e-9 and np.isfinite(postopp) else np.nan,
            "pre_ppg":preppg,"post_ppg":postppg,
            "post_ppg_ratio":postppg/preppg if np.isfinite(preppg) and preppg>1e-9 and np.isfinite(postppg) else np.nan,
            **dur
        })
    for (pid,season),g in rosters.groupby(["player_id","season"]):
        gg=g.sort_values("week"); prior_s=None; prior_t=None; pos=""
        ww=weekly_groups.get((str(pid),int(season)),pd.DataFrame())
        if not ww.empty: pos=str(ww.iloc[0].position)
        if pos not in POSITIONS: continue
        seen=set()
        for week,wg in gg.groupby("week"):
            st=set(wg._status.astype(str)); tm=set(wg._team.astype(str))-{"","nan"}
            if prior_s is not None:
                if tm and prior_t and tm!=prior_t and "team_change" not in seen:
                    add(str(pid),int(season),pos,int(week),"team_change","roster_transition");seen.add("team_change")
                if st&RELEASE_STATUSES and not(prior_s&RELEASE_STATUSES) and "release_cut" not in seen:
                    add(str(pid),int(season),pos,int(week),"release_cut","roster_status");seen.add("release_cut")
                if st&ATTACHED_STATUSES and prior_s&(RELEASE_STATUSES|PRACTICE_STATUSES|RESERVE_STATUSES) and "reattachment_return" not in seen:
                    add(str(pid),int(season),pos,int(week),"reattachment_return","roster_status");seen.add("reattachment_return")
                if st&SUSP_STATUSES and not(prior_s&SUSP_STATUSES) and "suspension_exempt" not in seen:
                    add(str(pid),int(season),pos,int(week),"suspension_exempt","roster_status");seen.add("suspension_exempt")
                if st&RETIRED_STATUSES and not(prior_s&RETIRED_STATUSES) and "retired" not in seen:
                    add(str(pid),int(season),pos,int(week),"retired","roster_status");seen.add("retired")
            prior_s,prior_t=st,tm
    # Observed role changes: no future outcome used in detection.
    for (pid,season),g in weekly.groupby(["player_id","season"]):
        g=g.sort_values("week").reset_index(drop=True)
        if len(g)<5: continue
        seen=set()
        for i in range(4,len(g)):
            prior=float(g.loc[i-4:i-2,"opportunity"].mean()); recent=float(g.loc[i-1:i,"opportunity"].mean())
            if prior<=0: continue
            ratio=recent/prior
            if ratio>=1.50 and recent-prior>=3 and "promotion" not in seen:
                add(str(pid),int(season),str(g.loc[i,"position"]),int(g.loc[i,"week"]),"promotion","observed_opportunity");seen.add("promotion")
            if ratio<=.67 and prior-recent>=3 and "demotion" not in seen:
                add(str(pid),int(season),str(g.loc[i,"position"]),int(g.loc[i,"week"]),"demotion","observed_opportunity");seen.add("demotion")
    return pd.DataFrame(events)

def event_summary(events):
    out=[]
    if events.empty:return pd.DataFrame()
    for keys,g in events.groupby(["event_type","position"]):
        et,pos=keys
        out.append({
            "event_type":et,"position":pos,"n":len(g),
            "median_post_opportunity_ratio":float(g.post_opportunity_ratio.median()) if g.post_opportunity_ratio.notna().any() else np.nan,
            "median_post_ppg_ratio":float(g.post_ppg_ratio.median()) if g.post_ppg_ratio.notna().any() else np.nan,
            "y2_persist_share":float(g.loc[g.y2_resolved,"y2_persist"].mean()) if g.y2_resolved.any() else np.nan,
            "y3_persist_share":float(g.loc[g.y3_resolved,"y3_persist"].mean()) if g.y3_resolved.any() else np.nan,
        })
    for et,g in events.groupby("event_type"):
        out.append({
            "event_type":et,"position":"ALL","n":len(g),
            "median_post_opportunity_ratio":float(g.post_opportunity_ratio.median()) if g.post_opportunity_ratio.notna().any() else np.nan,
            "median_post_ppg_ratio":float(g.post_ppg_ratio.median()) if g.post_ppg_ratio.notna().any() else np.nan,
            "y2_persist_share":float(g.loc[g.y2_resolved,"y2_persist"].mean()) if g.y2_resolved.any() else np.nan,
            "y3_persist_share":float(g.loc[g.y3_resolved,"y3_persist"].mean()) if g.y3_resolved.any() else np.nan,
        })
    return pd.DataFrame(out)

def interpretation(overall,cohorts,folds):
    rows=[]
    for h in HORIZONS:
        m=overall[(overall.horizon==h)&(overall.position=="ALL")].set_index("path")
        if not {"reduced","continuity","full"}.issubset(m.index): continue
        red=m.loc["reduced"]; cont=m.loc["continuity"]; full=m.loc["full"]
        for family,child,parent in [
            ("organizational","continuity","reduced"),
            ("availability_participation","full","continuity"),
            ("all_event","full","reduced"),
        ]:
            a=m.loc[child]; b=m.loc[parent]
            improvements={
                "persistence_brier":1-a.persistence_brier/b.persistence_brier,
                "state_brier":1-a.state_brier/b.state_brier,
                "point_mae":1-a.point_mae/b.point_mae,
            }
            best=max(improvements.values())
            worst=min(improvements.values())
            fd=folds[(folds.horizon==h)&(folds.family==family)]
            stable_wins=int(((fd.persistence_brier_rel<0)|(fd.state_brier_rel<0)|(fd.point_mae_rel<0)).sum())
            supported=bool(best>=.02 and worst>=-.05 and stable_wins>=3)
            rows.append({
                "horizon":h,"family":family,"n":int(a["n"]),
                **{f"{k}_improvement":v for k,v in improvements.items()},
                "holdout_seasons_with_any_core_win":stable_wins,
                "supported":supported,
            })
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--research-root",type=Path,required=True)
    ap.add_argument("--career-panel",type=Path,required=True)
    ap.add_argument("--usage-panel",type=Path,required=True)
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    root=args.research_root/"scripts"
    evt=load_module(root/"reconstruct_event_time_absence_cause_evidence.py","evt")
    pf=load_module(root/"run_persistence_first_forecast_calibration.py","pf")
    legacy=load_module(root/"run_fundamental_intrinsic_residual_calibration.py","legacy")
    base=load_module(root/"run_intrinsic_explicit_state_challenge.py","base")
    validator=load_module(Path("scripts/validate_i1_production_parity.py"),"validator")
    panel=legacy.load_rows(args.career_panel)
    usage=pf.load_usage(args.usage_panel)
    ev=event_evidence(evt,list(range(2012,2025)))
    rows,fitdiag=evaluate_oot(validator,base,pf,panel,usage,ev)
    overall=summarize_oot(rows); cohorts=cohort_summary(rows); folds=fold_deltas(rows)
    weekly=build_weekly(ev["raw_stats"])
    injuries=injury_episodes(evt,ev,panel,base,pf,weekly)
    injury_sum=episode_summary(injuries)
    other=noninjury_events(ev,weekly,panel,base,pf)
    other_sum=event_summary(other)
    interp=interpretation(overall,cohorts,folds)

    rows.to_csv(OUT/"OOT_EVENT_STATE_PREDICTIONS.csv",index=False)
    fitdiag.to_csv(OUT/"OOT_FIT_DIAGNOSTICS.csv",index=False)
    overall.to_csv(OUT/"OOT_PATH_METRICS.csv",index=False)
    cohorts.to_csv(OUT/"OOT_EVENT_COHORT_METRICS.csv",index=False)
    folds.to_csv(OUT/"OOT_FOLD_DELTAS.csv",index=False)
    interp.to_csv(OUT/"HORIZON_EVENT_LAYER_INTERPRETATION.csv",index=False)
    injuries.to_csv(OUT/"INJURY_EPISODES.csv",index=False)
    injury_sum.to_csv(OUT/"INJURY_EPISODE_SUMMARY.csv",index=False)
    other.to_csv(OUT/"NONINJURY_EVENTS.csv",index=False)
    other_sum.to_csv(OUT/"NONINJURY_EVENT_SUMMARY.csv",index=False)

    result={
        "study":"current-football-state-h3-historical-validation",
        "authority":"research_only_no_production_change",
        "holdouts":list(HOLDOUTS),
        "paths":["reduced","continuity","full"],
        "fit_diagnostics":fitdiag.to_dict("records"),
        "horizon_interpretation":interp.to_dict("records"),
        "injury_episode_n":len(injuries),
        "noninjury_event_n":len(other),
        "source_counts":{
            "weekly_rosters":len(ev["raw_rosters"]),"injuries":len(ev["raw_injuries"]),
            "snap_counts":len(ev["raw_snaps"]),"weekly_stats":len(ev["raw_stats"])
        },
        "snap_identity_audit":ev["snap_audit"],
        "guards":{"market":False,"owner":False,"fantasy_trades":False,"team_utility":False,"production_h3_changed":False},
    }
    (OUT/"HISTORICAL_VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print("HORIZON INTERPRETATION")
    print(interp.to_string(index=False))
    print("INJURY SUMMARY")
    print(injury_sum.to_string(index=False))
    print("EVENT SUMMARY")
    print(other_sum.to_string(index=False))
    print("RESULT_JSON_BEGIN")
    print(json.dumps(result,sort_keys=True))
    print("RESULT_JSON_END")

if __name__=="__main__":
    main()

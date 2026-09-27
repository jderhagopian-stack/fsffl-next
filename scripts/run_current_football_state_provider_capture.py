from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from fsffl.providers.in_season_projection_sources import (
    CBSInSeasonProjectionSource,
    RazzballRestOfSeasonProjectionSource,
)
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatsSource
from fsffl.forecast.current_normalization import current_snapshot_from_razzball

OUT=Path("artifacts/research/current_football_state_h3_20260926")
POSITIONS=("QB","RB","WR","TE")
SCORING={
    "pass_yd":.04,"pass_td":4.0,"pass_int":-2.0,
    "rush_yd":.1,"rush_td":6.0,
    "rec_yd":.1,"rec_td":6.0,
    "fum_lost":-2.0,
}
REQ={
    "QB":{"pass_yd","pass_td","pass_int","rush_yd","rush_td","fum_lost"},
    "RB":{"rush_yd","rush_td","rec_yd","rec_td","fum_lost"},
    "WR":{"rec_yd","rec_td","fum_lost"},
    "TE":{"rec_yd","rec_td","fum_lost"},
}

def load_module(path: Path,name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def norm_name(x):
    s=unicodedata.normalize("NFKD",str(x or ""))
    s="".join(c for c in s if not unicodedata.combining(c)).lower()
    parts=re.findall(r"[a-z0-9]+",s)
    while parts and parts[-1] in {"jr","sr","ii","iii","iv","v"}: parts.pop()
    return "".join(parts)

def norm_team(x):
    t=str(x or "").upper().strip()
    return {"JAC":"JAX","WSH":"WAS","LA":"LAR"}.get(t,t)

def score_row(row):
    stats={str(k):float(v) for k,v in row.stats.items()}
    pos=row.position.value
    missing=sorted(REQ[pos]-set(stats))
    score=sum(SCORING[k]*v for k,v in stats.items() if k in SCORING)
    return score,missing

def board_indexes(board):
    # The governed 335-player standard board intentionally carries no NFL-team
    # coordinate. Mapping is therefore unique normalized name + position only.
    loose={}
    for r in board.itertuples():
        loose.setdefault((norm_name(r.player_name),str(r.position)),[]).append(r)
    return loose

def map_provider(snapshot,board):
    loose=board_indexes(board)
    rows=[]
    for r in snapshot.rows:
        hits=loose.get((norm_name(r.player_name),r.position.value),[])
        method="name_position_unique"
        if len(hits)!=1: continue
        b=hits[0]
        score,missing=score_row(r)
        rows.append({
            "provider":snapshot.provider,"captured_at":snapshot.captured_at.isoformat(),
            "effective_at":snapshot.effective_at.isoformat(),"source_version":snapshot.source_version,
            "usage_class":snapshot.usage_class,
            "player_id":str(b.player_id),"historical_gsis_id":str(b.historical_gsis_id),
            "player_name":str(b.player_name),"position":str(b.position),
            "provider_team":str(r.nfl_team),"mapping_method":method,
            "ros_standard_points":score,"exact_standard_score":len(missing)==0,
            "missing_required_stats":";".join(missing),
        })
    return pd.DataFrame(rows)

def current_event_map(evt):
    seasons=[2026]
    players,raw_rosters,raw_injuries,raw_snaps,raw_stats=evt.load_nflverse(seasons)
    rosters=evt.prepare_roster_weekly(raw_rosters)
    injuries=evt.prepare_injuries(raw_injuries)
    stats=evt.prepare_stats(raw_stats)
    snaps,_=evt.prepare_snaps(raw_snaps,players)
    rs=evt.weekly_roster_summary(rosters)
    ins=evt.injury_summary(injuries,rosters)
    ps=evt.participation_summary(stats,snaps)
    x=rs.merge(ins,on=["player_id","season"],how="outer").merge(ps,on=["player_id","season"],how="outer")
    numeric=[c for c in x.columns if c not in {"player_id","season","terminal_statuses","terminal_teams","all_statuses","all_teams"}]
    for c in numeric: x[c]=pd.to_numeric(x[c],errors="coerce").fillna(0.0)
    return x

def event_label(r):
    labs=[]
    if float(getattr(r,"injury_limited_weeks",0) or 0)>0: labs.append("injury")
    if float(getattr(r,"team_change_count",0) or 0)>0: labs.append("team_change")
    if float(getattr(r,"release_entry_count",0) or 0)>0: labs.append("release_cut")
    if float(getattr(r,"active_return_count",0) or 0)>0: labs.append("active_return")
    if float(getattr(r,"practice_entry_count",0) or 0)>0: labs.append("practice")
    if float(getattr(r,"reserve_entry_count",0) or 0)>0: labs.append("reserve")
    if float(getattr(r,"suspension_entry_count",0) or 0)>0: labs.append("suspension")
    statuses=str(getattr(r,"all_statuses",""))
    if "RET" in statuses.split("|"): labs.append("retired")
    return ";".join(sorted(set(labs)))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--research-root",type=Path,required=True)
    ap.add_argument("--board",type=Path,required=True)
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    board=pd.read_csv(args.board)
    board=board[board.position.isin(POSITIONS)].copy()
    state=SleeperWeeklyStatsSource().fetch_nfl_state()
    if state.season!=2026: raise RuntimeError(f"unexpected Sleeper season {state.season}")
    completed=int(state.completed_through_week)
    # Exact structural fallback used when player/team bye identity is not applied:
    # one bye over 18 structural weeks => 17 active-game prior.
    remaining_factor=max(0.0,(18-completed)/18.0)
    board["preseason_remaining_prior"]=pd.to_numeric(board.standard_y1_points,errors="coerce").fillna(0)*remaining_factor

    providers=[]
    failures=[]
    for name,fn in (
        ("razzball",lambda:current_snapshot_from_razzball(RazzballRestOfSeasonProjectionSource().fetch_latest(season=2026))),
        ("cbs",lambda:CBSInSeasonProjectionSource().fetch_rest_of_season(season=2026)),
    ):
        try:
            snap=fn()
            providers.append(map_provider(snap,board))
        except Exception as exc:
            failures.append({"provider":name,"error_type":type(exc).__name__,"error":str(exc)})
    p=pd.concat(providers,ignore_index=True) if providers else pd.DataFrame()
    if not p.empty:
        p=p.merge(board[["player_id","preseason_remaining_prior"]],on="player_id",how="left")
        p["delta_vs_remaining_prior"]=p.ros_standard_points-p.preseason_remaining_prior
        p["ratio_vs_remaining_prior"]=np.where(p.preseason_remaining_prior>0,p.ros_standard_points/p.preseason_remaining_prior,np.nan)

    evt=load_module(args.research_root/"scripts/reconstruct_event_time_absence_cause_evidence.py","evt_current")
    try:
        events=current_event_map(evt)
    except Exception as exc:
        events=pd.DataFrame()
        failures.append({"provider":"nflverse_current_event_state","error_type":type(exc).__name__,"error":str(exc)})
    if not events.empty:
        events=events[events.season==2026].copy()
        events["historical_gsis_id"]=events.player_id.astype(str)
        events["current_event_labels"]=[event_label(r) for r in events.itertuples()]
        event_cols=["historical_gsis_id","current_event_labels","injury_limited_weeks","non_ir_injury_limited_weeks",
                    "inactive_injury_limited_weeks","reserve_injury_limited_weeks","team_change_count",
                    "active_return_count","release_entry_count","practice_entry_count","reserve_entry_count",
                    "suspension_entry_count","participation_weeks","last_status_active","last_status_attached",
                    "last_status_release","last_status_practice","last_status_reserve"]
        event_cols=[c for c in event_cols if c in events.columns]
        em=events[event_cols].copy()
    else:
        em=pd.DataFrame(columns=["historical_gsis_id","current_event_labels"])

    if not p.empty:
        p=p.merge(em,on="historical_gsis_id",how="left")
        p["current_event_labels"]=p.current_event_labels.fillna("")
    exact=p[p.exact_standard_score].copy() if not p.empty else pd.DataFrame()
    if not exact.empty:
        consensus=exact.pivot_table(
            index=["player_id","historical_gsis_id","player_name","position","preseason_remaining_prior"],
            columns="provider",values="ros_standard_points",aggfunc="first"
        ).reset_index()
        source_cols=[c for c in ("razzball","cbs") if c in consensus.columns]
        consensus["source_count"]=consensus[source_cols].notna().sum(axis=1)
        consensus["consensus_ros_standard_points"]=consensus[source_cols].mean(axis=1)
        consensus["consensus_delta_vs_remaining_prior"]=consensus.consensus_ros_standard_points-consensus.preseason_remaining_prior
        consensus["consensus_ratio_vs_remaining_prior"]=np.where(consensus.preseason_remaining_prior>0,consensus.consensus_ros_standard_points/consensus.preseason_remaining_prior,np.nan)
        consensus=consensus.merge(em,on="historical_gsis_id",how="left")
        consensus["current_event_labels"]=consensus.current_event_labels.fillna("")
    else:
        consensus=pd.DataFrame()

    event_cons=consensus[consensus.current_event_labels!=""].copy() if not consensus.empty else pd.DataFrame()
    summary=[]
    if not event_cons.empty:
        for label in ["injury","team_change","release_cut","active_return","practice","reserve","suspension","retired"]:
            g=event_cons[event_cons.current_event_labels.str.contains(label,regex=False)]
            if len(g):
                summary.append({
                    "event":label,"n":len(g),
                    "two_source_n":int((g.source_count>=2).sum()),
                    "median_consensus_ratio_vs_remaining_prior":float(g.consensus_ratio_vs_remaining_prior.median()),
                    "median_consensus_delta_points":float(g.consensus_delta_vs_remaining_prior.median()),
                })
    pd.DataFrame(summary).to_csv(OUT/"CURRENT_PROVIDER_EVENT_SUMMARY.csv",index=False)
    p.to_csv(OUT/"CURRENT_PROVIDER_ROWS.csv",index=False)
    consensus.to_csv(OUT/"CURRENT_PROVIDER_CONSENSUS.csv",index=False)
    em.to_csv(OUT/"CURRENT_EVENT_STATE_2026.csv",index=False)
    (OUT/"CURRENT_PROVIDER_FAILURES.json").write_text(json.dumps(failures,indent=2,sort_keys=True),encoding="utf-8")
    result={
        "captured_at":datetime.now(UTC).isoformat(),
        "sleeper_nfl_state":{"season":state.season,"week":state.week,"season_type":state.season_type,"completed_through_week":completed},
        "remaining_prior_method":"standard preseason Y1 * (18-completed_through_week)/18; structural unknown-bye comparator only",
        "provider_rows":int(len(p)),"exact_provider_rows":int(len(exact)),
        "consensus_rows":int(len(consensus)),"two_source_exact_rows":int((consensus.source_count>=2).sum()) if not consensus.empty else 0,
        "event_consensus_rows":int(len(event_cons)),
        "failures":failures,
        "rights_note":"research-only capture; source rights ledger is unchanged and neither CBS nor Razzball is promoted for deployment by this artifact",
        "historical_revision_table_available":False,
        "double_count_note":"provider ROS delta is diagnostic of current Y1 outlook; never add a second event haircut to the same Y1 total",
    }
    (OUT/"CURRENT_PROVIDER_CAPTURE_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    if summary:
        print(pd.DataFrame(summary).to_string(index=False))

if __name__=="__main__":
    main()

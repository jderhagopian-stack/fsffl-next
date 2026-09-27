from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fsffl.forecast.current_normalization import current_snapshot_from_razzball
from fsffl.providers.in_season_projection_sources import (
    CBSInSeasonProjectionSource,
    RazzballRestOfSeasonProjectionSource,
)
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatsSource

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
SCHEMA_VERSION="prospective-current-football-state-v1"

def load_module(path: Path,name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

def canonical(value: Any) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def clean(v: Any):
    if v is None:
        return None
    if isinstance(v,(np.integer,)):
        return int(v)
    if isinstance(v,(np.floating,)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v,(np.bool_,)):
        return bool(v)
    if isinstance(v,float):
        return None if not math.isfinite(v) else v
    if pd.isna(v):
        return None
    return v

def norm_name(x):
    s=unicodedata.normalize("NFKD",str(x or ""))
    s="".join(c for c in s if not unicodedata.combining(c)).lower()
    parts=re.findall(r"[a-z0-9]+",s)
    while parts and parts[-1] in {"jr","sr","ii","iii","iv","v"}:
        parts.pop()
    return "".join(parts)

def board_indexes(board):
    loose={}
    for r in board.itertuples():
        loose.setdefault((norm_name(r.player_name),str(r.position)),[]).append(r)
    return loose

def provider_payload(snapshot,board,season,week,captured_at):
    loose=board_indexes(board)
    mapped=[]
    observations=[]
    for r in snapshot.rows:
        hits=loose.get((norm_name(r.player_name),r.position.value),[])
        if len(hits)!=1:
            continue
        b=hits[0]
        stats={str(k):float(v) for k,v in r.stats.items()}
        missing=sorted(REQ[r.position.value]-set(stats))
        score=sum(SCORING[k]*v for k,v in stats.items() if k in SCORING)
        mapped.append({
            "player_id":str(b.player_id),
            "historical_gsis_id":str(b.historical_gsis_id),
            "external_id":str(r.external_id),
            "player_name":str(b.player_name),
            "position":r.position.value,
            "provider_team":str(r.nfl_team),
            "mapping_method":"name_position_unique",
            "exact_standard_score":len(missing)==0,
            "missing_required_stats":missing,
        })
        for metric,value in sorted(stats.items()):
            observations.append({
                "player_id":str(b.player_id),
                "external_id":str(r.external_id),
                "position":r.position.value,
                "metric":metric,
                "mean":float(value),
                "stddev":0.0,
                "p10":None,"p50":None,"p90":None,
            })
        if not missing:
            observations.append({
                "player_id":str(b.player_id),
                "external_id":str(r.external_id),
                "position":r.position.value,
                "metric":"standard_points",
                "mean":float(score),
                "stddev":0.0,
                "p10":None,"p50":None,"p90":None,
            })

    normalized={
        "schema_version":SCHEMA_VERSION,
        "provider":snapshot.provider,
        "season":season,
        "mapped_rows":mapped,
        "observation_count":len(observations),
        "mapping_note":"unique normalized player name + position against governed current 335-player board",
        "raw_html_retained":False,
    }
    effective=snapshot.effective_at.astimezone(UTC)
    retrieved=snapshot.captured_at.astimezone(UTC)
    # Structural bound only: this stores the evidence horizon without claiming
    # an exact team-specific remaining schedule.
    period_end=datetime(season+1,1,15,tzinfo=UTC)
    return {
        "provider":snapshot.provider,
        "effective_at":effective.isoformat(),
        "retrieved_at":retrieved.isoformat(),
        "period_start":captured_at.isoformat(),
        "period_end":period_end.isoformat(),
        "source_version":snapshot.source_version,
        "usage_class":snapshot.usage_class,
        "content_fingerprint":digest({
            "provider":snapshot.provider,
            "effective_at":effective.isoformat(),
            "source_version":snapshot.source_version,
            "observations":observations,
            "mapped_rows":mapped,
        }),
        "raw_payload":normalized,
        "observations":observations,
    }

def current_event_map(evt,season):
    players,raw_rosters,raw_injuries,raw_snaps,raw_stats=evt.load_nflverse([season])
    rosters=evt.prepare_roster_weekly(raw_rosters)
    injuries=evt.prepare_injuries(raw_injuries)
    stats=evt.prepare_stats(raw_stats)
    snaps,_=evt.prepare_snaps(raw_snaps,players)
    rs=evt.weekly_roster_summary(rosters)
    ins=evt.injury_summary(injuries,rosters)
    ps=evt.participation_summary(stats,snaps)
    x=rs.merge(ins,on=["player_id","season"],how="outer").merge(ps,on=["player_id","season"],how="outer")
    numeric=[c for c in x.columns if c not in {
        "player_id","season","terminal_statuses","terminal_teams","all_statuses","all_teams"
    }]
    for c in numeric:
        x[c]=pd.to_numeric(x[c],errors="coerce").fillna(0.0)
    return x[x.season==season].copy()

def event_labels(r):
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
    return sorted(set(labs))

def event_payloads(events,board,captured_at):
    idmap={}
    for r in board.itertuples():
        gid=str(r.historical_gsis_id)
        if gid and gid not in {"nan","None"}:
            idmap[gid]=str(r.player_id)
    out=[]
    for r in events.itertuples():
        gid=str(r.player_id)
        current_id=idmap.get(gid)
        if current_id is None:
            continue
        payload={}
        for col in events.columns:
            if col in {"player_id","season"}:
                continue
            payload[col]=clean(getattr(r,col))
        payload["historical_gsis_id"]=gid
        labels=event_labels(r)
        out.append({
            "source":"nflverse_current_state",
            "player_id":current_id,
            "observed_at":captured_at.isoformat(),
            "event_labels":labels,
            "state_fingerprint":digest(payload),
            "payload":payload,
        })
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--research-root",type=Path,required=True)
    ap.add_argument("--board",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()

    captured_at=datetime.now(UTC)
    board=pd.read_csv(args.board)
    board=board[board.position.isin(POSITIONS)].copy()
    if len(board)!=335:
        raise RuntimeError(f"expected governed 335-player board, got {len(board)}")

    state=SleeperWeeklyStatsSource().fetch_nfl_state()
    if int(state.season)!=2026:
        raise RuntimeError(f"unexpected Sleeper season {state.season}")
    season=int(state.season)
    week=int(state.week)
    completed=int(state.completed_through_week)

    providers=[]
    failures=[]
    for name,fn in (
        ("razzball",lambda:current_snapshot_from_razzball(
            RazzballRestOfSeasonProjectionSource().fetch_latest(season=season)
        )),
        ("cbs",lambda:CBSInSeasonProjectionSource().fetch_rest_of_season(season=season)),
    ):
        try:
            providers.append(provider_payload(fn(),board,season,week,captured_at))
        except Exception as exc:
            failures.append({"source":name,"error_type":type(exc).__name__,"error":str(exc)[:1000]})

    events=[]
    try:
        evt=load_module(args.research_root/"scripts/reconstruct_event_time_absence_cause_evidence.py","evt_archive")
        events=event_payloads(current_event_map(evt,season),board,captured_at)
    except Exception as exc:
        failures.append({
            "source":"nflverse_current_event_state",
            "error_type":type(exc).__name__,
            "error":str(exc)[:1000],
        })

    board_fingerprint=digest([
        {
            "player_id":str(r.player_id),
            "historical_gsis_id":str(r.historical_gsis_id),
            "player_name":str(r.player_name),
            "position":str(r.position),
        }
        for r in board.sort_values("player_id").itertuples()
    ])

    manifest={
        "schema_version":SCHEMA_VERSION,
        "authority":"research_only",
        "season":season,
        "week":week,
        "completed_through_week":completed,
        "provider_count":len(providers),
        "provider_names":[p["provider"] for p in providers],
        "event_rows":len(events),
        "board_player_count":len(board),
        "board_fingerprint":board_fingerprint,
        "provider_raw_html_retained":False,
        "period_end_semantics":"structural ROS research bound only; not team-specific schedule authority",
        "rights_note":"research-only retention; provider deployment/commercial rights remain governed by SOURCE_RIGHTS_LEDGER.md",
        "double_count_note":"retained ROS evidence is observational; if future ROS becomes Forecast authority, do not add a second injury/event haircut to H1",
    }
    body_without_key={
        "season":season,
        "week":week,
        "completed_through_week":completed,
        "captured_at":captured_at.isoformat(),
        "manifest":manifest,
        "failures":failures,
        "providers":providers,
        "events":events,
    }
    content_hash=digest(body_without_key)
    capture_key=captured_at.strftime("%Y%m%dT%H%M%SZ")+"-"+content_hash[:16]
    body={"capture_key":capture_key,**body_without_key}

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(canonical(body),encoding="utf-8")
    print(json.dumps({
        "capture_key":capture_key,
        "season":season,
        "week":week,
        "completed_through_week":completed,
        "providers":[
            {"provider":p["provider"],"observations":len(p["observations"]),
             "fingerprint":p["content_fingerprint"][:16]}
            for p in providers
        ],
        "event_rows":len(events),
        "failure_count":len(failures),
        "payload_sha256":digest(body),
    },indent=2,sort_keys=True))

if __name__=="__main__":
    main()

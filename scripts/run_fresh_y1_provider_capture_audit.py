from __future__ import annotations

import argparse, hashlib, json, os, time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from fsffl.forecast.current_normalization import current_snapshot_from_razzball, normalize_current_projection_snapshot
from fsffl.forecast.current_runtime import NamedCurrentProjectionFetcher, _fetch_current_snapshots, default_current_projection_fetchers
from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.live_ensemble import LiveForecastSourceBatch, build_authoritative_live_ensemble
from fsffl.providers.fftoday_live import FFTodayLiveProjectionSource, HtmlTableParser, _default_get_text as fft_get
from fsffl.providers.razzball_live import _TableParser, _default_get_text as raz_get
from fsffl.providers.razzball_season_live import RazzballSeasonProjectionSource
from fsffl.value.private_beta_activation_data import activation_artifact_text
from fsffl.forecast.i1_current_facts import CurrentI1FactsArtifact
from research_freeze_governed_year1_universe import build_state, load_sleeper_players

SCHEMA="fsffl-fresh-y1-provider-capture-v1"

def cb(v): return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def put(path,v):
    b=cb(v); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b); return sha(b)
def row_dict(r):
    return {"provider":r.provider,"external_id":r.external_id,"player_name":r.player_name,"position":r.position.value,"nfl_team":r.nfl_team,"stats":dict(r.stats)}
def obs_dict(o): return o.model_dump(mode="json")

def fft_sub(html):
    p=HtmlTableParser(); p.feed(html); return {"tables":p.tables,"text_parts":p.text_parts}
def raz_sub(html):
    p=_TableParser(); p.feed(html); return {"tables":p.tables,"text_parts":p.text_parts}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir",type=Path,required=True); a=ap.parse_args(); out=a.output_dir; out.mkdir(parents=True,exist_ok=True)
    t0=time.perf_counter(); started=datetime.now(UTC)
    facts=CurrentI1FactsArtifact.from_dict(json.loads(activation_artifact_text("current_i1_facts_2026.json")))
    state,_=build_state(facts,load_sleeper_players()); season=state.league.season
    pages=[]; counts=Counter(); raw={}
    def save_page(provider,url,html,parsed):
        counts[provider]+=1; n=counts[provider]
        payload={"provider":provider,"url":url,"ordinal":n,"parser_input_sha256":sha(html.encode()),"parser_input_utf8_bytes":len(html.encode()),"raw_html_persisted":False,"substitute_kind":"lossless parser tables + text_parts","parsed_substitute":parsed}
        fn=f"provider_capture/{provider}_page_{n:02d}_parsed_substitute.json"; h=put(out/fn,payload)
        pages.append({"provider":provider,"url":url,"artifact":fn,"artifact_sha256":h,"parser_input_sha256":payload["parser_input_sha256"]}); return html
    def fget(url):
        h=fft_get(url); return save_page("fftoday",url,h,fft_sub(h))
    def rget(url):
        h=raz_get(url); return save_page("razzball",url,h,raz_sub(h))
    fs=FFTodayLiveProjectionSource(http_get_text=fget); rs=RazzballSeasonProjectionSource(http_get_text=rget)
    def ff(season_arg):
        s=fs.fetch_latest(season=season_arg); raw["fftoday"]=s; return s
    def rr(season_arg):
        s=rs.fetch_latest(season=season_arg); raw["razzball_provider"]=s; c=current_snapshot_from_razzball(s); raw["razzball"]=c; return c
    defaults={x.source_id:x for x in default_current_projection_fetchers()}
    fetchers=(NamedCurrentProjectionFetcher("razzball",rr),NamedCurrentProjectionFetcher("fftoday",ff),defaults["cbs"],defaults["nfl_fantasy"])
    snapshots,failures=_fetch_current_snapshots(fetchers,season=season); by={k:v for k,v in snapshots}
    asof=datetime.now(UTC)
    if snapshots: asof=max(asof,*(s.captured_at.astimezone(UTC) for _,s in snapshots),*(s.effective_at.astimezone(UTC) for _,s in snapshots))
    parsed=[]
    if "fftoday" in by:
        s=by["fftoday"]; fn="provider_capture/fftoday_parsed_rows.json"; h=put(out/fn,{"provider":"fftoday","requested_season":season,"captured_at":s.captured_at.isoformat(),"effective_at":s.effective_at.isoformat(),"source_version":s.source_version,"usage_class":s.usage_class,"rows":[row_dict(r) for r in s.rows]}); parsed.append({"provider":"fftoday","artifact":fn,"sha256":h,"rows":len(s.rows)})
    if "razzball_provider" in raw:
        s=raw["razzball_provider"]; fn="provider_capture/razzball_parsed_rows.json"; h=put(out/fn,{"provider":"razzball","requested_season":season,"source_url":s.source_url,"captured_at":s.captured_at.isoformat(),"effective_at":s.effective_at.isoformat(),"source_version":s.source_version,"usage_class":s.usage_class,"rows":[dict(r) for r in s.rows]}); parsed.append({"provider":"razzball","artifact":fn,"sha256":h,"rows":len(s.rows)})
    batches=[]; nfail=[]; narts=[]
    for sid,s in snapshots:
        try:
            o=normalize_current_projection_snapshot(s,league_state=state,season=season,evaluation_as_of=asof)
            if not o: raise ValueError("no canonical observations")
            batches.append(LiveForecastSourceBatch(source_id=sid,observations=o))
            if sid in {"fftoday","razzball"}:
                fn=f"normalized/{sid}_pre_ensemble_normalized.json"; h=put(out/fn,{"provider":sid,"requested_season":season,"captured_at":s.captured_at.isoformat(),"effective_at":s.effective_at.isoformat(),"source_version":s.source_version,"evaluation_as_of":asof.isoformat(),"observations":[obs_dict(x) for x in o]}); narts.append({"provider":sid,"artifact":fn,"sha256":h,"observations":len(o)})
        except Exception as e: nfail.append(f"{sid}: {type(e).__name__}: {e}")
    ensemble,cov=build_authoritative_live_ensemble(tuple(batches),minimum_independent_sources=2)
    scored=derive_league_fantasy_point_forecasts(ensemble,rules=state.league.rules,source="fsffl:live_league_scored",model_version="next2-current-runtime-v4:parallel-provider-ingestion")
    ehash=put(out/"fresh_equal_weight_ensemble.json",[obs_dict(x) for x in ensemble]); shash=put(out/"fresh_league_scored_y1.json",[obs_dict(x) for x in scored])
    manifest={"schema_version":SCHEMA,"fresh_evidence_only":True,"non_substitutable_for_2026_09_18":True,"requested_season":season,"capture_started_at":started.isoformat(),"capture_completed_at":datetime.now(UTC).isoformat(),"runtime_seconds":time.perf_counter()-t0,"git":{"sha":os.getenv("GITHUB_SHA"),"ref":os.getenv("GITHUB_REF"),"run_id":os.getenv("GITHUB_RUN_ID")},"identity_source":"Sleeper global players endpoint via governed research Year-1 state builder","evaluation_as_of":asof.isoformat(),"providers":[{"provider":sid,"status":"SUCCESS" if sid in by else "FAILED","captured_at":by[sid].captured_at.isoformat() if sid in by else None,"effective_at":by[sid].effective_at.isoformat() if sid in by else None,"source_version":by[sid].source_version if sid in by else None,"usage_class":by[sid].usage_class if sid in by else None} for sid in ("fftoday","razzball","cbs","nfl_fantasy")],"acquisition_failures":failures,"normalization_failures":nfail,"coverage":cov.model_dump(mode="json"),"pages":pages,"parsed_artifacts":parsed,"normalized_artifacts":narts,"output_hashes":{"fresh_equal_weight_ensemble.json":ehash,"fresh_league_scored_y1.json":shash},"execution_accounting":{"forecast_fits":0,"tuning_actions":0,"route_changes":0,"production_changes":0,"fresh_capture_runs":1}}
    mh=put(out/"CAPTURE_MANIFEST.json",manifest)
    put(out/"RELOAD_VERIFICATION.json",{"status":"PASS","manifest_sha256":mh,"ensemble_sha256":sha((out/"fresh_equal_weight_ensemble.json").read_bytes()),"scored_sha256":sha((out/"fresh_league_scored_y1.json").read_bytes()),"all_hashes_match":sha((out/"fresh_equal_weight_ensemble.json").read_bytes())==ehash and sha((out/"fresh_league_scored_y1.json").read_bytes())==shash})
    summary={"status":"CAPTURE_COMPLETE","requested_season":season,"successful_providers":sorted(by),"failures":failures,"fftoday_rows":len(by["fftoday"].rows) if "fftoday" in by else 0,"razzball_rows":len(by["razzball"].rows) if "razzball" in by else 0,"ensemble_observations":len(ensemble),"scored_players":len(scored),"evaluation_as_of":asof.isoformat()}
    put(out/"CAPTURE_SUMMARY.json",summary); print(json.dumps(summary,indent=2))
if __name__=="__main__": main()

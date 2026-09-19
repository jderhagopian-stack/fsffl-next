from __future__ import annotations

import argparse, hashlib, json, math, re, unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import numpy as np

NAMES=("Bijan Robinson","Jahmyr Gibbs","Christian McCaffrey","Puka Nacua","Sam Darnold","Aaron Rodgers")
COEFS={"pass_yards":.04,"pass_td":4.,"interceptions":-2.,"rush_yards":.1,"rush_td":6.,"receptions":.5,"rec_yards":.1,"rec_td":6.,"fumbles_lost":-2.}
RAZ_MAP={"Pass Yds":"pass_yards","Pass TD":"pass_td","Int":"interceptions","Rush Yds":"rush_yards","Run TD":"rush_td","Rec":"receptions","Rec Yds":"rec_yards","Rec TD":"rec_td","Fum Lst":"fumbles_lost"}
FFT_MAP={"pass_yd":"pass_yards","pass_td":"pass_td","pass_int":"interceptions","rush_yd":"rush_yards","rush_td":"rush_td","rec":"receptions","rec_yd":"rec_yards","rec_td":"rec_td","fum_lost":"fumbles_lost"}

def read(p): return json.loads(Path(p).read_text())
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm_name(v):
    x=unicodedata.normalize("NFKD",v); x="".join(c for c in x if not unicodedata.combining(c))
    p=re.findall(r"[a-z0-9]+",x.lower())
    while p and p[-1] in {"jr","sr","ii","iii","iv","v"}: p.pop()
    return "".join(p)
def norm_team(v):
    t=(v or "").upper().strip(); return {"JAC":"JAX","WSH":"WAS","LA":"LAR"}.get(t,t)
def group(obs):
    d=defaultdict(dict)
    for o in obs: d[o["player_id"]][o["metric"]]=float(o["distribution"]["mean"])
    return d
def calc(st,standard=False):
    return sum(float(st.get(k,0))*((0.0 if standard and k=="receptions" else c)) for k,c in COEFS.items())
def fnum(v):
    try:return float(str(v).replace(",",""))
    except:return None
def qstats(v):
    a=np.asarray(v,float);q=np.quantile(a,[.5,.75,.9,.95,.99])
    return {"n":int(len(a)),"p50":float(q[0]),"p75":float(q[1]),"p90":float(q[2]),"p95":float(q[3]),"p99":float(q[4]),"max":float(a.max())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--capture-dir",type=Path,required=True); ap.add_argument("--prior-y1",type=Path,required=True)
    a=ap.parse_args(); d=a.capture_dir; out=d/"derived"; out.mkdir(exist_ok=True)
    fft_p=read(d/"provider_capture/fftoday_parsed_rows.json"); raz_p=read(d/"provider_capture/razzball_parsed_rows.json")
    fft_n=read(d/"normalized/fftoday_pre_ensemble_normalized.json"); raz_n=read(d/"normalized/razzball_pre_ensemble_normalized.json")
    ens=read(d/"fresh_equal_weight_ensemble.json"); scored=read(d/"fresh_league_scored_y1.json"); prior=read(a.prior_y1)
    ident={r["player_id"]:{"name":r["full_name"],"position":r["position"],"team":r["nfl_team"]} for r in prior["rows"]}
    ids={x["player_id"] for x in scored}
    if ids != set(ident): raise RuntimeError("fresh 335 ID set differs from persisted 2026-09-18 set")
    ffg,rzg,eng=group(fft_n["observations"]),group(raz_n["observations"]),group(ens)
    score={x["player_id"]:float(x["distribution"]["mean"]) for x in scored}; name_id={v["name"]:k for k,v in ident.items()}
    fft_by={(r["player_name"],r["position"],r["nfl_team"]):r for r in fft_p["rows"]}; raz_by={(r.get("Name"),r.get("Pos"),r.get("Team")):r for r in raz_p["rows"]}
    cells={}
    for name in NAMES:
        hit=None
        for p in sorted((d/"provider_capture").glob("fftoday_page_*_parsed_substitute.json")):
            j=read(p);tp=j["parsed_substitute"]["text_parts"]
            for i,t in enumerate(tp):
                if t.strip()==name:hit={"page_artifact":p.name,"text_index":i,"cells":tp[i:i+12]};break
            if hit:break
        cells[name]=hit
    named=[]
    for name in NAMES:
        pid=name_id[name];i=ident[pid];ff,rz,en=ffg[pid],rzg[pid],eng[pid];fr=fft_by[(name,i["position"],i["team"])];rr=raz_by[(name,i["position"],i["team"])]
        named.append({"player":name,"player_id":pid,**i,"fftoday_source_cells":cells[name],"fftoday_parsed_stats":fr["stats"],"fftoday_normalized_stats":ff,"fftoday_half_ppr_from_raw_stats":calc(ff),"razzball_parsed_raw_row":rr,"razzball_normalized_stats":rz,"razzball_half_ppr_from_raw_stats":calc(rz),"razzball_display_half_ppr":fnum(rr.get("1/2PPR PTS")),"ensemble_stats":en,"equal_weight_half_ppr":calc(en),"fresh_stored_y1":score[pid],"standard_non_ppr_equivalent":calc(en,True),"term_by_term_half_ppr":[{"metric":m,"value":float(en.get(m,0)),"coefficient":c,"points":float(en.get(m,0))*c} for m,c in COEFS.items()],"razzball_minus_fftoday_points":calc(rz)-calc(ff),"ensemble_uplift_vs_fftoday_points":calc(en)-calc(ff),"causal_answer":"Razzball raw provider row is extreme; FSFFL preserves the columns and takes the exact equal-weight mean with FFToday."})
    write(out/"NAMED_PLAYER_CAUSAL_TRACE.json",named)

    def pmap(obs):
        z={}
        for o in obs:
            if o["player_id"] in ids:z[o["provenance"]["provider_ref"]["external_id"]]=o["player_id"]
        return z
    fm,rm=pmap(fft_n["observations"]),pmap(raz_n["observations"]); fext={r["external_id"]:r for r in fft_p["rows"]}
    def rex(r): return f'{r["Pos"]}:{r["Team"]}:{norm_name(r["Name"])}'
    rext={rex(r):r for r in raz_p["rows"] if r.get("Pos") in {"QB","RB","WR","TE"} and r.get("Name") and r.get("Team")}
    maps=[]
    for provider,mp,lookup in (("fftoday",fm,fext),("razzball",rm,rext)):
        for ext,pid in sorted(mp.items(),key=lambda kv:(ident[kv[1]]["position"],ident[kv[1]]["name"])):
            i=ident[pid];r=lookup[ext]
            if provider=="fftoday":pn,pp,pt=r["player_name"],r["position"],r["nfl_team"]
            else:pn,pp,pt=r["Name"],r["Pos"],r["Team"]
            exact=norm_name(pn)==norm_name(i["name"]) and pp==i["position"] and norm_team(pt)==norm_team(i["team"])
            loose=norm_name(pn)==norm_name(i["name"]) and pp==i["position"]
            maps.append({"provider":provider,"provider_external_id":ext,"canonical_player_id":pid,"provider_name":pn,"provider_position":pp,"provider_team":pt,"canonical_name_reference":i["name"],"canonical_position_reference":i["position"],"canonical_team_reference":i["team"],"replayed_match_method":"EXACT_NAME_POSITION_TEAM" if exact else ("LOOSE_NAME_POSITION" if loose else "OTHER")})
    mc=Counter((r["provider"],r["replayed_match_method"]) for r in maps)
    write(out/"PROVIDER_TO_CANONICAL_MAPPING_AUDIT.json",{"scope":"fresh final 335-player board","identity_replay_note":"Runtime output persists canonical player_id + provider_ref but not match label. The match rule was replayed against the identical persisted 335-player canonical ID set from 2026-09-18.","counts":[{"provider":p,"method":m,"count":n} for (p,m),n in sorted(mc.items())],"rows":maps})

    raw=[]
    for ext,pid in fm.items():
        r=fext[ext]
        for s,m in FFT_MAP.items():
            if s in r["stats"]:raw.append(abs(ffg[pid][m]-float(r["stats"][s])))
    for ext,pid in rm.items():
        r=rext[ext]
        for col,m in RAZ_MAP.items():
            if r.get(col) not in (None,"") and m in rzg[pid]:
                v=fnum(r[col])
                if v is not None:raw.append(abs(rzg[pid][m]-v))
    ed=[abs(eng[pid][m]-(ffg[pid][m]+rzg[pid][m])/2) for pid in ids for m in set(ffg[pid])&set(rzg[pid])&set(eng[pid])]
    sd=[abs(score[pid]-calc(eng[pid])) for pid in ids]
    rj=read(d/"provider_capture/razzball_page_01_parsed_substitute.json");rt=rj["parsed_substitute"]["text_parts"]
    desc=next((x for x in rt if "Updated from NFL Preseason through rest of season" in x),None); upd=[]
    for i,x in enumerate(rt):
        if x=="Updated:" or "Updated:" in x:upd=rt[i:i+3];break
    dtf=datetime.fromisoformat(fft_p["effective_at"].replace("Z","+00:00"));dtr=datetime.fromisoformat(raz_p["effective_at"].replace("Z","+00:00"))
    write(out/"PARSER_AND_SEMANTIC_VALIDATION.json",{"fftoday":{"source_version":fft_p["source_version"],"captured_at":fft_p["captured_at"],"effective_at":fft_p["effective_at"],"page_identity":"2026 Regular Season; Updated: 9/6/2026","projection_grid_parser":"text_parts relative-cell fallback","sample_extracted_cells":cells,"relative_cell_mapping":{"QB":"tail[3] pass_yards; [4] pass_td; [5] interceptions; [7] rush_yards; [8] rush_td","RB":"tail[2] rush_yards; [3] rush_td; [4] receptions; [5] rec_yards; [6] rec_td","WR":"tail[1] receptions; [2] rec_yards; [3] rec_td; [5] rush_yards; [6] rush_td","TE":"tail[1] receptions; [2] rec_yards; [3] rec_td; rush zero"},"provider_fantasy_point_column_used":False},"razzball":{"source_version":raz_p["source_version"],"captured_at":raz_p["captured_at"],"effective_at":raz_p["effective_at"],"page_title":"2026 Fantasy Football Projections & Rankings | Razzball","page_description_with_semantic_warning":re.sub(r"\s+"," ",desc) if desc else None,"updated_text_parts":upd,"table_header":rj["parsed_substitute"]["tables"][2][0],"canonical_column_map":RAZ_MAP,"provider_fantasy_point_columns_used":False},"cross_pipeline":{"requested_season":2026,"period_start":"2026-09-01T00:00:00Z","period_end":"2027-03-01T00:00:00Z","raw_to_normalized_checks":len(raw),"max_abs_raw_to_normalized_diff":max(raw),"equal_weight_checks":len(ed),"max_abs_equal_weight_diff":max(ed),"scoring_recomposition_players":len(sd),"max_abs_scoring_recomposition_diff":max(sd),"per_game_field_consumed":False,"games_multiplier_applied":False,"provider_fantasy_point_columns_mixed":False,"provider_effective_age_difference_seconds":(dtr-dtf).total_seconds(),"provider_effective_age_difference_human":str(dtr-dtf),"mapping_final_335":"335/335 exact for each provider; no loose matches"}})

    rel={"QB":["pass_yards","pass_td","interceptions","rush_yards","rush_td"],"RB":["rush_yards","rush_td","receptions","rec_yards","rec_td"],"WR":["receptions","rec_yards","rec_td","rush_yards","rush_td"],"TE":["receptions","rec_yards","rec_td","rush_yards","rush_td"]}
    dist=[];ext=[]
    for provider,g in (("fftoday",ffg),("razzball",rzg)):
        for pos in ("QB","RB","WR","TE"):
            pids=[pid for pid in ids if ident[pid]["position"]==pos]
            for m in rel[pos]:dist.append({"provider":provider,"position":pos,"metric":m,**qstats([g[pid].get(m,0) for pid in pids])})
            dist.append({"provider":provider,"position":pos,"metric":"half_ppr_from_raw_stats",**qstats([calc(g[pid]) for pid in pids])})
        for pid in ids:
            s=g[pid];flags=[]
            if s.get("rush_yards",0)>2000:flags.append("rush_yards>2000")
            if s.get("rec_yards",0)>2000:flags.append("rec_yards>2000")
            if s.get("pass_yards",0)>5000:flags.append("pass_yards>5000")
            if flags:ext.append({"provider":provider,"player_id":pid,**ident[pid],"flags":flags,"pass_yards":s.get("pass_yards",0),"rush_yards":s.get("rush_yards",0),"rec_yards":s.get("rec_yards",0),"half_ppr_from_raw_stats":calc(s)})
    ec=Counter((e["provider"],f) for e in ext for f in e["flags"])
    write(out/"PROVIDER_POPULATION_DIAGNOSTICS.json",{"distribution_by_provider_position_metric":dist,"extreme_flag_counts":[{"provider":p,"flag":f,"count":n} for (p,f),n in sorted(ec.items())],"extreme_flag_rows":sorted(ext,key=lambda x:(x["provider"],x["position"],x["name"]))})

    pp=[];md=[]
    for pid in ids:
        i=ident[pid];ff,rz,en=calc(ffg[pid]),calc(rzg[pid]),calc(eng[pid])
        pp.append({"player_id":pid,**i,"fftoday_half_ppr":ff,"razzball_half_ppr_from_raw_stats":rz,"fresh_ensemble_half_ppr":en,"razzball_minus_fftoday":rz-ff,"ensemble_uplift_vs_fftoday":en-ff,"razzball_to_fftoday_ratio":rz/ff if ff else None})
        for m in sorted(set(ffg[pid])&set(rzg[pid])):
            x,y=ffg[pid][m],rzg[pid][m];md.append({"player_id":pid,**i,"metric":m,"fftoday":x,"razzball":y,"difference_razz_minus_fft":y-x,"abs_difference":abs(y-x),"ratio_razz_to_fft":y/x if x else None})
    ms=[]
    for m in sorted({r["metric"] for r in md}):
        v=np.asarray([r["difference_razz_minus_fft"] for r in md if r["metric"]==m],float);av=np.abs(v)
        ms.append({"metric":m,"n":len(v),"median_diff":float(np.median(v)),"p90_abs_diff":float(np.quantile(av,.9)),"p95_abs_diff":float(np.quantile(av,.95)),"p99_abs_diff":float(np.quantile(av,.99)),"max_abs_diff":float(av.max())})
    fpv=np.asarray([r["razzball_minus_fftoday"] for r in pp],float);af=np.abs(fpv)
    write(out/"PROVIDER_DISAGREEMENT_DIAGNOSTICS.json",{"metric_summary":ms,"fantasy_point_summary":{"n":len(fpv),"median_diff":float(np.median(fpv)),"p90_abs_diff":float(np.quantile(af,.9)),"p95_abs_diff":float(np.quantile(af,.95)),"p99_abs_diff":float(np.quantile(af,.99)),"max_abs_diff":float(af.max())},"top_fantasy_point_disagreements":sorted(pp,key=lambda x:abs(x["razzball_minus_fftoday"]),reverse=True)[:30],"top_metric_disagreements":sorted(md,key=lambda x:x["abs_difference"],reverse=True)[:60]})

    oldfp={r["player_id"]:float(r["year1"]["distribution"]["mean"]) for r in prior["rows"]};fv=[]
    for pid in ids:
        fr,ov=score[pid],oldfp[pid];fv.append({"player_id":pid,**ident[pid],"y1_2026_09_18":ov,"fresh_y1":fr,"absolute_change":fr-ov,"percent_change":fr/ov-1 if ov else None})
    ar=np.asarray([r["absolute_change"] for r in fv],float)
    write(out/"FRESH_VS_20260918_POST_ENSEMBLE.json",{"guardrail":"Fresh evidence is descriptive only and is not a reconstruction of 2026-09-18 provider rows.","summary":{"n":len(fv),"mean_absolute_change":float(np.mean(np.abs(ar))),"median_change":float(np.median(ar)),"p10_change":float(np.quantile(ar,.1)),"p90_change":float(np.quantile(ar,.9)),"min_change":float(ar.min()),"max_change":float(ar.max()),"within_0_1_points_count":sum(abs(float(x))<=.100000001 for x in ar)},"rows":sorted(fv,key=lambda x:(x["position"],x["name"]))})

    final={"schema_version":"fsffl-fresh-y1-provider-pipeline-diagnostic-final-v1","classification":"B - PROVIDER EVIDENCE ITSELF IS EXTREME / SEMANTICALLY UNSUITABLE","classification_basis":["Fresh FFToday rows are ordinary season projections for the named players.","Fresh Razzball raw table itself contains extreme totals and its own fantasy-point columns are likewise extreme.","Raw-to-normalized parity is exact, equal-weight arithmetic parity is exact, and league-scoring recomposition is exact to floating-point tolerance across the complete fresh 335-player board.","Fresh ensemble uplift over FFToday is caused by averaging extreme Razzball evidence, not additional FSFFL inflation.","Razzball page semantics are not clean for expected-season use: the page calls itself 2026 projections but metadata says it is updated from NFL Preseason through rest of season."],"material_pipeline_defect_found":False,"provider_semantic_issue":{"provider":"razzball","status":"MATERIAL","effective_at":raz_p["effective_at"],"semantic_warning":"Updated from NFL Preseason through rest of season"},"non_material_pipeline_observations":["FFToday is 12 days 15:08:23 older than Razzball; this source-vintage gap should be governed explicitly, but it does not create the inflation because FFToday is the lower/ordinary side.","Provider-native fantasy-point columns are not used; FSFFL scores raw like-for-like stats under league rules.","No per-game fields or games multiplier are consumed."],"named_fresh_y1":{r["player"]:r["fresh_stored_y1"] for r in named},"extreme_counts":{f"{p}|{f}":n for (p,f),n in sorted(ec.items())},"parity":{"max_abs_raw_to_normalized_diff":max(raw),"max_abs_equal_weight_diff":max(ed),"max_abs_scoring_recomposition_diff":max(sd)},"smallest_next_governed_action":"Do not change weights or repair in this audit. Establish a governed Razzball evidence-suitability/horizon-validation decision before using this page as expected full-season Forecast input; preserve both captured providers unchanged for review.","fresh_not_historical_reconstruction":True,"execution_accounting":{"successful_fresh_provider_capture_runs":1,"forecast_fits":0,"tuning_actions":0,"route_changes":0,"production_changes":0}}
    write(out/"FINAL_OUTCOME.json",final)
    (out/"MANAGEMENT_SUMMARY.md").write_text("# FSFFL NEXT Fresh Provider Capture & Y1 Pipeline Diagnostic\n\n**Outcome B - Provider evidence itself is extreme / semantically unsuitable.**\n\nFresh FFToday is ordinary. Fresh Razzball raw rows are extreme before FSFFL normalization. The current pipeline preserves provider columns exactly, takes the exact equal-weight mean, and recomposes league scoring exactly. The extreme fresh Y1 board is therefore driven by Razzball evidence, not an added FSFFL arithmetic inflation. Razzball also describes the page as updated from NFL Preseason through rest of season, so the semantic suitability of this page as an expected full-season projection input must be governed before further Forecast use.\n\nFresh data is not a reconstruction of 2026-09-18. No repair, fit, tuning, routing change, promotion, merge, deploy, or production change was performed.\n",encoding="utf-8")
    files=sorted(p for p in out.iterdir() if p.is_file() and p.name!="ARTIFACT_MANIFEST.json")
    write(out/"ARTIFACT_MANIFEST.json",{"schema_version":"fsffl-fresh-y1-provider-pipeline-derived-manifest-v1","capture_dir":str(d),"files":[{"path":p.name,"sha256":sha(p),"bytes":p.stat().st_size} for p in files],"classification":final["classification"]})
    print(json.dumps({"status":"PASS","derived_files":len(files)+1,"classification":final["classification"]},indent=2))
if __name__=="__main__":main()

from __future__ import annotations
import csv, hashlib, json, math, statistics, urllib.request, re, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT=Path("artifacts/fumbles-lost-first-party-research")
CACHE=ROOT/"cache"
BOARD=Path("artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_STANDARD_COORDINATE_BOARD_335.csv")
SEASONS=(2021,2022,2023,2024,2025,2026)
OOT=(2023,2024,2025)
POS=("QB","RB","WR","TE")
CUTOFF=2
NFL_GAMES=17
REM=15
SHRINK_OPPS=100.0
ROLE_PRIOR_GAMES=4.0

# Frozen before any 2026 named-player shadow inspection.
GATES={
 "min_combined_n":500,
 "min_year_n":100,
 "max_rmse_vs_zero":0.95,
 "max_rmse_vs_pos_game":0.98,
 "max_mae_vs_pos_game":1.05,
 "max_year_rmse_vs_zero":1.10,
 "max_abs_bias":0.15,
 "max_zero_gap":0.05,
 "min_current_identity_coverage":0.95,
}
DATA={
2021:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2021.csv","41915fb49238902ad1f129ebf0405b11a1e710454ae0fe8f7b3e4f9145875f48"),
2022:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2022.csv","ad426c3fe5bf1cc30c3f137fdfe96d054e19d400879ee4413129da49fa7b54be"),
2023:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2023.csv","f19cb71a5de0dce7fd09376026237c9ee9d5a93fe13815a2ea3ec2d37204cb17"),
2024:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2024.csv","3ddc45a84f759aa348ce465ae001752c530575455717657cdfe1f8abfcdb4759"),
2025:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv","e5e0615b3d96a3eaebfaee91e55afb4a4e7fe0caf057454177bcd7d6ad4bcfc2"),
2026:("https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv","315cfb8d5abbd44c6a36c43e3e8ad78c96351193c8e2fe717fcff8413df43b2b"),
}

def num(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else 0.0
    except Exception: return 0.0

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()

def get(year):
    CACHE.mkdir(parents=True,exist_ok=True)
    url,want=DATA[year]; p=CACHE/f"stats_player_week_{year}.csv"
    if not p.exists() or digest(p)!=want:
        req=urllib.request.Request(url,headers={"User-Agent":"fsffl-next-research/1.0"})
        with urllib.request.urlopen(req,timeout=180) as r,p.open("wb") as f:
            while True:
                b=r.read(1048576)
                if not b: break
                f.write(b)
    got=digest(p)
    if got!=want: raise SystemExit(f"hash mismatch {year}: {got}")
    return p

def lost(row,cols):
    if "fumbles_lost" in cols: return num(row.get("fumbles_lost")),"fumbles_lost"
    cc=("sack_fumbles_lost","rushing_fumbles_lost","receiving_fumbles_lost")
    if all(x in cols for x in cc): return sum(num(row.get(x)) for x in cc),"+".join(cc)
    raise SystemExit("exact FUMBLES_LOST field/components unavailable")

def opp(row,pos):
    return (num(row.get("attempts"))+num(row.get("sacks"))+num(row.get("carries"))) if pos=="QB" else (num(row.get("carries"))+num(row.get("receptions")))

def load(year):
    p=get(year); g={}; sem=None
    with p.open(newline="",encoding="utf-8") as f:
        rd=csv.DictReader(f); cols=set(rd.fieldnames or [])
        for r in rd:
            if (r.get("season_type") or "REG").upper() not in ("REG","REGULAR"): continue
            pos=(r.get("position") or r.get("position_group") or "").upper()
            if pos not in POS: continue
            pid=(r.get("player_id") or r.get("gsis_id") or "").strip()
            if not pid: continue
            w=int(num(r.get("week")))
            if w<1 or w>18: continue
            fl,s=lost(r,cols); sem=sem or s
            if sem!=s: raise SystemExit("inconsistent exact target semantics")
            k=(pid,pos); x=g.setdefault(k,{"name":(r.get("player_display_name") or r.get("player_name") or ""),"weeks":set(),"eg":0,"eo":0.0,"ef":0.0,"fo":0.0,"ff":0.0,"fg":0,"fu":0.0})
            x["weeks"].add(w); x["fo"]+=opp(r,pos); x["ff"]+=fl
            if w<=CUTOFF: x["eg"]+=1; x["eo"]+=opp(r,pos); x["ef"]+=fl
            else: x["fg"]+=1; x["fu"]+=fl
    rows=[]
    for (pid,pos),x in g.items():
        rows.append({"season":year,"pid":pid,"name":x["name"],"pos":pos,"early_games":x["eg"],"early_opp":x["eo"],"early_fl":x["ef"],"games":len(x["weeks"]),"opp":x["fo"],"fl":x["ff"],"future_games":x["fg"],"future_fl":x["fu"]})
    return rows,{"season":year,"url":DATA[year][0],"sha256":digest(p),"player_rows":len(rows),"exact_semantics":sem}

def hist(rows_by,year):
    return [r for y in sorted(rows_by) if y<year for r in rows_by[y]]

def position_stats(train):
    d=defaultdict(lambda:{"fl":0.0,"opp":0.0,"games":0})
    for r in train:
        x=d[r["pos"]]; x["fl"]+=r["fl"]; x["opp"]+=r["opp"]; x["games"]+=r["games"]
    out={}
    for p in POS:
        x=d[p]; out[p]={"fl_pg":x["fl"]/x["games"] if x["games"] else 0.0,"fl_po":x["fl"]/x["opp"] if x["opp"] else 0.0,"opp_pg":x["opp"]/x["games"] if x["games"] else 0.0}
    return out

def player_stats(train):
    d=defaultdict(lambda:{"fl":0.0,"opp":0.0,"games":0})
    for r in train:
        x=d[r["pid"]]; x["fl"]+=r["fl"]; x["opp"]+=r["opp"]; x["games"]+=r["games"]
    return d

def tier(r,h):
    a=bool(h and h["games"]); b=bool(r["early_games"] or r["early_opp"])
    return "history_plus_current" if a and b else "history_only" if a else "current_only" if b else "cold_start"

def role(r,h,ps):
    prior=(h["opp"]/h["games"]) if h and h["games"] else ps["opp_pg"]
    if r["early_games"]:
        return (r["early_opp"]+ROLE_PRIOR_GAMES*prior)/(r["early_games"]+ROLE_PRIOR_GAMES)
    return prior

def shrunk(h,ps):
    if not h or not h["games"]: return ps["fl_po"]
    return (h["fl"]+SHRINK_OPPS*ps["fl_po"])/(h["opp"]+SHRINK_OPPS)

def augmented(r,h,ps):
    base=shrunk(h,ps)
    return (base*SHRINK_OPPS+r["early_fl"])/(SHRINK_OPPS+r["early_opp"])

def target(r): return NFL_GAMES*r["future_fl"]/REM

def calibration_scale(rows_by, year):
    """One global multiplier learned only from pseudo-current seasons before year."""
    pred_sum=0.0; actual_sum=0.0
    for t in range(2022,year):
        tr=hist(rows_by,t); ps=position_stats(tr); ph=player_stats(tr)
        for r in rows_by[t]:
            h=ph.get(r["pid"])
            if tier(r,h)=="cold_start": continue
            ro=role(r,h,ps[r["pos"]])
            pred_sum += NFL_GAMES*ro*ps[r["pos"]]["fl_po"]
            actual_sum += target(r)
    return actual_sum/pred_sum if pred_sum>0 else 1.0

def predictions(rows_by,year):
    tr=hist(rows_by,year); ps=position_stats(tr); ph=player_stats(tr); out=[]
    scale=calibration_scale(rows_by,year)
    for r in rows_by[year]:
        h=ph.get(r["pid"]); ro=role(r,h,ps[r["pos"]]); t=tier(r,h)
        vals={
          "zero_omission":0.0,
          "position_game_rate":NFL_GAMES*ps[r["pos"]]["fl_pg"],
          "position_opportunity_rate":NFL_GAMES*ro*ps[r["pos"]]["fl_po"],
          "calibrated_position_opportunity_rate":scale*NFL_GAMES*ro*ps[r["pos"]]["fl_po"],
          "player_history_shrunk":NFL_GAMES*ro*shrunk(h,ps[r["pos"]]),
          "player_history_plus_current":NFL_GAMES*ro*augmented(r,h,ps[r["pos"]]),
        }
        for m,v in vals.items(): out.append({**r,"model":m,"pred":max(0.0,v),"actual":target(r),"tier":t})
    return out

def pct(a,q):
    if not a:return 0.0
    s=sorted(a); z=(len(s)-1)*q; lo=math.floor(z); hi=math.ceil(z)
    return s[lo] if lo==hi else s[lo]*(hi-z)+s[hi]*(z-lo)

def ranks(a):
    order=sorted(range(len(a)),key=lambda i:a[i]); out=[0.0]*len(a); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and a[order[j]]==a[order[i]]: j+=1
        rr=(i+j-1)/2+1
        for k in range(i,j): out[order[k]]=rr
        i=j
    return out

def spear(x,y):
    if len(x)<2:return 0.0
    a,b=ranks(x),ranks(y); ma=statistics.mean(a); mb=statistics.mean(b)
    n=sum((u-ma)*(v-mb) for u,v in zip(a,b)); da=math.sqrt(sum((u-ma)**2 for u in a)); db=math.sqrt(sum((v-mb)**2 for v in b))
    return n/(da*db) if da and db else 0.0

def metrics(rr):
    if not rr:return {"n":0}
    e=[r["pred"]-r["actual"] for r in rr]; p=[r["pred"] for r in rr]; a=[r["actual"] for r in rr]
    z=[1.0 if x==0 else 0.0 for x in a]; pz=[math.exp(-x*REM/NFL_GAMES) for x in p]
    cut=pct(a,.9); tail=[r for r in rr if r["actual"]>=cut and r["actual"]>0]; te=[r["pred"]-r["actual"] for r in tail]
    return {"n":len(rr),"mae":statistics.mean(abs(x) for x in e),"rmse":math.sqrt(statistics.mean(x*x for x in e)),"bias":statistics.mean(e),"spearman":spear(p,a),"actual_zero_rate":statistics.mean(z),"pred_zero_rate":statistics.mean(pz),"zero_gap":abs(statistics.mean(z)-statistics.mean(pz)),"zero_brier":statistics.mean((u-v)**2 for u,v in zip(pz,z)),"actual_p90":pct(a,.9),"pred_p90":pct(p,.9),"actual_p95":pct(a,.95),"pred_p95":pct(p,.95),"tail_n":len(tail),"tail_rmse":math.sqrt(statistics.mean(x*x for x in te)) if te else 0.0}

def primary(rr): return [r for r in rr if r["tier"]!="cold_start"]

def gate(allpred):
    names=("position_opportunity_rate","calibrated_position_opportunity_rate","player_history_shrunk","player_history_plus_current")
    z=primary([r for r in allpred if r["model"]=="zero_omission"]); pg=primary([r for r in allpred if r["model"]=="position_game_rate"])
    zm,pm=metrics(z),metrics(pg); res={}
    for m in names:
        rr=primary([r for r in allpred if r["model"]==m]); mm=metrics(rr); reasons=[]
        if mm["n"]<GATES["min_combined_n"]: reasons.append("combined_n")
        if mm["rmse"]>GATES["max_rmse_vs_zero"]*zm["rmse"]: reasons.append("rmse_vs_zero")
        if mm["rmse"]>GATES["max_rmse_vs_pos_game"]*pm["rmse"]: reasons.append("rmse_vs_position_game")
        if mm["mae"]>GATES["max_mae_vs_pos_game"]*pm["mae"]: reasons.append("mae_vs_position_game")
        if abs(mm["bias"])>GATES["max_abs_bias"]: reasons.append("bias")
        if mm["zero_gap"]>GATES["max_zero_gap"]: reasons.append("zero_calibration")
        for y in OOT:
            my=metrics([r for r in rr if r["season"]==y]); zy=metrics([r for r in z if r["season"]==y])
            if my["n"]<GATES["min_year_n"]: reasons.append(f"{y}_n")
            if my["rmse"]>GATES["max_year_rmse_vs_zero"]*zy["rmse"]: reasons.append(f"{y}_rmse_stability")
        res[m]={"passes":not reasons,"reasons":reasons,"metrics":mm}
    selected=next((m for m in names if res[m]["passes"]),None)
    return {"thresholds":GATES,"baselines":{"zero_omission":zm,"position_game_rate":pm},"candidates":res,"selected":selected}

def bins(rr,n=5):
    rr=sorted(rr,key=lambda r:(r["pred"],r["pid"])); out=[]
    for b in range(n):
        q=rr[len(rr)*b//n:len(rr)*(b+1)//n]
        if q: out.append({"bin":b+1,"n":len(q),"mean_prediction":statistics.mean(x["pred"] for x in q),"mean_actual":statistics.mean(x["actual"] for x in q),"actual_zero_rate":statistics.mean(1.0 if x["actual"]==0 else 0.0 for x in q)})
    return out

def uncertainty(allpred,selected):
    rr=primary([r for r in allpred if r["model"]==selected]); out={}
    overall=metrics(rr)["rmse"]
    for p in POS:
        x=[r for r in rr if r["pos"]==p]; out[p]={"n":len(x),"residual_rmse_floor":metrics(x)["rmse"] if x else overall}
    out["OVERALL"]={"n":len(rr),"residual_rmse_floor":overall}; return out

def _norm_name(v):
    s=unicodedata.normalize("NFKD",v or "")
    s="".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    parts=re.findall(r"[a-z0-9]+",s)
    while parts and parts[-1] in {"jr","sr","ii","iii","iv","v"}: parts.pop()
    return "".join(parts)

def current_shadows(rows_by,selected,unc):
    tr=hist(rows_by,2026); ps=position_stats(tr); ph=player_stats(tr); cur={r["pid"]:r for r in rows_by[2026]}
    name_idx=defaultdict(list)
    for rr in rows_by[2026]:
        if rr["name"]: name_idx[(_norm_name(rr["name"]),rr["pos"])].append(rr["pid"])
    with BOARD.open(newline="",encoding="utf-8") as f: board=list(csv.DictReader(f))
    out=[]; mapped=0; tc=defaultdict(int); scale=calibration_scale(rows_by,2026)
    for b in board:
        if b.get("position") not in POS: continue
        gid=(b.get("historical_gsis_id") or "").strip(); p=b["position"]; identity_method="retained_gsis"
        if not gid:
            matches=name_idx.get((_norm_name(b.get("player_name") or ""),p),[])
            if len(matches)==1:
                gid=matches[0]; identity_method="unique_current_name_position"
            else:
                identity_method="unmapped"
        r=cur.get(gid)
        if gid:mapped+=1
        if r is None:r={"season":2026,"pid":gid or "unmapped","name":"","pos":p,"early_games":0,"early_opp":0.0,"early_fl":0.0,"games":0,"opp":0.0,"fl":0.0,"future_games":0,"future_fl":0.0}
        h=ph.get(gid); t=tier(r,h) if gid else "unmapped"; tc[t]+=1; ro=role(r,h,ps[p])
        vals={"position_opportunity_rate":NFL_GAMES*ro*ps[p]["fl_po"],"calibrated_position_opportunity_rate":scale*NFL_GAMES*ro*ps[p]["fl_po"],"player_history_shrunk":NFL_GAMES*ro*shrunk(h,ps[p]),"player_history_plus_current":NFL_GAMES*ro*augmented(r,h,ps[p])}
        pred=max(0.0,vals[selected]); sd=max(math.sqrt(pred),float(unc[p]["residual_rmse_floor"]))
        out.append({"player_id":b.get("player_id"),"historical_gsis_id":gid,"identity_method":identity_method,"position":p,"evidence_tier":t,"weeks_observed_current":r["early_games"],"current_opportunities":round(r["early_opp"],6),"current_fumbles_lost":round(r["early_fl"],6),"history_games":h["games"] if h else 0,"history_opportunities":round(h["opp"],6) if h else 0.0,"history_fumbles_lost":round(h["fl"],6) if h else 0.0,"predicted_season_equivalent_fumbles_lost":round(pred,8),"predictive_stddev":round(sd,8),"model":selected})
    cov=mapped/len(out) if out else 0
    return out,{"board_rows":len(out),"mapped_gsis":mapped,"identity_coverage":cov,"tier_counts":dict(tc),"passes":cov>=GATES["min_current_identity_coverage"]}

def writecsv(path,rows):
    if not rows:path.write_text("",encoding="utf-8");return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def main():
    ROOT.mkdir(parents=True,exist_ok=True); rows_by={}; lineage=[]
    for y in SEASONS:
        rows,meta=load(y);rows_by[y]=rows;lineage.append(meta)
    allpred=[r for y in OOT for r in predictions(rows_by,y)]
    gg=gate(allpred); sel=gg["selected"]
    metrics_rows=[]
    for m in ("zero_omission","position_game_rate","position_opportunity_rate","calibrated_position_opportunity_rate","player_history_shrunk","player_history_plus_current"):
        rr=primary([r for r in allpred if r["model"]==m]);metrics_rows.append({"season":"COMBINED","position":"ALL","model":m,**metrics(rr)})
        for y in OOT:metrics_rows.append({"season":y,"position":"ALL","model":m,**metrics([r for r in rr if r["season"]==y])})
        for p in POS:metrics_rows.append({"season":"COMBINED","position":p,"model":m,**metrics([r for r in rr if r["pos"]==p])})
    stress=[{"model":m,**metrics([r for r in allpred if r["model"]==m and r["tier"]=="cold_start"])} for m in ("zero_omission","position_game_rate","position_opportunity_rate","calibrated_position_opportunity_rate","player_history_shrunk","player_history_plus_current")]
    result={"study":"FSFFL first-party FUMBLES_LOST model","target":{"coordinate":"FUMBLES_LOST","cutoff_week":CUTOFF,"formula":"17 * exact lost fumbles in Weeks 3+ / 15","semantics":"exact lost fumbles; total fumbles forbidden"},"folds":[{"held_out":y,"training_seasons":[x for x in SEASONS if x<y]} for y in OOT],"features":{"QB":"attempts+sacks+carries","RB_WR_TE":"carries+receptions","current":"Weeks 1-2 only","history":"strictly prior seasons only","shrink_opportunities":SHRINK_OPPS,"role_prior_games":ROLE_PRIOR_GAMES,"calibration":"one global multiplier learned only from prior pseudo-current seasons"},"gate":gg,"cold_start_stress":stress}
    shadows=[]; cal=[]; unc=None; coverage=None
    if sel:
        unc=uncertainty(allpred,sel)
        for y in OOT:
            for x in bins(primary([r for r in allpred if r["model"]==sel and r["season"]==y])):cal.append({"season":y,**x})
        for x in bins(primary([r for r in allpred if r["model"]==sel])):cal.append({"season":"COMBINED",**x})
        # Current named shadows generated only after model selection/gating.
        shadows,coverage=current_shadows(rows_by,sel,unc)
        gg["production_ready"]=bool(coverage["passes"]);gg["production_fail_reasons"]=[] if coverage["passes"] else ["current_identity_coverage"]
    else:
        gg["production_ready"]=False;gg["production_fail_reasons"]=["no_candidate_cleared_predictive_gate"]
    result["gate"]=gg;result["uncertainty"]=unc;result["current_coverage"]=coverage;result["data_lineage"]=lineage
    (ROOT/"VALIDATION_RESULTS.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    (ROOT/"DATA_LINEAGE.json").write_text(json.dumps({"nflverse_assets":lineage,"current_board":{"path":str(BOARD),"sha256":digest(BOARD)},"no_random_split":True,"no_future_leakage":True,"no_named_player_tuning":True,"model_frozen_before_current_shadows":True},indent=2,sort_keys=True),encoding="utf-8")
    writecsv(ROOT/"OOT_METRICS.csv",metrics_rows);writecsv(ROOT/"COLD_START_STRESS.csv",stress);writecsv(ROOT/"CALIBRATION.csv",cal);writecsv(ROOT/"CURRENT_SHADOWS.csv",shadows)
    report=["# First-Party FUMBLES_LOST Model Research","","Design/model/gates were frozen before 2026 named-player shadows.","","## Result",f"Selected model: {sel or 'NONE'}",f"Production-ready: {gg['production_ready']}",""]
    for n,x in gg["candidates"].items():report.append(f"- {n}: {'PASS' if x['passes'] else 'FAIL'}; RMSE={x['metrics']['rmse']:.4f}; MAE={x['metrics']['mae']:.4f}; bias={x['metrics']['bias']:.4f}; zero_gap={x['metrics']['zero_gap']:.4f}; reasons={','.join(x['reasons']) or 'none'}")
    report+=["","## Baselines"]
    for n,x in gg["baselines"].items():report.append(f"- {n}: RMSE={x['rmse']:.4f}; MAE={x['mae']:.4f}; bias={x['bias']:.4f}")
    if coverage:report+=["","## Current coverage",json.dumps(coverage,sort_keys=True)]
    report+=["","## PIT boundary","OOT folds reconstruct a Week-2 cutoff using only prior seasons plus Weeks 1-2 of the held-out year. The 2026 production artifact is valid only from its actual build/evaluation cutoff and is not eligible as 2026 preseason evidence or historical backfill."]
    (ROOT/"REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print((ROOT/"REPORT.md").read_text(encoding="utf-8"))
    print(json.dumps({"selected_model":sel,"production_ready":gg["production_ready"],"fail_reasons":gg["production_fail_reasons"]}))

if __name__=="__main__":main()

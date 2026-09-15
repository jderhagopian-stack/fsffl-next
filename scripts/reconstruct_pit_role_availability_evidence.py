from __future__ import annotations

import argparse, json, math
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

POSITIONS=("QB","RB","WR","TE")
POSITIVE_STATES=("depth","usable","starter","premium","elite")
USEFUL_STATES={"usable","starter","premium","elite"}
RELEASE={"CUT","NWT","RFA","RSR","TRC","TRD","TRT","UFA"}
RESERVE={"INA","PUP","RES","RSN","SUS","EXE","E14"}


def q(values,p):
    xs=sorted(float(x) for x in values if pd.notna(x))
    if not xs:return 0.0
    z=p*(len(xs)-1);lo,hi=int(math.floor(z)),int(math.ceil(z));f=z-lo
    return xs[lo] if lo==hi else xs[lo]*(1-f)+xs[hi]*f

def age_band(pos,age):
    if age is None or pd.isna(age):return "unknown"
    if pos=="QB":return "young" if age<=25 else ("prime" if age<=31 else "aging")
    return "young" if age<=23 else ("prime" if age<=27 else "aging")
def kmeans_1d(values,k=5,iters=60):
    xs=sorted(math.log1p(max(0.0,float(v))) for v in values if pd.notna(v) and float(v)>0)
    if len(xs)<k: centers=[sum(xs)/len(xs)]*k if xs else [0.0]*k
    else: centers=[q(xs,(i+.5)/k) for i in range(k)]
    for _ in range(iters):
        groups=[[] for _ in range(k)]
        for x in xs: groups[min(range(k),key=lambda i:abs(x-centers[i]))].append(x)
        new=sorted(sum(g)/len(g) if g else centers[i] for i,g in enumerate(groups))
        if max(abs(a-b) for a,b in zip(new,centers))<1e-9: centers=new;break
        centers=new
    raw=[max(0.0,math.expm1(x)) for x in centers]
    return tuple(raw),tuple((raw[i]+raw[i+1])/2 for i in range(k-1))
def state_for_points(points,bound):
    if float(points)<=0:return "out"
    _,thr=bound;i=0
    while i<len(thr) and float(points)>thr[i]:i+=1
    return POSITIVE_STATES[i]
def pick(df,cands,required=False):
    for c in cands:
        if c in df.columns:return c
    if required:raise RuntimeError(f"missing {cands}; available={list(df.columns)}")
    return None
def norm_status(v): return "" if v is None or pd.isna(v) else str(v).strip().upper()
def restrict_reg(df):
    for c in ("game_type","season_type"):
        if c in df.columns:
            v=df[c].astype(str).str.upper()
            if (v=="REG").any():return df[v=="REG"].copy()
    return df.copy()
def last_value(g,col,order="week"):
    if col is None or col not in g.columns or g.empty:return None
    v=g.sort_values(order)[col].dropna();return v.iloc[-1] if len(v) else None

def smd(a,b):
    a=np.array([float(x) for x in a if pd.notna(x)]);b=np.array([float(x) for x in b if pd.notna(x)])
    if len(a)<2 or len(b)<2:return None
    s=math.sqrt(((len(a)-1)*a.var(ddof=1)+(len(b)-1)*b.var(ddof=1))/max(1,len(a)+len(b)-2))
    return 0.0 if s<=1e-12 else float((a.mean()-b.mean())/s)
def auc(a,b):
    p=np.array([float(x) for x in a if pd.notna(x)]);n=np.array([float(x) for x in b if pd.notna(x)])
    if not len(p) or not len(n):return None
    ranks=pd.Series(np.concatenate([p,n])).rank(method="average").to_numpy();u=ranks[:len(p)].sum()-len(p)*(len(p)+1)/2
    return float(u/(len(p)*len(n)))

def load_nflverse(seasons):
    import nflreadpy as nfl
    pdx=lambda x:x.to_pandas()
    return pdx(nfl.load_players()),pdx(nfl.load_rosters_weekly(seasons)),pdx(nfl.load_depth_charts(seasons)),pdx(nfl.load_injuries(seasons)),pdx(nfl.load_snap_counts(seasons))

def aggregate_rosters(df):
    x=restrict_reg(df);sc,wc=pick(x,["season"],True),pick(x,["week"],True);ic,st=pick(x,["gsis_id","player_id"],True),pick(x,["status"],True);tc=pick(x,["team","club_code"])
    x=x[x[wc].fillna(99).astype(float)<=18].copy();x[ic]=x[ic].astype(str);x["_status"]=x[st].map(norm_status);rows=[]
    for (pid,season),g in x.groupby([ic,sc]):
        if not pid or pid=="nan":continue
        sts=list(g["_status"]);d=max(1,len(sts));teams=[] if tc is None else [str(t) for t in g[tc].dropna() if str(t)];last=norm_status(last_value(g,"_status",wc))
        rows.append({"player_id":pid,"season":int(season),"roster_weeks":len(g),"active_share":sum(s=="ACT" for s in sts)/d,"practice_share":sum(s=="DEV" for s in sts)/d,"reserve_share":sum(s in RESERVE for s in sts)/d,"released_share":sum(s in RELEASE for s in sts)/d,"last_status":last,"last_status_active":float(last=="ACT"),"last_status_practice":float(last=="DEV"),"last_status_reserve":float(last in RESERVE),"last_status_released":float(last in RELEASE),"last_team":str(last_value(g,tc,wc)) if tc else None,"team_count":len(set(teams)) if teams else 0,"status_count":len(set(s for s in sts if s))})
    return pd.DataFrame(rows)
def aggregate_depth(df):
    x=restrict_reg(df);sc,wc=pick(x,["season"],True),pick(x,["week"],True);ic=pick(x,["gsis_id","player_id"],True);rc=pick(x,["depth_team","pos_rank","depth_rank"])
    if rc is None:return pd.DataFrame()
    x[ic]=x[ic].astype(str);x["_rank"]=pd.to_numeric(x[rc],errors="coerce");rows=[]
    for (pid,season),g in x.groupby([ic,sc]):
        v=g.sort_values(wc)["_rank"].dropna()
        if len(v):rows.append({"player_id":pid,"season":int(season),"depth_obs":len(v),"mean_depth_rank":float(v.mean()),"last_depth_rank":float(v.iloc[-1]),"starter_depth_share":float((v<=1).mean()),"depth_rank_trend":float(v.iloc[-1]-v.iloc[0])})
    return pd.DataFrame(rows)
def aggregate_injuries(df):
    x=restrict_reg(df);sc,wc=pick(x,["season"],True),pick(x,["week"],True);ic=pick(x,["gsis_id","player_id"],True);rp=pick(x,["report_status"]);pp=pick(x,["practice_status"]);x[ic]=x[ic].astype(str);rows=[]
    for (pid,season),g in x.groupby([ic,sc]):
        rep=[] if rp is None else [str(v).strip().lower() for v in g[rp].dropna()];pra=[] if pp is None else [str(v).strip().lower() for v in g[pp].dropna()]
        rows.append({"player_id":pid,"season":int(season),"injury_report_weeks":g[wc].nunique(),"injury_out_doubtful_share":sum(v in {"out","doubtful"} for v in rep)/max(1,len(rep)) if rep else 0.0,"practice_dnp_share":sum(("did not" in v) or v in {"dnp","out"} for v in pra)/max(1,len(pra)) if pra else 0.0,"last_report_status":str(last_value(g,rp,wc)) if rp else None})
    return pd.DataFrame(rows)
def aggregate_snaps(snaps,players):
    x=restrict_reg(snaps);pc=pick(x,["pfr_player_id","pfr_id"],True);sc,wc=pick(x,["season"],True),pick(x,["week"],True);pct=pick(x,["offense_pct","offense_snap_pct"],True);sn=pick(x,["offense_snaps"],True);pp=pick(players,["pfr_id","pfr_player_id"],True);pg=pick(players,["gsis_id","player_id"],True)
    m=players[[pp,pg]].dropna().drop_duplicates(pp);m.columns=["_pfr","player_id"];x=x.merge(m,left_on=pc,right_on="_pfr",how="left");audit={"snap_rows":int(len(x)),"mapped_rows":int(x.player_id.notna().sum())};audit["mapping_rate"]=audit["mapped_rows"]/audit["snap_rows"] if audit["snap_rows"] else 0
    x=x[x.player_id.notna()].copy();x.player_id=x.player_id.astype(str);x["_pct"]=pd.to_numeric(x[pct],errors="coerce");
    if len(x["_pct"].dropna()) and x["_pct"].dropna().median()>1.5:x["_pct"]/=100
    x["_snaps"]=pd.to_numeric(x[sn],errors="coerce");rows=[]
    for (pid,season),g in x.groupby(["player_id",sc]):
        v=g.sort_values(wc)["_pct"].dropna()
        if not len(v):continue
        rows.append({"player_id":pid,"season":int(season),"snap_games":len(v),"offense_snaps":float(g["_snaps"].fillna(0).sum()),"mean_offense_pct":float(v.mean()),"last4_offense_pct":float(v.iloc[-4:].mean()),"snap_pct_trend":float(v.iloc[-4:].mean()-v.iloc[:4].mean())})
    return pd.DataFrame(rows),audit

def build_panel(career,*aggs):
    c=career.copy();c.player_id=c.player_id.astype(str);c.season=c.season.astype(int);c.position=c.position.astype(str).str.upper();c=c[c.position.isin(POSITIONS)];by={(r.player_id,int(r.season)):r for r in c.itertuples()};years=c.groupby("player_id").season.apply(lambda s:sorted(set(int(x) for x in s))).to_dict();rows=[]
    for r in c[(c.season>=2012)&(c.season<=2023)].itertuples():
        hist=c[(c.position==r.position)&(c.season<=r.season)&(c.fantasy_points>0)];thr=q(hist.fantasy_points,.25);bound=kmeans_1d(hist.fantasy_points);target=by.get((r.player_id,r.season+1));out="out" if target is None else state_for_points(target.fantasy_points,bound);low=r.fantasy_points>0 and r.fantasy_points<=thr;band=age_band(r.position,getattr(r,"age_years",None));later=target is None and any(y>r.season+1 for y in years.get(r.player_id,[]))
        rows.append({"player_id":r.player_id,"season":int(r.season),"position":r.position,"fantasy_points":float(r.fantasy_points),"age_years":None if pd.isna(getattr(r,"age_years",np.nan)) else float(r.age_years),"experience_years":None if pd.isna(getattr(r,"experience_years",np.nan)) else int(r.experience_years),"age_band":band,"low_end":bool(low),"outcome_state":out,"true_developmental":bool(low and band=="young" and out in USEFUL_STATES),"depth_persistence":bool(low and out=="depth"),"temporary_absence_return":bool(low and target is None and later),"persistent_disappearance":bool(low and target is None and not later),"older_fringe":bool(low and band=="aging")})
    p=pd.DataFrame(rows)
    for a in aggs:
        if a is not None and not a.empty:p=p.merge(a,on=["player_id","season"],how="left")
    for col in ("injury_report_weeks","injury_out_doubtful_share","practice_dnp_share"):
        if col in p.columns:p[col]=p[col].fillna(0.0)
    return p,c

def missing_context(panel,rosters,injuries):
    rr=restrict_reg(rosters).copy();ir=restrict_reg(injuries).copy();ri,rs,rw,st=pick(rr,["gsis_id","player_id"],True),pick(rr,["season"],True),pick(rr,["week"],True),pick(rr,["status"],True);tc=pick(rr,["team","club_code"]);ii,isn=pick(ir,["gsis_id","player_id"],True),pick(ir,["season"],True);rr[ri]=rr[ri].astype(str);rr["_status"]=rr[st].map(norm_status);ir[ii]=ir[ii].astype(str);rows=[]
    for r in panel[panel.low_end & (panel.outcome_state=="out")].itertuples():
        target=r.season+1;rg=rr[(rr[ri]==r.player_id)&(rr[rs].astype(int)==target)];ig=ir[(ir[ii]==r.player_id)&(ir[isn].astype(int)==target)];sts=set(rg._status) if len(rg) else set();has_i=len(ig)>0
        if "RET" in sts:primary="retired"
        elif "SUS" in sts:primary="suspension"
        elif (sts&{"PUP","RSN"}) or (has_i and bool(sts&{"INA","RES","ACT"})):primary="injury_or_reserve"
        elif "DEV" in sts:primary="practice_squad_or_reserve"
        elif sts&{"ACT","INA","RES"}:primary="still_rostered_no_production"
        elif sts&RELEASE:primary="waived_released_unsigned"
        elif has_i:primary="injury_report_without_roster_match"
        else:primary="unknown_unresolvable"
        teams=set(str(x) for x in rg[tc].dropna()) if tc and len(rg) else set();transition=bool(teams and (len(teams)>1 or (getattr(r,"last_team",None) and str(r.last_team) not in teams)))
        rows.append({"player_id":r.player_id,"source_season":int(r.season),"target_season":int(target),"position":r.position,"age_band":r.age_band,"temporary_absence_return":bool(r.temporary_absence_return),"persistent_disappearance":bool(r.persistent_disappearance),"primary_context":primary,"target_roster_rows":len(rg),"target_injury_rows":len(ig),"team_transition":transition,"target_statuses":"|".join(sorted(sts))})
    return pd.DataFrame(rows)
def coverage(panel):
    fam={"weekly_roster":["active_share","last_status"],"depth_chart":["mean_depth_rank","starter_depth_share"],"snap_counts":["mean_offense_pct","last4_offense_pct"],"injury_reports":["injury_report_weeks"]};rows=[]
    for (season,pos),g in panel.groupby(["season","position"]):
        for name,cols in fam.items():
            pr=pd.Series(False,index=g.index)
            for c in cols:
                if c in g.columns:pr|=g[c].notna()
            rows.append({"season":int(season),"position":pos,"family":name,"n":len(g),"covered":int(pr.sum()),"coverage":float(pr.mean())})
    return pd.DataFrame(rows)
def discrimination(panel,features):
    a=panel[panel.true_developmental];b=panel[panel.persistent_disappearance];rows=[]
    for f in features:
        if f not in panel:continue
        x=a[f].dropna();y=b[f].dropna()
        if len(x)<5 or len(y)<5:continue
        z=auc(x,y);rows.append({"feature":f,"true_dev_n":len(x),"disappear_n":len(y),"true_dev_mean":float(x.mean()),"disappear_mean":float(y.mean()),"smd_true_dev_minus_disappear":smd(x,y),"auc_raw_high_predicts_true_dev":z,"auc_absolute_separation":max(z,1-z) if z is not None else None})
    return pd.DataFrame(rows).sort_values("auc_absolute_separation",ascending=False)
def cohort_summary(panel,features):
    groups={"true_developmental":panel[panel.true_developmental],"depth_persistence":panel[panel.depth_persistence],"temporary_absence_return":panel[panel.temporary_absence_return],"persistent_disappearance":panel[panel.persistent_disappearance],"older_fringe":panel[panel.older_fringe]};out={}
    for name,g in groups.items():
        d={"n":int(len(g)),"position_counts":g.position.value_counts().to_dict(),"season_min":int(g.season.min()) if len(g) else None,"season_max":int(g.season.max()) if len(g) else None}
        for f in features:
            if f in g:
                v=g[f].dropna();d[f]={"n":int(len(v)),"mean":float(v.mean()) if len(v) else None,"median":float(v.median()) if len(v) else None}
        out[name]=d
    return out
def era_position(panel,features):
    x=panel.copy();x["era"]=pd.cut(x.season,[2011,2015,2019,2023],labels=["2012-2015","2016-2019","2020-2023"]);rows=[]
    for (era,pos),g in x[x.low_end].groupby(["era","position"],observed=True):
        r={"era":str(era),"position":pos,"n":len(g),"true_dev_n":int(g.true_developmental.sum()),"persistent_disappearance_n":int(g.persistent_disappearance.sum())}
        for f in features:
            if f in g:r[f+"_coverage"]=float(g[f].notna().mean())
        rows.append(r)
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--career-panel",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    career=pd.read_csv(a.career_panel,dtype={"player_id":str});seasons=list(range(2012,2025));players,rosters,depth,injuries,snaps=load_nflverse(seasons)
    (a.output_dir/"source_columns.json").write_text(json.dumps({"players":list(players.columns),"weekly_rosters":list(rosters.columns),"depth_charts":list(depth.columns),"injuries":list(injuries.columns),"snap_counts":list(snaps.columns)},indent=2,sort_keys=True))
    ra=aggregate_rosters(rosters);da=aggregate_depth(depth);ia=aggregate_injuries(injuries);sa,snap_audit=aggregate_snaps(snaps,players);panel,_=build_panel(career,ra,da,ia,sa);missing=missing_context(panel,rosters,injuries);cov=coverage(panel)
    features=["active_share","practice_share","reserve_share","released_share","last_status_active","last_status_practice","last_status_reserve","last_status_released","team_count","mean_depth_rank","last_depth_rank","starter_depth_share","depth_rank_trend","mean_offense_pct","last4_offense_pct","snap_pct_trend","injury_report_weeks","injury_out_doubtful_share","practice_dnp_share"]
    disc=discrimination(panel,features);cohorts=cohort_summary(panel,features);era=era_position(panel,["active_share","mean_depth_rank","mean_offense_pct"])
    cc=missing.primary_context.value_counts().to_dict() if len(missing) else {};resolved=sum(v for k,v in cc.items() if k!="unknown_unresolvable");ms={"n":len(missing),"counts":{str(k):int(v) for k,v in cc.items()},"resolved_context_n":int(resolved),"resolved_context_share":resolved/len(missing) if len(missing) else 0,"unknown_share":cc.get("unknown_unresolvable",0)/len(missing) if len(missing) else 0,"team_transition_share":float(missing.team_transition.mean()) if len(missing) else 0}
    for flag in ("temporary_absence_return","persistent_disappearance"):
        g=missing[missing[flag]] if len(missing) else missing;ms[flag]={"n":len(g),"context_counts":{str(k):int(v) for k,v in g.primary_context.value_counts().to_dict().items()} if len(g) else {}}
    sc={"weekly_rosters":{"rows":len(rosters),"seasons":[int(rosters.season.min()),int(rosters.season.max())]},"depth_charts":{"rows":len(depth),"seasons":[int(depth.season.min()),int(depth.season.max())]},"injuries":{"rows":len(injuries),"seasons":[int(injuries.season.min()),int(injuries.season.max())]},"snap_counts":{"rows":len(snaps),"seasons":[int(snaps.season.min()),int(snaps.season.max())],**snap_audit}}
    broad=[]
    for fam in ("weekly_roster","depth_chart","snap_counts"):
        g=cov[cov.family==fam];ok=True
        for pos in POSITIONS:
            z=g[g.position==pos];ok=ok and len(z)>0 and z.covered.sum()/z.n.sum()>=.80
        if ok:broad.append(fam)
    strong=disc[(disc.auc_absolute_separation>=.60)&(disc.true_dev_n>=30)&(disc.disappear_n>=30)]
    gate={"core_families_ge80_each_position":broad,"resolved_missing_context_share":ms["resolved_context_share"],"strong_univariate_features":strong[["feature","auc_raw_high_predicts_true_dev","auc_absolute_separation","true_dev_n","disappear_n"]].to_dict("records"),"passes_descriptive_e1_signal_gate":bool(len(broad)>=2 and ms["resolved_context_share"]>=.70 and len(strong)>=2)}
    panel.to_csv(a.output_dir/"pit_role_availability_panel.csv",index=False);missing.to_csv(a.output_dir/"missing_row_contexts.csv",index=False);cov.to_csv(a.output_dir/"coverage_by_season_position.csv",index=False);disc.to_csv(a.output_dir/"descriptive_discrimination.csv",index=False);era.to_csv(a.output_dir/"era_position_coverage.csv",index=False)
    status=Counter(rosters[pick(rosters,["status"],True)].dropna().astype(str).str.upper())
    csum=cov.groupby("family").agg(n=("n","sum"),covered=("covered","sum"));csum["coverage"]=csum.covered/csum.n
    payload={"study":"pit-role-availability-evidence-reconstruction-v1","source_seasons_for_evidence":[2012,2024],"descriptive_source_seasons":[2012,2023],"source_counts":sc,"weekly_roster_status_counts":dict(status),"snap_id_mapping":snap_audit,"cohorts":cohorts,"missing_row_context":ms,"evidence_gate":gate,"coverage_summary":csum.reset_index().to_dict("records"),"discrimination_top":disc.head(20).to_dict("records"),"no_model_treatment_run":True,"notes":["Predictor-side role/availability features use only the completed source season.","Next-season roster/injury context is descriptive outcome context only.","Outcome groups are descriptive labels, not fitted features."]}
    (a.output_dir/"pit_role_availability_evidence_results.json").write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps({"evidence_gate":gate,"missing":ms,"top_discrimination":payload["discrimination_top"][:8],"coverage":payload["coverage_summary"],"snap_mapping":snap_audit,"cohort_ns":{k:v["n"] for k,v in cohorts.items()}},indent=2,sort_keys=True))
if __name__=="__main__":main()

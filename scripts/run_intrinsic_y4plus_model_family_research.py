from __future__ import annotations

import argparse
import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

OUT = Path("artifacts/research/intrinsic_y4plus_model_family_20260926")
POSITIONS = ("QB","RB","WR","TE")
HORIZONS = (4,5,6,7,8)
FAMILIES = (
    "carry_y3",
    "direct_ridge",
    "two_part_state",
    "conditional_cohort",
    "survival_hazard",
    "career_state_transition",
)
COMPLEXITY = {
    "carry_y3":0.0,
    "direct_ridge":1.0,
    "two_part_state":1.4,
    "conditional_cohort":1.2,
    "survival_hazard":1.6,
    "career_state_transition":1.8,
}
SWITCH_PENALTY = 0.025
HOLDOUT_TOLERANCE = 0.10
MIN_CELL_N = 25
MIN_DEV_STABILITY = 0.50
RANDOM_SEED = 20260926
FEATURES = (
    "age","experience","prior_pct","log_prior_points","log_y1",
    "y1_pct","y2_ratio","y3_ratio","y2_delta","y3_delta",
)

def load_module(path: str):
    spec=importlib.util.spec_from_file_location("hist",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen historical helper")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def safe_ratio(a,b,default=1.0):
    if b is None or not np.isfinite(b) or abs(b)<1e-12:
        return default
    return float(a)/float(b)

def spearman(a,b):
    a=pd.Series(list(a),dtype=float)
    b=pd.Series(list(b),dtype=float)
    if len(a)<2 or a.nunique()<2 or b.nunique()<2:
        return float("nan")
    return float(a.corr(b,method="spearman"))

def state_brier(prob_cols: np.ndarray, actual_state: np.ndarray) -> float:
    if len(actual_state)==0:
        return float("nan")
    y=np.zeros_like(prob_cols,dtype=float)
    y[np.arange(len(actual_state)),actual_state.astype(int)]=1.0
    return float(np.mean(np.sum((prob_cols-y)**2,axis=1)))

def metrics(df: pd.DataFrame) -> dict[str,float|int|None]:
    if len(df)==0:
        return {"n":0}
    pred=df["pred"].to_numpy(float)
    actual=df["actual"].to_numpy(float)
    err=pred-actual
    out={
        "n":int(len(df)),
        "mae":float(np.mean(np.abs(err))),
        "rmse":float(np.sqrt(np.mean(err*err))),
        "bias":float(np.mean(err)),
        "spearman":spearman(pred,actual),
        "actual_active_rate":float(np.mean(actual>0)),
    }
    if "p_active" in df and df["p_active"].notna().any():
        p=df["p_active"].fillna(df["p_active"].mean()).clip(0,1).to_numpy(float)
        y=(actual>0).astype(float)
        out["survival_brier"]=float(np.mean((p-y)**2))
        out["survival_calibration_gap"]=float(abs(np.mean(p)-np.mean(y)))
    else:
        out["survival_brier"]=None
        out["survival_calibration_gap"]=None
    if all(c in df for c in ("p_state0","p_state1","p_state2","p_state3","actual_state")):
        p=df[["p_state0","p_state1","p_state2","p_state3"]].to_numpy(float)
        out["state_brier"]=state_brier(p,df["actual_state"].to_numpy(int))
    else:
        out["state_brier"]=None
    return out

def add_base_features(base: pd.DataFrame) -> pd.DataFrame:
    b=base.copy()
    b["y3_pct"]=b.groupby(["season","position"])["y3"].rank(pct=True,method="average")
    return b

def horizon_frame(base: pd.DataFrame, player: pd.DataFrame, horizon: int) -> pd.DataFrame:
    pm={(str(r.player_id),int(r.season)):max(0.0,float(r.fantasy_points)) for r in player.itertuples()}
    x=base.copy()
    x["target_season"]=x["season"]+horizon-1
    x["actual"]=[pm.get((str(pid),int(ts)),0.0) for pid,ts in zip(x.player_id,x.target_season)]
    return x

def eval_folds(player: pd.DataFrame, horizon: int) -> tuple[tuple[int,...],tuple[int,...]]:
    max_complete=int(player["season"].max())-horizon+1
    holdout=tuple(range(max_complete-2,max_complete+1))
    dev=tuple(range(2012,max_complete-2))
    return dev,holdout

def prep_matrix(df: pd.DataFrame, features=FEATURES, med=None):
    X=df[list(features)].astype(float).copy()
    if med is None:
        med=X.median(numeric_only=True).fillna(0)
    return X.fillna(med).to_numpy(float),med

def constant_survival(train: pd.DataFrame) -> float:
    return float((train["actual"]>0).mean()) if len(train) else 0.0

def predict_direct(hist, train: pd.DataFrame, ev: pd.DataFrame, pos: str):
    model=hist.fit_position_models(train,pos)
    if "scaler" not in model:
        pred=np.repeat(max(0.0,float(model["fallback"])),len(ev))
    else:
        X,_=hist.prep_matrix(ev,model["med"])
        pred=np.expm1(model["ridge_direct"].predict(model["scaler"].transform(X))).clip(0,600)
    return pred,np.repeat(constant_survival(train),len(ev))

def predict_two_part(hist, train: pd.DataFrame, ev: pd.DataFrame, pos: str):
    model=hist.fit_position_models(train,pos)
    if "scaler" not in model:
        pred=np.repeat(max(0.0,float(model["fallback"])),len(ev))
        p=np.repeat(constant_survival(train),len(ev))
        return pred,p
    X,_=hist.prep_matrix(ev,model["med"])
    Z=model["scaler"].transform(X)
    p=np.repeat(float(model["surv_mean"]),len(ev)) if model["logit"] is None else model["logit"].predict_proba(Z)[:,1]
    cp=np.repeat(float(model["positive_mean"]),len(ev)) if model["ridge_pos"] is None else np.expm1(model["ridge_pos"].predict(Z)).clip(0,600)
    return (p*cp).clip(0,600),p

def quantile_edges(values: pd.Series, q=(1/3,2/3)):
    v=pd.to_numeric(values,errors="coerce").dropna()
    if len(v)<10:
        return (-math.inf,math.inf)
    cuts=[float(v.quantile(z)) for z in q]
    cuts=sorted(set(cuts))
    return tuple([-math.inf]+cuts+[math.inf])

def assign_bin(values: pd.Series, edges):
    arr=np.asarray(values,dtype=float)
    return np.digitize(arr,np.asarray(edges[1:-1],dtype=float),right=True)

def predict_conditional_cohort(hist, train: pd.DataFrame, ev: pd.DataFrame, pos: str):
    tr=train.copy()
    age_edges=quantile_edges(tr["age"])
    tr["age_bin"]=assign_bin(tr["age"].fillna(tr["age"].median()),age_edges)
    tr["y3_bin"]=np.clip((tr["y3_pct"].fillna(.5)*4).astype(int),0,3)
    overall=float((tr["actual"]>0).mean())
    prior_strength=20.0
    grouped=tr.groupby(["age_bin","y3_bin"])["actual"].agg(["count",lambda s:float((s>0).sum())])
    p_map={}
    for idx,row in grouped.iterrows():
        n=float(row["count"])
        k=float(row["<lambda_0>"])
        p_map[idx]=(k+prior_strength*overall)/(n+prior_strength)
    age_med=float(tr["age"].median()) if tr["age"].notna().any() else 27.0
    e=ev.copy()
    e["age_bin"]=assign_bin(e["age"].fillna(age_med),age_edges)
    e["y3_bin"]=np.clip((e["y3_pct"].fillna(.5)*4).astype(int),0,3)
    p=np.array([p_map.get((int(a),int(y)),overall) for a,y in zip(e.age_bin,e.y3_bin)],dtype=float)

    posrows=tr[tr["actual"]>0].copy()
    if len(posrows)<20:
        cp=np.repeat(float(posrows["actual"].mean()) if len(posrows) else 0.0,len(ev))
    else:
        X,med=prep_matrix(posrows)
        sc=StandardScaler().fit(X)
        rg=Ridge(alpha=10.0).fit(sc.transform(X),np.log1p(posrows["actual"].to_numpy(float)))
        Xe,_=prep_matrix(ev,med=med)
        cp=np.expm1(rg.predict(sc.transform(Xe))).clip(0,600)
    return (p*cp).clip(0,600),p

def build_transition_rows(base: pd.DataFrame, player: pd.DataFrame, cutoff: int, max_horizon: int):
    pm={(str(r.player_id),int(r.season)):max(0.0,float(r.fantasy_points)) for r in player.itertuples()}
    rows=[]
    for r in base[base["season"]<cutoff].itertuples():
        for step in range(4,max_horizon+1):
            target=int(r.season)+step-1
            prev_year=target-1
            if target>=cutoff:
                continue
            prev_active=1.0 if pm.get((str(r.player_id),prev_year),0.0)>0 else 0.0
            active=1.0 if pm.get((str(r.player_id),target),0.0)>0 else 0.0
            d={f:getattr(r,f) for f in FEATURES}
            d.update({
                "player_id":r.player_id,"position":r.position,"base_season":int(r.season),
                "step":step,"prev_active":prev_active,"active":active,
                "actual":pm.get((str(r.player_id),target),0.0),
            })
            rows.append(d)
    return pd.DataFrame(rows)

def predict_survival_hazard(hist, base: pd.DataFrame, player: pd.DataFrame, cutoff: int, horizon: int, ev: pd.DataFrame, pos: str):
    tr=build_transition_rows(base,player,cutoff,horizon)
    tr=tr[tr["position"]==pos].copy()
    # Initial probability of being active in Y3 from base features.
    pm={(str(r.player_id),int(r.season)):max(0.0,float(r.fantasy_points)) for r in player.itertuples()}
    init=base[(base["position"]==pos)&(base["season"]<cutoff)&((base["season"]+2)<cutoff)].copy()
    init["active3"]=[1.0 if pm.get((str(pid),int(s)+2),0.0)>0 else 0.0 for pid,s in zip(init.player_id,init.season)]
    X0,med0=prep_matrix(init)
    sc0=StandardScaler().fit(X0)
    if init["active3"].nunique()>1:
        lg0=LogisticRegression(C=1.0,solver="lbfgs",max_iter=2000,random_state=RANDOM_SEED).fit(sc0.transform(X0),init["active3"].astype(int))
        Xe,_=prep_matrix(ev,med=med0)
        p=lg0.predict_proba(sc0.transform(Xe))[:,1]
    else:
        p=np.repeat(float(init["active3"].mean()),len(ev))

    trans_features=FEATURES+("step","prev_active")
    Xt,medt=prep_matrix(tr,trans_features)
    sct=StandardScaler().fit(Xt)
    if tr["active"].nunique()>1:
        lgt=LogisticRegression(C=1.0,solver="lbfgs",max_iter=2500,random_state=RANDOM_SEED).fit(sct.transform(Xt),tr["active"].astype(int))
        for step in range(4,horizon+1):
            e1=ev.copy(); e0=ev.copy()
            e1["step"]=step; e0["step"]=step
            e1["prev_active"]=1.0; e0["prev_active"]=0.0
            X1,_=prep_matrix(e1,trans_features,med=medt)
            X0e,_=prep_matrix(e0,trans_features,med=medt)
            p1=lgt.predict_proba(sct.transform(X1))[:,1]
            p0=lgt.predict_proba(sct.transform(X0e))[:,1]
            p=p*p1+(1-p)*p0
    else:
        p=np.repeat(float(tr["active"].mean()),len(ev))

    # Conditional production at requested horizon.
    hf=horizon_frame(base,player,horizon)
    ctrain=hf[(hf["position"]==pos)&(hf["season"]<cutoff)&(hf["target_season"]<cutoff)&(hf["actual"]>0)].copy()
    if len(ctrain)<20:
        cp=np.repeat(float(ctrain["actual"].mean()) if len(ctrain) else 0.0,len(ev))
    else:
        Xc,medc=prep_matrix(ctrain)
        scc=StandardScaler().fit(Xc)
        rg=Ridge(alpha=10.0).fit(scc.transform(Xc),np.log1p(ctrain["actual"].to_numpy(float)))
        Xe,_=prep_matrix(ev,med=medc)
        cp=np.expm1(rg.predict(scc.transform(Xe))).clip(0,600)
    return (p*cp).clip(0,600),p

def state_thresholds(player: pd.DataFrame, cutoff: int, pos: str):
    x=player[(player["position"]==pos)&(player["season"]<cutoff)&(player["fantasy_points"]>0)]["fantasy_points"]
    if len(x)<20:
        return (50.0,150.0)
    return (float(x.quantile(1/3)),float(x.quantile(2/3)))

def to_state(points, thresholds):
    a=np.asarray(points,dtype=float)
    lo,hi=thresholds
    out=np.zeros(len(a),dtype=int)
    out[(a>0)&(a<=lo)]=1
    out[(a>lo)&(a<=hi)]=2
    out[a>hi]=3
    return out

def age_edges_for_transition(rows: pd.DataFrame):
    return quantile_edges(rows["transition_age"])

def predict_career_state(hist, base: pd.DataFrame, player: pd.DataFrame, cutoff: int, horizon: int, ev: pd.DataFrame, pos: str):
    pm={(str(r.player_id),int(r.season)):max(0.0,float(r.fantasy_points)) for r in player.itertuples()}
    thresholds=state_thresholds(player,cutoff,pos)
    seq=[]
    base_pos=base[(base["position"]==pos)&(base["season"]<cutoff)].copy()
    for r in base_pos.itertuples():
        for step in range(4,horizon+1):
            target=int(r.season)+step-1
            prev_year=target-1
            if target>=cutoff:
                continue
            prev_pts=pm.get((str(r.player_id),prev_year),0.0)
            cur_pts=pm.get((str(r.player_id),target),0.0)
            prev_state=int(to_state([prev_pts],thresholds)[0])
            cur_state=int(to_state([cur_pts],thresholds)[0])
            seq.append({
                "prev_state":prev_state,"cur_state":cur_state,
                "transition_age":float(r.age)+step-2 if pd.notna(r.age) else np.nan,
                "cur_points":cur_pts,
            })
    tr=pd.DataFrame(seq)
    if len(tr)<40:
        p=np.zeros((len(ev),4)); p[:,0]=1.0
        return np.zeros(len(ev)),np.zeros(len(ev)),p

    age_edges=age_edges_for_transition(tr)
    age_med=float(tr["transition_age"].median()) if tr["transition_age"].notna().any() else 27.0
    tr["age_bin"]=assign_bin(tr["transition_age"].fillna(age_med),age_edges)

    global_counts=np.ones((4,4),dtype=float)
    for a,b in zip(tr.prev_state,tr.cur_state):
        global_counts[int(a),int(b)]+=1.0
    global_mat=global_counts/global_counts.sum(axis=1,keepdims=True)

    mats={}
    means={}
    for age_bin,g in tr.groupby("age_bin"):
        counts=np.zeros((4,4),dtype=float)
        for a,b in zip(g.prev_state,g.cur_state):
            counts[int(a),int(b)]+=1.0
        counts += 8.0*global_mat
        mats[int(age_bin)]=counts/counts.sum(axis=1,keepdims=True)
        for state in range(4):
            pts=g.loc[g.cur_state==state,"cur_points"]
            global_pts=tr.loc[tr.cur_state==state,"cur_points"]
            gmean=float(global_pts.mean()) if len(global_pts) else 0.0
            means[(int(age_bin),state)]=(float(pts.sum())+10.0*gmean)/(len(pts)+10.0)

    # Start from Y3 forecast state deterministically; no named-player tuning.
    start=to_state(ev["y3"].to_numpy(float),thresholds)
    dist=np.zeros((len(ev),4),dtype=float)
    dist[np.arange(len(ev)),start]=1.0
    for step in range(4,horizon+1):
        ages=ev["age"].fillna(ev["age"].median()).to_numpy(float)+step-2
        bins=assign_bin(pd.Series(ages),age_edges)
        nextd=np.zeros_like(dist)
        for i,b in enumerate(bins):
            mat=mats.get(int(b),global_mat)
            nextd[i]=dist[i]@mat
        dist=nextd
    # Expected production by final state and projected age bin.
    final_ages=ev["age"].fillna(ev["age"].median()).to_numpy(float)+horizon-2
    bins=assign_bin(pd.Series(final_ages),age_edges)
    pred=np.zeros(len(ev),dtype=float)
    for i,b in enumerate(bins):
        vals=np.array([means.get((int(b),s),float(tr.loc[tr.cur_state==s,"cur_points"].mean()) if (tr.cur_state==s).any() else 0.0) for s in range(4)])
        pred[i]=float(dist[i]@vals)
    p_active=1.0-dist[:,0]
    return pred.clip(0,600),p_active,dist

def predict_family(hist, family: str, base: pd.DataFrame, player: pd.DataFrame, cutoff: int, horizon: int, train: pd.DataFrame, ev: pd.DataFrame, pos: str):
    if family=="carry_y3":
        pred=ev["y3"].clip(lower=0).to_numpy(float)
        p=np.repeat(constant_survival(train),len(ev))
        return pred,p,None
    if family=="direct_ridge":
        pred,p=predict_direct(hist,train,ev,pos)
        return pred,p,None
    if family=="two_part_state":
        pred,p=predict_two_part(hist,train,ev,pos)
        return pred,p,None
    if family=="conditional_cohort":
        pred,p=predict_conditional_cohort(hist,train,ev,pos)
        return pred,p,None
    if family=="survival_hazard":
        pred,p=predict_survival_hazard(hist,base,player,cutoff,horizon,ev,pos)
        return pred,p,None
    if family=="career_state_transition":
        pred,p,dist=predict_career_state(hist,base,player,cutoff,horizon,ev,pos)
        return pred,p,dist
    raise KeyError(family)

def outcome_state(player: pd.DataFrame, cutoff: int, pos: str, values: pd.Series):
    return to_state(values.to_numpy(float),state_thresholds(player,cutoff,pos))

def build_oot_predictions(hist, base: pd.DataFrame, player: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for h in HORIZONS:
        hf=horizon_frame(base,player,h)
        dev,hold=eval_folds(player,h)
        for segment,folds in (("development",dev),("holdout",hold)):
            for T in folds:
                ev_all=hf[hf["season"]==T].copy()
                train_all=hf[(hf["season"]<T)&(hf["target_season"]<T)].copy()
                if len(ev_all)==0 or len(train_all)<150:
                    continue
                for pos in POSITIONS:
                    ev=ev_all[ev_all["position"]==pos].copy()
                    train=train_all[train_all["position"]==pos].copy()
                    if len(ev)==0 or len(train)<30:
                        continue
                    actual_state=outcome_state(player,T,pos,ev["actual"])
                    for family in FAMILIES:
                        pred,p,dist=predict_family(hist,family,base,player,T,h,train,ev,pos)
                        for i,r in enumerate(ev.itertuples()):
                            rec={
                                "segment":segment,"fold":T,"horizon":h,"position":pos,
                                "player_id":r.player_id,"family":family,
                                "pred":float(pred[i]),"actual":float(r.actual),
                                "p_active":float(p[i]) if p is not None else np.nan,
                                "actual_state":int(actual_state[i]),
                            }
                            if dist is not None:
                                for s in range(4):
                                    rec[f"p_state{s}"]=float(dist[i,s])
                            rows.append(rec)
    return pd.DataFrame(rows)

def metric_table(pred: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (segment,h,pos,fam),g in pred.groupby(["segment","horizon","position","family"]):
        rows.append({"segment":segment,"horizon":int(h),"position":pos,"family":fam,**metrics(g)})
    return pd.DataFrame(rows)

def season_metric_table(pred: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (segment,fold,h,pos,fam),g in pred.groupby(["segment","fold","horizon","position","family"]):
        rows.append({"segment":segment,"fold":int(fold),"horizon":int(h),"position":pos,"family":fam,**metrics(g)})
    return pd.DataFrame(rows)

def score_from_metrics(row: pd.Series, base: pd.Series) -> float:
    eps=1e-6
    rmse=max(eps,float(row.rmse)); brmse=max(eps,float(base.rmse))
    mae=max(eps,float(row.mae)); bmae=max(eps,float(base.mae))
    brier=float(row.survival_brier) if pd.notna(row.survival_brier) else float(base.survival_brier)
    bbrier=float(base.survival_brier) if pd.notna(base.survival_brier) else 0.25
    rank=float(row.spearman) if pd.notna(row.spearman) else -1.0
    brank=float(base.spearman) if pd.notna(base.spearman) else -1.0
    gap=float(row.survival_calibration_gap) if pd.notna(row.survival_calibration_gap) else float(base.survival_calibration_gap)
    bgap=float(base.survival_calibration_gap) if pd.notna(base.survival_calibration_gap) else 0.0
    return (
        0.35*math.log(rmse/brmse)
        +0.25*math.log(mae/bmae)
        +0.15*math.log((brier+0.01)/(bbrier+0.01))
        +0.15*(brank-rank)
        +0.10*(gap-bgap)
        +0.015*COMPLEXITY[str(row.family)]
    )

def cell_scores(m: pd.DataFrame, segment="development") -> pd.DataFrame:
    rows=[]
    x=m[m["segment"]==segment]
    for (h,pos),g in x.groupby(["horizon","position"]):
        base=g[g.family=="carry_y3"]
        if len(base)!=1:
            continue
        b=base.iloc[0]
        for _,r in g.iterrows():
            rows.append({
                "segment":segment,"horizon":int(h),"position":pos,"family":r.family,
                "score":score_from_metrics(r,b),
                "n":int(r["n"]),
            })
    return pd.DataFrame(rows)

def dev_stability(pred: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    out=[]
    dp=pred[pred.segment=="development"]
    for h in HORIZONS:
        for pos in POSITIONS:
            cell=scores[(scores.horizon==h)&(scores.position==pos)]
            if cell.empty:
                continue
            full=cell.sort_values(["score","family"]).iloc[0].family
            folds=sorted(dp[(dp.horizon==h)&(dp.position==pos)].fold.unique())
            winners=[]
            for omit in folds:
                sub=dp[(dp.horizon==h)&(dp.position==pos)&(dp.fold!=omit)]
                mm=[]
                for fam,g in sub.groupby("family"):
                    z=metrics(g)
                    mm.append({"family":fam,**z})
                mm=pd.DataFrame(mm)
                b=mm[mm.family=="carry_y3"]
                if len(b)!=1:
                    continue
                b=b.iloc[0]
                mm["score"]=[score_from_metrics(r,b) for _,r in mm.iterrows()]
                winners.append(str(mm.sort_values(["score","family"]).iloc[0].family))
            agree=float(np.mean([w==full for w in winners])) if winners else 0.0
            out.append({"horizon":h,"position":pos,"full_dev_winner":full,"leave_one_fold_agreement":agree,"dev_folds":len(folds)})
    return pd.DataFrame(out)

def dp_route(scores: pd.DataFrame, position: str):
    s=scores[scores.position==position]
    fams=list(FAMILIES)
    dp={}
    parent={}
    for i,h in enumerate(HORIZONS):
        cell={r.family:float(r.score) for _,r in s[s.horizon==h].iterrows()}
        if i==0:
            for f in fams:
                dp[(h,f)]=cell.get(f,999)
                parent[(h,f)]=None
        else:
            prev=HORIZONS[i-1]
            for f in fams:
                best=None
                for pf in fams:
                    v=dp[(prev,pf)]+cell.get(f,999)+(SWITCH_PENALTY if pf!=f else 0.0)
                    cand=(v,pf)
                    if best is None or cand<best:
                        best=cand
                dp[(h,f)]=best[0]
                parent[(h,f)]=best[1]
    last=HORIZONS[-1]
    end=min(fams,key=lambda f:(dp[(last,f)],f))
    route={}
    f=end
    for h in reversed(HORIZONS):
        route[h]=f
        f=parent[(h,f)] if parent[(h,f)] is not None else f
    return {h:route[h] for h in HORIZONS},float(dp[(last,end)])

def global_and_position_models(scores: pd.DataFrame):
    global_loss={}
    for fam in FAMILIES:
        z=scores[scores.family==fam]
        global_loss[fam]=float(z.score.sum()) if len(z)==len(POSITIONS)*len(HORIZONS) else 999.0
    global_family=min(global_loss,key=lambda f:(global_loss[f],f))
    position={}
    for pos in POSITIONS:
        losses={}
        for fam in FAMILIES:
            z=scores[(scores.position==pos)&(scores.family==fam)]
            losses[fam]=float(z.score.sum()) if len(z)==len(HORIZONS) else 999.0
        position[pos]=min(losses,key=lambda f:(losses[f],f))
    return global_family,global_loss,position

def confirmation(row: pd.Series, carry: pd.Series) -> tuple[bool,list[str]]:
    reasons=[]
    if int(row["n"])<MIN_CELL_N:
        reasons.append("sparse_n")
    if float(row.rmse)>HOLDOUT_TOLERANCE*float(carry.rmse)+float(carry.rmse):
        reasons.append("rmse_regression")
    if float(row.mae)>HOLDOUT_TOLERANCE*float(carry.mae)+float(carry.mae):
        reasons.append("mae_regression")
    if pd.notna(row.spearman) and pd.notna(carry.spearman) and float(row.spearman)<float(carry.spearman)-0.05:
        reasons.append("rank_regression")
    if pd.notna(row.survival_brier) and pd.notna(carry.survival_brier) and float(row.survival_brier)>1.10*float(carry.survival_brier):
        reasons.append("survival_regression")
    wins=sum([
        float(row.rmse)<=float(carry.rmse),
        float(row.mae)<=float(carry.mae),
        (pd.isna(row.spearman) or pd.isna(carry.spearman) or float(row.spearman)>=float(carry.spearman)),
        (pd.isna(row.survival_brier) or pd.isna(carry.survival_brier) or float(row.survival_brier)<=float(carry.survival_brier)),
    ])
    if wins<2:
        reasons.append("insufficient_metric_wins")
    return len(reasons)==0,reasons

def build_route(m: pd.DataFrame, pred: pd.DataFrame):
    devscores=cell_scores(m,"development")
    stability=dev_stability(pred,devscores)
    global_family,global_loss,position_family=global_and_position_models(devscores)
    routes={}
    route_loss={}
    for pos in POSITIONS:
        routes[pos],route_loss[pos]=dp_route(devscores,pos)

    hold=m[m.segment=="holdout"].copy()
    rows=[]
    for pos in POSITIONS:
        for h in HORIZONS:
            selected=routes[pos][h]
            sg=hold[(hold.position==pos)&(hold.horizon==h)&(hold.family==selected)]
            carry=hold[(hold.position==pos)&(hold.horizon==h)&(hold.family=="carry_y3")]
            inc=hold[(hold.position==pos)&(hold.horizon==h)&(hold.family=="two_part_state")]
            stab=stability[(stability.position==pos)&(stability.horizon==h)]
            if len(sg)!=1 or len(carry)!=1:
                continue
            ok,reasons=confirmation(sg.iloc[0],carry.iloc[0])
            stab_rate=float(stab.iloc[0].leave_one_fold_agreement) if len(stab) else 0.0
            if stab_rate<MIN_DEV_STABILITY:
                ok=False
                reasons.append("dev_route_instability")
            final=selected
            fallback_reason=""
            if not ok:
                if len(inc)==1:
                    iok,_=confirmation(inc.iloc[0],carry.iloc[0])
                    final="two_part_state" if iok else "carry_y3"
                else:
                    final="carry_y3"
                fallback_reason=";".join(sorted(set(reasons)))
            rows.append({
                "position":pos,"horizon":h,
                "dev_selected_family":selected,
                "dev_leave_one_fold_agreement":stab_rate,
                "holdout_confirmed":ok,
                "final_research_route_family":final,
                "fallback_reason":fallback_reason,
                "global_family":global_family,
                "position_only_family":position_family[pos],
            })
    return pd.DataFrame(rows),{
        "global_family":global_family,
        "global_family_dev_loss":global_loss,
        "position_only_family":position_family,
        "dynamic_route_dev_loss_by_position":route_loss,
        "switch_penalty":SWITCH_PENALTY,
        "holdout_tolerance":HOLDOUT_TOLERANCE,
        "min_cell_n":MIN_CELL_N,
        "min_dev_stability":MIN_DEV_STABILITY,
    },devscores,stability

def routed_predictions(pred: pd.DataFrame, route: pd.DataFrame, family_col: str) -> pd.DataFrame:
    keys=route[["position","horizon",family_col]].rename(columns={family_col:"family"})
    x=pred.merge(keys,on=["position","horizon","family"],how="inner")
    return x

def route_metrics(pred: pd.DataFrame, route: pd.DataFrame, summary: dict):
    rows=[]
    hp=pred[pred.segment=="holdout"].copy()
    # Dynamic final route.
    for label,family_col in (("dynamic_route","final_research_route_family"),):
        rp=routed_predictions(hp,route,family_col)
        for h,g in rp.groupby("horizon"):
            rows.append({"architecture":label,"horizon":int(h),"position":"ALL",**metrics(g)})
    # Position-only, global, incumbent, carry.
    for label in ("position_only","global","two_part_state","carry_y3"):
        if label=="position_only":
            temp=route[["position","horizon","position_only_family"]].rename(columns={"position_only_family":"family"})
            rp=hp.merge(temp,on=["position","horizon","family"],how="inner")
        elif label=="global":
            rp=hp[hp.family==summary["global_family"]]
        else:
            rp=hp[hp.family==label]
        for h,g in rp.groupby("horizon"):
            rows.append({"architecture":label,"horizon":int(h),"position":"ALL",**metrics(g)})
    return pd.DataFrame(rows)

def uncertainty_route(pred: pd.DataFrame, route: pd.DataFrame):
    hp=pred[pred.segment=="holdout"].copy()
    rp=routed_predictions(hp,route,"final_research_route_family")
    rows=[]
    for pos in POSITIONS:
        prev=0.0
        for h in HORIZONS:
            g=rp[(rp.position==pos)&(rp.horizon==h)]
            if len(g)==0:
                continue
            e=g.pred.to_numpy(float)-g.actual.to_numpy(float)
            rmse=float(np.sqrt(np.mean(e*e)))
            p68=float(np.quantile(np.abs(e),0.68))
            p90=float(np.quantile(np.abs(e),0.90))
            floor=max(prev,rmse)
            prev=floor
            rows.append({
                "position":pos,"horizon":h,"n":len(g),
                "raw_rmse":rmse,"abs_error_p68":p68,"abs_error_p90":p90,
                "monotone_rmse_floor":floor,
            })
    return pd.DataFrame(rows)

def breakpoint_summary(route: pd.DataFrame):
    out={}
    for pos in POSITIONS:
        x=route[route.position==pos].sort_values("horizon")
        seq=[(int(r.horizon),str(r.final_research_route_family),bool(r.holdout_confirmed)) for r in x.itertuples()]
        changes=[]
        prev=None
        for h,f,ok in seq:
            if prev is not None and f!=prev[1]:
                changes.append({"between":[prev[0],h],"from":prev[1],"to":f})
            prev=(h,f,ok)
        out[pos]={"route":seq,"empirical_breakpoints":changes}
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-module",default="scripts/run_intrinsic_term_structure_research.py")
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--player-seasons",required=True)
    args=ap.parse_args()

    OUT.mkdir(parents=True,exist_ok=True)
    hist=load_module(args.history_module)
    m=pd.read_csv(args.model_a_rows)
    q=json.loads(Path(args.qb_results).read_text())
    player=pd.read_csv(args.player_seasons)
    m,_=hist.integrate_qb(m,q)
    base=add_base_features(hist.build_base(m,player))

    pred=build_oot_predictions(hist,base,player)
    mt=metric_table(pred)
    sm=season_metric_table(pred)
    route,summary,devscores,stability=build_route(mt,pred)
    arch=route_metrics(pred,route,summary)
    unc=uncertainty_route(pred,route)
    breakpoints=breakpoint_summary(route)

    pred.to_csv(OUT/"OOT_PREDICTIONS.csv",index=False)
    mt.to_csv(OUT/"COMPARATIVE_MODEL_MATRIX.csv",index=False)
    sm.to_csv(OUT/"HOLDOUT_SEASON_METRICS.csv",index=False)
    devscores.to_csv(OUT/"DEVELOPMENT_CELL_SCORES.csv",index=False)
    stability.to_csv(OUT/"DEVELOPMENT_ROUTE_STABILITY.csv",index=False)
    route.to_csv(OUT/"EMPIRICAL_ROUTING.csv",index=False)
    arch.to_csv(OUT/"ARCHITECTURE_HOLDOUT_METRICS.csv",index=False)
    unc.to_csv(OUT/"ROUTED_UNCERTAINTY.csv",index=False)

    # Production H3 is preserved: Y1-Y3 forecasts are features of these Y4+ challengers,
    # so benchmarking the same challengers against H1-Y3 would be target leakage.
    h3_note={
        "production_h3_status":"preserved_unchanged",
        "reason":"Y1-Y3 governed forecasts are explicit inputs to post-H3 models. Reusing them to claim a challenger beats the H1-Y3 production problem would not be a comparable independent test.",
        "separate_h1_h3_replacement_evidence_found":False,
    }

    result={
        "directive":"comparative Y4+ model-family selection",
        "authority":"research_only_no_production_change",
        "families":FAMILIES,
        "horizons":HORIZONS,
        "positions":POSITIONS,
        "selection_rule":{
            "development_score":"35% log RMSE ratio + 25% log MAE ratio + 15% log survival-Brier ratio + 15% rank-correlation delta + 10% survival-calibration-gap delta + fixed complexity penalty",
            "routing":"dynamic programming independently by position across Y4-Y8 with frozen switch penalty",
            "holdout":"last three target-complete base seasons per horizon; route must pass no-catastrophic-regression confirmation and development leave-one-fold stability",
            "fallback":"incumbent two_part_state if holdout-confirmed, otherwise carry_y3",
        },
        "folds":{
            str(h):{"development":eval_folds(player,h)[0],"holdout":eval_folds(player,h)[1]}
            for h in HORIZONS
        },
        "routing_summary":summary,
        "empirical_breakpoints":breakpoints,
        "h3_preservation":h3_note,
    }
    (OUT/"ROUTING_SUMMARY.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")

    print("ROUTING_TABLE")
    print(route.to_string(index=False))
    print("ARCHITECTURE_HOLDOUT")
    print(arch.to_string(index=False))
    print("BREAKPOINTS")
    print(json.dumps(breakpoints,indent=2,sort_keys=True))
    print("SUMMARY_JSON_BEGIN")
    print(json.dumps(result,sort_keys=True))
    print("SUMMARY_JSON_END")

if __name__=="__main__":
    main()

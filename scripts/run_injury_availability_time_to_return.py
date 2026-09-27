from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

OUT=Path("artifacts/research/current_football_state_h3_20260926")
HOLDOUTS=(2019,2020,2021,2022,2023,2024)
CALIBRATION_ORIGINS=(2016,2017,2018)
POSITIONS=("QB","RB","WR","TE")
ENDPOINTS=(1,2,3,4)
RANDOM_STATE=20260927

CAT=("position","severity","injury_family")
NUM=("event_week","weeks_remaining","pre_ppg","pre_opportunity","age_years","experience_years")

def regular_weeks(season:int)->int:
    return 17 if int(season)<=2020 else 18

def prepare(episodes:pd.DataFrame, career:pd.DataFrame):
    x=episodes.copy()
    x["player_id"]=x.player_id.astype(str)
    x["season"]=pd.to_numeric(x.season,errors="coerce").astype("Int64")
    x["event_week"]=pd.to_numeric(x.event_week,errors="coerce")
    x["games_to_return"]=pd.to_numeric(x.games_to_return,errors="coerce")
    x["availability_raw"]=pd.to_numeric(x.remaining_roster_week_participation_share,errors="coerce")
    x["availability_target"]=x.availability_raw.clip(0,1)
    x["weeks_remaining"]=[max(0,regular_weeks(int(s))-int(w)) for s,w in zip(x.season,x.event_week)]
    x["structurally_inconsistent_return"]=x.games_to_return.notna() & (x.games_to_return>x.weeks_remaining)
    c=career[["player_id","season","age_years","experience_years"]].drop_duplicates(["player_id","season"]).copy()
    c["player_id"]=c.player_id.astype(str)
    c["season"]=pd.to_numeric(c.season,errors="coerce").astype("Int64")
    x=x.merge(c,on=["player_id","season"],how="left")
    for col in ("pre_ppg","pre_opportunity","age_years","experience_years"):
        x[col]=pd.to_numeric(x[col],errors="coerce")
    x["episode_id"]=np.arange(len(x),dtype=int)
    return x

def week_bin(v):
    v=int(v)
    if v<=2:return "0_2"
    if v<=5:return "3_5"
    if v<=8:return "6_8"
    return "9_plus"

def empirical_rate(train, keys, target, base_rate=None, strength=20.0):
    if base_rate is None: base_rate=float(train[target].mean())
    grp=train.groupby(keys,dropna=False)[target].agg(["sum","count"]).reset_index()
    grp["rate"]=(grp["sum"]+strength*base_rate)/(grp["count"]+strength)
    return {tuple(r[k] for k in keys):float(r.rate) for _,r in grp.iterrows()},base_rate

def empirical_mean(train, keys, target, parent=None, strength=20.0):
    overall=float(train[target].mean())
    grp=train.groupby(keys,dropna=False)[target].agg(["sum","count"]).reset_index()
    out={}
    for _,r in grp.iterrows():
        key=tuple(r[k] for k in keys)
        prior=overall if parent is None else float(parent.get(key[:-1],overall))
        out[key]=(float(r["sum"])+strength*prior)/(float(r["count"])+strength)
    return out,overall

def build_hazard_rows(x):
    rows=[]
    for r in x.itertuples():
        if bool(r.structurally_inconsistent_return):
            continue
        md=int(r.weeks_remaining)
        observed=pd.notna(r.games_to_return)
        d=int(r.games_to_return) if observed else md
        d=min(d,md)
        for delay in range(0,d+1):
            rows.append({
                "episode_id":int(r.episode_id),"player_id":r.player_id,"season":int(r.season),
                "position":r.position,"severity":r.severity,"injury_family":r.injury_family,
                "event_week":float(r.event_week),"weeks_remaining":float(r.weeks_remaining),
                "pre_ppg":r.pre_ppg,"pre_opportunity":r.pre_opportunity,
                "age_years":r.age_years,"experience_years":r.experience_years,
                "delay":delay,"hazard_event":int(observed and delay==d),
            })
    return pd.DataFrame(rows)

def preprocessor():
    return ColumnTransformer([
        ("cat",OneHotEncoder(handle_unknown="ignore",sparse_output=False),list(CAT)),
        ("num",Pipeline([("scale",StandardScaler())]),list(NUM)+["delay"]),
    ],remainder="drop")

def preprocessor_avail():
    return ColumnTransformer([
        ("cat",OneHotEncoder(handle_unknown="ignore",sparse_output=False),list(CAT)),
        ("num",Pipeline([("scale",StandardScaler())]),list(NUM)),
    ],remainder="drop")

def fit_hazard_models(train_h):
    lin=Pipeline([
        ("prep",preprocessor()),
        ("model",LogisticRegression(C=1.0,max_iter=2500,solver="lbfgs",random_state=RANDOM_STATE)),
    ])
    lin.fit(train_h[list(CAT)+list(NUM)+["delay"]],train_h.hazard_event)
    gb=Pipeline([
        ("prep",preprocessor()),
        ("model",HistGradientBoostingClassifier(
            learning_rate=.06,max_iter=160,max_leaf_nodes=15,l2_regularization=3.0,
            min_samples_leaf=30,random_state=RANDOM_STATE
        )),
    ])
    gb.fit(train_h[list(CAT)+list(NUM)+["delay"]],train_h.hazard_event)
    return {"linear_logistic":lin,"histgb":gb}

def hazard_empirical_predict(train_h, eval_rows, context=False):
    tr=train_h.copy()
    tr["delay_key"]=tr.delay.astype(int)
    if context:
        parent,_=empirical_rate(tr,["severity","delay_key"],"hazard_event",strength=20)
        keys=["severity","position","injury_family","delay_key"]
        grp=tr.groupby(keys)["hazard_event"].agg(["sum","count"]).reset_index()
        rates={}
        global_rate=float(tr.hazard_event.mean())
        for _,r in grp.iterrows():
            pkey=(r.severity,int(r.delay_key))
            prior=parent.get(pkey,global_rate)
            key=(r.severity,r.position,r.injury_family,int(r.delay_key))
            rates[key]=(float(r["sum"])+25*prior)/(float(r["count"])+25)
        def one(r):
            key=(r.severity,r.position,r.injury_family,int(r.delay))
            return rates.get(key,parent.get((r.severity,int(r.delay)),global_rate))
    else:
        rates,global_rate=empirical_rate(tr,["severity","delay_key"],"hazard_event",strength=25)
        def one(r):
            return rates.get((r.severity,int(r.delay)),global_rate)
    return np.asarray([one(r) for r in eval_rows.itertuples()],dtype=float)

def episode_cdf_predictions(train_h, eval_ep, models):
    risk=[]
    for r in eval_ep.itertuples():
        if bool(r.structurally_inconsistent_return): continue
        for delay in range(0,int(r.weeks_remaining)+1):
            risk.append({
                "episode_id":int(r.episode_id),"position":r.position,"severity":r.severity,
                "injury_family":r.injury_family,"event_week":float(r.event_week),
                "weeks_remaining":float(r.weeks_remaining),"pre_ppg":r.pre_ppg,
                "pre_opportunity":r.pre_opportunity,"age_years":r.age_years,
                "experience_years":r.experience_years,"delay":delay,
            })
    rr=pd.DataFrame(risk)
    if rr.empty:return pd.DataFrame()
    hazards={
        "severity":hazard_empirical_predict(train_h,rr,False),
        "context":hazard_empirical_predict(train_h,rr,True),
    }
    X=rr[list(CAT)+list(NUM)+["delay"]]
    for name,model in models.items():
        hazards[name]=model.predict_proba(X)[:,1]
    for k,v in hazards.items():
        rr[k+"_hazard"]=np.clip(v,1e-5,1-1e-5)
    out=[]
    ep_lookup=eval_ep.set_index("episode_id")
    for eid,g in rr.groupby("episode_id"):
        g=g.sort_values("delay")
        e=ep_lookup.loc[eid]
        rec={"episode_id":int(eid),"season":int(e.season),"position":e.position,
             "severity":e.severity,"injury_family":e.injury_family,
             "weeks_remaining":int(e.weeks_remaining),
             "observed_return":bool(pd.notna(e.games_to_return) and not e.structurally_inconsistent_return),
             "games_to_return":float(e.games_to_return) if pd.notna(e.games_to_return) and not e.structurally_inconsistent_return else np.nan}
        for name in ("severity","context","linear_logistic","histgb"):
            surv=1.0; cdfs={}
            for row in g.itertuples():
                h=float(getattr(row,name+"_hazard"))
                surv*=1-h
                cdfs[int(row.delay)]=1-surv
            for kk in ENDPOINTS:
                if int(e.weeks_remaining)>=kk:
                    rec[f"{name}_p_return_by_{kk}"]=cdfs.get(kk,cdfs[max(cdfs)])
                else:
                    rec[f"{name}_p_return_by_{kk}"]=np.nan
            rec[f"{name}_p_return_any"]=cdfs[max(cdfs)]
            # Integrated Brier uses all structurally possible delay thresholds.
            ib=[]
            for d,p in cdfs.items():
                y=int(pd.notna(e.games_to_return) and not e.structurally_inconsistent_return and float(e.games_to_return)<=d)
                ib.append((p-y)**2)
            rec[f"{name}_ibs"]=float(np.mean(ib)) if ib else np.nan
        out.append(rec)
    return pd.DataFrame(out)

def endpoint_metrics(pred,name):
    bs=[]; ll=[]; cal=[]
    for kk in ENDPOINTS:
        q=pred[pred.weeks_remaining>=kk].copy()
        if q.empty:continue
        y=(q.games_to_return.notna() & (q.games_to_return<=kk)).astype(int).to_numpy()
        p=q[f"{name}_p_return_by_{kk}"].clip(1e-6,1-1e-6).to_numpy(float)
        bs.append(float(np.mean((p-y)**2)))
        ll.append(float(log_loss(y,p,labels=[0,1])))
        cal.append(abs(float(p.mean()-y.mean())))
    y=pred.games_to_return.notna().astype(int).to_numpy()
    p=pred[f"{name}_p_return_any"].clip(1e-6,1-1e-6).to_numpy(float)
    bs.append(float(np.mean((p-y)**2)))
    ll.append(float(log_loss(y,p,labels=[0,1])))
    cal.append(abs(float(p.mean()-y.mean())))
    return {
        "mean_brier":float(np.mean(bs)),
        "mean_log_loss":float(np.mean(ll)),
        "mean_abs_calibration_error":float(np.mean(cal)),
        "integrated_brier":float(pred[f"{name}_ibs"].mean()),
        "n":int(len(pred)),
    }

def fit_availability_models(train):
    y=train.availability_target.to_numpy(float)
    lin=Pipeline([
        ("prep",preprocessor_avail()),
        ("model",Ridge(alpha=10.0)),
    ])
    lin.fit(train[list(CAT)+list(NUM)],y)
    gb=Pipeline([
        ("prep",preprocessor_avail()),
        ("model",HistGradientBoostingRegressor(
            learning_rate=.05,max_iter=180,max_leaf_nodes=15,l2_regularization=3.0,
            min_samples_leaf=30,random_state=RANDOM_STATE
        )),
    ])
    gb.fit(train[list(CAT)+list(NUM)],y)
    return {"linear_ridge":lin,"histgb":gb}

def avail_empirical_predict(train,ev,context=False):
    tr=train.copy()
    tr["week_bin"]=[week_bin(v) for v in tr.weeks_remaining]
    e=ev.copy(); e["week_bin"]=[week_bin(v) for v in e.weeks_remaining]
    overall=float(tr.availability_target.mean())
    sev,_=empirical_mean(tr,["severity","week_bin"],"availability_target",strength=25)
    if not context:
        return np.asarray([sev.get((r.severity,r.week_bin),overall) for r in e.itertuples()])
    grp=tr.groupby(["severity","position","injury_family","week_bin"]).availability_target.agg(["sum","count"]).reset_index()
    rates={}
    for _,r in grp.iterrows():
        prior=sev.get((r.severity,r.week_bin),overall)
        key=(r.severity,r.position,r.injury_family,r.week_bin)
        rates[key]=(float(r["sum"])+25*prior)/(float(r["count"])+25)
    return np.asarray([rates.get((r.severity,r.position,r.injury_family,r.week_bin),
                                 sev.get((r.severity,r.week_bin),overall)) for r in e.itertuples()])

def availability_predictions(train,ev,models):
    out=ev[["episode_id","season","position","severity","injury_family","availability_target"]].copy()
    out["severity_pred"]=avail_empirical_predict(train,ev,False)
    out["context_pred"]=avail_empirical_predict(train,ev,True)
    X=ev[list(CAT)+list(NUM)]
    for name,m in models.items():
        out[name+"_pred"]=np.clip(m.predict(X),0,1)
    return out

def avail_metrics(g,pred_col):
    y=g.availability_target.to_numpy(float); p=g[pred_col].to_numpy(float)
    e=p-y
    return {"n":len(g),"mae":float(np.mean(np.abs(e))),
            "rmse":float(np.sqrt(np.mean(e*e))),"bias":float(np.mean(e))}

def run_origins(x):
    all_ttr=[]; all_avail=[]; fold_rows=[]
    for T in range(2016,2025):
        tr=x[x.season<T].copy(); ev=x[x.season==T].copy()
        if len(tr)<1000 or ev.empty:continue
        tr_h=build_hazard_rows(tr)
        hmods=fit_hazard_models(tr_h)
        ttr=episode_cdf_predictions(tr_h,ev,hmods)
        ttr["origin"]=T
        all_ttr.append(ttr)
        amods=fit_availability_models(tr)
        av=availability_predictions(tr,ev,amods)
        av["origin"]=T
        all_avail.append(av)
        if T in HOLDOUTS:
            for name in ("severity","context","linear_logistic","histgb"):
                m=endpoint_metrics(ttr,name); fold_rows.append({"component":"return_timing","season":T,"model":name,**m})
            for name in ("severity","context","linear_ridge","histgb"):
                m=avail_metrics(av,name+"_pred"); fold_rows.append({"component":"remaining_availability","season":T,"model":name,**m})
    return pd.concat(all_ttr,ignore_index=True),pd.concat(all_avail,ignore_index=True),pd.DataFrame(fold_rows)

def pooled_ttr_metrics(ttr):
    q=ttr[ttr.season.isin(HOLDOUTS)].copy()
    rows=[]
    for name in ("severity","context","linear_logistic","histgb"):
        rows.append({"model":name,**endpoint_metrics(q,name)})
    return pd.DataFrame(rows)

def pooled_avail_metrics(av):
    q=av[av.season.isin(HOLDOUTS)].copy()
    return pd.DataFrame([{"model":name,**avail_metrics(q,name+"_pred")}
                         for name in ("severity","context","linear_ridge","histgb")])

def safety_ttr(ttr,name):
    rows=[]
    q=ttr[ttr.season.isin(HOLDOUTS)]
    for pos,g in q.groupby("position"):
        if len(g)<100:continue
        a=endpoint_metrics(g,name); b=endpoint_metrics(g,"severity")
        rows.append({"position":pos,"n":len(g),"model":name,
                     "mean_brier_rel":a["mean_brier"]/b["mean_brier"]-1})
    return rows

def safety_avail(av,name):
    rows=[]
    q=av[av.season.isin(HOLDOUTS)]
    for pos,g in q.groupby("position"):
        if len(g)<100:continue
        a=avail_metrics(g,name+"_pred"); b=avail_metrics(g,"severity_pred")
        rows.append({"position":pos,"n":len(g),"model":name,"mae_rel":a["mae"]/b["mae"]-1})
    return rows

def select_ttr(ttr,folds,pooled):
    base=pooled.set_index("model").loc["severity"]
    candidates=[]
    for name in ("context","linear_logistic","histgb"):
        r=pooled.set_index("model").loc[name]
        wins=0
        for T in HOLDOUTS:
            a=folds[(folds.component=="return_timing")&(folds.season==T)&(folds.model==name)].iloc[0]
            b=folds[(folds.component=="return_timing")&(folds.season==T)&(folds.model=="severity")].iloc[0]
            wins+=int(a.mean_brier<b.mean_brier)
        pos=safety_ttr(ttr,name)
        clears=(
            r.mean_brier<=.98*base.mean_brier and
            r.integrated_brier<=.99*base.integrated_brier and
            r.mean_log_loss<=1.03*base.mean_log_loss and
            r.mean_abs_calibration_error<=base.mean_abs_calibration_error+.02 and
            wins>=4 and
            all(x["mean_brier_rel"]<=.07 for x in pos)
        )
        candidates.append({"model":name,"clears":bool(clears),"holdout_brier_wins":wins,
                           "mean_brier_improvement":1-r.mean_brier/base.mean_brier,
                           "integrated_brier_improvement":1-r.integrated_brier/base.integrated_brier})
    ok=[x for x in candidates if x["clears"]]
    selected=None
    if ok:
        order={"context":0,"linear_logistic":1,"histgb":2}
        ok=sorted(ok,key=lambda z:(order[z["model"]],-z["mean_brier_improvement"]))
        selected=ok[0]["model"]
        if selected!="histgb":
            hg=next((z for z in ok if z["model"]=="histgb"),None)
            cur=next(z for z in ok if z["model"]==selected)
            if hg and hg["mean_brier_improvement"]-cur["mean_brier_improvement"]>=.01:
                selected="histgb"
    return selected,candidates

def select_avail(av,folds,pooled):
    base=pooled.set_index("model").loc["severity"]
    candidates=[]
    for name in ("context","linear_ridge","histgb"):
        r=pooled.set_index("model").loc[name]
        wins=0
        for T in HOLDOUTS:
            a=folds[(folds.component=="remaining_availability")&(folds.season==T)&(folds.model==name)].iloc[0]
            b=folds[(folds.component=="remaining_availability")&(folds.season==T)&(folds.model=="severity")].iloc[0]
            wins+=int(a.mae<b.mae)
        pos=safety_avail(av,name)
        clears=(
            r.mae<=.98*base.mae and
            r.rmse<=1.03*base.rmse and
            abs(r.bias)<=abs(base.bias)+.02 and
            wins>=4 and
            all(x["mae_rel"]<=.07 for x in pos)
        )
        candidates.append({"model":name,"clears":bool(clears),"holdout_mae_wins":wins,
                           "mae_improvement":1-r.mae/base.mae})
    ok=[x for x in candidates if x["clears"]]
    selected=None
    if ok:
        order={"context":0,"linear_ridge":1,"histgb":2}
        ok=sorted(ok,key=lambda z:(order[z["model"]],-z["mae_improvement"]))
        selected=ok[0]["model"]
        if selected!="histgb":
            hg=next((z for z in ok if z["model"]=="histgb"),None)
            cur=next(z for z in ok if z["model"]==selected)
            if hg and hg["mae_improvement"]-cur["mae_improvement"]>=.01:
                selected="histgb"
    return selected,candidates

def conformal_availability(av,selected):
    pred_col=selected+"_pred"
    q=av.copy()
    q["abs_error"]=(q[pred_col]-q.availability_target).abs()
    rows=[]; cov=[]
    for T in HOLDOUTS:
        ev=q[q.season==T].copy()
        prior=q[(q.season<T)&(q.season>=min(CALIBRATION_ORIGINS))].copy()
        overall80=float(prior.abs_error.quantile(.80)); overall90=float(prior.abs_error.quantile(.90))
        for pos,g in ev.groupby("position"):
            pp=prior[prior.position==pos]
            q80=float(pp.abs_error.quantile(.80)) if len(pp)>=100 else overall80
            q90=float(pp.abs_error.quantile(.90)) if len(pp)>=100 else overall90
            e=g.abs_error
            rows.append({"season":T,"position":pos,"n":len(g),"calibration_n":len(pp),
                         "q80":q80,"q90":q90,"coverage80":float((e<=q80).mean()),
                         "coverage90":float((e<=q90).mean())})
            for r in g.itertuples():
                cov.append({"episode_id":r.episode_id,"season":T,"position":pos,
                            "pred":getattr(r,pred_col),"actual":r.availability_target,
                            "q80":q80,"q90":q90,
                            "covered80":abs(getattr(r,pred_col)-r.availability_target)<=q80,
                            "covered90":abs(getattr(r,pred_col)-r.availability_target)<=q90})
    return pd.DataFrame(rows),pd.DataFrame(cov)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--episodes",type=Path,required=True)
    ap.add_argument("--career-panel",type=Path,required=True)
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    episodes=pd.read_csv(args.episodes)
    career=pd.read_csv(args.career_panel)
    x=prepare(episodes,career)
    ttr,av,folds=run_origins(x)
    pt=pooled_ttr_metrics(ttr); pa=pooled_avail_metrics(av)
    st,gt=select_ttr(ttr,folds,pt)
    sa,ga=select_avail(av,folds,pa)

    ttr_safety=[]
    for n in ("context","linear_logistic","histgb"):ttr_safety.extend(safety_ttr(ttr,n))
    av_safety=[]
    for n in ("context","linear_ridge","histgb"):av_safety.extend(safety_avail(av,n))

    if sa:
        conf_summary,conf_rows=conformal_availability(av,sa)
    else:
        conf_summary=pd.DataFrame(); conf_rows=pd.DataFrame()

    folds.to_csv(OUT/"INJURY_AVAILABILITY_OOT_FOLD_METRICS.csv",index=False)
    pt.to_csv(OUT/"INJURY_RETURN_TIMING_POOLED_METRICS.csv",index=False)
    pa.to_csv(OUT/"INJURY_REMAINING_AVAILABILITY_POOLED_METRICS.csv",index=False)
    pd.DataFrame(ttr_safety).to_csv(OUT/"INJURY_RETURN_TIMING_POSITION_SAFETY.csv",index=False)
    pd.DataFrame(av_safety).to_csv(OUT/"INJURY_AVAILABILITY_POSITION_SAFETY.csv",index=False)
    ttr.to_csv(OUT/"INJURY_RETURN_TIMING_OOT_PREDICTIONS.csv",index=False)
    av.to_csv(OUT/"INJURY_AVAILABILITY_OOT_PREDICTIONS.csv",index=False)
    conf_summary.to_csv(OUT/"INJURY_AVAILABILITY_CONFORMAL_SUMMARY.csv",index=False)
    conf_rows.to_csv(OUT/"INJURY_AVAILABILITY_CONFORMAL_PREDICTIONS.csv",index=False)

    result={
        "study":"injury-availability-time-to-return",
        "authority":"research_only_no_production_change",
        "episode_n":int(len(x)),
        "episode_seasons":[int(x.season.min()),int(x.season.max())],
        "holdouts":list(HOLDOUTS),
        "structurally_inconsistent_return_rows_excluded_from_ttr":int(x.structurally_inconsistent_return.sum()),
        "availability_rows_clipped_to_0_1":int(((x.availability_raw<0)|(x.availability_raw>1)).sum()),
        "age_coverage":float(x.age_years.notna().mean()),
        "experience_coverage":float(x.experience_years.notna().mean()),
        "return_timing":{"selected":st,"candidate_gates":gt,"pooled":pt.to_dict("records")},
        "remaining_availability":{"selected":sa,"candidate_gates":ga,"pooled":pa.to_dict("records")},
        "conformal":conf_summary.to_dict("records") if sa else [],
        "guards":{
            "conditional_healthy_production_changed":False,
            "post_return_role_changed":False,
            "recurrence_or_h2_h3_changed":False,
            "production_h3_changed":False,
            "intrinsic_changed":False,
            "provider_ros_authority_changed":False
        }
    }
    (OUT/"INJURY_AVAILABILITY_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

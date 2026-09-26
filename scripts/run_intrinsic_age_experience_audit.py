from __future__ import annotations

import argparse, importlib.util, json, math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

OUT=Path("artifacts/research/intrinsic_cell_routing_y4_y8_20260926")
POSITIONS=("QB","RB","WR","TE")
HORIZONS=(4,5,6,7,8)
RANDOM_SEED=20260926
MIN_TRAIN=80
MIN_POS=25

BASE_FORECAST=(
    "prior_pct","log_prior_points","log_y1","y1_pct",
    "y2_ratio","y3_ratio","y2_delta","y3_delta"
)
RECENT=(
    "l1_games","games_mean2","games_mean3",
    "l1_opportunities","opp_mean2","opp_mean3","opp_slope12",
    "l1_role_share","role_mean2","role_mean3","role_slope12",
    "l1_points_per_game","l1_points_per_opp","fantasy_slope12"
)

def load_module(path):
    spec=importlib.util.spec_from_file_location("dev",path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def cumulative_at_base(base,raw):
    r=raw.copy()
    for c in ["games","attempts","carries","targets","receptions","sacks_suffered","opportunities","fantasy_target"]:
        if c not in r: r[c]=0.0
        r[c]=pd.to_numeric(r[c],errors="coerce").fillna(0.0)
    r["dropbacks"]=r["attempts"]+r["sacks_suffered"]
    r["touches"]=r["carries"]+r["receptions"]
    r["season_played"]=(r["games"]>0).astype(float)
    cols=["games","season_played","attempts","dropbacks","carries","targets","receptions","touches","opportunities","fantasy_target"]
    r=r.sort_values(["player_id","season"])
    for c in cols:
        r[f"career_{c}"]=r.groupby("player_id")[c].cumsum()-r[c]
    keep=["player_id","season"]+[f"career_{c}" for c in cols]
    q=r[keep].rename(columns={"season":"base_season"})
    x=base.merge(q,on=["player_id","base_season"],how="left")
    for c in [f"career_{z}" for z in cols]:
        x[c]=pd.to_numeric(x[c],errors="coerce").fillna(0.0)
    x=x.rename(columns={
        "career_season_played":"career_seasons",
        "career_fantasy_target":"career_fantasy_points",
    })
    return x

def build_long(dev,args):
    m=pd.read_csv(args.model_a_rows)
    qb=json.loads(Path(args.qb_results).read_text())
    raw=dev.prep_raw(pd.read_csv(args.raw_seasons))
    players=pd.read_csv(args.players)
    m=dev.add_qb_governed_path(m,qb)
    base=dev.build_forecast_base(m)
    base=dev.merge_lags(base,raw)
    base=dev.add_engineered_features(base,players)
    base=cumulative_at_base(base,raw)
    long=dev.build_long(base,raw)
    long["age_at_target"]=long["age"]+long["horizon"]-1
    long["experience_at_target"]=long["experience"]+long["horizon"]-1
    long["age_target_sq"]=long["age_at_target"]**2
    long["age_target_cube"]=long["age_at_target"]**3
    long["exp_target_sq"]=long["experience_at_target"]**2

    # Position-appropriate primary cumulative workload.
    long["career_primary_workload"]=np.select(
        [long.position=="QB",long.position=="RB",long.position.isin(["WR","TE"])],
        [long["career_dropbacks"],long["career_touches"],long["career_targets"]],
        default=long["career_opportunities"],
    )
    long["career_secondary_workload"]=np.select(
        [long.position=="QB",long.position=="RB",long.position.isin(["WR","TE"])],
        [long["career_attempts"]+long["career_carries"],long["career_targets"],long["career_receptions"]],
        default=long["career_opportunities"],
    )
    long["log_career_games"]=np.log1p(long["career_games"].clip(lower=0))
    long["log_career_primary"]=np.log1p(long["career_primary_workload"].clip(lower=0))
    long["log_career_secondary"]=np.log1p(long["career_secondary_workload"].clip(lower=0))
    long["workload_per_season"]=long["career_primary_workload"]/long["career_seasons"].clip(lower=1)
    long["recent_to_career_workload"]=(long["opp_mean2"].fillna(0)*2)/long["career_primary_workload"].clip(lower=1)
    long["age_x_logwork"]=long["age_at_target"]*long["log_career_primary"]
    long["exp_x_logwork"]=long["experience_at_target"]*long["log_career_primary"]
    long["age_x_recent_role"]=long["age_at_target"]*long["role_mean2"].fillna(0)
    long["exp_x_recent_role"]=long["experience_at_target"]*long["role_mean2"].fillna(0)
    return long

def features_for(variant):
    target=BASE_FORECAST+(
        "age_at_target","experience_at_target","age_target_sq","age_target_cube","exp_target_sq"
    )
    recent=target+RECENT
    exposure=recent+(
        "log_career_games","career_seasons","log_career_primary","log_career_secondary",
        "workload_per_season","recent_to_career_workload",
        "age_x_logwork","exp_x_logwork","age_x_recent_role","exp_x_recent_role"
    )
    if variant=="base_linear":
        return ("age","experience")+BASE_FORECAST
    if variant=="target_poly":
        return target
    if variant=="exposure_ablation":
        return recent
    if variant in {"target_poly_exposure","target_exposure_histgb"}:
        return exposure
    raise KeyError(variant)

def matrix(train,ev,features):
    tr=train[list(features)].apply(pd.to_numeric,errors="coerce")
    te=ev[list(features)].apply(pd.to_numeric,errors="coerce")
    med=tr.median().fillna(0)
    tr=tr.fillna(med); te=te.fillna(med)
    lo=tr.quantile(.005); hi=tr.quantile(.995)
    tr=tr.clip(lo,hi,axis=1); te=te.clip(lo,hi,axis=1)
    sc=StandardScaler().fit(tr)
    return sc.transform(tr),sc.transform(te)

def fit_predict(train,ev,variant):
    feats=features_for(variant)
    X,Z=matrix(train,ev,feats)
    y=train.actual.to_numpy(float)
    active=(y>0).astype(int)
    if len(train)<MIN_TRAIN:
        p=np.repeat(float(active.mean()) if len(active) else 0.0,len(ev))
        cp=np.repeat(float(y[y>0].mean()) if np.any(y>0) else 0.0,len(ev))
        return p,cp,p*cp
    if variant=="target_exposure_histgb":
        if len(np.unique(active))>1:
            cl=HistGradientBoostingClassifier(
                learning_rate=.05,max_iter=100,max_leaf_nodes=11,min_samples_leaf=20,
                l2_regularization=10.0,random_state=RANDOM_SEED
            ).fit(X,active)
            p=cl.predict_proba(Z)[:,1]
        else:
            p=np.repeat(float(active.mean()),len(ev))
        pos=y>0
        if pos.sum()>=MIN_POS:
            rg=HistGradientBoostingRegressor(
                learning_rate=.05,max_iter=110,max_leaf_nodes=15,min_samples_leaf=20,
                l2_regularization=10.0,random_state=RANDOM_SEED
            ).fit(X[pos],y[pos])
            cp=np.clip(rg.predict(Z),0,650)
        else:
            cp=np.repeat(float(y[pos].mean()) if pos.sum() else 0.0,len(ev))
    else:
        if len(np.unique(active))>1:
            cl=LogisticRegression(C=1.0,solver="lbfgs",max_iter=3000,random_state=RANDOM_SEED).fit(X,active)
            p=cl.predict_proba(Z)[:,1]
        else:
            p=np.repeat(float(active.mean()),len(ev))
        pos=y>0
        if pos.sum()>=MIN_POS:
            rg=Ridge(alpha=10.0).fit(X[pos],np.log1p(y[pos]))
            cp=np.expm1(rg.predict(Z)).clip(0,650)
        else:
            cp=np.repeat(float(y[pos].mean()) if pos.sum() else 0.0,len(ev))
    return np.clip(p,0,1),np.clip(cp,0,650),np.clip(p*cp,0,650)

def metric(g):
    y=g.actual.to_numpy(float); pred=g.pred.to_numpy(float); e=pred-y
    active=(y>0).astype(float)
    p=g.p_active.to_numpy(float)
    out={
        "n":len(g),
        "rmse":float(np.sqrt(np.mean(e*e))),
        "mae":float(np.mean(np.abs(e))),
        "bias":float(np.mean(e)),
        "spearman":float(pd.Series(pred).corr(pd.Series(y),method="spearman")) if len(set(pred))>1 and len(set(y))>1 else 0.0,
        "tail_rmse":float(np.sqrt(np.mean(e[y>=np.quantile(y,.9)]**2))) if len(y)>=10 else float(np.sqrt(np.mean(e*e))),
        "survival_brier":float(np.mean((p-active)**2)),
        "survival_calibration_gap":float(abs(p.mean()-active.mean())),
        "active_rate":float(active.mean()),
        "pred_active_rate":float(p.mean()),
    }
    q=g[g.actual>0]
    if len(q)>=3:
        ce=q.conditional_pred-q.actual
        out.update({
            "conditional_n":len(q),
            "conditional_rmse":float(np.sqrt(np.mean(ce*ce))),
            "conditional_mae":float(np.mean(np.abs(ce))),
            "conditional_bias":float(np.mean(ce)),
            "conditional_spearman":float(q.conditional_pred.corr(q.actual,method="spearman")) if q.conditional_pred.nunique()>1 and q.actual.nunique()>1 else 0.0,
        })
    else:
        out.update({"conditional_n":len(q),"conditional_rmse":np.nan,"conditional_mae":np.nan,"conditional_bias":np.nan,"conditional_spearman":np.nan})
    return out

def score(m,base):
    eps=1e-9
    return (
        .25*math.log(max(eps,m["rmse"])/max(eps,base["rmse"]))+
        .10*math.log(max(eps,m["mae"])/max(eps,base["mae"]))+
        .15*math.log(max(eps,m["tail_rmse"])/max(eps,base["tail_rmse"]))+
        .20*math.log((m["survival_brier"]+.01)/(base["survival_brier"]+.01))+
        .20*math.log(max(eps,m["conditional_rmse"])/max(eps,base["conditional_rmse"]))+
        .10*(base["spearman"]-m["spearman"])
    )

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--development-module",required=True)
    ap.add_argument("--origin-plan",required=True)
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--raw-seasons",required=True)
    ap.add_argument("--players",required=True)
    args=ap.parse_args()

    dev=load_module(args.development_module)
    long=build_long(dev,args)
    origin_plan=json.loads(Path(args.origin_plan).read_text())
    variants=["base_linear","target_poly","exposure_ablation","target_poly_exposure","target_exposure_histgb"]
    rec=[]
    for h in HORIZONS:
        outers=[int(x) for x in origin_plan[str(h)]["outer"]]
        for T in outers:
            evh=long[(long.horizon==h)&(long.base_season==T)]
            for pos in POSITIONS:
                ev=evh[evh.position==pos]
                tr=long[(long.horizon==h)&(long.position==pos)&(long.target_season<T)]
                if ev.empty or len(tr)<MIN_TRAIN: continue
                for v in variants:
                    p,cp,pred=fit_predict(tr,ev,v)
                    for i,r in enumerate(ev.itertuples()):
                        rec.append({
                            "base_season":T,"horizon":h,"position":pos,"player_id":r.player_id,
                            "variant":v,"actual":float(r.actual),"pred":float(pred[i]),
                            "p_active":float(p[i]),"conditional_pred":float(cp[i]),
                            "age_at_target":float(r.age_at_target) if np.isfinite(r.age_at_target) else np.nan,
                            "experience_at_target":float(r.experience_at_target) if np.isfinite(r.experience_at_target) else np.nan,
                            "career_games":float(r.career_games),"career_seasons":float(r.career_seasons),
                            "career_primary_workload":float(r.career_primary_workload),
                            "recent_role":float(r.role_mean2) if np.isfinite(r.role_mean2) else np.nan,
                            "recent_opportunities":float(r.opp_mean2) if np.isfinite(r.opp_mean2) else np.nan,
                        })
    pred=pd.DataFrame(rec)
    pred.to_csv(OUT/"AGE_EXPERIENCE_ROLLING_PREDICTIONS.csv",index=False)

    rows=[]; folds=[]
    for (v,h,pos),g in pred.groupby(["variant","horizon","position"]):
        rows.append({"variant":v,"horizon":h,"position":pos,**metric(g)})
        for T,q in g.groupby("base_season"):
            folds.append({"variant":v,"horizon":h,"position":pos,"outer_origin":T,**metric(q)})
    mt=pd.DataFrame(rows); ft=pd.DataFrame(folds)
    mt.to_csv(OUT/"AGE_EXPERIENCE_CELL_METRICS.csv",index=False)
    ft.to_csv(OUT/"AGE_EXPERIENCE_OUTER_METRICS.csv",index=False)

    # Incremental comparisons against inherited linear, and cumulative exposure against recent-role-only ablation.
    comps=[]
    for h in HORIZONS:
        for pos in POSITIONS:
            cell=mt[(mt.horizon==h)&(mt.position==pos)]
            if cell.empty: continue
            base=cell[cell.variant=="base_linear"].iloc[0].to_dict()
            noexp=cell[cell.variant=="exposure_ablation"].iloc[0].to_dict()
            for v in variants:
                m=cell[cell.variant==v].iloc[0].to_dict()
                ref=noexp if v=="target_poly_exposure" else base
                ref_name="exposure_ablation" if v=="target_poly_exposure" else "base_linear"
                comps.append({
                    "position":pos,"horizon":h,"variant":v,"reference":ref_name,
                    "overall_score_vs_reference":score(m,ref),
                    "rmse_ratio":m["rmse"]/ref["rmse"],
                    "tail_rmse_ratio":m["tail_rmse"]/ref["tail_rmse"],
                    "survival_brier_ratio":m["survival_brier"]/ref["survival_brier"],
                    "conditional_rmse_ratio":m["conditional_rmse"]/ref["conditional_rmse"],
                    "spearman_delta":m["spearman"]-ref["spearman"],
                })
    inc=pd.DataFrame(comps)
    inc.to_csv(OUT/"AGE_EXPERIENCE_INCREMENTAL_EFFECTS.csv",index=False)

    # Outer-origin stability counts.
    stab=[]
    for h in HORIZONS:
        for pos in POSITIONS:
            q=ft[(ft.horizon==h)&(ft.position==pos)]
            if q.empty: continue
            for v in variants:
                wins=0; surv=0; cond=0; usable=0
                for T in sorted(q.outer_origin.unique()):
                    a=q[(q.outer_origin==T)&(q.variant==v)]
                    b=q[(q.outer_origin==T)&(q.variant=="base_linear")]
                    if len(a)!=1 or len(b)!=1: continue
                    aa=a.iloc[0].to_dict(); bb=b.iloc[0].to_dict()
                    usable+=1
                    if score(aa,bb)<0: wins+=1
                    if aa["survival_brier"]<bb["survival_brier"]: surv+=1
                    if aa["conditional_rmse"]<bb["conditional_rmse"]: cond+=1
                stab.append({"position":pos,"horizon":h,"variant":v,"outer_origins":usable,
                             "overall_win_share_vs_base":wins/usable if usable else np.nan,
                             "survival_win_share_vs_base":surv/usable if usable else np.nan,
                             "conditional_win_share_vs_base":cond/usable if usable else np.nan})
    stab=pd.DataFrame(stab); stab.to_csv(OUT/"AGE_EXPERIENCE_STABILITY.csv",index=False)

    # Era sensitivity: earliest vs latest half of rolling outer origins.
    era=[]
    for (v,h,pos),g in pred.groupby(["variant","horizon","position"]):
        os=sorted(g.base_season.unique())
        if len(os)<4: continue
        split=len(os)//2
        for name,yrs in [("earlier",os[:split]),("later",os[-split:])]:
            z=g[g.base_season.isin(yrs)]
            era.append({"variant":v,"horizon":h,"position":pos,"era":name,"origins":";".join(map(str,yrs)),**metric(z)})
    pd.DataFrame(era).to_csv(OUT/"AGE_EXPERIENCE_ERA_SENSITIVITY.csv",index=False)

    # Quantile curves from rolling predictions: report target-age and target-experience gradients without named-player tuning.
    curves=[]
    for (v,h,pos),g in pred.groupby(["variant","horizon","position"]):
        for axis in ["age_at_target","experience_at_target","career_primary_workload"]:
            z=g.dropna(subset=[axis]).copy()
            if len(z)<30 or z[axis].nunique()<5: continue
            try:
                z["bin"]=pd.qcut(z[axis],q=min(5,z[axis].nunique()),duplicates="drop")
            except Exception:
                continue
            for b,q in z.groupby("bin",observed=True):
                active=q.actual>0
                curves.append({
                    "variant":v,"horizon":h,"position":pos,"axis":axis,"bin":str(b),"n":len(q),
                    "x_mean":float(q[axis].mean()),
                    "actual_active_rate":float(active.mean()),"pred_active_rate":float(q.p_active.mean()),
                    "actual_conditional_mean":float(q.loc[active,"actual"].mean()) if active.any() else np.nan,
                    "pred_conditional_mean_active":float(q.loc[active,"conditional_pred"].mean()) if active.any() else np.nan,
                    "actual_overall_mean":float(q.actual.mean()),"pred_overall_mean":float(q.pred.mean()),
                })
    pd.DataFrame(curves).to_csv(OUT/"AGE_EXPERIENCE_TRAJECTORY_CURVES.csv",index=False)

    # Position-level audit summary.
    summary_rows=[]
    for pos in POSITIONS:
        a=inc[(inc.position==pos)&(inc.variant=="target_poly")]
        e=inc[(inc.position==pos)&(inc.variant=="target_poly_exposure")]
        h=inc[(inc.position==pos)&(inc.variant=="target_exposure_histgb")]
        st=stab[stab.position==pos]
        summary_rows.append({
            "position":pos,
            "target_nonlinear_mean_score_vs_base":float(a.overall_score_vs_reference.mean()),
            "target_nonlinear_cells_better":int((a.overall_score_vs_reference<0).sum()),
            "cumulative_exposure_mean_score_vs_recent_only":float(e.overall_score_vs_reference.mean()),
            "cumulative_exposure_cells_better":int((e.overall_score_vs_reference<0).sum()),
            "nonlinear_histgb_mean_score_vs_base":float(h.overall_score_vs_reference.mean()),
            "nonlinear_histgb_cells_better":int((h.overall_score_vs_reference<0).sum()),
            "exposure_survival_cells_better":int((e.survival_brier_ratio<1).sum()),
            "exposure_conditional_cells_better":int((e.conditional_rmse_ratio<1).sum()),
        })
    summ=pd.DataFrame(summary_rows); summ.to_csv(OUT/"AGE_EXPERIENCE_POSITION_SUMMARY.csv",index=False)

    result={
        "state":"AGE_EXPERIENCE_EXPOSURE_AUDIT_COMPLETE",
        "authority":"research_only_no_production_change",
        "outer_origin_plan":origin_plan,
        "position_summary":summ.to_dict("records"),
        "guards":{"prior_final_holdout_consumed":False,"current_named_players_consumed":False,"manual_age_curve":False,"production_h3_changed":False},
        "limitations":[
            "Historical routes are unavailable in the governed retained panel; WR/TE accumulated exposure uses targets/receptions/opportunities rather than routes.",
            "Y8 has only two valid rolling outer origins and cannot establish exact new authority.",
            "Accumulated workload is observational football history and may partly proxy talent/role durability; causal wear-and-tear is not claimed."
        ]
    }
    (OUT/"AGE_EXPERIENCE_AUDIT_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print("POSITION SUMMARY")
    print(summ.to_string(index=False))
    print("RESULT_JSON_BEGIN")
    print(json.dumps(result,sort_keys=True))
    print("RESULT_JSON_END")

if __name__=="__main__":
    main()

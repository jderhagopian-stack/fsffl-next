from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler

STATES=("out","depth","usable","starter","premium","elite")
POSITIVE=STATES[1:]
STATE_RANK={s:i for i,s in enumerate(STATES)}
THRESHOLDS=(("useful",2),("starter",3),("premium",4),("elite",5))
POSITIONS=("QB","RB","WR","TE")
SEED=20260927
OUTER_H2=tuple(range(2014,2024))
OUTER_H3=tuple(range(2014,2023))

CAT_STATE=("position","source_state","career_stage","age_band","source_role_band","horizon")
NUM_STATE=(
    "age","experience","source_log","source_percentile","state_percentile",
    "prior1_log","prior1_coverage","prior_age_state_resid_z","prior_age_coverage",
    "prior2_mean_age_state_z","prior2_gap_age_state_z","prior2_coverage",
    "games_log","games_coverage","opportunity_per_game","opportunity_coverage",
)

def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

def finite(v, default=0.0):
    try:
        x=float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default

def feature_frame(df: pd.DataFrame, future_state: str|None=None) -> pd.DataFrame:
    z=pd.DataFrame(index=df.index)
    z["position"]=df.position.astype(str)
    z["source_state"]=df.source_state.astype(str)
    z["career_stage"]=df.career_stage.astype(str)
    z["age_band"]=df.age_band.astype(str)
    z["source_role_band"]=df.source_role_band.fillna("unknown").astype(str)
    z["horizon"]=df.horizon.astype(int).astype(str)
    z["age"]=pd.to_numeric(df.age,errors="coerce").fillna(0.0)
    z["experience"]=pd.to_numeric(df.experience,errors="coerce").fillna(0.0)
    z["source_log"]=np.log1p(pd.to_numeric(df.source_points,errors="coerce").fillna(0.0).clip(lower=0.0))
    z["source_percentile"]=pd.to_numeric(df.source_percentile,errors="coerce").fillna(0.5)
    z["state_percentile"]=pd.to_numeric(df.state_percentile,errors="coerce").fillna(0.5)
    p1=pd.to_numeric(df.prior1_points,errors="coerce")
    z["prior1_log"]=np.log1p(p1.fillna(0.0).clip(lower=0.0))
    z["prior1_coverage"]=pd.to_numeric(df.prior1_coverage,errors="coerce").fillna(0.0)
    paz=pd.to_numeric(df.prior_age_state_resid_z,errors="coerce")
    z["prior_age_state_resid_z"]=paz.fillna(0.0)
    z["prior_age_coverage"]=paz.notna().astype(float)
    z["prior2_mean_age_state_z"]=pd.to_numeric(df.prior2_mean_age_state_z,errors="coerce").fillna(0.0)
    z["prior2_gap_age_state_z"]=pd.to_numeric(df.prior2_gap_age_state_z,errors="coerce").fillna(0.0)
    z["prior2_coverage"]=pd.to_numeric(df.prior2_coverage,errors="coerce").fillna(0.0)
    games=pd.to_numeric(df.games,errors="coerce")
    z["games_log"]=np.log1p(games.fillna(0.0).clip(lower=0.0))
    z["games_coverage"]=games.notna().astype(float)
    opp=pd.to_numeric(df.opportunity_per_game,errors="coerce")
    z["opportunity_per_game"]=opp.fillna(0.0)
    z["opportunity_coverage"]=opp.notna().astype(float)
    if future_state is not None:
        z["future_state"]=str(future_state)
    elif "future_state" in df.columns:
        z["future_state"]=df["future_state"].astype(str)
    return z

def tree_preprocessor(include_future=False):
    cats=list(CAT_STATE)+( ["future_state"] if include_future else [] )
    return ColumnTransformer(
        [
            ("cat",OneHotEncoder(handle_unknown="ignore",sparse_output=False),cats),
            ("num",StandardScaler(),list(NUM_STATE)),
        ],
        remainder="drop",
    )

def spline_preprocessor(include_future=False):
    cats=list(CAT_STATE)+( ["future_state"] if include_future else [] )
    num_pipe=Pipeline([
        ("spline",SplineTransformer(n_knots=5,degree=3,include_bias=False)),
        ("scale",StandardScaler()),
    ])
    return ColumnTransformer(
        [
            ("cat",OneHotEncoder(handle_unknown="ignore",sparse_output=False),cats),
            ("num",num_pipe,list(NUM_STATE)),
        ],
        remainder="drop",
    )

class ConstantOrLogit:
    def __init__(self):
        self.constant=None
        self.model=None
    def fit(self,X,y):
        y=np.asarray(y,int)
        u=np.unique(y)
        if len(u)<2:
            self.constant=float(u[0]) if len(u) else 0.0
            return self
        self.model=Pipeline([
            ("prep",spline_preprocessor(False)),
            ("model",LogisticRegression(C=.25,solver="lbfgs",max_iter=2500,random_state=SEED)),
        ])
        self.model.fit(X,y)
        return self
    def p(self,X):
        if self.model is None:
            return np.full(len(X),float(self.constant),dtype=float)
        return self.model.predict_proba(X)[:,1]

class N1:
    name="N1_histgb"
    def fit(self,state_train,prod_train):
        self.state=Pipeline([
            ("prep",tree_preprocessor(False)),
            ("model",HistGradientBoostingClassifier(
                learning_rate=.05,max_iter=180,max_leaf_nodes=15,
                min_samples_leaf=30,l2_regularization=3.0,random_state=SEED
            ))
        ])
        self.state.fit(feature_frame(state_train),state_train.target_state.astype(str))
        p=prod_train[prod_train.target_state!="out"].copy()
        pf=feature_frame(p)
        pf["future_state"]=p.target_state.astype(str).to_numpy()
        self.prod=Pipeline([
            ("prep",tree_preprocessor(True)),
            ("model",HistGradientBoostingRegressor(
                learning_rate=.05,max_iter=180,max_leaf_nodes=15,
                min_samples_leaf=30,l2_regularization=3.0,random_state=SEED
            ))
        ])
        self.prod.fit(pf,p.target_points.to_numpy(float))
        return self
    def predict(self,test):
        X=feature_frame(test)
        probs_raw=self.state.predict_proba(X)
        classes=[str(c) for c in self.state.named_steps["model"].classes_]
        probs=np.zeros((len(test),len(STATES)),float)
        for j,c in enumerate(classes):
            if c in STATE_RANK:
                probs[:,STATE_RANK[c]]=probs_raw[:,j]
        ss=probs.sum(axis=1,keepdims=True); ss[ss<=0]=1
        probs=probs/ss
        means=np.zeros((len(test),len(STATES)),float)
        for st in POSITIVE:
            q=feature_frame(test,future_state=st)
            means[:,STATE_RANK[st]]=np.clip(self.prod.predict(q),0,None)
        return probs,means

class N2:
    name="N2_spline_two_part"
    def fit(self,state_train,prod_train):
        X=feature_frame(state_train)
        ypersist=(state_train.target_state!="out").astype(int).to_numpy()
        self.persist=ConstantOrLogit().fit(X,ypersist)
        pos=state_train[state_train.target_state!="out"].copy()
        Xp=feature_frame(pos)
        self.ordered=[]
        for _,rank in THRESHOLDS:
            y=(pos.target_state.map(STATE_RANK)>=rank).astype(int).to_numpy()
            self.ordered.append(ConstantOrLogit().fit(Xp,y))
        pp=prod_train[prod_train.target_state!="out"].copy()
        pfx=feature_frame(pp); pfx["future_state"]=pp.target_state.astype(str).to_numpy()
        self.prod=Pipeline([
            ("prep",spline_preprocessor(True)),
            ("model",Ridge(alpha=10.0)),
        ])
        self.prod.fit(pfx,pp.target_points.to_numpy(float))
        return self
    def predict(self,test):
        X=feature_frame(test)
        persist=np.clip(self.persist.p(X),1e-6,1-1e-6)
        pos_probs=[]
        last=np.ones(len(test),float)
        for m in self.ordered:
            q=np.clip(m.p(X),0,1)
            q=np.minimum(last,q)
            pos_probs.append(q); last=q
        useful,starter,premium,elite=pos_probs
        cond=np.column_stack([
            1-useful,
            useful-starter,
            starter-premium,
            premium-elite,
            elite,
        ])
        cond=np.clip(cond,0,1)
        cs=cond.sum(axis=1,keepdims=True); cs[cs<=0]=1
        cond=cond/cs
        probs=np.zeros((len(test),len(STATES)),float)
        probs[:,0]=1-persist
        probs[:,1:]=persist[:,None]*cond
        means=np.zeros((len(test),len(STATES)),float)
        for st in POSITIVE:
            q=feature_frame(test,future_state=st)
            means[:,STATE_RANK[st]]=np.clip(self.prod.predict(q),0,None)
        return probs,means

def state_train_for(rows,T,h):
    if h==2:
        return rows[(rows.source_season<T)&(rows.source_season+rows.horizon<=T-1)&(rows.horizon.isin([1,2]))].copy()
    return rows[(rows.source_season<T)&(rows.source_season+3<=T-1)&(rows.horizon==3)].copy()

def prod_train_for(rows,T,h):
    return rows[(rows.source_season<T)&(rows.source_season+h<=T-1)&(rows.horizon==h)].copy()

def crps_discrete(vals,probs,y):
    v=np.asarray(vals,float); p=np.asarray(probs,float); s=p.sum()
    if s<=0:return np.nan
    p=p/s
    return float(np.sum(p*np.abs(v-y))-.5*np.sum(p[:,None]*p[None,:]*np.abs(v[:,None]-v[None,:])))

def add_scores(df,name):
    pcols=[f"{name}_p_{s}" for s in STATES]
    probs=df[pcols].to_numpy(float)
    idx=np.asarray([STATE_RANK[s] for s in df.target_state.astype(str)],int)
    oh=np.eye(len(STATES))[idx]
    df[f"{name}_state_brier"]=np.sum((probs-oh)**2,axis=1)
    df[f"{name}_state_logloss"]=-np.log(np.clip(probs[np.arange(len(df)),idx],1e-12,1))
    active=(df.target_state!="out").astype(int).to_numpy()
    pa=1-probs[:,0]
    df[f"{name}_persist_brier"]=(pa-active)**2
    df[f"{name}_persist_logloss"]=-(active*np.log(np.clip(pa,1e-12,1))+(1-active)*np.log(np.clip(1-pa,1e-12,1)))
    err=df[f"{name}_points"].to_numpy(float)-df.target_points.to_numpy(float)
    df[f"{name}_abs_error"]=np.abs(err)
    df[f"{name}_sq_error"]=err*err
    df[f"{name}_bias_error"]=err
    return df

def build_new_predictions(rows):
    pieces=[]
    for h,origins in ((2,OUTER_H2),(3,OUTER_H3)):
        for T in origins:
            test=rows[(rows.source_season==T)&(rows.horizon==h)].copy()
            if test.empty:continue
            st=state_train_for(rows,T,h); pt=prod_train_for(rows,T,h)
            if len(st)<500 or len(pt)<300:continue
            for cls in (N1,N2):
                model=cls().fit(st,pt)
                probs,means=model.predict(test)
                out=test[[
                    "source_season","player_id","position","horizon","career_stage","age","age_band",
                    "source_points","source_percentile","target_points","target_state","target_present",
                    "role_loss","top10","top5","deep_collapse"
                ]].copy()
                out["model"]=model.name
                for j,s in enumerate(STATES):
                    out[f"p_{s}"]=probs[:,j]
                    out[f"mean_{s}"]=means[:,j]
                out["pred_points"]=np.sum(probs*means,axis=1)
                out["crps"]=[
                    crps_discrete(means[i],probs[i],float(out.iloc[i].target_points))
                    for i in range(len(out))
                ]
                pieces.append(out)
    return pd.concat(pieces,ignore_index=True)

def canonicalize_d01(redpred):
    pieces=[]
    base=redpred.copy()
    for name in ("D0","D1"):
        z=base[[
            "source_season","player_id","position","horizon","career_stage","age",
            "source_points","source_percentile","target_points","target_state","target_present",
            "role_loss","top10","top5","deep_collapse"
        ]].copy()
        z["age_band"]=base["age"].map(lambda x:"unknown")
        # Prefer durable age_band if rolling output contains it.
        if "age_band" in base.columns:z["age_band"]=base["age_band"]
        z["model"]=name
        for s in STATES:z[f"p_{s}"]=base[f"p_{s}"].to_numpy(float)
        if name=="D0":
            z["mean_out"]=0.0
            for s in POSITIVE:z[f"mean_{s}"]=base["active_D0"].to_numpy(float)
            z["pred_points"]=base["pred_D0"].to_numpy(float)
        else:
            z["mean_out"]=0.0
            for s in POSITIVE:z[f"mean_{s}"]=base[f"d1_mean_{s}"].to_numpy(float)
            z["pred_points"]=base["pred_D1"].to_numpy(float)
        z["crps"]=[
            crps_discrete(
                [z.iloc[i][f"mean_{s}"] for s in STATES],
                [z.iloc[i][f"p_{s}"] for s in STATES],
                float(z.iloc[i].target_points),
            ) for i in range(len(z))
        ]
        pieces.append(z)
    return pd.concat(pieces,ignore_index=True)

def wide_rows(long):
    keys=["source_season","player_id","position","horizon","career_stage","age","age_band",
          "source_points","source_percentile","target_points","target_state","target_present",
          "role_loss","top10","top5","deep_collapse"]
    models=sorted(long.model.unique())
    base=long[keys].drop_duplicates(["source_season","player_id","position","horizon"])
    out=base.copy()
    for m in models:
        q=long[long.model==m].copy()
        keep=["source_season","player_id","position","horizon","pred_points","crps"]+[f"p_{s}" for s in STATES]
        q=q[keep].rename(columns={"pred_points":f"{m}_points","crps":f"{m}_crps",**{f"p_{s}":f"{m}_p_{s}" for s in STATES}})
        out=out.merge(q,on=["source_season","player_id","position","horizon"],how="inner",validate="one_to_one")
    for m in models:out=add_scores(out,m)
    return out,models

def metric_summary(g,m):
    y=g.target_points.to_numpy(float); p=g[f"{m}_points"].to_numpy(float)
    return {
        "n":int(len(g)),
        "mae":float(np.mean(np.abs(p-y))),
        "rmse":float(np.sqrt(np.mean((p-y)**2))),
        "bias":float(np.mean(p-y)),
        "spearman":float(pd.Series(p).corr(pd.Series(y),method="spearman")) if len(g)>1 else None,
        "state_brier":float(g[f"{m}_state_brier"].mean()),
        "state_logloss":float(g[f"{m}_state_logloss"].mean()),
        "persist_brier":float(g[f"{m}_persist_brier"].mean()),
        "persist_logloss":float(g[f"{m}_persist_logloss"].mean()),
        "crps":float(g[f"{m}_crps"].mean()),
    }

def two_way_boot(g,a,b,metric,reps=2000):
    # Positive gain means A has lower loss than B.
    if metric=="mae":
        d=g[f"{b}_abs_error"].to_numpy(float)-g[f"{a}_abs_error"].to_numpy(float)
    elif metric=="rmse":
        # Bootstrap MSE gain, report root-scale central separately in summary.
        d=g[f"{b}_sq_error"].to_numpy(float)-g[f"{a}_sq_error"].to_numpy(float)
    else:
        d=g[f"{b}_{metric}"].to_numpy(float)-g[f"{a}_{metric}"].to_numpy(float)
    seasons=pd.Categorical(g.source_season).codes
    players=pd.Categorical(g.player_id).codes
    ns=int(seasons.max()+1); np_=int(players.max()+1)
    rng=np.random.default_rng(SEED+sum(map(ord,a+b+metric)))
    vals=np.empty(reps,float)
    for i in range(reps):
        ws=rng.exponential(1,ns); wp=rng.exponential(1,np_)
        w=ws[seasons]*wp[players]
        vals[i]=float(np.sum(w*d)/np.sum(w))
    q=np.quantile(vals,[.025,.975])
    return {"gain_a_over_b":float(d.mean()),"ci95":[float(q[0]),float(q[1])],"reps":reps}

def pairwise(wide,models):
    rows=[]
    metrics=("mae","state_brier","state_logloss","persist_brier","persist_logloss","crps")
    for h in (2,3):
        gh=wide[wide.horizon==h]
        for i,a in enumerate(models):
            for b in models[i+1:]:
                for metric in metrics:
                    z=two_way_boot(gh,a,b,metric)
                    rows.append({"scope":"horizon","horizon":h,"position":"ALL","a":a,"b":b,"metric":metric,**z})
                for pos in POSITIONS:
                    g=gh[gh.position==pos]
                    if len(g)<100:continue
                    for metric in ("mae","state_brier","crps"):
                        z=two_way_boot(g,a,b,metric,reps=1000)
                        rows.append({"scope":"position","horizon":h,"position":pos,"a":a,"b":b,"metric":metric,**z})
    return pd.DataFrame(rows)

def summaries(wide,models):
    rows=[]
    groups=[("ALL",wide)]
    for h in (2,3):groups.append((f"H{h}",wide[wide.horizon==h]))
    for h in (2,3):
        for p in POSITIONS:groups.append((f"H{h}_{p}",wide[(wide.horizon==h)&(wide.position==p)]))
        for cs in ("developmental","established","veteran"):groups.append((f"H{h}_{cs}",wide[(wide.horizon==h)&(wide.career_stage==cs)]))
    for label,g in groups:
        if len(g)<30:continue
        for m in models:rows.append({"group":label,"model":m,**metric_summary(g,m)})
    return pd.DataFrame(rows)

def origin_metrics(wide,models):
    rows=[]
    for (h,yr),g in wide.groupby(["horizon","source_season"]):
        for m in models:rows.append({"horizon":int(h),"origin":int(yr),"model":m,**metric_summary(g,m)})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--career-panel",type=Path,required=True)
    ap.add_argument("--redevelopment-code",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    red=load_module(args.redevelopment_code,"authority_red")
    panel=pd.read_csv(args.career_panel)
    rows=red.build_rows(panel,max_source_season=2023)

    # Exact D0/D1 reproduction from the frozen redevelopment implementation.
    redpred,fitlog=red.rolling_predictions(rows,seasons=range(2014,2024))
    redpred=redpred[((redpred.horizon==2)&redpred.source_season.isin(OUTER_H2))|
                    ((redpred.horizon==3)&redpred.source_season.isin(OUTER_H3))].copy()

    new=build_new_predictions(rows)
    old=canonicalize_d01(redpred)
    long=pd.concat([old,new],ignore_index=True)
    wide,models=wide_rows(long)

    summ=summaries(wide,models)
    orig=origin_metrics(wide,models)
    pairs=pairwise(wide,models)

    summ.to_csv(args.output_dir/"NEW_FAMILY_SYMMETRIC_SUMMARY.csv",index=False)
    orig.to_csv(args.output_dir/"NEW_FAMILY_ORIGIN_METRICS.csv",index=False)
    pairs.to_csv(args.output_dir/"NEW_FAMILY_PAIRWISE_UNCERTAINTY.csv",index=False)
    wide.to_csv(args.output_dir/"NEW_FAMILY_COMMON_OOT_ROWS.csv",index=False)

    result={
        "study":"forecast-model-authority-bounded-new-family",
        "authority":"research_only_no_production_change",
        "common_coordinate":{
            "H2_origins":list(OUTER_H2),"H3_origins":list(OUTER_H3),
            "rows":int(len(wide)),
            "H2_rows":int((wide.horizon==2).sum()),"H3_rows":int((wide.horizon==3).sum()),
        },
        "models":models,
        "frozen_new_families":{
            "N1_histgb":{
                "state":"direct six-state HistGradientBoostingClassifier",
                "production":"state-conditioned HistGradientBoostingRegressor",
                "learning_rate":.05,"max_iter":180,"max_leaf_nodes":15,"min_samples_leaf":30,
                "l2_regularization":3.0,"random_state":SEED,
            },
            "N2_spline_two_part":{
                "state":"logistic persistence + ordered positive-state logistic heads on cubic spline basis",
                "production":"state-conditioned Ridge on same spline basis",
                "n_knots":5,"degree":3,"C":.25,"ridge_alpha":10.0,
            },
        },
        "fitlog_rows":len(fitlog),
        "guards":{
            "post_result_hyperparameter_search":False,
            "named_player_tuning":False,
            "current_board_selection":False,
            "production_forecast_changed":False,
            "production_h3_changed":False,
            "intrinsic_changed":False,
        },
    }
    (args.output_dir/"NEW_FAMILY_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

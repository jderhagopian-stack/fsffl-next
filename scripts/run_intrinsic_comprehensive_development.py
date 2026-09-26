from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss
from sklearn.preprocessing import StandardScaler

OUT = Path("artifacts/research/intrinsic_comprehensive_y4_y8_20260926")
POSITIONS = ("QB","RB","WR","TE")
HORIZONS = (4,5,6,7,8)
RANDOM_SEED = 20260926
MIN_TRAIN_ROWS = 80
MIN_POSITIVE_ROWS = 25
MIN_MATERIAL_IMPROVEMENT = 0.005
MAX_INNER_FOLDS = 4

MODEL_COMPLEXITY = {
    "carry_y3":0.0,
    "ridge_direct":0.001,
    "two_part_ridge":0.002,
    "histgb_direct":0.004,
    "two_part_histgb":0.005,
    "state_histgb":0.006,
    "extra_trees":0.006,
}
FEATURE_COMPLEXITY = {
    "forecast10":0.0,
    "forecast_rich":0.001,
    "pedigree_plus":0.002,
    "football_plus":0.003,
    "trajectory_plus":0.003,
    "full_rich":0.004,
    "full_no_pedigree":0.003,
    "full_no_football":0.003,
    "full_no_trajectory":0.003,
    "full_no_uncertainty":0.003,
}
ARCH_COMPLEXITY = {
    "specialist":0.006,
    "shared_horizon":0.003,
    "position_continuous":0.003,
    "global_continuous":0.0,
    "hierarchical_blend":0.005,
}

BASE10 = (
    "age","experience","prior_pct","log_prior_points","log_y1",
    "y1_pct","y2_ratio","y3_ratio","y2_delta","y3_delta",
)
FORECAST_PLUS = (
    "y1","y2","y3","sd1","sd2","sd3","sd2_ratio","sd3_ratio",
    "forecast_slope12","forecast_slope23","forecast_curvature",
    "forecast_cv1","forecast_cv2","forecast_cv3",
)
PEDIGREE = (
    "drafted","draft_round","draft_pick","draft_pick_percentile",
    "rookie_age","height","weight","bmi_proxy","draft_team_same_lag1",
)
FOOTBALL = (
    "l1_games","l2_games","l3_games","games_mean2","games_mean3","games_min2","games_vol3",
    "l1_fantasy","l2_fantasy","l3_fantasy","fantasy_mean2","fantasy_mean3","fantasy_slope12","fantasy_vol3",
    "l1_opportunities","l2_opportunities","l3_opportunities","opp_mean2","opp_mean3","opp_slope12","opp_vol3",
    "l1_role_share","l2_role_share","l3_role_share","role_mean2","role_mean3","role_slope12","role_vol3",
    "l1_points_per_game","l1_points_per_opp","l1_pass_yards_per_att","l1_pass_td_rate","l1_int_rate",
    "l1_pass_epa_per_att","l1_cpoe","l1_rush_yards_per_carry","l1_rush_epa_per_carry",
    "l1_catch_rate","l1_rec_yards_per_target","l1_rec_epa_per_target","l1_target_share","l1_air_yards_share","l1_wopr",
    "same_team_1_2","same_team_2_3","prior_team_tenure3","established_qb_starter_seasons3",
)
TRAJECTORY = (
    "res_history_n","residual_mean","residual_sd","residual_last","production_history_n",
    "production_slope","production_volatility","career_high_recency","res_reliability","player_residual_component",
    "innov_history_n","stable_level_baseline","latest_residual","latest_innovation","innovation_slope",
    "innovation_acceleration","innovation_autocorrelation","innovation_volatility","innovation_z",
    "same_sign_count","signed_same_sign_count","volatility_ratio","level_component",
)
CATEGORICAL = (
    "college_conference","trajectory_state","innovation_state","volatility_band",
    "production_pattern","career_stage","production_tier","prior_direction",
)

FEATURE_SETS: dict[str, tuple[str,...]] = {}

def uniq(seq):
    out=[]
    seen=set()
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return tuple(out)

FEATURE_SETS["forecast10"] = BASE10
FEATURE_SETS["forecast_rich"] = uniq(BASE10 + FORECAST_PLUS)
FEATURE_SETS["pedigree_plus"] = uniq(BASE10 + FORECAST_PLUS + PEDIGREE + ("college_conference",))
FEATURE_SETS["football_plus"] = uniq(BASE10 + FORECAST_PLUS + FOOTBALL)
FEATURE_SETS["trajectory_plus"] = uniq(BASE10 + FORECAST_PLUS + TRAJECTORY + ("trajectory_state","innovation_state","volatility_band","production_pattern","career_stage","production_tier","prior_direction"))
FEATURE_SETS["full_rich"] = uniq(BASE10 + FORECAST_PLUS + PEDIGREE + FOOTBALL + TRAJECTORY + CATEGORICAL)
FEATURE_SETS["full_no_pedigree"] = uniq(BASE10 + FORECAST_PLUS + FOOTBALL + TRAJECTORY + tuple(x for x in CATEGORICAL if x!="college_conference"))
FEATURE_SETS["full_no_football"] = uniq(BASE10 + FORECAST_PLUS + PEDIGREE + TRAJECTORY + CATEGORICAL)
FEATURE_SETS["full_no_trajectory"] = uniq(BASE10 + FORECAST_PLUS + PEDIGREE + FOOTBALL + ("college_conference",))
FEATURE_SETS["full_no_uncertainty"] = uniq(BASE10 + tuple(x for x in FORECAST_PLUS if not x.startswith("sd") and not x.startswith("forecast_cv")) + PEDIGREE + FOOTBALL + TRAJECTORY + CATEGORICAL)

SPECIALIST_SPECS = [
    ("forecast10","ridge_direct"),("forecast10","two_part_ridge"),("forecast10","histgb_direct"),("forecast10","two_part_histgb"),
    ("forecast_rich","ridge_direct"),("forecast_rich","two_part_ridge"),("forecast_rich","histgb_direct"),("forecast_rich","two_part_histgb"),
    ("pedigree_plus","two_part_ridge"),("pedigree_plus","two_part_histgb"),
    ("football_plus","ridge_direct"),("football_plus","two_part_ridge"),("football_plus","histgb_direct"),("football_plus","two_part_histgb"),
    ("trajectory_plus","two_part_ridge"),("trajectory_plus","two_part_histgb"),
    ("full_rich","ridge_direct"),("full_rich","two_part_ridge"),("full_rich","histgb_direct"),("full_rich","two_part_histgb"),("full_rich","state_histgb"),("full_rich","extra_trees"),
    ("full_no_pedigree","two_part_ridge"),("full_no_pedigree","two_part_histgb"),
    ("full_no_football","two_part_ridge"),("full_no_football","two_part_histgb"),
    ("full_no_trajectory","two_part_ridge"),("full_no_trajectory","two_part_histgb"),
    ("full_no_uncertainty","two_part_ridge"),("full_no_uncertainty","two_part_histgb"),
]
SHARED_SPECS = [
    ("forecast_rich","ridge_direct"),("forecast_rich","two_part_ridge"),
    ("football_plus","two_part_ridge"),("football_plus","two_part_histgb"),
    ("full_rich","ridge_direct"),("full_rich","two_part_ridge"),("full_rich","histgb_direct"),("full_rich","two_part_histgb"),
]

def nfloat(x, default=np.nan):
    try:
        v=float(x)
        return v if np.isfinite(v) else default
    except Exception:
        return default

def add_qb_governed_path(m: pd.DataFrame, qb: dict) -> pd.DataFrame:
    m=m.copy()
    probs={}
    for r in qb.get("records",[]):
        fid=f"preseason-{int(r['source_season'])}"
        probs[(fid,str(r["player_id"]),1)]=float(r["prob_y2"])
        probs[(fid,str(r["player_id"]),2)]=float(r["prob_y3"])
    y1={(str(r.fold_id),str(r.asset_id)):float(r.player_forecast_mean) for r in m.itertuples() if int(r.season_offset)==0}
    for idx,r in m.iterrows():
        off=int(r.season_offset)
        key=(str(r.fold_id),str(r.asset_id),off)
        if str(r.position)=="QB" and off in (1,2) and key in probs:
            m.at[idx,"player_forecast_mean"]=probs[key]*y1[(str(r.fold_id),str(r.asset_id))]
    return m

def build_forecast_base(m: pd.DataFrame) -> pd.DataFrame:
    p=m.pivot_table(
        index=["fold_id","target_season","asset_id","position"],
        columns="season_offset",
        values=["player_forecast_mean","player_forecast_stddev"],
        aggfunc="first",
    ).reset_index()
    p.columns=["_".join(str(x) for x in col if str(x)!="") if isinstance(col,tuple) else str(col) for col in p.columns]
    p=p.rename(columns={
        "fold_id":"fold_id","target_season":"base_season","asset_id":"player_id","position":"position",
        "player_forecast_mean_0":"y1","player_forecast_mean_1":"y2","player_forecast_mean_2":"y3",
        "player_forecast_stddev_0":"sd1","player_forecast_stddev_1":"sd2","player_forecast_stddev_2":"sd3",
    })
    p["player_id"]=p["player_id"].astype(str)
    p["base_season"]=p["base_season"].astype(int)
    return p

def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    r=raw.copy()
    r["player_id"]=r["player_id"].astype(str)
    r["season"]=pd.to_numeric(r["season"],errors="coerce").astype("Int64")
    r=r[r["position"].isin(POSITIONS)&r["season"].notna()].copy()
    r["season"]=r["season"].astype(int)
    fp="fantasyPoints" if "fantasyPoints" in r.columns else "fantasy_points"
    r["fantasy_target"]=pd.to_numeric(r[fp],errors="coerce").fillna(0).clip(lower=0)
    for c in r.columns:
        if c in {"player_id","player_name","position","position_group","team","birth_date","college_name","college_conference","draft_team"}:
            continue
        if c!="season":
            r[c]=pd.to_numeric(r[c],errors="coerce")
    r["fp_pct"]=r.groupby(["season","position"])["fantasy_target"].rank(pct=True,method="average")

    for c in ["attempts","carries","targets","games","passing_yards","passing_tds","passing_interceptions","passing_epa","passing_cpoe",
              "rushing_yards","rushing_tds","rushing_epa","receptions","receiving_yards","receiving_tds","receiving_epa","target_share",
              "air_yards_share","wopr","fumbles"]:
        if c not in r: r[c]=0.0
        r[c]=r[c].fillna(0.0)

    team=r.groupby(["season","team"],dropna=False).agg(
        team_pass_attempts=("attempts","sum"),
        team_carries=("carries","sum"),
        team_targets=("targets","sum"),
    ).reset_index()
    r=r.merge(team,on=["season","team"],how="left")
    r["pass_share"]=np.where(r.team_pass_attempts>0,r.attempts/r.team_pass_attempts,0.0)
    r["carry_share"]=np.where(r.team_carries>0,r.carries/r.team_carries,0.0)
    r["target_share_derived"]=np.where(r.team_targets>0,r.targets/r.team_targets,0.0)
    r["opportunities"]=np.select(
        [r.position=="QB",r.position=="RB",r.position.isin(["WR","TE"])],
        [r.attempts+r.get("sacks_suffered",0).fillna(0)+r.carries,r.carries+r.targets,r.targets+r.carries],
        default=r.carries+r.targets,
    )
    r["role_share"]=np.select(
        [r.position=="QB",r.position=="RB",r.position.isin(["WR","TE"])],
        [r.pass_share,
         np.where((r.team_carries+r.team_targets)>0,(r.carries+r.targets)/(r.team_carries+r.team_targets),0.0),
         r.target_share_derived],
        default=0.0,
    )
    r["points_per_game"]=np.where(r.games>0,r.fantasy_target/r.games,0.0)
    r["points_per_opp"]=np.where(r.opportunities>0,r.fantasy_target/r.opportunities,0.0)
    r["pass_yards_per_att"]=np.where(r.attempts>0,r.passing_yards/r.attempts,0.0)
    r["pass_td_rate"]=np.where(r.attempts>0,r.passing_tds/r.attempts,0.0)
    r["int_rate"]=np.where(r.attempts>0,r.passing_interceptions/r.attempts,0.0)
    r["pass_epa_per_att"]=np.where(r.attempts>0,r.passing_epa/r.attempts,0.0)
    r["rush_yards_per_carry"]=np.where(r.carries>0,r.rushing_yards/r.carries,0.0)
    r["rush_epa_per_carry"]=np.where(r.carries>0,r.rushing_epa/r.carries,0.0)
    r["catch_rate"]=np.where(r.targets>0,r.receptions/r.targets,0.0)
    r["rec_yards_per_target"]=np.where(r.targets>0,r.receiving_yards/r.targets,0.0)
    r["rec_epa_per_target"]=np.where(r.targets>0,r.receiving_epa/r.targets,0.0)
    return r

def metadata_frame(players: pd.DataFrame) -> pd.DataFrame:
    p=players.copy()
    p["player_id"]=p["gsis_id"].astype(str)
    keep=["player_id","birth_date","height","weight","college_name","college_conference","rookie_season","draft_year","draft_round","draft_pick","draft_team"]
    for c in keep:
        if c not in p: p[c]=np.nan
    p=p[keep].drop_duplicates("player_id")
    p["birth_date"]=pd.to_datetime(p["birth_date"],errors="coerce")
    for c in ["height","weight","rookie_season","draft_year","draft_round","draft_pick"]:
        p[c]=pd.to_numeric(p[c],errors="coerce")
    p["drafted"]=p["draft_pick"].notna().astype(float)
    # Draft percentile within class is static and outcome-independent.
    p["draft_pick_percentile"]=np.nan
    for yr,g in p[p.draft_pick.notna()].groupby("draft_year"):
        mx=max(1.0,float(g.draft_pick.max()))
        p.loc[g.index,"draft_pick_percentile"]=1.0-(g.draft_pick-1.0)/mx
    return p

def merge_lags(base: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    cols=[
        "player_id","season","team","games","fantasy_target","fp_pct","opportunities","role_share",
        "points_per_game","points_per_opp","pass_yards_per_att","pass_td_rate","int_rate","pass_epa_per_att","passing_cpoe",
        "rush_yards_per_carry","rush_epa_per_carry","catch_rate","rec_yards_per_target","rec_epa_per_target",
        "target_share","air_yards_share","wopr","attempts"
    ]
    out=base.copy()
    for lag in (1,2,3):
        q=raw[cols].copy()
        q["base_season"]=q["season"]+lag
        q=q.drop(columns=["season"]).rename(columns={c:f"l{lag}_{c}" for c in cols if c!="player_id" and c!="base_season"})
        out=out.merge(q,on=["player_id","base_season"],how="left")
    return out

def add_engineered_features(base: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    x=base.merge(metadata_frame(players),on="player_id",how="left")
    season_date=pd.to_datetime(x["base_season"].astype(str)+"-09-01")
    x["age"]=(season_date-x["birth_date"]).dt.days/365.2425
    x["experience"]=(x["base_season"]-x["rookie_season"]).clip(lower=0)
    rookie_date=pd.to_datetime(x["rookie_season"].astype("Int64").astype(str)+"-09-01",errors="coerce")
    x["rookie_age"]=(rookie_date-x["birth_date"]).dt.days/365.2425
    x["bmi_proxy"]=np.where(x.height>0,703.0*x.weight/(x.height*x.height),np.nan)
    x["draft_team_same_lag1"]=(x["draft_team"].fillna("")==x["l1_team"].fillna("")).astype(float)
    x["prior_pct"]=x["l1_fp_pct"]
    x["prior_points"]=x["l1_fantasy_target"]
    x["log_prior_points"]=np.log1p(x["prior_points"].fillna(0).clip(lower=0))
    x["log_y1"]=np.log1p(x["y1"].fillna(0).clip(lower=0))
    x["y1_pct"]=x.groupby(["base_season","position"])["y1"].rank(pct=True,method="average")
    denom=x["y1"].abs().clip(lower=25.0)
    x["y2_ratio"]=(x.y2/x.y1.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    x["y3_ratio"]=(x.y3/x.y1.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    x["y2_delta"]=((x.y2-x.y1)/denom).clip(-3,3)
    x["y3_delta"]=((x.y3-x.y1)/denom).clip(-3,3)
    x["sd2_ratio"]=(x.sd2/x.sd1.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan)
    x["sd3_ratio"]=(x.sd3/x.sd1.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan)
    x["forecast_slope12"]=x.y2-x.y1
    x["forecast_slope23"]=x.y3-x.y2
    x["forecast_curvature"]=x.y3-2*x.y2+x.y1
    for h in (1,2,3):
        x[f"forecast_cv{h}"]=x[f"sd{h}"]/x[f"y{h}"].abs().clip(lower=25.0)

    for prefix,source in [
        ("games","games"),("fantasy","fantasy_target"),("opportunities","opportunities"),("role_share","role_share")
    ]:
        vals=[x[f"l{k}_{source}"] for k in (1,2,3)]
        x[f"{prefix}_mean2"]=pd.concat(vals[:2],axis=1).mean(axis=1,skipna=True)
        x[f"{prefix}_mean3"]=pd.concat(vals,axis=1).mean(axis=1,skipna=True)
        x[f"{prefix}_slope12"]=vals[0]-vals[1]
        x[f"{prefix}_vol3"]=pd.concat(vals,axis=1).std(axis=1,ddof=0,skipna=True)
    x["games_min2"]=pd.concat([x.l1_games,x.l2_games],axis=1).min(axis=1,skipna=True)

    rename={
      "l1_fantasy_target":"l1_fantasy","l2_fantasy_target":"l2_fantasy","l3_fantasy_target":"l3_fantasy",
      "l1_points_per_game":"l1_points_per_game","l1_points_per_opp":"l1_points_per_opp",
      "l1_pass_yards_per_att":"l1_pass_yards_per_att","l1_pass_td_rate":"l1_pass_td_rate","l1_int_rate":"l1_int_rate",
      "l1_pass_epa_per_att":"l1_pass_epa_per_att","l1_passing_cpoe":"l1_cpoe",
      "l1_rush_yards_per_carry":"l1_rush_yards_per_carry","l1_rush_epa_per_carry":"l1_rush_epa_per_carry",
      "l1_catch_rate":"l1_catch_rate","l1_rec_yards_per_target":"l1_rec_yards_per_target","l1_rec_epa_per_target":"l1_rec_epa_per_target",
      "l1_target_share":"l1_target_share","l1_air_yards_share":"l1_air_yards_share","l1_wopr":"l1_wopr"
    }
    x=x.rename(columns=rename)
    x["same_team_1_2"]=(x.l1_team.fillna("")==x.l2_team.fillna("")).astype(float)
    x["same_team_2_3"]=(x.l2_team.fillna("")==x.l3_team.fillna("")).astype(float)
    x["prior_team_tenure3"]=x["same_team_1_2"]+x["same_team_1_2"]*x["same_team_2_3"]
    x["established_qb_starter_seasons3"]=(
        (x["l1_attempts"].fillna(0)>=200).astype(int)+
        (x["l2_attempts"].fillna(0)>=200).astype(int)+
        (x["l3_attempts"].fillna(0)>=200).astype(int)
    ).where(x.position=="QB",0.0)
    return x

def merge_trajectory(x: pd.DataFrame, residual: pd.DataFrame, innovation: pd.DataFrame) -> pd.DataFrame:
    r=residual.copy()
    r["base_season"]=pd.to_numeric(r["forecast_fold"],errors="coerce").astype("Int64")
    r["player_id"]=r["player_id"].astype(str)
    r=r.rename(columns={
        "history_n":"res_history_n","reliability":"res_reliability"
    })
    rcols=["player_id","base_season","career_stage","production_tier","prior_direction","res_history_n",
           "residual_mean","residual_sd","residual_last","production_history_n","production_slope","production_volatility",
           "production_pattern","career_high_recency","res_reliability","player_residual_component","trajectory_state"]
    r=r[[c for c in rcols if c in r]].drop_duplicates(["player_id","base_season"])
    z=x.merge(r,on=["player_id","base_season"],how="left")

    i=innovation.copy()
    i["base_season"]=pd.to_numeric(i["forecast_fold"],errors="coerce").astype("Int64")
    i["player_id"]=i["player_id"].astype(str)
    i=i.rename(columns={"history_n":"innov_history_n"})
    icols=["player_id","base_season","innov_history_n","stable_level_baseline","latest_residual","latest_innovation",
           "innovation_slope","innovation_acceleration","innovation_autocorrelation","innovation_volatility","innovation_z",
           "same_sign_count","signed_same_sign_count","innovation_state","volatility_ratio","volatility_band","level_component"]
    i=i[[c for c in icols if c in i]].drop_duplicates(["player_id","base_season"])
    return z.merge(i,on=["player_id","base_season"],how="left")

def build_long(base: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    actual={(str(r.player_id),int(r.season)):float(r.fantasy_target) for r in raw.itertuples()}
    rows=[]
    for h in HORIZONS:
        z=base.copy()
        z["horizon"]=h
        z["target_season"]=z["base_season"]+h-1
        z=z[z.target_season<=int(raw.season.max())].copy()
        z["actual"]=[actual.get((str(pid),int(ts)),0.0) for pid,ts in zip(z.player_id,z.target_season)]
        z["active"]=(z.actual>0).astype(int)
        z["horizon_sq"]=float(h*h)
        rows.append(z)
    long=pd.concat(rows,ignore_index=True)
    long["row_id"]=long["base_season"].astype(str)+"|"+long["player_id"]+"|H"+long["horizon"].astype(str)
    return long

def final_holdouts(long: pd.DataFrame) -> dict[int,tuple[int,...]]:
    out={}
    for h in HORIZONS:
        seasons=sorted(long.loc[long.horizon==h,"base_season"].unique())
        out[h]=tuple(seasons[-3:])
    return out

def inner_folds(long: pd.DataFrame, holds: dict[int,tuple[int,...]]) -> dict[int,tuple[int,...]]:
    out={}
    for h in HORIZONS:
        dev=long[(long.horizon==h)&(long.base_season<min(holds[h]))]
        vals=[]
        for T in sorted(dev.base_season.unique(),reverse=True):
            tr=dev[dev.target_season<T]
            if len(tr)>=MIN_TRAIN_ROWS and tr.base_season.nunique()>=2:
                vals.append(int(T))
            if len(vals)>=MAX_INNER_FOLDS:
                break
        out[h]=tuple(sorted(vals))
    return out

def matrix(train: pd.DataFrame, ev: pd.DataFrame, features: tuple[str,...], architecture: str):
    feats=list(features)
    if architecture in {"shared_horizon","global_continuous"}:
        if "position_cat" not in feats: feats.append("position_cat")
    if architecture in {"position_continuous","global_continuous"}:
        if "horizon" not in feats: feats.append("horizon")
        if "horizon_sq" not in feats: feats.append("horizon_sq")
    tr=train.copy(); ee=ev.copy()
    tr["position_cat"]=tr["position"].astype(str); ee["position_cat"]=ee["position"].astype(str)
    cats=[f for f in feats if f in CATEGORICAL or f=="position_cat"]
    nums=[f for f in feats if f not in cats]
    for f in nums:
        if f not in tr: tr[f]=np.nan
        if f not in ee: ee[f]=np.nan
    med=tr[nums].apply(pd.to_numeric,errors="coerce").median().fillna(0)
    a=tr[nums].apply(pd.to_numeric,errors="coerce").fillna(med)
    b=ee[nums].apply(pd.to_numeric,errors="coerce").fillna(med)
    lo=a.quantile(.005); hi=a.quantile(.995)
    a=a.clip(lo,hi,axis=1); b=b.clip(lo,hi,axis=1)
    mean=a.mean(); sd=a.std(ddof=0).replace(0,1).fillna(1)
    a=(a-mean)/sd; b=(b-mean)/sd

    cat_train=[]; cat_eval=[]; cat_names=[]
    for f in cats:
        tv=tr[f].fillna("MISSING").astype(str) if f in tr else pd.Series(["MISSING"]*len(tr),index=tr.index)
        evv=ee[f].fillna("MISSING").astype(str) if f in ee else pd.Series(["MISSING"]*len(ee),index=ee.index)
        vc=tv.value_counts()
        levels=[str(x) for x,n in vc.items() if n>=10]
        if len(levels)>30: levels=levels[:30]
        if not levels: levels=["MISSING"]
        aa=np.column_stack([(tv==lvl).to_numpy(float) for lvl in levels])
        bb=np.column_stack([(evv==lvl).to_numpy(float) for lvl in levels])
        cat_train.append(aa); cat_eval.append(bb); cat_names.extend([f+"="+lvl for lvl in levels])
    A=a.to_numpy(float); B=b.to_numpy(float)
    if cat_train:
        A=np.column_stack([A]+cat_train); B=np.column_stack([B]+cat_eval)
    return A,B,nums+cat_names

def state_labels(train: pd.DataFrame) -> np.ndarray:
    out=np.zeros(len(train),dtype=int)
    for pos in train.position.unique():
        idx=np.where(train.position.to_numpy()==pos)[0]
        vals=train.iloc[idx].actual.to_numpy(float)
        posvals=vals[vals>0]
        if len(posvals)>=9:
            q1,q2=np.quantile(posvals,[1/3,2/3])
        elif len(posvals):
            q1=q2=float(np.median(posvals))
        else:
            q1=q2=0.0
        s=np.zeros(len(idx),dtype=int)
        s[(vals>0)&(vals<=q1)]=1
        s[(vals>q1)&(vals<=q2)]=2
        s[vals>q2]=3
        out[idx]=s
    return out

def fit_predict(train: pd.DataFrame, ev: pd.DataFrame, feature_set: str, model: str, architecture: str):
    if model=="carry_y3":
        return ev.y3.clip(lower=0).to_numpy(float), np.full(len(ev),np.nan)
    features=FEATURE_SETS[feature_set]
    X,Z,_=matrix(train,ev,features,architecture)
    y=train.actual.to_numpy(float)
    if len(train)<MIN_TRAIN_ROWS:
        return np.repeat(float(np.mean(y)) if len(y) else 0.0,len(ev)),np.repeat(float(np.mean(y>0)) if len(y) else 0.0,len(ev))

    if model=="ridge_direct":
        rg=Ridge(alpha=10.0).fit(X,np.log1p(np.clip(y,0,None)))
        pred=np.expm1(rg.predict(Z)).clip(0,650)
        return pred,np.full(len(ev),np.nan)

    if model=="two_part_ridge":
        active=(y>0).astype(int)
        if len(np.unique(active))>1:
            lg=LogisticRegression(C=1.0,solver="lbfgs",max_iter=2500,random_state=RANDOM_SEED).fit(X,active)
            p=lg.predict_proba(Z)[:,1]
        else:
            p=np.repeat(float(active.mean()),len(ev))
        pos=y>0
        if pos.sum()>=MIN_POSITIVE_ROWS:
            rg=Ridge(alpha=10.0).fit(X[pos],np.log1p(y[pos]))
            cp=np.expm1(rg.predict(Z)).clip(0,650)
        else:
            cp=np.repeat(float(y[pos].mean()) if pos.sum() else 0.0,len(ev))
        return (p*cp).clip(0,650),p

    if model=="histgb_direct":
        rg=HistGradientBoostingRegressor(
            loss="squared_error",learning_rate=.05,max_iter=100,max_leaf_nodes=15,
            min_samples_leaf=20,l2_regularization=10.0,random_state=RANDOM_SEED
        ).fit(X,y)
        return np.clip(rg.predict(Z),0,650),np.full(len(ev),np.nan)

    if model=="two_part_histgb":
        active=(y>0).astype(int)
        if len(np.unique(active))>1:
            lg=HistGradientBoostingClassifier(
                learning_rate=.05,max_iter=90,max_leaf_nodes=7,min_samples_leaf=20,
                l2_regularization=10.0,random_state=RANDOM_SEED
            ).fit(X,active)
            p=lg.predict_proba(Z)[:,1]
        else:
            p=np.repeat(float(active.mean()),len(ev))
        pos=y>0
        if pos.sum()>=MIN_POSITIVE_ROWS:
            rg=HistGradientBoostingRegressor(
                loss="squared_error",learning_rate=.05,max_iter=100,max_leaf_nodes=15,
                min_samples_leaf=20,l2_regularization=10.0,random_state=RANDOM_SEED
            ).fit(X[pos],y[pos])
            cp=np.clip(rg.predict(Z),0,650)
        else:
            cp=np.repeat(float(y[pos].mean()) if pos.sum() else 0.0,len(ev))
        return (p*cp).clip(0,650),p

    if model=="state_histgb":
        states=state_labels(train)
        if len(np.unique(states))<2:
            return np.repeat(float(y.mean()),len(ev)),np.repeat(float(np.mean(y>0)),len(ev))
        cl=HistGradientBoostingClassifier(
            learning_rate=.05,max_iter=100,max_leaf_nodes=15,min_samples_leaf=20,
            l2_regularization=10.0,random_state=RANDOM_SEED
        ).fit(X,states)
        probs=cl.predict_proba(Z)
        classes=list(cl.classes_)
        means={}
        for pos in POSITIONS:
            mask=train.position.to_numpy()==pos
            for s in range(4):
                vals=y[mask & (states==s)]
                means[(pos,s)]=float(vals.mean()) if len(vals) else (0.0 if s==0 else float(y[mask].mean()) if mask.any() else 0.0)
        pred=[]; pact=[]
        for i,pos in enumerate(ev.position.astype(str)):
            v=0.0; p0=0.0
            for j,s in enumerate(classes):
                v+=float(probs[i,j])*means.get((pos,int(s)),0.0)
                if int(s)==0: p0=float(probs[i,j])
            pred.append(v); pact.append(1-p0)
        return np.clip(np.asarray(pred),0,650),np.clip(np.asarray(pact),0,1)

    if model=="extra_trees":
        rg=ExtraTreesRegressor(
            n_estimators=140,min_samples_leaf=6,max_features=.7,
            random_state=RANDOM_SEED,n_jobs=-1
        ).fit(X,y)
        return np.clip(rg.predict(Z),0,650),np.full(len(ev),np.nan)

    raise KeyError(model)

def metric(g: pd.DataFrame) -> dict:
    y=g.actual.to_numpy(float); p=g.pred.to_numpy(float); e=p-y
    out={
        "n":int(len(g)),
        "rmse":float(np.sqrt(np.mean(e*e))),
        "mae":float(np.mean(np.abs(e))),
        "bias":float(np.mean(e)),
        "spearman":float(pd.Series(p).corr(pd.Series(y),method="spearman")) if len(g)>2 and len(set(p))>1 and len(set(y))>1 else 0.0,
    }
    if len(g)>=10:
        cut=float(np.quantile(y,.90))
        mask=y>=cut
        out["tail_rmse"]=float(np.sqrt(np.mean(e[mask]*e[mask]))) if mask.any() else out["rmse"]
    else:
        out["tail_rmse"]=out["rmse"]
    if "p_active" in g and g.p_active.notna().sum()>=10:
        q=g[g.p_active.notna()]
        out["survival_brier"]=float(brier_score_loss((q.actual>0).astype(int),q.p_active.clip(0,1)))
        out["survival_calibration_gap"]=float(abs(q.p_active.mean()-(q.actual>0).mean()))
    else:
        out["survival_brier"]=np.nan
        out["survival_calibration_gap"]=np.nan
    return out

def composite(m: dict, b: dict, complexity: float=0.0) -> float:
    eps=1e-6
    return (
        .32*math.log(max(eps,m["rmse"])/max(eps,b["rmse"]))+
        .16*math.log(max(eps,m["mae"])/max(eps,b["mae"]))+
        .22*math.log(max(eps,m["tail_rmse"])/max(eps,b["tail_rmse"]))+
        .15*(b["spearman"]-m["spearman"])+
        .05*abs(m["bias"])/(max(10.0,float(np.mean([b["rmse"],b["mae"]]))))+
        complexity
    )

def candidate_complexity(arch,fs,model):
    return ARCH_COMPLEXITY.get(arch,0)+FEATURE_COMPLEXITY.get(fs,0)+MODEL_COMPLEXITY.get(model,0)

def generate_specialist_oof(long,folds):
    rec=[]
    for h in HORIZONS:
        for T in folds[h]:
            evh=long[(long.horizon==h)&(long.base_season==T)]
            trainh=long[(long.horizon==h)&(long.target_season<T)]
            for pos in POSITIONS:
                ev=evh[evh.position==pos]
                tr=trainh[trainh.position==pos]
                if len(ev)==0 or len(tr)<MIN_TRAIN_ROWS: continue
                basepred=ev.y3.clip(lower=0).to_numpy(float)
                for i,r in enumerate(ev.itertuples()):
                    rec.append({"row_id":r.row_id,"base_season":T,"horizon":h,"position":pos,"player_id":r.player_id,
                                "actual":float(r.actual),"candidate":"specialist|forecast10|carry_y3","architecture":"specialist",
                                "feature_set":"forecast10","model":"carry_y3","pred":float(basepred[i]),"p_active":np.nan})
                for fs,model in SPECIALIST_SPECS:
                    pred,pa=fit_predict(tr,ev,fs,model,"specialist")
                    for i,r in enumerate(ev.itertuples()):
                        rec.append({"row_id":r.row_id,"base_season":T,"horizon":h,"position":pos,"player_id":r.player_id,
                                    "actual":float(r.actual),"candidate":f"specialist|{fs}|{model}","architecture":"specialist",
                                    "feature_set":fs,"model":model,"pred":float(pred[i]),
                                    "p_active":float(pa[i]) if np.isfinite(pa[i]) else np.nan})
    return pd.DataFrame(rec)

def generate_shared_oof(long,folds):
    rec=[]
    # Shared-by-horizon candidates.
    for h in HORIZONS:
        for T in folds[h]:
            ev=long[(long.horizon==h)&(long.base_season==T)]
            tr=long[(long.horizon==h)&(long.target_season<T)]
            if len(ev)==0 or len(tr)<MIN_TRAIN_ROWS: continue
            for fs,model in SHARED_SPECS:
                pred,pa=fit_predict(tr,ev,fs,model,"shared_horizon")
                for i,r in enumerate(ev.itertuples()):
                    rec.append({"row_id":r.row_id,"base_season":T,"horizon":h,"position":r.position,"player_id":r.player_id,
                                "actual":float(r.actual),"candidate":f"shared_horizon|{fs}|{model}","architecture":"shared_horizon",
                                "feature_set":fs,"model":model,"pred":float(pred[i]),
                                "p_active":float(pa[i]) if np.isfinite(pa[i]) else np.nan})
    # Position-continuous and global-continuous. Evaluate only rows belonging to each horizon's inner fold.
    valid={(h,T) for h in HORIZONS for T in folds[h]}
    all_T=sorted(set(T for _,T in valid))
    for T in all_T:
        eval_rows=long[(long.base_season==T)&long.apply(lambda r:(int(r.horizon),int(T)) in valid,axis=1)]
        train_all=long[long.target_season<T]
        for pos in POSITIONS:
            ev=eval_rows[eval_rows.position==pos]
            tr=train_all[train_all.position==pos]
            if len(ev)==0 or len(tr)<MIN_TRAIN_ROWS: continue
            for fs,model in SHARED_SPECS:
                pred,pa=fit_predict(tr,ev,fs,model,"position_continuous")
                for i,r in enumerate(ev.itertuples()):
                    rec.append({"row_id":r.row_id,"base_season":T,"horizon":int(r.horizon),"position":pos,"player_id":r.player_id,
                                "actual":float(r.actual),"candidate":f"position_continuous|{fs}|{model}","architecture":"position_continuous",
                                "feature_set":fs,"model":model,"pred":float(pred[i]),
                                "p_active":float(pa[i]) if np.isfinite(pa[i]) else np.nan})
        ev=eval_rows
        tr=train_all
        if len(ev) and len(tr)>=MIN_TRAIN_ROWS:
            for fs,model in SHARED_SPECS:
                pred,pa=fit_predict(tr,ev,fs,model,"global_continuous")
                for i,r in enumerate(ev.itertuples()):
                    rec.append({"row_id":r.row_id,"base_season":T,"horizon":int(r.horizon),"position":r.position,"player_id":r.player_id,
                                "actual":float(r.actual),"candidate":f"global_continuous|{fs}|{model}","architecture":"global_continuous",
                                "feature_set":fs,"model":model,"pred":float(pred[i]),
                                "p_active":float(pa[i]) if np.isfinite(pa[i]) else np.nan})
    return pd.DataFrame(rec)

def metrics_by_candidate(oof):
    rows=[]
    for (cand,h,pos),g in oof.groupby(["candidate","horizon","position"]):
        arch,fs,model=cand.split("|")
        rows.append({"candidate":cand,"architecture":arch,"feature_set":fs,"model":model,"horizon":h,"position":pos,**metric(g)})
    return pd.DataFrame(rows)

def baseline_metrics(oof):
    b=oof[oof.candidate=="specialist|forecast10|two_part_ridge"]
    out={}
    for (h,p),g in b.groupby(["horizon","position"]):
        out[(int(h),p)]=metric(g)
    return out

def score_candidates(mtab,base):
    z=mtab.copy()
    scores=[]
    for r in z.itertuples():
        b=base.get((int(r.horizon),str(r.position)))
        if not b:
            scores.append(np.nan); continue
        m={k:getattr(r,k) for k in ["rmse","mae","bias","spearman","tail_rmse"]}
        comp=candidate_complexity(r.architecture,r.feature_set,r.model)
        scores.append(composite(m,b,comp))
    z["cell_score"]=scores
    return z

def fold_stability(oof,base_candidate="specialist|forecast10|two_part_ridge"):
    rows=[]
    spec=oof[oof.architecture=="specialist"]
    for (h,pos),gcell in spec.groupby(["horizon","position"]):
        folds=sorted(gcell.base_season.unique())
        candidates=sorted(gcell.candidate.unique())
        for cand in candidates:
            beats=0; usable=0; margins=[]
            arch,fs,model=cand.split("|")
            for T in folds:
                gg=gcell[gcell.base_season==T]
                bg=gg[gg.candidate==base_candidate]
                cg=gg[gg.candidate==cand]
                if bg.empty or cg.empty: continue
                bm=metric(bg); cm=metric(cg)
                sc=composite(cm,bm,candidate_complexity(arch,fs,model))
                usable+=1; margins.append(sc)
                if sc < 0: beats+=1
            if usable:
                rows.append({"horizon":h,"position":pos,"candidate":cand,
                             "fold_wins":beats,"fold_count":usable,
                             "win_share":beats/usable,"mean_fold_score":float(np.mean(margins))})
    return pd.DataFrame(rows)

def select_specialist_route(scoretab,stability):
    route={}
    rows=[]
    for h in HORIZONS:
        for pos in POSITIONS:
            cell=scoretab[(scoretab.horizon==h)&(scoretab.position==pos)&(scoretab.architecture=="specialist")].copy()
            cell=cell.sort_values(["cell_score","candidate"])
            baseline=cell[cell.candidate=="specialist|forecast10|two_part_ridge"]
            if baseline.empty: continue
            bscore=float(baseline.iloc[0].cell_score)
            best=cell.iloc[0]
            stab=stability[(stability.horizon==h)&(stability.position==pos)&(stability.candidate==best.candidate)]
            winshare=float(stab.iloc[0].win_share) if len(stab) else 0.0
            use=best
            reason="development_best"
            if (bscore-float(best.cell_score))<MIN_MATERIAL_IMPROVEMENT or winshare<0.50:
                use=baseline.iloc[0]; reason="shrink_to_baseline_for_materiality_or_stability"
            route[(pos,h)]=str(use.candidate)
            rows.append({"position":pos,"horizon":h,"candidate":str(use.candidate),"reason":reason,
                         "development_cell_score":float(use.cell_score),"fold_win_share":winshare})
    return route,pd.DataFrame(rows)

def architecture_prediction(oof,route,architecture_candidate=None):
    parts=[]
    if route is not None:
        for (pos,h),cand in route.items():
            parts.append(oof[(oof.position==pos)&(oof.horizon==h)&(oof.candidate==cand)])
        return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    return oof[oof.candidate==architecture_candidate].copy()

def arch_score(pred,base_pred,complexity):
    # Aggregate cell-normalized composite to avoid large positions dominating.
    vals=[]
    for (h,pos),g in pred.groupby(["horizon","position"]):
        b=base_pred[(base_pred.horizon==h)&(base_pred.position==pos)]
        if b.empty: continue
        vals.append(composite(metric(g),metric(b),0.0))
    return float(np.mean(vals))+complexity if vals else 999.0

def choose_fixed_architecture(oof,arch_name,base_pred):
    cands=sorted(oof.loc[oof.architecture==arch_name,"candidate"].unique())
    rows=[]
    for cand in cands:
        p=oof[oof.candidate==cand]
        arch,fs,model=cand.split("|")
        sc=arch_score(p,base_pred,candidate_complexity(arch,fs,model))
        rows.append({"architecture":arch_name,"candidate":cand,"development_arch_score":sc})
    tab=pd.DataFrame(rows).sort_values(["development_arch_score","candidate"])
    if tab.empty: return None,tab
    best=tab.iloc[0]
    # Require material improvement over the incumbent baseline aggregate.
    if float(best.development_arch_score)>-MIN_MATERIAL_IMPROVEMENT:
        return None,tab
    return str(best.candidate),tab

def blend_predictions(a,b,w):
    z=a[["row_id","base_season","horizon","position","player_id","actual","pred"]].merge(
        b[["row_id","pred"]],on="row_id",suffixes=("_a","_b")
    )
    z["pred"]=w*z.pred_a+(1-w)*z.pred_b
    z["candidate"]=f"blend|{w:.2f}"
    z["p_active"]=np.nan
    return z

def feature_ablation(scoretab):
    z=scoretab[scoretab.architecture=="specialist"].copy()
    rows=[]
    for fs,g in z.groupby("feature_set"):
        rows.append({"feature_set":fs,"best_mean_cell_score":float(g.groupby("candidate").cell_score.mean().min()),
                     "best_candidate":str(g.groupby("candidate").cell_score.mean().idxmin())})
    return pd.DataFrame(rows).sort_values("best_mean_cell_score")

def provenance_matrix(base):
    groups=[
        ("governed_y1_y3_forecast","Y1-Y3 PIT Forecast mean/uncertainty",2005,2022,"preseason artifact; base-season PIT","none if exact fold used"),
        ("pedigree_static","draft/rookie/birth/height/weight/conference",1999,2025,"static known after draft/entry","missing draft means undrafted/unknown; conference sparse"),
        ("lagged_football","games/usage/efficiency/team continuity",1999,2025,"strict lag 1-3 seasons only","same-season team/role prohibited"),
        ("durability_workload","games and opportunity history",1999,2025,"strict lagged football","injury event detail unavailable"),
        ("trajectory_residual","governed residual/innovation state artifacts",2005,2022,"forecast_fold keyed PIT state","history sparse in early folds"),
    ]
    return pd.DataFrame(groups,columns=["feature_family","contents","source_start","source_end","pit_rule","known_gap"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--raw-seasons",required=True)
    ap.add_argument("--players",required=True)
    ap.add_argument("--residual-states",required=True)
    ap.add_argument("--innovation-states",required=True)
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)

    m=pd.read_csv(args.model_a_rows)
    qb=json.loads(Path(args.qb_results).read_text())
    raw=prep_raw(pd.read_csv(args.raw_seasons))
    players=pd.read_csv(args.players)
    residual=pd.read_csv(args.residual_states)
    innovation=pd.read_csv(args.innovation_states)

    m=add_qb_governed_path(m,qb)
    base=build_forecast_base(m)
    base=merge_lags(base,raw)
    base=add_engineered_features(base,players)
    base=merge_trajectory(base,residual,innovation)
    long=build_long(base,raw)

    holds=final_holdouts(long)
    folds=inner_folds(long,holds)

    # Do not generate or inspect final-holdout predictions in this workflow.
    final_ids=set()
    for h,seasons in holds.items():
        final_ids.update(long[(long.horizon==h)&(long.base_season.isin(seasons))].row_id)
    dev_long=long[~long.row_id.isin(final_ids)].copy()

    specialist=generate_specialist_oof(dev_long,folds)
    shared=generate_shared_oof(dev_long,folds)
    oof=pd.concat([specialist,shared],ignore_index=True)

    mtab=metrics_by_candidate(oof)
    base_metrics=baseline_metrics(oof)
    scoretab=score_candidates(mtab,base_metrics)
    stability=fold_stability(oof)
    route,route_tab=select_specialist_route(scoretab,stability)

    base_pred=oof[oof.candidate=="specialist|forecast10|two_part_ridge"].copy()
    route_pred=architecture_prediction(oof,route)
    route_score=arch_score(route_pred,base_pred,ARCH_COMPLEXITY["specialist"])

    arch_rows=[
        {"architecture":"incumbent_baseline","candidate":"specialist|forecast10|two_part_ridge","development_arch_score":0.0},
        {"architecture":"specialist_route","candidate":"cell_specific","development_arch_score":route_score},
    ]
    fixed={}
    for arch_name in ("shared_horizon","position_continuous","global_continuous"):
        cand,tab=choose_fixed_architecture(oof,arch_name,base_pred)
        fixed[arch_name]=cand
        if len(tab) and cand:
            arch_rows.append({"architecture":arch_name,"candidate":str(cand),
                              "development_arch_score":float(tab.iloc[0].development_arch_score)})

    # Hierarchical/ensemble blend between specialist route and best valid shared architecture.
    blend_options=[]
    valid_fixed=[(a,c) for a,c in fixed.items() if c]
    if valid_fixed:
        a,c=min(valid_fixed,key=lambda ac: arch_score(oof[oof.candidate==ac[1]],base_pred,candidate_complexity(*ac[1].split("|"))))
        shared_pred=oof[oof.candidate==c]
        for w in (0.25,0.50,0.75):
            bp=blend_predictions(route_pred,shared_pred,w)
            sc=arch_score(bp,base_pred,ARCH_COMPLEXITY["hierarchical_blend"])
            blend_options.append((sc,w,a,c))
            arch_rows.append({"architecture":"hierarchical_blend","candidate":f"{w:.2f} specialist + {1-w:.2f} {c}",
                              "development_arch_score":sc})

    arch_tab=pd.DataFrame(arch_rows).sort_values(["development_arch_score","architecture","candidate"])
    selected=arch_tab.iloc[0]
    selected_arch=str(selected.architecture)
    selected_score=float(selected.development_arch_score)
    selected_spec={}
    if selected_arch=="specialist_route":
        selected_spec={"type":"specialist_route","route":{f"{p}|Y{h}":c for (p,h),c in route.items()}}
    elif selected_arch=="incumbent_baseline":
        selected_spec={"type":"fixed","candidate":"specialist|forecast10|two_part_ridge"}
    elif selected_arch in fixed:
        selected_spec={"type":"fixed","candidate":fixed[selected_arch]}
    elif selected_arch=="hierarchical_blend":
        best=min(blend_options)
        selected_spec={"type":"hierarchical_blend","specialist_weight":best[1],"shared_architecture":best[2],
                       "shared_candidate":best[3],"route":{f"{p}|Y{h}":c for (p,h),c in route.items()}}
    else:
        raise RuntimeError(selected_arch)

    # Predeclare untouched-holdout confirmation / fallback before the final holdout is run.
    freeze={
        "state":"DEVELOPMENT_SELECTION_FROZEN_BEFORE_UNTOUCHED_FINAL_HOLDOUT",
        "authority":"research_only_no_production_change",
        "historical_base_seasons":[int(base.base_season.min()),int(base.base_season.max())],
        "horizons":HORIZONS,
        "final_holdout_by_horizon":{str(h):[int(x) for x in holds[h]] for h in HORIZONS},
        "inner_validation_folds":{str(h):[int(x) for x in folds[h]] for h in HORIZONS},
        "selected_architecture":selected_spec,
        "selected_development_score":selected_score,
        "fallback_if_final_rejected":{"type":"fixed","candidate":"specialist|forecast10|two_part_ridge"},
        "final_confirmation_rules":{
            "aggregate_rmse_max_ratio_vs_fallback":1.02,
            "aggregate_tail_rmse_max_ratio_vs_fallback":1.05,
            "cell_catastrophic_rmse_ratio":1.15,
            "cell_catastrophic_tail_rmse_ratio":1.20,
            "must_win_at_least_two_of":["rmse","mae","tail_rmse","spearman"],
            "no_candidate_redefinition_after_holdout":True,
        },
        "selection_principles":{
            "current_players_inspected":False,
            "final_holdout_predictions_generated":False,
            "market_owner_team_utility_inputs":False,
            "production_h3_changed":False,
        },
    }

    provenance_matrix(base).to_csv(OUT/"PIT_FEATURE_PROVENANCE.csv",index=False)
    pd.DataFrame([{"feature_set":k,"features":";".join(v),"n_features":len(v)} for k,v in FEATURE_SETS.items()]).to_csv(OUT/"FEATURE_SET_MATRIX.csv",index=False)
    feature_ablation(scoretab).to_csv(OUT/"FEATURE_GROUP_DEVELOPMENT_ABLATIONS.csv",index=False)
    scoretab.to_csv(OUT/"DEVELOPMENT_MODEL_MATRIX.csv",index=False)
    stability.to_csv(OUT/"DEVELOPMENT_FOLD_STABILITY.csv",index=False)
    route_tab.to_csv(OUT/"DEVELOPMENT_SPECIALIST_ROUTE.csv",index=False)
    arch_tab.to_csv(OUT/"DEVELOPMENT_ARCHITECTURE_COMPARISON.csv",index=False)
    (OUT/"FROZEN_ARCHITECTURE_CANDIDATE.json").write_text(json.dumps(freeze,indent=2,sort_keys=True),encoding="utf-8")

    gaps=[
        "# Comprehensive Long-Horizon Data Gaps",
        "",
        "- Historical contract guarantees, restructures and years-remaining are not used because no governed PIT source is presently established.",
        "- Historical injury-event/designation detail is not used; games played and workload history are the governed availability proxies.",
        "- Historical depth-chart/starter labels are not used unless represented indirectly by lagged usage; no hindsight starter label enters.",
        "- Athletic testing/combine metrics are not used because the governed source inventory contains height/weight but not a complete testing panel.",
        "- College/conference is available; high-cardinality school identity is retained as provenance but not promoted as a default predictive feature.",
        "- Current Market, dynasty rankings, Owner Intelligence, Team Utility and trade behavior are prohibited inputs.",
        "",
        "Negative findings from richer feature sets remain valid evidence and do not trigger data invention."
    ]
    (OUT/"DATA_GAPS.md").write_text("\n".join(gaps)+"\n",encoding="utf-8")
    report=[
        "# Comprehensive Y4-Y8 Development Selection",
        "",
        "Status: DEVELOPMENT SELECTION FROZEN BEFORE UNTOUCHED FINAL HOLDOUT.",
        "",
        f"Selected architecture: {selected_arch}",
        f"Development architecture score versus incumbent baseline: {selected_score:.6f}",
        "",
        "Final holdout has not been scored in this workflow and current named-player shadows have not been generated.",
        "",
        "The next authorized step is to persist this freeze, then run the separate final-holdout workflow without changing candidates."
    ]
    (OUT/"DEVELOPMENT_SELECTION.md").write_text("\n".join(report)+"\n",encoding="utf-8")

    print((OUT/"DEVELOPMENT_SELECTION.md").read_text())
    print("FREEZE_JSON_BEGIN")
    print(json.dumps(freeze,sort_keys=True))
    print("FREEZE_JSON_END")

if __name__=="__main__":
    main()

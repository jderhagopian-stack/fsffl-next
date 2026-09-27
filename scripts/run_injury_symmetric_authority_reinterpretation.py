from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np, pandas as pd

SEED=20260927
ENDPOINTS=(1,2,3,4)

def regular_weeks(season):
    return 17 if int(season)<=2020 else 18

def map_episode_identity(episodes):
    x=episodes.copy().reset_index(drop=True)
    x["episode_id"]=np.arange(len(x),dtype=int)
    x["player_id"]=x.player_id.astype(str)
    x["season"]=pd.to_numeric(x.season,errors="coerce").astype(int)
    x["event_week"]=pd.to_numeric(x.event_week,errors="coerce").astype(int)
    x["weeks_remaining"]=[max(0,regular_weeks(s)-w) for s,w in zip(x.season,x.event_week)]
    return x[["episode_id","player_id","season","event_week","weeks_remaining"]]

def row_return_scores(df,name):
    out=[]
    for r in df.itertuples(index=False):
        bs=[]; ll=[]; ps=[]; ys=[]
        for k in ENDPOINTS:
            if int(r.weeks_remaining)<k:continue
            p=float(getattr(r,f"{name}_p_return_by_{k}"))
            y=int(pd.notna(r.games_to_return) and float(r.games_to_return)<=k)
            p=min(1-1e-9,max(1e-9,p))
            bs.append((p-y)**2); ll.append(-(y*math.log(p)+(1-y)*math.log(1-p)));ps.append(p);ys.append(y)
        p=float(getattr(r,f"{name}_p_return_any")); y=int(pd.notna(r.games_to_return))
        p=min(1-1e-9,max(1e-9,p))
        bs.append((p-y)**2);ll.append(-(y*math.log(p)+(1-y)*math.log(1-p)));ps.append(p);ys.append(y)
        out.append((np.mean(bs),np.mean(ll),float(getattr(r,f"{name}_ibs")),np.mean(ps),np.mean(ys)))
    return np.asarray(out,float)

def weighted_calibration(df,name,w):
    gaps=[]
    for k in ENDPOINTS:
        q=df.weeks_remaining>=k
        if not q.any():continue
        ww=w[q.to_numpy()]
        p=df.loc[q,f"{name}_p_return_by_{k}"].to_numpy(float)
        y=(df.loc[q,"games_to_return"].notna()&(df.loc[q,"games_to_return"]<=k)).astype(float).to_numpy()
        gaps.append(abs(np.sum(ww*(p-y))/np.sum(ww)))
    p=df[f"{name}_p_return_any"].to_numpy(float)
    y=df.games_to_return.notna().astype(float).to_numpy()
    gaps.append(abs(np.sum(w*(p-y))/np.sum(w)))
    return float(np.mean(gaps))

def two_way_weights(df,rng):
    sy=pd.Categorical(df.season).codes; pl=pd.Categorical(df.player_id).codes
    ws=rng.exponential(1,int(sy.max()+1)); wp=rng.exponential(1,int(pl.max()+1))
    return ws[sy]*wp[pl]

def bootstrap_return(df,a,b,reps=5000):
    sa=row_return_scores(df,a); sb=row_return_scores(df,b)
    # Positive = A lower/better than B.
    base={
        "endpoint_brier_gain_a_over_b":float(np.mean(sb[:,0]-sa[:,0])),
        "logloss_gain_a_over_b":float(np.mean(sb[:,1]-sa[:,1])),
        "integrated_brier_gain_a_over_b":float(np.mean(sb[:,2]-sa[:,2])),
        "calibration_gain_a_over_b":float(weighted_calibration(df,b,np.ones(len(df)))-weighted_calibration(df,a,np.ones(len(df)))),
    }
    rng=np.random.default_rng(SEED+sum(map(ord,a+b)))
    vals={k:[] for k in base}
    for _ in range(reps):
        w=two_way_weights(df,rng); sw=w.sum()
        vals["endpoint_brier_gain_a_over_b"].append(float(np.sum(w*(sb[:,0]-sa[:,0]))/sw))
        vals["logloss_gain_a_over_b"].append(float(np.sum(w*(sb[:,1]-sa[:,1]))/sw))
        vals["integrated_brier_gain_a_over_b"].append(float(np.sum(w*(sb[:,2]-sa[:,2]))/sw))
        vals["calibration_gain_a_over_b"].append(weighted_calibration(df,b,w)-weighted_calibration(df,a,w))
    return {k:{"gain":v,"ci95":[float(np.quantile(vals[k],.025)),float(np.quantile(vals[k],.975))],"reps":reps} for k,v in base.items()}

def availability_scores(df,name):
    p=df[f"{name}_pred"].to_numpy(float); y=df.availability_target.to_numpy(float)
    wr=df.weeks_remaining.to_numpy(float)
    return {
        "mae":float(np.mean(np.abs(p-y))),
        "rmse":float(np.sqrt(np.mean((p-y)**2))),
        "bias":float(np.mean(p-y)),
        "active_weeks_mae":float(np.mean(np.abs((p-y)*wr))),
        "expected_active_weeks_mean":float(np.mean(p*wr)),
        "actual_active_weeks_mean":float(np.mean(y*wr)),
    }

def bootstrap_availability(df,a,b,reps=5000):
    pa=df[f"{a}_pred"].to_numpy(float);pb=df[f"{b}_pred"].to_numpy(float);y=df.availability_target.to_numpy(float);wr=df.weeks_remaining.to_numpy(float)
    diffs={
        "mae_gain_a_over_b":np.abs(pb-y)-np.abs(pa-y),
        "sq_error_gain_a_over_b":(pb-y)**2-(pa-y)**2,
        "active_weeks_mae_gain_a_over_b":np.abs((pb-y)*wr)-np.abs((pa-y)*wr),
        "expected_active_weeks_a_minus_b":(pa-pb)*wr,
    }
    rng=np.random.default_rng(SEED+999+sum(map(ord,a+b))); vals={k:[] for k in diffs}
    for _ in range(reps):
        w=two_way_weights(df,rng); sw=w.sum()
        for k,d in diffs.items():vals[k].append(float(np.sum(w*d)/sw))
    return {k:{"value":float(v.mean()),"ci95":[float(np.quantile(vals[k],.025)),float(np.quantile(vals[k],.975))],"reps":reps} for k,v in diffs.items()}

def fold_direction(df,a,b,metric):
    wins=0;rows=[]
    for y,g in df.groupby("season"):
        aa=row_return_scores(g,a);bb=row_return_scores(g,b)
        idx={"endpoint_brier":0,"logloss":1,"integrated_brier":2}[metric]
        gain=float(np.mean(bb[:,idx]-aa[:,idx]))
        wins+=gain>0;rows.append({"season":int(y),"gain_a_over_b":gain})
    return {"a_wins":int(wins),"total":len(rows),"folds":rows}

def position_return(df,a,b):
    rows=[]
    for pos,g in df.groupby("position"):
        aa=row_return_scores(g,a);bb=row_return_scores(g,b)
        rows.append({
            "position":pos,"n":len(g),
            "endpoint_brier_gain_a_over_b":float(np.mean(bb[:,0]-aa[:,0])),
            "integrated_brier_gain_a_over_b":float(np.mean(bb[:,2]-aa[:,2])),
            "logloss_gain_a_over_b":float(np.mean(bb[:,1]-aa[:,1])),
        })
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--artifact-dir",type=Path,required=True)
    ap.add_argument("--episodes",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    ttr=pd.read_csv(next(args.artifact_dir.rglob("JOINT_INJURY_RETURN_OOT_PREDICTIONS.csv")))
    av=pd.read_csv(next(args.artifact_dir.rglob("JOINT_INJURY_AVAILABILITY_OOT_PREDICTIONS.csv")))
    episodes=pd.read_csv(args.episodes)
    ident=map_episode_identity(episodes)
    if len(ident)!=4793:raise RuntimeError(f"episode identity mismatch {len(ident)}")
    ttr=ttr.merge(ident,on=["episode_id","season"],how="left",validate="one_to_one",suffixes=("","_src"))
    av=av.merge(ident,on=["episode_id","season"],how="left",validate="one_to_one",suffixes=("","_src"))
    if ttr.player_id.isna().any() or av.player_id.isna().any():raise RuntimeError("episode identity join failed")
    if "weeks_remaining_x" in ttr.columns:
        ttr["weeks_remaining"]=ttr["weeks_remaining_x"]
    elif "weeks_remaining" not in ttr.columns:
        ttr["weeks_remaining"]=ttr["weeks_remaining_src"]

    ret_models=["severity","histgb","joint"]
    av_models=["severity","histgb","joint"]
    ret_summary=[]
    for m in ret_models:
        z=row_return_scores(ttr,m)
        ret_summary.append({
            "model":m,"n":len(ttr),
            "endpoint_brier":float(z[:,0].mean()),"logloss":float(z[:,1].mean()),
            "integrated_brier":float(z[:,2].mean()),
            "calibration_error":weighted_calibration(ttr,m,np.ones(len(ttr))),
        })
    av_summary=[{"model":m,"n":len(av),**availability_scores(av,m)} for m in av_models]

    pairs={}
    for a,b in (("joint","histgb"),("joint","severity"),("histgb","severity")):
        pairs[f"{a}_vs_{b}"]=bootstrap_return(ttr,a,b)
    avpairs={}
    for a,b in (("joint","histgb"),("joint","severity"),("histgb","severity")):
        avpairs[f"{a}_vs_{b}"]=bootstrap_availability(av,a,b)

    jh=bootstrap_return(ttr,"joint","histgb")
    signs=[jh["endpoint_brier_gain_a_over_b"]["gain"],jh["integrated_brier_gain_a_over_b"]["gain"],jh["logloss_gain_a_over_b"]["gain"],jh["calibration_gain_a_over_b"]["gain"]]
    if all(x>0 for x in signs): disposition="joint_supported_difference"
    elif all(x<0 for x in signs): disposition="separate_supported_difference"
    else: disposition="tradeoff_no_single_return_time_authority"

    exact_av=float(np.max(np.abs(av.joint_pred.to_numpy(float)-av.histgb_pred.to_numpy(float))))<=1e-12
    result={
        "study":"symmetric-injury-joint-vs-separate-reinterpretation",
        "authority":"research_only_no_production_change",
        "return_summary":ret_summary,
        "availability_summary":av_summary,
        "return_pairwise":pairs,
        "availability_pairwise":avpairs,
        "joint_vs_separate_holdout_direction":{
            "endpoint_brier":fold_direction(ttr,"joint","histgb","endpoint_brier"),
            "integrated_brier":fold_direction(ttr,"joint","histgb","integrated_brier"),
            "logloss":fold_direction(ttr,"joint","histgb","logloss"),
        },
        "joint_vs_separate_position":position_return(ttr,"joint","histgb"),
        "joint_availability_exact_match":exact_av,
        "joint_vs_separate_disposition":disposition,
        "downstream_h1_availability_interpretation":(
            "exact_tie_expected_active_weeks" if exact_av else "see_active_weeks_pairwise"
        ),
        "old_replacement_margin_used_for_authority":False,
        "guards":{
            "models_refit":False,"thresholds_changed":False,"production_h3_changed":False,
            "intrinsic_changed":False,"healthy_production_changed":False,"provider_ros_authority_changed":False,
        },
    }
    pd.DataFrame(ret_summary).to_csv(args.output_dir/"INJURY_RETURN_SYMMETRIC_SUMMARY.csv",index=False)
    pd.DataFrame(av_summary).to_csv(args.output_dir/"INJURY_AVAILABILITY_SYMMETRIC_SUMMARY.csv",index=False)
    pd.DataFrame(result["joint_vs_separate_position"]).to_csv(args.output_dir/"INJURY_JOINT_VS_SEPARATE_POSITION.csv",index=False)
    (args.output_dir/"INJURY_SYMMETRIC_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

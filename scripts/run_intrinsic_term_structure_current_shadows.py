from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("artifacts/research/intrinsic_term_structure_20260926")
BOARD_DEFAULT = Path(
    "artifacts/implementation/final_forecast_route_implementation_20260920/"
    "FINAL_STANDARD_COORDINATE_BOARD_335.csv"
)
REFERENCE_DEFAULT = OUT / "CURRENT_PRODUCTION_H3_REFERENCE.json"
DISCOUNT = 0.85
CURRENT_SEASON = 2026
SELECTED_MODEL = "two_part_state"
HORIZONS = tuple(range(4, 9))
VALUE_HORIZONS = (1, 3, 5, 8)
PRODUCTION_SHAPLEY_PERMUTATIONS = 2048
PRODUCTION_SHAPLEY_SEED = 20260915


def load_module(path: str):
    spec = importlib.util.spec_from_file_location("term_history", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load frozen historical research module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gini(values: pd.Series) -> float:
    x=np.asarray(values.fillna(0),dtype=float)
    x=np.clip(x,0,None)
    if len(x)==0 or float(x.sum())<=0:
        return 0.0
    x=np.sort(x)
    n=len(x)
    return float((2*np.sum((np.arange(1,n+1))*x)/(n*x.sum()))-(n+1)/n)


def top_fraction_share(values: pd.Series, frac: float=0.10) -> float:
    x=np.sort(np.clip(np.asarray(values.fillna(0),dtype=float),0,None))[::-1]
    if len(x)==0 or x.sum()<=0:
        return 0.0
    k=max(1,int(math.ceil(len(x)*frac)))
    return float(x[:k].sum()/x.sum())


def build_current_features(board: pd.DataFrame, player: pd.DataFrame) -> pd.DataFrame:
    current=board[board["position"].isin(("QB","RB","WR","TE"))].copy()
    current["season"]=CURRENT_SEASON

    prior=player[player["season"]==CURRENT_SEASON-1][
        ["player_id","position","fantasy_points","prior_production_percentile"]
    ].copy()
    prior=prior.rename(columns={
        "player_id":"historical_gsis_id",
        "fantasy_points":"prior_points",
        "prior_production_percentile":"prior_pct",
    })
    current=current.merge(prior,on=["historical_gsis_id","position"],how="left")

    current["y1"]=pd.to_numeric(current["standard_y1_points"],errors="coerce").fillna(0).clip(lower=0)
    current["y2"]=pd.to_numeric(current["y2_standard_expected_points"],errors="coerce").fillna(0).clip(lower=0)
    current["y3"]=pd.to_numeric(current["y3_standard_expected_points"],errors="coerce").fillna(0).clip(lower=0)
    current["age"]=pd.to_numeric(current["age"],errors="coerce")
    current["experience"]=pd.to_numeric(current["experience"],errors="coerce")
    current["log_prior_points"]=np.log1p(pd.to_numeric(current["prior_points"],errors="coerce").clip(lower=0))
    current["log_y1"]=np.log1p(current["y1"])
    current["y1_pct"]=current.groupby("position")["y1"].rank(pct=True,method="average")
    denom=current["y1"].abs().clip(lower=25.0)
    current["y2_ratio"]=(current["y2"]/current["y1"].replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    current["y3_ratio"]=(current["y3"]/current["y1"].replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    current["y2_delta"]=((current["y2"]-current["y1"])/denom).clip(-3,3)
    current["y3_delta"]=((current["y3"]-current["y1"])/denom).clip(-3,3)
    current["scoring_multiplier"]=pd.to_numeric(current["player_specific_scoring_multiplier"],errors="coerce").fillna(1.0)
    return current


def historical_training_for_horizon(hist, base: pd.DataFrame, player: pd.DataFrame, horizon: int) -> pd.DataFrame:
    pm=hist.points_map(player)
    allh=base.copy()
    allh["target"]=allh["season"]+horizon-1
    allh["actual"]=[
        max(0.0,pm.get((pid,int(ts)),0.0))
        for pid,ts in zip(allh.player_id,allh.target)
    ]
    return allh[(allh["season"]<CURRENT_SEASON)&(allh["target"]<CURRENT_SEASON)].copy()


def current_long_forecasts(hist, base: pd.DataFrame, player: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    out=current.copy()
    for h in HORIZONS:
        train=historical_training_for_horizon(hist,base,player,h)
        out[f"y{h}"]=0.0
        out[f"y{h}_positive_probability"]=np.nan
        out[f"y{h}_conditional_positive_points"]=np.nan
        for pos in ("QB","RB","WR","TE"):
            mask=out["position"]==pos
            if not mask.any():
                continue
            model=hist.fit_position_models(train,pos)
            ev=out.loc[mask]
            if "scaler" not in model:
                pred=np.repeat(max(0.0,float(model["fallback"])),len(ev))
                ps=np.repeat(np.nan,len(ev))
                cp=np.repeat(np.nan,len(ev))
            else:
                X,_=hist.prep_matrix(ev,model["med"])
                Z=model["scaler"].transform(X)
                if model["logit"] is None:
                    ps=np.repeat(float(model["surv_mean"]),len(ev))
                else:
                    ps=model["logit"].predict_proba(Z)[:,1]
                if model["ridge_pos"] is None:
                    cp=np.repeat(float(model["positive_mean"]),len(ev))
                else:
                    cp=np.expm1(model["ridge_pos"].predict(Z)).clip(0,600)
                pred=(ps*cp).clip(0,600)
            out.loc[mask,f"y{h}"]=pred
            out.loc[mask,f"y{h}_positive_probability"]=ps
            out.loc[mask,f"y{h}_conditional_positive_points"]=cp
    return out


def annual_shapley(hist, current: pd.DataFrame) -> dict[int,dict[str,float]]:
    old_perm=hist.SHAPLEY_PERMUTATIONS
    try:
        hist.SHAPLEY_PERMUTATIONS=PRODUCTION_SHAPLEY_PERMUTATIONS
        result={}
        for h in range(1,9):
            rows=[
                (
                    str(r.player_id),
                    str(r.position),
                    max(0.0,float(getattr(r,f"y{h}"))*float(r.scoring_multiplier)),
                )
                for r in current.itertuples()
            ]
            result[h]=hist.shapley(rows,PRODUCTION_SHAPLEY_SEED+h-1)
        return result
    finally:
        hist.SHAPLEY_PERMUTATIONS=old_perm


def cumulative_values(phi: dict[int,dict[str,float]], horizon: int) -> dict[str,float]:
    ids=sorted(phi[1])
    return {
        pid:sum((DISCOUNT**(h-1))*float(phi[h].get(pid,0.0)) for h in range(1,horizon+1))
        for pid in ids
    }


def add_value_columns(current: pd.DataFrame, phi: dict[int,dict[str,float]]) -> pd.DataFrame:
    out=current.copy()
    for h in range(1,9):
        out[f"y{h}_shapley"]=out["player_id"].map(phi[h]).fillna(0.0)
    for H in VALUE_HORIZONS:
        vals=cumulative_values(phi,H)
        out[f"h{H}_value"]=out["player_id"].map(vals).fillna(0.0)
        out[f"h{H}_rank"]=out[f"h{H}_value"].rank(method="min",ascending=False)
    out["h3_to_h5_rank_delta"]=out["h3_rank"]-out["h5_rank"]
    out["h3_to_h8_rank_delta"]=out["h3_rank"]-out["h8_rank"]
    out["h5_increment"]=out["h5_value"]-out["h3_value"]
    out["h8_increment"]=out["h8_value"]-out["h3_value"]
    return out


def attach_production_reference(current: pd.DataFrame, path: Path) -> tuple[pd.DataFrame,dict[str,object]]:
    payload=json.loads(path.read_text())
    ref={k:float(v) for k,v in payload["values"].items()}
    out=current.copy()
    out["production_h3_value"]=out["player_id"].map(ref)
    out["production_h3_rank"]=out["production_h3_value"].rank(method="min",ascending=False)
    matched=out.dropna(subset=["production_h3_value"]).copy()
    corr=float(matched["h3_value"].corr(matched["production_h3_value"],method="spearman"))
    mae=float(np.mean(np.abs(matched["h3_value"]-matched["production_h3_value"])))
    rank_mae=float(np.mean(np.abs(matched["h3_rank"]-matched["production_h3_rank"])))
    return out,{
        "artifact_id":payload["artifact_id"],
        "computed_at":payload["computed_at"],
        "matched_players":int(len(matched)),
        "spearman_shadow_h3_vs_production":corr,
        "mean_absolute_raw_value_gap":mae,
        "mean_absolute_rank_gap":rank_mae,
        "note":"Production H3 remains authority; current research H3 is a comparability shadow only.",
    }


def load_uncertainty(path: Path) -> pd.DataFrame:
    u=pd.read_csv(path)
    return u[(u["horizon"].between(4,8))&(u["position"].isin(("QB","RB","WR","TE")))].copy()


def uncertainty_interpretation(current: pd.DataFrame, u: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for h in HORIZONS:
        for pos in ("QB","RB","WR","TE"):
            uu=u[(u["horizon"]==h)&(u["position"]==pos)]
            if uu.empty:
                continue
            floor=float(uu.iloc[0]["monotone_uncertainty_floor"])
            x=current[current["position"]==pos][f"y{h}"].clip(lower=0)
            positive=x[x>0]
            mean=float(x.mean()) if len(x) else 0.0
            median_positive=float(positive.median()) if len(positive) else 0.0
            rows.append({
                "horizon":h,
                "position":pos,
                "oot_residual_rmse":float(uu.iloc[0]["oot_residual_rmse"]),
                "monotone_uncertainty_floor":floor,
                "current_mean_expected_points":mean,
                "current_median_positive_expected_points":median_positive,
                "uncertainty_floor_to_mean_ratio":floor/mean if mean>0 else None,
                "uncertainty_floor_to_median_positive_ratio":floor/median_positive if median_positive>0 else None,
            })
    return pd.DataFrame(rows)


def current_position_distributions(current: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    total_n=len(current)
    for H in VALUE_HORIZONS:
        value_col=f"h{H}_value"
        rank_col=f"h{H}_rank"
        top_counts={
            25:int((current[rank_col]<=25).sum()),
            50:int((current[rank_col]<=50).sum()),
            100:int((current[rank_col]<=100).sum()),
        }
        for pos in ("QB","RB","WR","TE"):
            x=current[current["position"]==pos]
            vals=x[value_col]
            rows.append({
                "horizon":H,
                "position":pos,
                "n":int(len(x)),
                "population_share":len(x)/total_n if total_n else 0.0,
                "value_share":float(vals.sum()/current[value_col].sum()) if current[value_col].sum()>0 else 0.0,
                "median":float(vals.median()) if len(vals) else 0.0,
                "p90":float(vals.quantile(.90)) if len(vals) else 0.0,
                "p95":float(vals.quantile(.95)) if len(vals) else 0.0,
                "iqr":float(vals.quantile(.75)-vals.quantile(.25)) if len(vals) else 0.0,
                "gini":gini(vals),
                "top10pct_within_position_value_share":top_fraction_share(vals,.10),
                "top25_share":float((x[rank_col]<=25).sum()/max(1,top_counts[25])),
                "top50_share":float((x[rank_col]<=50).sum()/max(1,top_counts[50])),
                "top100_share":float((x[rank_col]<=100).sum()/max(1,top_counts[100])),
            })
    return pd.DataFrame(rows)


def age_effects(current: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for pos in ("QB","RB","WR","TE"):
        for band,g in current[current["position"]==pos].groupby("age_band",dropna=False):
            if not len(g):
                continue
            rows.append({
                "position":pos,
                "age_band":str(band),
                "n":int(len(g)),
                "median_age":float(g["age"].median()) if g["age"].notna().any() else None,
                "median_h1_value":float(g["h1_value"].median()),
                "median_h3_value":float(g["h3_value"].median()),
                "median_h5_value":float(g["h5_value"].median()),
                "median_h8_value":float(g["h8_value"].median()),
                "mean_h3_to_h5_rank_delta":float(g["h3_to_h5_rank_delta"].mean()),
                "mean_h3_to_h8_rank_delta":float(g["h3_to_h8_rank_delta"].mean()),
                "median_h5_increment":float(g["h5_increment"].median()),
                "median_h8_increment":float(g["h8_increment"].median()),
            })
    return pd.DataFrame(rows)


def crossovers(current: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for target in (5,8):
        delta=f"h3_to_h{target}_rank_delta"
        cols=[
            "player_id","player_name","position","age","age_band",
            "production_h3_value","production_h3_rank",
            "h1_value","h3_value",f"h{target}_value",
            "h3_rank",f"h{target}_rank",delta,
        ]
        x=current.reindex(current[delta].abs().sort_values(ascending=False).index).head(50)
        for _,r in x[cols].iterrows():
            d=r.to_dict()
            d["target_horizon"]=target
            d["direction"]="riser" if float(d[delta])>0 else "faller" if float(d[delta])<0 else "unchanged"
            rows.append(d)
    return pd.DataFrame(rows)


def representatives(current: pd.DataFrame) -> pd.DataFrame:
    chosen=[]
    seen=set()
    for delta in ("h3_to_h5_rank_delta","h3_to_h8_rank_delta"):
        for ascending in (False,True):
            x=current.sort_values(delta,ascending=ascending)
            for _,r in x.iterrows():
                pid=str(r["player_id"])
                if pid in seen:
                    continue
                chosen.append(r)
                seen.add(pid)
                if len(chosen)%3==0:
                    break
    for _,r in current.sort_values("production_h3_rank").head(5).iterrows():
        pid=str(r["player_id"])
        if pid not in seen:
            chosen.append(r);seen.add(pid)
        if len(chosen)>=10:
            break
    rows=[]
    for r in chosen[:10]:
        rows.append({
            "player_id":r["player_id"],"player_name":r["player_name"],"position":r["position"],
            "age":r["age"],"selection_basis":"deterministic_post_selection_rank_movement_or_top_h3",
            "h1_value":r["h1_value"],"h3_value":r["h3_value"],"h5_value":r["h5_value"],"h8_value":r["h8_value"],
            "h3_rank":r["h3_rank"],"h5_rank":r["h5_rank"],"h8_rank":r["h8_rank"],
            "h3_to_h5_rank_delta":r["h3_to_h5_rank_delta"],"h3_to_h8_rank_delta":r["h3_to_h8_rank_delta"],
        })
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-module",default="scripts/run_intrinsic_term_structure_research.py")
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--player-seasons",required=True)
    ap.add_argument("--historical-uncertainty",default=str(OUT/"UNCERTAINTY_BY_HORIZON.csv"))
    ap.add_argument("--current-board",default=str(BOARD_DEFAULT))
    ap.add_argument("--production-h3-reference",default=str(REFERENCE_DEFAULT))
    args=ap.parse_args()

    hist=load_module(args.history_module)
    if hist.DISCOUNT != DISCOUNT:
        raise SystemExit("historical research discount changed; refusing current shadow")
    m=pd.read_csv(args.model_a_rows)
    q=json.loads(Path(args.qb_results).read_text())
    player=pd.read_csv(args.player_seasons)
    m,_=hist.integrate_qb(m,q)
    base=hist.build_base(m,player)

    historical_pred=hist.build_predictions(base,player)
    historical_metrics=hist.model_metrics(historical_pred)
    selected,_=hist.select_model(historical_metrics)
    gate=hist.selection_gate(historical_metrics,selected)
    if selected!=SELECTED_MODEL or not gate["passes"]:
        raise SystemExit(f"frozen historical selection no longer reproduces: selected={selected}, gate={gate}")

    board=pd.read_csv(args.current_board)
    current=build_current_features(board,player)
    if len(current)!=335:
        raise SystemExit(f"expected governed 335-player current board, got {len(current)}")
    current=current_long_forecasts(hist,base,player,current)

    phi=annual_shapley(hist,current)
    current=add_value_columns(current,phi)
    current,prod_comparison=attach_production_reference(current,Path(args.production_h3_reference))

    uncertainty=load_uncertainty(Path(args.historical_uncertainty))
    uinterp=uncertainty_interpretation(current,uncertainty)
    distributions=current_position_distributions(current)
    ages=age_effects(current)
    crosses=crossovers(current)
    reps=representatives(current)

    keep=[
        "player_id","current_player_id","historical_gsis_id","player_name","position","age","experience","age_band",
        "mapping_status","history_status","prior_points","prior_pct","scoring_multiplier",
    ]
    for h in range(1,9):
        keep.extend([f"y{h}",f"y{h}_shapley"])
        if h>=4:
            keep.extend([f"y{h}_positive_probability",f"y{h}_conditional_positive_points"])
    keep += [
        "production_h3_value","production_h3_rank",
        "h1_value","h3_value","h5_value","h8_value",
        "h1_rank","h3_rank","h5_rank","h8_rank",
        "h3_to_h5_rank_delta","h3_to_h8_rank_delta","h5_increment","h8_increment",
    ]
    current[keep].to_csv(OUT/"CURRENT_HORIZON_SHADOWS.csv",index=False)
    crosses.to_csv(OUT/"CURRENT_CROSSOVERS.csv",index=False)
    distributions.to_csv(OUT/"CURRENT_POSITION_DISTRIBUTIONS.csv",index=False)
    ages.to_csv(OUT/"CURRENT_AGE_EFFECTS.csv",index=False)
    uinterp.to_csv(OUT/"CURRENT_UNCERTAINTY_INTERPRETATION.csv",index=False)
    reps.to_csv(OUT/"REPRESENTATIVE_PLAYER_CURVES.csv",index=False)

    summary={
        "authority":"research_shadow_only_no_production_change",
        "current_input_board":str(args.current_board),
        "current_player_count":int(len(current)),
        "frozen_selected_model":SELECTED_MODEL,
        "historical_gate_reproduced":True,
        "discount":DISCOUNT,
        "shapley_permutations":PRODUCTION_SHAPLEY_PERMUTATIONS,
        "shapley_seed":PRODUCTION_SHAPLEY_SEED,
        "production_h3_comparison":prod_comparison,
        "horizon_rank_correlations":{
            "h1_vs_h3":float(current["h1_rank"].corr(current["h3_rank"],method="spearman")),
            "h3_vs_h5":float(current["h3_rank"].corr(current["h5_rank"],method="spearman")),
            "h3_vs_h8":float(current["h3_rank"].corr(current["h8_rank"],method="spearman")),
            "h5_vs_h8":float(current["h5_rank"].corr(current["h8_rank"],method="spearman")),
        },
        "rank_movement":{
            "median_abs_h3_to_h5":float(current["h3_to_h5_rank_delta"].abs().median()),
            "p90_abs_h3_to_h5":float(current["h3_to_h5_rank_delta"].abs().quantile(.9)),
            "max_abs_h3_to_h5":float(current["h3_to_h5_rank_delta"].abs().max()),
            "median_abs_h3_to_h8":float(current["h3_to_h8_rank_delta"].abs().median()),
            "p90_abs_h3_to_h8":float(current["h3_to_h8_rank_delta"].abs().quantile(.9)),
            "max_abs_h3_to_h8":float(current["h3_to_h8_rank_delta"].abs().max()),
        },
        "current_mapping":{
            "players_with_2025_prior_points":int(current["prior_points"].notna().sum()),
            "players_without_2025_prior_points":int(current["prior_points"].isna().sum()),
            "note":"Missing prior-season rows remain missing and are handled by the frozen model's training median; no current named-player override.",
        },
        "terminal_interpretation":{
            "exact_y6_y8_cardinal_value_authority":"not_recommended_from_current_evidence",
            "reason":"historical ordering persists but exact-year signal weakens and discount/magnitude sensitivity grows; current terminal rows remain diagnostic shadows only.",
        },
    }
    (OUT/"CURRENT_SHADOW_SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))


if __name__=="__main__":
    main()

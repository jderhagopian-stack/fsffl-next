from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT=Path("artifacts/research/intrinsic_y4plus_model_family_20260926")
BOARD=Path("artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_STANDARD_COORDINATE_BOARD_335.csv")
H3REF=Path("artifacts/research/intrinsic_term_structure_20260926/CURRENT_PRODUCTION_H3_REFERENCE.json")
POSITIONS=("QB","RB","WR","TE")
HORIZONS=(4,5,6,7,8)
DISCOUNT=0.85

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def build_current_models(hist,cmp,curmod,base,player,board,route):
    current=curmod.build_current_features(board,player)
    current["y3_pct"]=current.groupby("position")["y3"].rank(pct=True,method="average")
    if len(current)!=335:
        raise SystemExit(f"expected 335 current rows, got {len(current)}")

    archs={
        "primary_two_part":{},
        "development_dynamic_sensitivity":{},
    }
    for pos in POSITIONS:
        for h in HORIZONS:
            archs["primary_two_part"][(pos,h)]="two_part_state"
            row=route[(route.position==pos)&(route.horizon==h)]
            if len(row)!=1:
                raise SystemExit(f"missing route {pos} Y{h}")
            archs["development_dynamic_sensitivity"][(pos,h)]=str(row.iloc[0].final_research_route_family)

    outputs={}
    for label,mapping in archs.items():
        x=current.copy()
        for h in HORIZONS:
            x[f"y{h}"]=0.0
            x[f"y{h}_p_active"]=np.nan
            x[f"y{h}_family"]=""
            hf=cmp.horizon_frame(base,player,h)
            train_all=hf[(hf["season"]<2026)&(hf["target_season"]<2026)].copy()
            for pos in POSITIONS:
                mask=x.position==pos
                ev=x.loc[mask].copy()
                train=train_all[train_all.position==pos].copy()
                fam=mapping[(pos,h)]
                pred,p,_=cmp.predict_family(hist,fam,base,player,2026,h,train,ev,pos)
                x.loc[mask,f"y{h}"]=pred
                x.loc[mask,f"y{h}_p_active"]=p
                x.loc[mask,f"y{h}_family"]=fam
        phi=curmod.annual_shapley(hist,x)
        for h in range(1,9):
            x[f"y{h}_shapley"]=x.player_id.map(phi[h]).fillna(0.0)
        for H in (1,3,4,5,6,7,8):
            vals=curmod.cumulative_values(phi,H)
            x[f"h{H}_value"]=x.player_id.map(vals).fillna(0.0)
            x[f"h{H}_rank"]=x[f"h{H}_value"].rank(method="min",ascending=False)
        outputs[label]=x
    return outputs

def summarize(primary,dynamic):
    rows=[]
    for H in (4,5,6,7,8):
        pr=primary[f"h{H}_rank"]
        dr=dynamic[f"h{H}_rank"]
        rows.append({
            "horizon":H,
            "rank_spearman_primary_vs_dynamic":float(pr.corr(dr,method="spearman")),
            "median_abs_rank_difference":float((pr-dr).abs().median()),
            "p90_abs_rank_difference":float((pr-dr).abs().quantile(.9)),
            "max_abs_rank_difference":float((pr-dr).abs().max()),
            "top25_overlap":int(len(set(primary.loc[pr<=25,"player_id"]) & set(dynamic.loc[dr<=25,"player_id"]))),
            "top50_overlap":int(len(set(primary.loc[pr<=50,"player_id"]) & set(dynamic.loc[dr<=50,"player_id"]))),
        })
    return pd.DataFrame(rows)

def position_dist(df,label):
    rows=[]
    for H in (3,4,5,6,7,8):
        rank=df[f"h{H}_rank"]
        for pos in POSITIONS:
            x=df[df.position==pos]
            rows.append({
                "architecture":label,"horizon":H,"position":pos,"n":len(x),
                "top25_share":float((x[f"h{H}_rank"]<=25).sum()/25),
                "top50_share":float((x[f"h{H}_rank"]<=50).sum()/50),
                "top100_share":float((x[f"h{H}_rank"]<=100).sum()/100),
                "median_value":float(x[f"h{H}_value"].median()),
                "p90_value":float(x[f"h{H}_value"].quantile(.9)),
            })
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-module",default="scripts/run_intrinsic_term_structure_research.py")
    ap.add_argument("--compare-module",default="scripts/run_intrinsic_y4plus_model_family_research.py")
    ap.add_argument("--current-helper",default="scripts/run_intrinsic_term_structure_current_shadows.py")
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--player-seasons",required=True)
    ap.add_argument("--routing",required=True)
    args=ap.parse_args()

    OUT.mkdir(parents=True,exist_ok=True)
    hist=load_module("hist",args.history_module)
    cmp=load_module("cmp",args.compare_module)
    curmod=load_module("curmod",args.current_helper)

    m=pd.read_csv(args.model_a_rows)
    q=json.loads(Path(args.qb_results).read_text())
    player=pd.read_csv(args.player_seasons)
    m,_=hist.integrate_qb(m,q)
    base=cmp.add_base_features(hist.build_base(m,player))
    board=pd.read_csv(BOARD)
    route=pd.read_csv(args.routing)

    out=build_current_models(hist,cmp,curmod,base,player,board,route)
    primary=out["primary_two_part"]
    dynamic=out["development_dynamic_sensitivity"]

    primary,prod=curmod.attach_production_reference(primary,H3REF)
    # H1-H3 are identical by construction for dynamic; attach the same production fields.
    dynamic["production_h3_value"]=primary["production_h3_value"].to_numpy()
    dynamic["production_h3_rank"]=primary["production_h3_rank"].to_numpy()

    combined=[]
    for label,df in (("primary_two_part",primary),("development_dynamic_sensitivity",dynamic)):
        keep=["player_id","player_name","position","age","experience","age_band","production_h3_value","production_h3_rank"]
        for h in range(1,9):
            keep += [f"y{h}",f"y{h}_shapley"]
            if h>=4:
                keep += [f"y{h}_p_active",f"y{h}_family"]
        for H in (1,3,4,5,6,7,8):
            keep += [f"h{H}_value",f"h{H}_rank"]
        z=df[keep].copy()
        z.insert(0,"architecture",label)
        combined.append(z)
    allrows=pd.concat(combined,ignore_index=True)
    allrows.to_csv(OUT/"CURRENT_COMPARATIVE_SHADOWS.csv",index=False)

    sensitivity=summarize(primary,dynamic)
    sensitivity.to_csv(OUT/"CURRENT_ARCHITECTURE_SENSITIVITY.csv",index=False)

    pos=pd.concat([
        position_dist(primary,"primary_two_part"),
        position_dist(dynamic,"development_dynamic_sensitivity"),
    ],ignore_index=True)
    pos.to_csv(OUT/"CURRENT_POSITION_DISTRIBUTIONS_COMPARATIVE.csv",index=False)

    # Largest model-family-sensitive current players, selected mechanically after historical freeze.
    rep=primary[["player_id","player_name","position","age"]].copy()
    for H in (5,8):
        rep[f"primary_h{H}_rank"]=primary[f"h{H}_rank"].to_numpy()
        rep[f"dynamic_h{H}_rank"]=dynamic[f"h{H}_rank"].to_numpy()
        rep[f"h{H}_rank_difference_dynamic_minus_primary"]=dynamic[f"h{H}_rank"].to_numpy()-primary[f"h{H}_rank"].to_numpy()
    score=rep["h5_rank_difference_dynamic_minus_primary"].abs()+rep["h8_rank_difference_dynamic_minus_primary"].abs()
    rep=rep.loc[score.sort_values(ascending=False).index].head(40)
    rep.to_csv(OUT/"CURRENT_MODEL_SENSITIVITY_PLAYERS.csv",index=False)

    summary={
        "authority":"research_shadows_only",
        "historical_selection_frozen_before_this_run":True,
        "primary_cardinal_family":"two_part_state for every position and Y4-Y8",
        "development_dynamic_route_status":"sensitivity_only_not_recommended",
        "current_player_count":len(primary),
        "production_h3_comparison":prod,
        "architecture_sensitivity":sensitivity.to_dict("records"),
        "largest_model_sensitivity_rows":rep.head(12).to_dict("records"),
    }
    (OUT/"CURRENT_COMPARATIVE_SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

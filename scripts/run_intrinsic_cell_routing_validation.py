from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

OUT=Path("artifacts/research/intrinsic_cell_routing_y4_y8_20260926")
POSITIONS=("QB","RB","WR","TE")
HORIZONS=(4,5,6,7,8)

def load_module(path):
    spec=importlib.util.spec_from_file_location("dev",path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def build_inputs(dev,args):
    m=pd.read_csv(args.model_a_rows)
    qb=json.loads(Path(args.qb_results).read_text())
    raw=dev.prep_raw(pd.read_csv(args.raw_seasons))
    players=pd.read_csv(args.players)
    residual=pd.read_csv(args.residual_states)
    innovation=pd.read_csv(args.innovation_states)
    m=dev.add_qb_governed_path(m,qb)
    base=dev.build_forecast_base(m)
    base=dev.merge_lags(base,raw)
    base=dev.add_engineered_features(base,players)
    base=dev.merge_trajectory(base,residual,innovation)
    long=dev.build_long(base,raw)
    return long

def parse_candidate(c):
    arch,fs,model=c.split("|")
    return arch,fs,model

def fit_candidate(dev,long,candidate,T,h,pos,ev):
    arch,fs,model=parse_candidate(candidate)
    if arch=="specialist":
        tr=long[(long.horizon==h)&(long.position==pos)&(long.target_season<T)]
    elif arch=="global_continuous":
        tr=long[long.target_season<T]
    elif arch=="position_continuous":
        tr=long[(long.position==pos)&(long.target_season<T)]
    elif arch=="shared_horizon":
        tr=long[(long.horizon==h)&(long.target_season<T)]
    else:
        raise KeyError(candidate)
    return dev.fit_predict(tr,ev,fs,model,arch),len(tr)

def eligible_origins(long,h,min_train):
    out=[]
    for T in sorted(int(x) for x in long.loc[long.horizon==h,"base_season"].unique()):
        ev=long[(long.horizon==h)&(long.base_season==T)]
        tr=long[(long.horizon==h)&(long.target_season<T)]
        if len(ev)>0 and len(tr)>=min_train and tr.base_season.nunique()>=2:
            out.append(T)
    return out

def generate_bank(dev,long,freeze):
    outer_n=int(freeze["rolling_contract"]["outer_origins_per_horizon"])
    inner_w=int(freeze["rolling_contract"]["inner_origin_window"])
    baseline=freeze["incumbent_comparator"]
    shared=freeze["shared_anchor"]
    rows=[]
    origin_plan={}
    for h in HORIZONS:
        elig=eligible_origins(long,h,dev.MIN_TRAIN_ROWS)
        outer_eligible=[T for i,T in enumerate(elig) if i>=int(freeze["rolling_contract"]["minimum_inner_origins"])]
        outer=outer_eligible[-outer_n:]
        if len(outer)<outer_n:
            raise SystemExit(f"insufficient eligible rolling outer origins for Y{h}: eligible={elig}, outer={outer}")
        needed=set(outer)
        for T in outer:
            prior=[x for x in elig if x<T][-inner_w:]
            if len(prior)<int(freeze["rolling_contract"]["minimum_inner_origins"]):
                raise SystemExit(f"insufficient prior origins for Y{h} T{T}: {prior}")
            needed.update(prior)
        bank=sorted(needed)
        origin_plan[str(h)]={"eligible_all":elig,"bank":bank,"outer":outer}
        for T in bank:
            evh=long[(long.horizon==h)&(long.base_season==T)]
            for pos in POSITIONS:
                ev=evh[evh.position==pos]
                if ev.empty: continue
                key=f"{pos}|Y{h}"
                cands=list(dict.fromkeys(freeze["specialist_shortlists"][key]+[baseline,shared]))
                for cand in cands:
                    (pred,pa),train_n=fit_candidate(dev,long,cand,T,h,pos,ev)
                    for i,r in enumerate(ev.itertuples()):
                        rows.append({
                            "row_id":r.row_id,"base_season":T,"horizon":h,"position":pos,
                            "player_id":r.player_id,"actual":float(r.actual),"candidate":cand,
                            "pred":float(pred[i]),
                            "p_active":float(pa[i]) if np.isfinite(pa[i]) else np.nan,
                            "train_n":int(train_n),
                        })
    return pd.DataFrame(rows),origin_plan

def metrics(dev,g):
    return dev.metric(g)

def neutral_scores(dev,inner,cands):
    rec=[]
    for cand in cands:
        g=inner[inner.candidate==cand]
        if g.empty: continue
        m=metrics(dev,g)
        arch,fs,model=parse_candidate(cand)
        rec.append({
            "candidate":cand,
            **{k:m[k] for k in ["n","rmse","mae","bias","spearman","tail_rmse","survival_brier","survival_calibration_gap"]},
            "complexity":dev.candidate_complexity(arch,fs,model),
        })
    z=pd.DataFrame(rec)
    if z.empty: return z
    eps=1e-9
    refs={
        "rmse":float(z.rmse.median()),
        "mae":float(z.mae.median()),
        "tail_rmse":float(z.tail_rmse.median()),
        "spearman":float(z.spearman.median()),
    }
    z["selection_score"]=(
        .32*np.log(np.maximum(eps,z.rmse)/max(eps,refs["rmse"]))+
        .16*np.log(np.maximum(eps,z.mae)/max(eps,refs["mae"]))+
        .22*np.log(np.maximum(eps,z.tail_rmse)/max(eps,refs["tail_rmse"]))+
        .15*(refs["spearman"]-z.spearman)+
        .05*z.bias.abs()/max(10.0,refs["rmse"])+
        z.complexity
    )
    # Fold-level rank stability uses the same neutral reference logic per origin.
    fold_rank={c:[] for c in z.candidate}
    for T in sorted(inner.base_season.unique()):
        q=inner[inner.base_season==T]
        fr=[]
        for cand in z.candidate:
            g=q[q.candidate==cand]
            if g.empty: continue
            m=metrics(dev,g); arch,fs,model=parse_candidate(cand)
            fr.append({"candidate":cand,"rmse":m["rmse"],"mae":m["mae"],"bias":m["bias"],
                       "spearman":m["spearman"],"tail_rmse":m["tail_rmse"],
                       "complexity":dev.candidate_complexity(arch,fs,model)})
        f=pd.DataFrame(fr)
        if f.empty: continue
        rr={k:float(f[k].median()) for k in ["rmse","mae","tail_rmse","spearman"]}
        f["s"]=(
            .32*np.log(np.maximum(eps,f.rmse)/max(eps,rr["rmse"]))+
            .16*np.log(np.maximum(eps,f.mae)/max(eps,rr["mae"]))+
            .22*np.log(np.maximum(eps,f.tail_rmse)/max(eps,rr["tail_rmse"]))+
            .15*(rr["spearman"]-f.spearman)+
            .05*f.bias.abs()/max(10.0,rr["rmse"])+f.complexity
        )
        f=f.sort_values(["s","candidate"]).reset_index(drop=True)
        for i,r in enumerate(f.itertuples()):
            fold_rank[str(r.candidate)].append(i+1)
    best=[]; top2=[]; meanrank=[]; folds=[]
    for cand in z.candidate:
        rs=fold_rank.get(cand,[])
        folds.append(len(rs))
        best.append(float(np.mean(np.asarray(rs)==1)) if rs else 0.0)
        top2.append(float(np.mean(np.asarray(rs)<=2)) if rs else 0.0)
        meanrank.append(float(np.mean(rs)) if rs else np.nan)
    z["fold_count"]=folds
    z["fold_best_share"]=best
    z["fold_top2_share"]=top2
    z["fold_mean_rank"]=meanrank
    return z.sort_values(["selection_score","candidate"]).reset_index(drop=True)

def weights_from_scores(scoretab):
    top=scoretab.head(3).copy()
    vals=top.selection_score.to_numpy(float)
    med=float(np.median(vals))
    mad=float(np.median(np.abs(vals-med)))
    tau=max(mad,0.02)
    raw=np.exp(-(vals-float(vals.min()))/tau)
    raw=raw/raw.sum()
    return {str(c):float(w) for c,w in zip(top.candidate,raw)},tau

def combine(rows,weights):
    cands=list(weights)
    q=rows[rows.candidate.isin(cands)].copy()
    if q.empty: return pd.DataFrame()
    p=q.pivot_table(index=["row_id","base_season","horizon","position","player_id","actual"],
                    columns="candidate",values="pred",aggfunc="first").reset_index()
    for c in cands:
        if c not in p.columns:
            return pd.DataFrame()
    p["pred"]=0.0
    for c,w in weights.items():
        p["pred"]+=float(w)*p[c]
    return p[["row_id","base_season","horizon","position","player_id","actual","pred"]]

def calibrate(inner_combo):
    e=(inner_combo.pred-inner_combo.actual).abs().to_numpy(float)
    return float(np.quantile(e,.80)),float(np.quantile(e,.90))

def annotate_outer(outer_combo,policy,q80,q90):
    z=outer_combo.copy()
    z["policy"]=policy
    z["q80"]=q80; z["q90"]=q90
    e=(z.pred-z.actual).abs()
    z["covered80"]=e<=q80
    z["covered90"]=e<=q90
    return z

def run_outer(dev,bank,origin_plan,freeze,blanket):
    outer_n=int(freeze["rolling_contract"]["outer_origins_per_horizon"])
    inner_w=int(freeze["rolling_contract"]["inner_origin_window"])
    min_inner=int(freeze["rolling_contract"]["minimum_inner_origins"])
    baseline=freeze["incumbent_comparator"]
    shared=freeze["shared_anchor"]
    preds=[]; decisions=[]; score_rows=[]
    for h in HORIZONS:
        bank_orig=origin_plan[str(h)]["bank"]
        outer_orig=origin_plan[str(h)]["outer"]
        for T in outer_orig:
            prior=[x for x in bank_orig if x<T][-inner_w:]
            if len(prior)<min_inner:
                raise SystemExit(f"not enough inner origins for Y{h} T{T}: {prior}")
            for pos in POSITIONS:
                key=f"{pos}|Y{h}"
                cands=list(dict.fromkeys(freeze["specialist_shortlists"][key]+[baseline,shared]))
                inner=bank[(bank.horizon==h)&(bank.position==pos)&(bank.base_season.isin(prior))&
                           (bank.candidate.isin(cands))]
                outer=bank[(bank.horizon==h)&(bank.position==pos)&(bank.base_season==T)&
                           (bank.candidate.isin(cands))]
                scoretab=neutral_scores(dev,inner,cands)
                if scoretab.empty: continue
                hard=str(scoretab.iloc[0].candidate)
                soft_w,tau=weights_from_scores(scoretab)
                blanket_cand=str(blanket["route"][key])
                policy_weights={
                    "baseline":{baseline:1.0},
                    "hard_router":{hard:1.0},
                    "soft_stack":soft_w,
                    "blanket_75_25":{blanket_cand:.75,shared:.25},
                }
                for r in scoretab.itertuples():
                    score_rows.append({
                        "outer_origin":T,"horizon":h,"position":pos,
                        "inner_origins":";".join(str(x) for x in prior),
                        "candidate":r.candidate,"selection_score":r.selection_score,
                        "fold_count":r.fold_count,"fold_best_share":r.fold_best_share,
                        "fold_top2_share":r.fold_top2_share,"fold_mean_rank":r.fold_mean_rank,
                        "rmse":r.rmse,"mae":r.mae,"bias":r.bias,"spearman":r.spearman,
                        "tail_rmse":r.tail_rmse,"complexity":r.complexity,
                    })
                decisions.append({
                    "outer_origin":T,"horizon":h,"position":pos,
                    "inner_origins":";".join(str(x) for x in prior),
                    "hard_candidate":hard,
                    "hard_score":float(scoretab.iloc[0].selection_score),
                    "hard_fold_best_share":float(scoretab.iloc[0].fold_best_share),
                    "hard_fold_top2_share":float(scoretab.iloc[0].fold_top2_share),
                    "soft_weights":json.dumps(soft_w,sort_keys=True),
                    "soft_tau":tau,
                    "blanket_specialist_candidate":blanket_cand,
                })
                for policy,w in policy_weights.items():
                    ic=combine(inner,w); oc=combine(outer,w)
                    if ic.empty or oc.empty:
                        raise SystemExit(f"missing combination for {policy} {key} T{T}")
                    q80,q90=calibrate(ic)
                    preds.append(annotate_outer(oc,policy,q80,q90))
    return pd.concat(preds,ignore_index=True),pd.DataFrame(decisions),pd.DataFrame(score_rows)

def policy_metric_rows(dev,pred):
    rows=[]
    for (policy,h,pos),g in pred.groupby(["policy","horizon","position"]):
        m=metrics(dev,g)
        rows.append({"policy":policy,"horizon":h,"position":pos,**m,
                     "coverage80":float(g.covered80.mean()),"coverage90":float(g.covered90.mean()),
                     "mean_q80":float(g.q80.mean()),"mean_q90":float(g.q90.mean())})
    return pd.DataFrame(rows)

def outer_fold_metric_rows(dev,pred):
    rows=[]
    for (policy,h,pos,T),g in pred.groupby(["policy","horizon","position","base_season"]):
        m=metrics(dev,g)
        rows.append({"policy":policy,"horizon":h,"position":pos,"outer_origin":T,**m,
                     "coverage80":float(g.covered80.mean()),"coverage90":float(g.covered90.mean())})
    return pd.DataFrame(rows)

def neutral_policy_scores(cell_metrics,eligible=("baseline","hard_router","soft_stack")):
    rows=[]
    eps=1e-9
    for (h,pos),g in cell_metrics[cell_metrics.policy.isin(eligible)].groupby(["horizon","position"]):
        ref={k:float(g[k].median()) for k in ["rmse","mae","tail_rmse","spearman"]}
        for r in g.itertuples():
            s=(.32*math.log(max(eps,r.rmse)/max(eps,ref["rmse"]))+
               .16*math.log(max(eps,r.mae)/max(eps,ref["mae"]))+
               .22*math.log(max(eps,r.tail_rmse)/max(eps,ref["tail_rmse"]))+
               .15*(ref["spearman"]-r.spearman)+
               .05*abs(r.bias)/max(10.0,ref["rmse"]))
            rows.append({"horizon":h,"position":pos,"policy":r.policy,"policy_score":s})
    return pd.DataFrame(rows)

def fold_policy_winners(dev,fold_metrics):
    rows=[]
    eps=1e-9
    eligible={"baseline","hard_router","soft_stack"}
    for (h,pos,T),g in fold_metrics[fold_metrics.policy.isin(eligible)].groupby(["horizon","position","outer_origin"]):
        ref={k:float(g[k].median()) for k in ["rmse","mae","tail_rmse","spearman"]}
        tmp=[]
        for r in g.itertuples():
            s=(.32*math.log(max(eps,r.rmse)/max(eps,ref["rmse"]))+
               .16*math.log(max(eps,r.mae)/max(eps,ref["mae"]))+
               .22*math.log(max(eps,r.tail_rmse)/max(eps,ref["tail_rmse"]))+
               .15*(ref["spearman"]-r.spearman)+
               .05*abs(r.bias)/max(10.0,ref["rmse"]))
            tmp.append((s,str(r.policy)))
        tmp.sort()
        rows.append({"horizon":h,"position":pos,"outer_origin":T,"winner":tmp[0][1],
                     "winner_score":tmp[0][0],"runner_score":tmp[1][0]})
    return pd.DataFrame(rows)

def cell_interpretation(dev,pred,cell_metrics,fold_metrics,policy_scores,freeze):
    th=freeze["final_cell_interpretation"]["thresholds"]
    winners=fold_policy_winners(dev,fold_metrics)
    rows=[]
    eligible=["baseline","hard_router","soft_stack"]
    for h in HORIZONS:
        for pos in POSITIONS:
            sc=policy_scores[(policy_scores.horizon==h)&(policy_scores.position==pos)].sort_values(["policy_score","policy"])
            if len(sc)<2: continue
            best=str(sc.iloc[0].policy); margin=float(sc.iloc[1].policy_score-sc.iloc[0].policy_score)
            wg=winners[(winners.horizon==h)&(winners.position==pos)]
            win_share=float((wg.winner==best).mean()) if len(wg) else 0.0
            fm=fold_metrics[(fold_metrics.horizon==h)&(fold_metrics.position==pos)]
            severe=0
            for T,q in fm.groupby("outer_origin"):
                med=float(q.rmse.median())
                rr=q[q.policy==best]
                if len(rr) and float(rr.iloc[0].rmse)>1.20*med: severe+=1
            pg=pred[(pred.horizon==h)&(pred.position==pos)&(pred.policy==best)]
            cm=cell_metrics[(cell_metrics.horizon==h)&(cell_metrics.position==pos)&(cell_metrics.policy==best)].iloc[0]
            q90=float(np.quantile(np.abs(pg.pred-pg.actual),.90))
            p90_actual=max(25.0,float(np.quantile(pg.actual,.90)))
            rel_q90=q90/p90_actual
            coarse=(float(cm.spearman)<float(th["adequate_rank_spearman_min"]) and
                    rel_q90>=float(th["coarse_relative_q90_min"]))
            exact=(not coarse and
                   win_share>=float(th["repeatable_outer_policy_win_share_min"]) and
                   margin>=float(th["material_policy_score_margin_min"]) and
                   severe<=1)
            if coarse:
                status="coarse_only"
                recommendation="coarse_or_state_band"
            elif exact and best=="baseline":
                status="baseline_earned"
                recommendation="baseline"
            elif exact and best=="hard_router":
                status="routed_exact_supported"
                recommendation="hard_router"
            elif exact and best=="soft_stack":
                status="shrinkage_exact_supported"
                recommendation="soft_stack"
            else:
                status="indistinguishable_or_unstable"
                recommendation="soft_stack_with_uncertainty"
            blanket=cell_metrics[(cell_metrics.horizon==h)&(cell_metrics.position==pos)&(cell_metrics.policy=="blanket_75_25")].iloc[0]
            base=cell_metrics[(cell_metrics.horizon==h)&(cell_metrics.position==pos)&(cell_metrics.policy=="baseline")].iloc[0]
            rows.append({
                "position":pos,"horizon":h,"rolling_best_policy":best,
                "policy_score_margin_vs_runner":margin,"outer_policy_win_share":win_share,
                "severe_instability_origin_count":severe,"best_rmse":float(cm.rmse),
                "best_mae":float(cm.mae),"best_tail_rmse":float(cm.tail_rmse),
                "best_spearman":float(cm.spearman),"rolling_q90_abs_error":q90,
                "relative_q90_to_p90_actual":rel_q90,"status":status,
                "recommendation":recommendation,
                "baseline_rmse":float(base.rmse),"blanket_rmse":float(blanket.rmse),
                "blanket_rmse_ratio_vs_baseline":float(blanket.rmse/base.rmse),
            })
    return pd.DataFrame(rows)

def aggregate_summary(dev,pred,cell_metrics):
    rows=[]
    base_cells=cell_metrics[cell_metrics.policy=="baseline"].set_index(["horizon","position"])
    for policy,g in pred.groupby("policy"):
        m=metrics(dev,g)
        scores=[]; rmse_ratios=[]; cell_wins=0
        for (h,pos),q in cell_metrics[cell_metrics.policy==policy].groupby(["horizon","position"]):
            r=q.iloc[0]; b=base_cells.loc[(h,pos)]
            comp=dev.composite(
                {k:float(r[k]) for k in ["rmse","mae","bias","spearman","tail_rmse"]},
                {k:float(b[k]) for k in ["rmse","mae","bias","spearman","tail_rmse"]},0.0)
            scores.append(comp); rmse_ratios.append(float(r.rmse/b.rmse))
            if comp<0: cell_wins+=1
        rows.append({"policy":policy,**m,
                     "coverage80":float(g.covered80.mean()),"coverage90":float(g.covered90.mean()),
                     "mean_cell_composite_vs_baseline":float(np.mean(scores)),
                     "cells_better_than_baseline":cell_wins,
                     "worst_cell_rmse_ratio_vs_baseline":float(max(rmse_ratios))})
    return pd.DataFrame(rows).sort_values("mean_cell_composite_vs_baseline")

def current_route_from_history(dev,bank,origin_plan,freeze,blanket,cell_interp):
    baseline=freeze["incumbent_comparator"]; shared=freeze["shared_anchor"]
    inner_w=int(freeze["rolling_contract"]["inner_origin_window"])
    rows=[]
    for h in HORIZONS:
        origins=origin_plan[str(h)]["bank"][-inner_w:]
        for pos in POSITIONS:
            key=f"{pos}|Y{h}"
            cands=list(dict.fromkeys(freeze["specialist_shortlists"][key]+[baseline,shared]))
            inner=bank[(bank.horizon==h)&(bank.position==pos)&(bank.base_season.isin(origins))&
                       (bank.candidate.isin(cands))]
            sc=neutral_scores(dev,inner,cands)
            hard=str(sc.iloc[0].candidate)
            soft,tau=weights_from_scores(sc)
            ci=cell_interp[(cell_interp.horizon==h)&(cell_interp.position==pos)].iloc[0]
            rows.append({
                "position":pos,"horizon":h,"history_origins":";".join(str(x) for x in origins),
                "hard_candidate":hard,"hard_score":float(sc.iloc[0].selection_score),
                "hard_fold_best_share":float(sc.iloc[0].fold_best_share),
                "hard_fold_top2_share":float(sc.iloc[0].fold_top2_share),
                "soft_weights":json.dumps(soft,sort_keys=True),"soft_tau":tau,
                "rolling_best_policy":ci.rolling_best_policy,
                "cell_status":ci.status,"recommendation":ci.recommendation,
                "baseline_is_current_hard_choice":hard==baseline,
                "prior_blanket_specialist_candidate":blanket["route"][key],
            })
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--development-module",default="scripts/run_intrinsic_comprehensive_development.py")
    ap.add_argument("--policy-freeze",required=True)
    ap.add_argument("--prior-architecture-freeze",required=True)
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--raw-seasons",required=True)
    ap.add_argument("--players",required=True)
    ap.add_argument("--residual-states",required=True)
    ap.add_argument("--innovation-states",required=True)
    args=ap.parse_args()

    OUT.mkdir(parents=True,exist_ok=True)
    freeze=json.loads(Path(args.policy_freeze).read_text())
    old=json.loads(Path(args.prior_architecture_freeze).read_text())
    blanket=old["selected_architecture"]
    if blanket.get("type")!="hierarchical_blend" or abs(float(blanket["specialist_weight"])-.75)>1e-12:
        raise SystemExit("prior blanket comparator contract changed")

    dev=load_module(args.development_module)
    long=build_inputs(dev,args)

    bank,origin_plan=generate_bank(dev,long,freeze)
    pred,decisions,scores=run_outer(dev,bank,origin_plan,freeze,blanket)
    cellm=policy_metric_rows(dev,pred)
    foldm=outer_fold_metric_rows(dev,pred)
    pscore=neutral_policy_scores(cellm)
    interp=cell_interpretation(dev,pred,cellm,foldm,pscore,freeze)
    agg=aggregate_summary(dev,pred,cellm)
    route=current_route_from_history(dev,bank,origin_plan,freeze,blanket,interp)

    decisions.to_csv(OUT/"ROLLING_ROUTE_DECISIONS.csv",index=False)
    scores.to_csv(OUT/"ROLLING_CANDIDATE_SELECTION_SCORES.csv",index=False)
    pred.to_csv(OUT/"ROLLING_POLICY_PREDICTIONS.csv",index=False)
    cellm.to_csv(OUT/"ROLLING_POLICY_CELL_METRICS.csv",index=False)
    foldm.to_csv(OUT/"ROLLING_POLICY_OUTER_FOLD_METRICS.csv",index=False)
    pscore.to_csv(OUT/"ROLLING_POLICY_CELL_SCORES.csv",index=False)
    interp.to_csv(OUT/"CELL_ROUTING_INTERPRETATION.csv",index=False)
    agg.to_csv(OUT/"ROUTING_POLICY_AGGREGATE.csv",index=False)
    route.to_csv(OUT/"CURRENT_RESEARCH_ROUTE.csv",index=False)
    (OUT/"OUTER_ORIGIN_PLAN.json").write_text(json.dumps(origin_plan,indent=2,sort_keys=True),encoding="utf-8")

    counts=interp.status.value_counts().to_dict()
    result={
        "state":"REPEATED_ROLLING_VALIDATION_COMPLETE",
        "authority":"research_only_no_production_change",
        "prior_holdout_consumed_by_selector":False,
        "current_named_players_consumed":False,
        "outer_origin_plan":origin_plan,
        "aggregate":agg.to_dict("records"),
        "cell_status_counts":counts,
        "cell_interpretation":interp.to_dict("records"),
        "current_research_route":route.to_dict("records"),
        "limitations":[
            "No second truly untouched Y8 holdout exists after the prior comprehensive holdout was exposed.",
            "Repeated rolling outer validation includes historical years that have now been seen; it is not relabeled as untouched.",
            "Current research route is a policy replay over historical evidence, not production authority.",
            "Cross-horizon covariance remains outside this corrective."
        ],
        "guards":{"production_h3_changed":False,"market_owner_team_utility_inputs":False}
    }
    (OUT/"ROLLING_VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print("AGGREGATE")
    print(agg.to_string(index=False))
    print("CELL_INTERPRETATION")
    print(interp.to_string(index=False))
    print("RESULT_JSON_BEGIN")
    print(json.dumps(result,sort_keys=True))
    print("RESULT_JSON_END")

if __name__=="__main__":
    main()

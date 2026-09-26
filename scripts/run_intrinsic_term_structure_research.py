from __future__ import annotations

import argparse, json, math, random, statistics, bisect
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

OUT = Path("artifacts/research/intrinsic_term_structure_20260926")
DISCOUNT = 0.85
DEV_FOLDS = tuple(range(2014, 2019))
HOLDOUT_FOLDS = (2019, 2020, 2021)
TERMINAL_FOLDS = (2016, 2017, 2018)
POSITIONS = ("QB","RB","WR","TE")
FEATURES = ("age","experience","prior_pct","log_prior_points","log_y1","y1_pct","y2_ratio","y3_ratio","y2_delta","y3_delta")
CANDIDATES = ("carry_y3","direct_ridge","two_part_state")
DISCOUNT_SENSITIVITY = (0.70, 0.85, 0.95)
SHAPLEY_PERMUTATIONS = 512
SHAPLEY_SEED = 20260926

def spearman(a,b):
    a=pd.Series(list(a),dtype=float); b=pd.Series(list(b),dtype=float)
    if len(a)<2 or a.nunique()<2 or b.nunique()<2:
        return float("nan")
    return float(a.corr(b,method="spearman"))

def metric(rows, pred="pred", actual="actual"):
    if len(rows)==0:
        return {"n":0}
    e=rows[pred].to_numpy(float)-rows[actual].to_numpy(float)
    return {
        "n":int(len(rows)),
        "mae":float(np.mean(np.abs(e))),
        "rmse":float(np.sqrt(np.mean(e*e))),
        "bias":float(np.mean(e)),
        "spearman":spearman(rows[pred],rows[actual]),
    }

def load_inputs(args):
    m=pd.read_csv(args.model_a_rows)
    q=json.loads(Path(args.qb_results).read_text())
    player=pd.read_csv(args.player_seasons)
    downstream=pd.DataFrame(json.loads(Path(args.shapley_rows).read_text()))
    return m,q,player,downstream

def integrate_qb(m,q):
    m=m.copy()
    probs={}
    for r in q.get("records",[]):
        fid=f"preseason-{int(r['source_season'])}"
        probs[(fid,r["player_id"],1)]=float(r["prob_y2"])
        probs[(fid,r["player_id"],2)]=float(r["prob_y3"])
    y1={(r.fold_id,r.asset_id):float(r.player_forecast_mean) for r in m.itertuples() if int(r.season_offset)==0}
    changed=0
    for idx,r in m.iterrows():
        off=int(r.season_offset)
        key=(r.fold_id,r.asset_id,off)
        if r.position=="QB" and off in (1,2) and key in probs:
            m.at[idx,"player_forecast_mean"]=probs[key]*y1[(r.fold_id,r.asset_id)]
            changed+=1
    return m,changed

def build_base(m,player):
    pvt=m.pivot_table(
        index=["fold_id","target_season","asset_id","position"],
        columns="season_offset",
        values=[
            "player_forecast_mean","player_forecast_stddev","replacement_forecast_mean",
            "realized_player_points","realized_replacement_points","annual_weight"
        ],
        aggfunc="first",
    ).reset_index()
    pvt.columns=[
        "_".join(str(x) for x in col if str(x)!="") if isinstance(col,tuple) else str(col)
        for col in pvt.columns
    ]
    pvt=pvt.rename(columns={
        "target_season":"season","asset_id":"player_id",
        "player_forecast_mean_0":"y1","player_forecast_mean_1":"y2","player_forecast_mean_2":"y3",
        "player_forecast_stddev_0":"sd1","player_forecast_stddev_1":"sd2","player_forecast_stddev_2":"sd3",
        "replacement_forecast_mean_0":"r1","replacement_forecast_mean_1":"r2","replacement_forecast_mean_2":"r3",
        "realized_player_points_0":"a1","realized_player_points_1":"a2","realized_player_points_2":"a3",
        "realized_replacement_points_0":"ar1","realized_replacement_points_1":"ar2","realized_replacement_points_2":"ar3",
        "annual_weight_0":"w1","annual_weight_1":"w2","annual_weight_2":"w3",
    })
    prev=player.copy()
    prev["season"]=prev["season"]+1
    prev=prev.rename(columns={
        "fantasy_points":"prior_points","age_years":"prior_age",
        "experience_years":"prior_experience","prior_production_percentile":"prior_pct"
    })
    prev=prev[["player_id","season","position","prior_points","prior_age","prior_experience","prior_pct"]]
    b=pvt.merge(prev,on=["player_id","season","position"],how="left")
    b["age"]=b["prior_age"]+1
    b["experience"]=b["prior_experience"]+1
    b["log_prior_points"]=np.log1p(b["prior_points"].clip(lower=0).fillna(0))
    b["log_y1"]=np.log1p(b["y1"].clip(lower=0))
    b["y1_pct"]=b.groupby(["season","position"])["y1"].rank(pct=True,method="average")
    denom=b["y1"].abs().clip(lower=25.0)
    b["y2_ratio"]=(b["y2"]/b["y1"].replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    b["y3_ratio"]=(b["y3"]/b["y1"].replace(0,np.nan)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-1,3)
    b["y2_delta"]=((b["y2"]-b["y1"])/denom).clip(-3,3)
    b["y3_delta"]=((b["y3"]-b["y1"])/denom).clip(-3,3)
    b["h3_pred"]=(
        np.maximum(0,b["y1"]-b["r1"])*b["w1"]+
        np.maximum(0,b["y2"]-b["r2"])*b["w2"]+
        np.maximum(0,b["y3"]-b["r3"])*b["w3"]
    )
    b["h3_actual"]=(
        np.maximum(0,b["a1"]-b["ar1"])*b["w1"]+
        np.maximum(0,b["a2"]-b["ar2"])*b["w2"]+
        np.maximum(0,b["a3"]-b["ar3"])*b["w3"]
    )
    return b

def points_map(player):
    return {(str(r.player_id),int(r.season)):float(r.fantasy_points) for r in player.itertuples()}

def lineup_replacement(player):
    out={}
    for season,g in player.groupby("season"):
        rec=[(str(r.player_id),str(r.position),max(0,float(r.fantasy_points))) for r in g.itertuples()]
        selected=[]; used=set()
        for pos,need in (("QB",12),("RB",24),("WR",36),("TE",12)):
            pool=sorted((x for x in rec if x[1]==pos),key=lambda x:x[2],reverse=True)
            for x in pool[:need]:
                selected.append(x); used.add(x[0])
        flex=sorted((x for x in rec if x[0] not in used and x[1] in {"RB","WR","TE"}),key=lambda x:x[2],reverse=True)
        for x in flex[:12]:
            selected.append(x); used.add(x[0])
        sf=sorted((x for x in rec if x[0] not in used),key=lambda x:x[2],reverse=True)
        for x in sf[:12]:
            selected.append(x); used.add(x[0])
        for pos in POSITIONS:
            vals=[x[2] for x in selected if x[1]==pos]
            if vals:
                out[(int(season),pos)]=min(vals)
    return out

def prep_matrix(df,med=None):
    X=df[list(FEATURES)].astype(float).copy()
    if med is None:
        med=X.median(numeric_only=True).fillna(0)
    return X.fillna(med).to_numpy(float),med

def fit_position_models(train,pos):
    tr=train[train.position==pos].copy()
    if len(tr)<40:
        return {"fallback":float(tr.actual.mean()) if len(tr) else 0}
    X,med=prep_matrix(tr)
    scaler=StandardScaler().fit(X)
    Z=scaler.transform(X)
    surv=(tr.actual.to_numpy(float)>0).astype(int)
    logit=LogisticRegression(C=1.0,solver="lbfgs",max_iter=2000,random_state=20260926).fit(Z,surv) if len(set(surv))>1 else None
    posrows=tr[tr.actual>0].copy()
    if len(posrows)>=20:
        Xp,_=prep_matrix(posrows,med)
        ridge_pos=Ridge(alpha=10).fit(scaler.transform(Xp),np.log1p(posrows.actual.to_numpy(float)))
    else:
        ridge_pos=None
    ridge_direct=Ridge(alpha=10).fit(Z,np.log1p(tr.actual.to_numpy(float)))
    return {
        "med":med,"scaler":scaler,"logit":logit,"ridge_pos":ridge_pos,"ridge_direct":ridge_direct,
        "surv_mean":float(surv.mean()),
        "positive_mean":float(posrows.actual.mean()) if len(posrows) else 0,
        "fallback":float(tr.actual.mean()),
    }

def predict_models(models,ev):
    if "scaler" not in models:
        v=max(0,models["fallback"])
        return np.repeat(v,len(ev)),np.repeat(v,len(ev))
    X,_=prep_matrix(ev,models["med"])
    Z=models["scaler"].transform(X)
    direct=np.expm1(models["ridge_direct"].predict(Z)).clip(0,600)
    ps=np.repeat(models["surv_mean"],len(ev)) if models["logit"] is None else models["logit"].predict_proba(Z)[:,1]
    cp=np.repeat(models["positive_mean"],len(ev)) if models["ridge_pos"] is None else np.expm1(models["ridge_pos"].predict(Z)).clip(0,600)
    return direct,(ps*cp).clip(0,600)

def build_predictions(base,player):
    pm=points_map(player)
    maxseason=int(player.season.max())
    records=[]
    for h in range(4,9):
        allh=base.copy()
        allh["target"]=allh["season"]+h-1
        allh["actual"]=[pm.get((pid,int(ts)),0) for pid,ts in zip(allh.player_id,allh.target)]
        allh=allh[allh.target<=maxseason].copy()
        for T in sorted(allh.season.unique()):
            ev=allh[allh.season==T].copy()
            train=allh[(allh.season<T)&(allh.target<T)].copy()
            if len(train)<200:
                continue
            ev["carry_y3"]=ev["y3"].clip(lower=0)
            ev["direct_ridge"]=0.0
            ev["two_part_state"]=0.0
            for pos in POSITIONS:
                mask=ev.position==pos
                if not mask.any():
                    continue
                d,t=predict_models(fit_position_models(train,pos),ev.loc[mask])
                ev.loc[mask,"direct_ridge"]=d
                ev.loc[mask,"two_part_state"]=t
            for r in ev.itertuples():
                for model in CANDIDATES:
                    records.append({
                        "season":int(r.season),"player_id":r.player_id,"position":r.position,
                        "horizon":h,"actual":float(r.actual),"model":model,"pred":float(getattr(r,model)),
                        "age":None if pd.isna(r.age) else float(r.age),
                        "experience":None if pd.isna(r.experience) else float(r.experience),
                    })
    return pd.DataFrame(records)

def model_metrics(pred):
    rows=[]
    for segment,folds in (("development",DEV_FOLDS),("holdout",HOLDOUT_FOLDS),("terminal",TERMINAL_FOLDS)):
        for h in range(4,9):
            if segment in ("development","holdout") and h>5:
                continue
            if segment=="terminal" and h<6:
                continue
            for model in CANDIDATES:
                x=pred[(pred.season.isin(folds))&(pred.horizon==h)&(pred.model==model)]
                if len(x):
                    rows.append({"segment":segment,"horizon":h,"position":"ALL","model":model,**metric(x)})
                for pos in POSITIONS:
                    xp=x[x.position==pos]
                    if len(xp):
                        rows.append({"segment":segment,"horizon":h,"position":pos,"model":model,**metric(xp)})
    return pd.DataFrame(rows)

def select_model(metrics):
    dev=metrics[(metrics.segment=="development")&(metrics.position=="ALL")&(metrics.horizon.isin([4,5]))]
    carry=dev[dev.model=="carry_y3"].set_index("horizon")
    scores=[]
    for model in ("direct_ridge","two_part_state"):
        x=dev[dev.model==model].set_index("horizon")
        ratios=[]
        for h in (4,5):
            ratios.extend([x.loc[h,"mae"]/carry.loc[h,"mae"],x.loc[h,"rmse"]/carry.loc[h,"rmse"]])
        scores.append((float(np.mean(ratios)),model))
    return sorted(scores)[0][1],sorted(scores)

def trailing_replacement(repl,season,pos):
    vals=[repl.get((s,pos)) for s in range(int(season)-3,int(season)) if repl.get((s,pos)) is not None]
    return float(statistics.median(vals)) if vals else 0.0

def economic_crosscheck(base,pred,player,selected):
    repl=lineup_replacement(player)
    chosen=pred[pred.model==selected].copy()
    chosen["pred_repl"]=[trailing_replacement(repl,s,p) for s,p in zip(chosen.season,chosen.position)]
    chosen["actual_repl"]=[repl.get((int(s+h-1),p),0.0) for s,h,p in zip(chosen.season,chosen.horizon,chosen.position)]
    chosen["pred_surplus"]=np.maximum(0,chosen.pred-chosen.pred_repl)
    chosen["actual_surplus"]=np.maximum(0,chosen.actual-chosen.actual_repl)
    idx=chosen.set_index(["season","player_id","horizon"])
    out=[]
    for segment,folds,maxh in (("holdout_h5",HOLDOUT_FOLDS,5),("terminal_h8",TERMINAL_FOLDS,8)):
        for d in DISCOUNT_SENSITIVITY:
            rec=[]
            for r in base[base.season.isin(folds)].itertuples():
                pv=float(r.h3_pred)
                av=float(r.h3_actual)
                ok=True
                for h in range(4,maxh+1):
                    key=(int(r.season),r.player_id,h)
                    if key not in idx.index:
                        ok=False
                        break
                    rr=idx.loc[key]
                    pv+=(d**(h-1))*float(rr.pred_surplus)
                    av+=(d**(h-1))*float(rr.actual_surplus)
                if ok:
                    rec.append({"pred":pv,"actual":av,"h3_pred":float(r.h3_pred)})
            dd=pd.DataFrame(rec)
            if len(dd):
                out.append({"segment":segment,"discount":d,"candidate":"extended","horizon":maxh,**metric(dd)})
                baseline=dd[["h3_pred","actual"]].rename(columns={"h3_pred":"pred"})
                out.append({"segment":segment,"discount":d,"candidate":"h3_only","horizon":maxh,**metric(baseline)})
    return pd.DataFrame(out)

POSIDX={p:i for i,p in enumerate(POSITIONS)}

def cap_rules():
    direct={"QB":12,"RB":24,"WR":36,"TE":12}
    out=[]
    for mask in range(1,1<<4):
        cap=sum(direct[POSITIONS[i]] for i in range(4) if mask&(1<<i))
        if any(mask&(1<<POSIDX[p]) for p in ("RB","WR","TE")):
            cap+=12
        cap+=12
        out.append((tuple(i for i in range(4) if mask&(1<<i)),cap))
    return tuple(out)
CAPS=cap_rules()

class Basis:
    def __init__(self):
        self.count=[0]*4
        self.by=[[] for _ in range(4)]
    def valid(self,c):
        return all(sum(c[i] for i in inds)<=cap for inds,cap in CAPS)
    def plan(self,pos):
        inc=POSIDX[pos]
        a=self.count.copy()
        a[inc]+=1
        if self.valid(a):
            return (None,None,None)
        best=None
        for o in range(4):
            if self.count[o]<=0:
                continue
            s=self.count.copy()
            s[o]-=1
            s[inc]+=1
            if self.valid(s):
                ow,oid=self.by[o][0]
                z=(ow,oid,o)
                if best is None or z<best:
                    best=z
        if best is None:
            return None
        ow,oid,o=best
        return (o,ow,oid)
    def marginal(self,pos,w,plan):
        w=max(0,float(w))
        if w<=0 or plan is None:
            return 0,None
        if plan[0] is None:
            return w,plan
        o,ow,oid=plan
        if w<=ow+1e-12:
            return 0,None
        return w-ow,plan
    def add(self,pid,pos,w,plan):
        d,r=self.marginal(pos,w,plan)
        w=max(0,float(w))
        inc=POSIDX[pos]
        if r is None:
            return
        if r[0] is None:
            bisect.insort(self.by[inc],(w,pid))
            self.count[inc]+=1
        else:
            o,ow,oid=r
            self.by[o].pop(0)
            self.count[o]-=1
            bisect.insort(self.by[inc],(w,pid))
            self.count[inc]+=1

def shapley(rows,seed):
    ids=[x[0] for x in rows]
    by={x[0]:(x[1],float(x[2])) for x in rows}
    sums={i:0.0 for i in ids}
    rng=random.Random(seed)
    for _ in range(SHAPLEY_PERMUTATIONS):
        order=ids[:]
        rng.shuffle(order)
        b=Basis()
        for pid in order:
            pos,w=by[pid]
            pl=b.plan(pos)
            d,_=b.marginal(pos,w,pl)
            sums[pid]+=d
            b.add(pid,pos,w,pl)
    return {i:sums[i]/SHAPLEY_PERMUTATIONS for i in ids}

def annual_pred(base,pred,season,h,selected):
    if h<=3:
        col={1:"y1",2:"y2",3:"y3"}[h]
        g=base[base.season==season]
        return {r.player_id:(r.position,float(getattr(r,col))) for r in g.itertuples()}
    g=pred[(pred.season==season)&(pred.horizon==h)&(pred.model==selected)]
    return {r.player_id:(r.position,float(r.pred)) for r in g.itertuples()}

def annual_actual(base,player,season,h):
    pm=points_map(player)
    g=base[base.season==season]
    if h<=3:
        col={1:"a1",2:"a2",3:"a3"}[h]
        return {r.player_id:(r.position,float(getattr(r,col))) for r in g.itertuples()}
    target=season+h-1
    return {r.player_id:(r.position,float(pm.get((r.player_id,target),0))) for r in g.itertuples()}

def horizon_phi(base,pred,player,season,maxh,selected):
    pp={}
    aa={}
    for h in range(1,maxh+1):
        p=annual_pred(base,pred,season,h,selected)
        a=annual_actual(base,player,season,h)
        ids=sorted(set(p)&set(a))
        pp[h]=shapley([(i,p[i][0],p[i][1]) for i in ids],SHAPLEY_SEED+season*20+h)
        aa[h]=shapley([(i,a[i][0],a[i][1]) for i in ids],SHAPLEY_SEED+season*20+100+h)
    return pp,aa

def shapley_diagnostics(base,pred,player,down,selected):
    bridge=[]
    cross=[]
    dist=[]
    sens=[]
    for season in (2021,2022):
        ph,_=horizon_phi(base,pred,player,season,3,selected)
        score={pid:ph[1].get(pid,0)+DISCOUNT*ph[2].get(pid,0)+(DISCOUNT**2)*ph[3].get(pid,0) for pid in ph[1]}
        d=down[down.season==season].copy()
        d["proxy"]=d.player_id.map(score)
        d=d.dropna(subset=["proxy"])
        bridge.append({
            "season":season,"n":len(d),
            "spearman_proxy_vs_current_i1_shapley":spearman(d.proxy,d.integrated_shapley),
            "mae_proxy_vs_current_i1_shapley":float(np.mean(np.abs(d.proxy-d.integrated_shapley))),
        })
    for season,maxh in ((2021,5),(2018,8)):
        ph,ah=horizon_phi(base,pred,player,season,maxh,selected)
        bg=base[base.season==season][["player_id","position","age"]].drop_duplicates().set_index("player_id")
        for dsc in DISCOUNT_SENSITIVITY:
            ps={pid:sum((dsc**(h-1))*ph[h].get(pid,0) for h in range(1,maxh+1)) for pid in ph[1]}
            av={pid:sum((dsc**(h-1))*ah[h].get(pid,0) for h in range(1,maxh+1)) for pid in ph[1]}
            dd=pd.DataFrame({"pred":list(ps.values()),"actual":[av.get(x,0) for x in ps]})
            sens.append({"season":season,"horizon":maxh,"discount":dsc,**metric(dd)})
        h3={pid:sum((DISCOUNT**(h-1))*ph[h].get(pid,0) for h in range(1,4)) for pid in ph[1]}
        hx={pid:sum((DISCOUNT**(h-1))*ph[h].get(pid,0) for h in range(1,maxh+1)) for pid in ph[1]}
        dd=pd.DataFrame({"player_id":list(hx),"h3":[h3[x] for x in hx],"hx":[hx[x] for x in hx]})
        dd["h3_rank"]=dd.h3.rank(method="min",ascending=False)
        dd["hx_rank"]=dd.hx.rank(method="min",ascending=False)
        dd["rank_delta"]=dd.h3_rank-dd.hx_rank
        dd=dd.join(bg,on="player_id")
        ordered=dd.reindex(dd.rank_delta.abs().sort_values(ascending=False).index).head(40)
        for rr in ordered.itertuples():
            cross.append({
                "season":season,"horizon":maxh,"player_id":rr.player_id,"position":rr.position,
                "age":None if pd.isna(rr.age) else float(rr.age),
                "h3_value":float(rr.h3),"horizon_value":float(rr.hx),
                "h3_rank":float(rr.h3_rank),"horizon_rank":float(rr.hx_rank),
                "rank_delta":float(rr.rank_delta),
            })
        for label,vals in (("H1",{pid:ph[1].get(pid,0) for pid in ph[1]}),("H3",h3),(f"H{maxh}",hx)):
            z=pd.DataFrame({"player_id":list(vals),"value":[vals[x] for x in vals]}).join(bg,on="player_id")
            z["rank"]=z.value.rank(method="min",ascending=False)
            for pos in POSITIONS:
                xp=z[z.position==pos]
                if len(xp):
                    dist.append({
                        "season":season,"horizon_label":label,"position":pos,"n":len(xp),
                        "median":float(xp.value.median()),"p90":float(xp.value.quantile(.9)),
                        "iqr":float(xp.value.quantile(.75)-xp.value.quantile(.25)),
                        "top25_share":float((xp["rank"]<=25).sum()/max(1,(z["rank"]<=25).sum())),
                        "top50_share":float((xp["rank"]<=50).sum()/max(1,(z["rank"]<=50).sum())),
                        "top100_share":float((xp["rank"]<=100).sum()/max(1,(z["rank"]<=100).sum())),
                    })
    return pd.DataFrame(bridge),pd.DataFrame(cross),pd.DataFrame(dist),pd.DataFrame(sens)

def uncertainty_table(pred,selected):
    z=pred[
        (pred.model==selected)&(
            ((pred.season.isin(HOLDOUT_FOLDS))&(pred.horizon.isin([4,5])))|
            ((pred.season.isin(TERMINAL_FOLDS))&(pred.horizon.isin([6,7,8])))
        )
    ]
    rows=[]
    prev={}
    for h in range(4,9):
        for pos in ("ALL",)+POSITIONS:
            x=z[z.horizon==h] if pos=="ALL" else z[(z.horizon==h)&(z.position==pos)]
            if len(x):
                raw=metric(x)["rmse"]
                mono=max(prev.get(pos,0),raw)
                prev[pos]=mono
                rows.append({
                    "horizon":h,"position":pos,"n":len(x),
                    "oot_residual_rmse":raw,"monotone_uncertainty_floor":mono,
                })
    return pd.DataFrame(rows)

def selection_gate(metrics,selected):
    hold=metrics[(metrics.segment=="holdout")&(metrics.position=="ALL")&(metrics.horizon.isin([4,5]))]
    s=hold[hold.model==selected].set_index("horizon")
    c=hold[hold.model=="carry_y3"].set_index("horizon")
    imp=[]
    for h in (4,5):
        imp.append({
            "horizon":h,
            "mae_improvement":1-s.loc[h,"mae"]/c.loc[h,"mae"],
            "rmse_improvement":1-s.loc[h,"rmse"]/c.loc[h,"rmse"],
            "spearman_delta":s.loc[h,"spearman"]-c.loc[h,"spearman"],
        })
    pos=metrics[(metrics.segment=="holdout")&(metrics.horizon.isin([4,5]))&(metrics.position!="ALL")]
    bad=[]
    for h in (4,5):
        for p in POSITIONS:
            a=pos[(pos.horizon==h)&(pos.position==p)&(pos.model==selected)]
            b=pos[(pos.horizon==h)&(pos.position==p)&(pos.model=="carry_y3")]
            if len(a) and len(b) and float(a.iloc[0].rmse)>1.15*float(b.iloc[0].rmse):
                bad.append(f"{p}_Y{h}")
    return {
        "passes":all(x["rmse_improvement"]>0 for x in imp) and all(x["mae_improvement"]>-0.02 for x in imp) and not bad,
        "improvements":imp,
        "position_catastrophes":bad,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model-a-rows",required=True)
    ap.add_argument("--qb-results",required=True)
    ap.add_argument("--player-seasons",required=True)
    ap.add_argument("--shapley-rows",required=True)
    args=ap.parse_args()

    OUT.mkdir(parents=True,exist_ok=True)
    m,q,player,down=load_inputs(args)
    m,changed=integrate_qb(m,q)
    base=build_base(m,player)
    pred=build_predictions(base,player)
    metrics=model_metrics(pred)
    selected,scores=select_model(metrics)
    gate=selection_gate(metrics,selected)
    econ=economic_crosscheck(base,pred,player,selected)
    unc=uncertainty_table(pred,selected)
    bridge,cross,dist,sens=shapley_diagnostics(base,pred,player,down,selected)

    metrics.to_csv(OUT/"FORECAST_HORIZON_METRICS.csv",index=False)
    econ.to_csv(OUT/"VALUE_HORIZON_METRICS.csv",index=False)
    unc.to_csv(OUT/"UNCERTAINTY_BY_HORIZON.csv",index=False)
    bridge.to_csv(OUT/"SHAPLEY_BRIDGE_VALIDATION.csv",index=False)
    cross.to_csv(OUT/"HISTORICAL_CROSSOVERS.csv",index=False)
    dist.to_csv(OUT/"POSITION_DISTRIBUTIONS.csv",index=False)
    sens.to_csv(OUT/"DISCOUNT_SENSITIVITY.csv",index=False)

    result={
        "study":"bounded long-horizon Intrinsic term-structure research",
        "authority":"research_only_no_production_change",
        "production_baseline":{
            "coordinate":"intrinsic-shapley-i1-v1","horizon_years":3,"discount":DISCOUNT,
            "oracle_holdout_rows":int(len(down)),
            "oracle_seasons":sorted(int(x) for x in down.season.unique()),
        },
        "historical_bridge":{
            "method":"same frozen lineup-capacity Shapley economy applied to governed PIT Model-A expected point paths",
            "permutations":SHAPLEY_PERMUTATIONS,
            "rows":bridge.to_dict("records"),
            "authority_limit":"research proxy only",
        },
        "forecast_candidate_selection":{
            "frozen_candidates":CANDIDATES,
            "development_folds":DEV_FOLDS,
            "selection_scores":scores,
            "selected":selected,
            "holdout_folds":HOLDOUT_FOLDS,
            "gate":gate,
        },
        "holdout_forecast_metrics":metrics[(metrics.segment=="holdout")&(metrics.position=="ALL")&(metrics.model==selected)].to_dict("records"),
        "terminal_forecast_metrics":metrics[(metrics.segment=="terminal")&(metrics.position=="ALL")&(metrics.model==selected)].to_dict("records"),
        "uncertainty_contract":{
            "basis":"empirical OOT residual RMSE by horizon/position",
            "monotone_envelope_required":True,
        },
        "economic_crosscheck":{
            "coordinate":"replacement-adjusted surplus; secondary only",
            "rows":econ.to_dict("records"),
        },
        "discount_sensitivity":{
            "discounts":DISCOUNT_SENSITIVITY,
            "rows":sens.to_dict("records"),
        },
        "qb_rows_replaced_with_governed_career_state":changed,
        "pit_rules":{
            "features":"prior-season football outcomes plus governed PIT Y1-Y3 forecasts only",
            "fit":"training S,H eligible only when S+H-1 < target fold T",
            "no_current_player_inspection_before_selection":True,
            "no_market_owner_team_utility_inputs":True,
        },
    }
    (OUT/"RESULTS.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")

    lines=[
        "# Long-Horizon Intrinsic Term-Structure Research","",
        "Status: historical model-selection pass complete; current-player shadows remain post-selection.","",
        "## Authority baseline","",
        "Current three-year authority remains intrinsic-shapley-i1-v1 with the frozen 0.85 annual discount. This study does not alter it.","",
        "The long-history extension uses the same lineup-capacity Shapley economy on the older governed PIT deep-Forecast panel as a research bridge; it is not current production authority.","",
        "## Frozen model-family selection","",
        f"Selected long-horizon Forecast family: **{selected}**.",
        f"Untouched Y4/Y5 holdout gate: **{'PASS' if gate['passes'] else 'FAIL'}**.","",
    ]
    for x in gate["improvements"]:
        lines.append(
            f"- Y{x['horizon']}: MAE improvement vs Y3 carry {x['mae_improvement']:.1%}; "
            f"RMSE improvement {x['rmse_improvement']:.1%}; Spearman delta {x['spearman_delta']:+.3f}."
        )
    lines+=["","## Shapley bridge"]
    for x in bridge.to_dict("records"):
        lines.append(
            f"- {x['season']}: n={x['n']}, Spearman proxy vs current I1-Shapley="
            f"{x['spearman_proxy_vs_current_i1_shapley']:.3f}, MAE={x['mae_proxy_vs_current_i1_shapley']:.2f}."
        )
    lines+=["","## Uncertainty",
        "Long-horizon uncertainty is estimated from OOT residual RMSE by horizon/position and must use a monotone non-decreasing envelope.","",
        "## Authority boundary",
        "Replacement-surplus diagnostics are secondary only. Current Shapley Intrinsic is not replaced, rescaled or redefined. No production code changes are authorized.","",
        "## Current-player discipline",
        "No current named-player ranks were inspected before the historical candidate family was frozen."
    ]
    (OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print((OUT/"REPORT.md").read_text())
    print("RESULT_JSON_BEGIN")
    print(json.dumps(result,sort_keys=True))
    print("RESULT_JSON_END")
    if not gate["passes"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()

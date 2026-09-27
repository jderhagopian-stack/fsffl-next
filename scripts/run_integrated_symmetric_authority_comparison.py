from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd

MODELS={"B0":"b0_","B1":"b1_","I1":"i1_","I2":"i2_"}
STATES=("out","depth","usable","starter","premium","elite")
SEED=20260927

def crps(vals,probs,y):
    v=np.asarray(vals,float);p=np.asarray(probs,float);p=p/p.sum()
    return float(np.sum(p*np.abs(v-y))-.5*np.sum(p[:,None]*p[None,:]*np.abs(v[:,None]-v[None,:])))

def prepare(df):
    q=df[df.factual_state.notna()].copy()
    q["player_id"]=q.player_id.astype(str)
    for n,p in MODELS.items():
        probs=q[[p+"p_"+s for s in STATES]].to_numpy(float)
        idx=np.array([STATES.index(s) for s in q.factual_state.astype(str)])
        oh=np.eye(6)[idx]
        q[n+"_state_brier"]=np.sum((probs-oh)**2,axis=1)
        q[n+"_state_logloss"]=-np.log(np.clip(probs[np.arange(len(q)),idx],1e-12,1))
        y=q.factual_persist.astype(float).to_numpy();pa=q[p+"persist"].to_numpy(float)
        q[n+"_persist_brier"]=(pa-y)**2
        q[n+"_persist_logloss"]=-(y*np.log(np.clip(pa,1e-12,1))+(1-y)*np.log(np.clip(1-pa,1e-12,1)))
        e=q[p+"points"].to_numpy(float)-q.actual_points.to_numpy(float)
        q[n+"_abs_error"]=np.abs(e);q[n+"_sq_error"]=e*e;q[n+"_bias_error"]=e
        if n in ("I1","I2"):
            means=q[[p+"mean_"+s for s in STATES]].to_numpy(float)
            q[n+"_crps"]=[crps(means[i],probs[i],float(q.iloc[i].actual_points)) for i in range(len(q))]
    return q

def summary(g,n):
    p=MODELS[n];pred=g[p+"points"].to_numpy(float);y=g.actual_points.to_numpy(float)
    d={
        "n":len(g),"mae":float(np.mean(np.abs(pred-y))),
        "rmse":float(np.sqrt(np.mean((pred-y)**2))),"bias":float(np.mean(pred-y)),
        "spearman":float(pd.Series(pred).corr(pd.Series(y),method="spearman")) if len(g)>1 else None,
        "persist_brier":float(g[n+"_persist_brier"].mean()),
        "persist_logloss":float(g[n+"_persist_logloss"].mean()),
        "state_brier":float(g[n+"_state_brier"].mean()),
        "state_logloss":float(g[n+"_state_logloss"].mean()),
    }
    d["crps"]=float(g[n+"_crps"].mean()) if n in ("I1","I2") else None
    return d

def weights(g,rng):
    sy=pd.Categorical(g.source_season).codes;pl=pd.Categorical(g.player_id).codes
    return rng.exponential(1,int(sy.max()+1))[sy]*rng.exponential(1,int(pl.max()+1))[pl]

def boot(g,a,b,metric,reps=3000):
    if metric=="mae":d=g[b+"_abs_error"].to_numpy(float)-g[a+"_abs_error"].to_numpy(float)
    elif metric=="rmse":d=g[b+"_sq_error"].to_numpy(float)-g[a+"_sq_error"].to_numpy(float)
    else:d=g[b+"_"+metric].to_numpy(float)-g[a+"_"+metric].to_numpy(float)
    rng=np.random.default_rng(SEED+sum(map(ord,a+b+metric)));vals=[]
    for _ in range(reps):
        w=weights(g,rng);vals.append(float(np.sum(w*d)/np.sum(w)))
    lo,hi=np.quantile(vals,[.025,.975])
    return float(d.mean()),float(lo),float(hi)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rows",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    q=prepare(pd.read_csv(args.rows))
    sums=[]
    groups=[("ALL",q)]
    for h in sorted(q.horizon.unique()):groups.append((f"H{int(h)}",q[q.horizon==h]))
    for h in sorted(q.horizon.unique()):
        for p in ("QB","RB","WR","TE"):groups.append((f"H{int(h)}_{p}",q[(q.horizon==h)&(q.position==p)]))
    for label,g in groups:
        if len(g)<30:continue
        for n in MODELS:sums.append({"group":label,"model":n,**summary(g,n)})
    pairs=[]
    names=list(MODELS)
    for h in sorted(q.horizon.unique()):
        g=q[q.horizon==h]
        for i,a in enumerate(names):
            for b in names[i+1:]:
                for met in ("mae","state_brier","state_logloss","persist_brier","persist_logloss"):
                    gain,lo,hi=boot(g,a,b,met)
                    pairs.append({"horizon":int(h),"position":"ALL","a":a,"b":b,"metric":met,"gain_a_over_b":gain,"ci_low":lo,"ci_high":hi})
                for p in ("QB","RB","WR","TE"):
                    z=g[g.position==p]
                    if len(z)<100:continue
                    for met in ("mae","state_brier"):
                        gain,lo,hi=boot(z,a,b,met,reps=1500)
                        pairs.append({"horizon":int(h),"position":p,"a":a,"b":b,"metric":met,"gain_a_over_b":gain,"ci_low":lo,"ci_high":hi})
        # I1/I2 CRPS is directly symmetric.
        gain,lo,hi=boot(g,"I1","I2","crps")
        pairs.append({"horizon":int(h),"position":"ALL","a":"I1","b":"I2","metric":"crps","gain_a_over_b":gain,"ci_low":lo,"ci_high":hi})
    pd.DataFrame(sums).to_csv(args.output_dir/"INTEGRATED_SYMMETRIC_SUMMARY.csv",index=False)
    pd.DataFrame(pairs).to_csv(args.output_dir/"INTEGRATED_PAIRWISE_UNCERTAINTY.csv",index=False)
    result={
      "study":"integrated-family-symmetric-authority-replay",
      "authority":"research_only_no_production_change",
      "rows":len(q),"source_seasons":sorted(int(x) for x in q.source_season.unique()),
      "models":list(MODELS),
      "crps_available":["I1","I2"],
      "crps_unavailable_reason":{"B0":"historical control exposes scalar expected points without coherent state-conditioned magnitude support","B1":"persistence-first control changes probabilities while retaining scalar prior points; no coherent state-conditioned magnitude distribution persisted"},
      "guards":{"model_math_changed":False,"metadata_export_only":True,"production_changed":False}
    }
    (args.output_dir/"INTEGRATED_SYMMETRIC_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()

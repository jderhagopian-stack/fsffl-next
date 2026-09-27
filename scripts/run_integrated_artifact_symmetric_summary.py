from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd

MODELS={"B0":"b0_","B1":"b1_","I1":"i1_","I2":"i2_"}
LOSSES=("pb","pll","sb","sll","ub","stb","prb","ae","csb")

def summarize(g,name,p):
    x=g[g.factual_state.notna()].copy()
    pred=pd.to_numeric(x[p+"points"],errors="coerce")
    y=pd.to_numeric(x.actual_points,errors="coerce")
    return {
      "n":int(len(x)),
      "persist_brier":float(pd.to_numeric(x[p+"pb"],errors="coerce").mean()),
      "persist_logloss":float(pd.to_numeric(x[p+"pll"],errors="coerce").mean()),
      "state_brier":float(pd.to_numeric(x[p+"sb"],errors="coerce").mean()),
      "state_logloss":float(pd.to_numeric(x[p+"sll"],errors="coerce").mean()),
      "useful_brier":float(pd.to_numeric(x[p+"ub"],errors="coerce").mean()),
      "starter_brier":float(pd.to_numeric(x[p+"stb"],errors="coerce").mean()),
      "premium_brier":float(pd.to_numeric(x[p+"prb"],errors="coerce").mean()),
      "mae":float(pd.to_numeric(x[p+"ae"],errors="coerce").mean()),
      "bias":float(pd.to_numeric(x[p+"bias"],errors="coerce").mean()),
      "conditional_state_brier":float(pd.to_numeric(x[p+"csb"],errors="coerce").dropna().mean()),
      "spearman":float(pred.corr(y,method="spearman")),
      "factual_out_rate":float((x.factual_state=="out").mean()),
      "pred_out_rate":float((1-pd.to_numeric(x[p+"persist"],errors="coerce")).mean()),
    }

def paired_rows(g,a,b,metric):
    pa=MODELS[a];pb=MODELS[b]
    col={"mae":"ae","persist_brier":"pb","persist_logloss":"pll","state_brier":"sb","state_logloss":"sll","useful_brier":"ub","starter_brier":"stb","premium_brier":"prb","conditional_state_brier":"csb"}[metric]
    aa=pd.to_numeric(g[pa+col],errors="coerce")
    bb=pd.to_numeric(g[pb+col],errors="coerce")
    ok=aa.notna()&bb.notna()
    d=bb[ok].to_numpy(float)-aa[ok].to_numpy(float) # positive => A lower/better
    if len(d)==0:return None
    # Paired row bootstrap is a sensitivity interval only: repeated player identity was not persisted.
    rng=np.random.default_rng(20260927+sum(map(ord,a+b+metric)))
    vals=[]
    n=len(d)
    for _ in range(3000):
      idx=rng.integers(0,n,n);vals.append(float(d[idx].mean()))
    lo,hi=np.quantile(vals,[.025,.975])
    return {"n":n,"gain_a_over_b":float(d.mean()),"row_bootstrap_ci95":[float(lo),float(hi)],"uncertainty_class":"paired_row_sensitivity_not_player_clustered"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rows",type=Path,required=True)
    ap.add_argument("--result-json",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(args.rows)
    prior=json.loads(args.result_json.read_text())
    res=df[df.factual_state.notna()].copy()
    summaries=[]
    groups=[("ALL",res)]
    for h in sorted(res.horizon.unique()):groups.append((f"H{int(h)}",res[res.horizon==h]))
    for h in sorted(res.horizon.unique()):
      for pos in ("QB","RB","WR","TE"):
        groups.append((f"H{int(h)}_{pos}",res[(res.horizon==h)&(res.position==pos)]))
    for label,g in groups:
      if len(g)<30:continue
      for n,p in MODELS.items():summaries.append({"group":label,"model":n,**summarize(g,n,p)})
    pairs=[]
    names=list(MODELS)
    for h in sorted(res.horizon.unique()):
      g=res[res.horizon==h]
      for i,a in enumerate(names):
        for b in names[i+1:]:
          for metric in ("mae","persist_brier","persist_logloss","state_brier","state_logloss","useful_brier","starter_brier","premium_brier","conditional_state_brier"):
            z=paired_rows(g,a,b,metric)
            if z:pairs.append({"horizon":int(h),"position":"ALL","a":a,"b":b,"metric":metric,**z})
          for pos in ("QB","RB","WR","TE"):
            q=g[g.position==pos]
            if len(q)<100:continue
            for metric in ("mae","persist_brier","state_brier"):
              z=paired_rows(q,a,b,metric)
              if z:pairs.append({"horizon":int(h),"position":pos,"a":a,"b":b,"metric":metric,**z})
    pd.DataFrame(summaries).to_csv(args.output_dir/"INTEGRATED_ARTIFACT_SYMMETRIC_SUMMARY.csv",index=False)
    pd.DataFrame(pairs).to_csv(args.output_dir/"INTEGRATED_ARTIFACT_PAIRWISE.csv",index=False)
    result={
      "study":"integrated-artifact-symmetric-authority",
      "source_artifact":"10422858437",
      "source_digest":"sha256:c80934cab0275d67281419b7fb8e49331b6c2e2679b90b930c6789da333d9600",
      "source_head":"c12402df1b7fa0bfbb3d994bdcf791d80e103a0c",
      "rows_total":int(len(df)),"rows_factual_resolved":int(len(res)),
      "source_seasons":sorted(int(x) for x in df.season.unique()),
      "horizons":sorted(int(x) for x in df.horizon.unique()),
      "historical_selected_label":prior.get("holdout",{}).get("selected"),
      "historical_selection_not_authority":True,
      "common_exact_row_comparison":True,
      "player_cluster_uncertainty_recoverable":False,
      "reason":"historical OOS artifact did not persist player_id; no row-order identity inference permitted",
      "crps_recoverable":False,
      "crps_reason":"historical artifact persisted proper state scores and scalar expected points but not the full state-probability/state-mean vectors",
      "production_changed":False,
    }
    (args.output_dir/"INTEGRATED_ARTIFACT_SYMMETRIC_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()

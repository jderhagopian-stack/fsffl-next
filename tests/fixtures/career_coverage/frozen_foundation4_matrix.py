# Frozen matrix oracle from accepted commit be2541a496227b33c12c755f576843dc4ab5a0bb.
import numpy as np
import pandas as pd

CATEGORICAL = (
    "college_conference","trajectory_state","innovation_state","volatility_band",
    "production_pattern","career_stage","production_tier","prior_direction",
)

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

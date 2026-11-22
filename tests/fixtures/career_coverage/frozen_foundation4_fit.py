# Verbatim learned-fit oracle: accepted be2541a496227b33c12c755f576843dc4ab5a0bb.
# Synthetic fixture features; production model/route code is not imported here.
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from tests.fixtures.career_coverage.frozen_foundation4_matrix import matrix
POSITIONS = ("QB", "RB", "WR", "TE")
RANDOM_SEED = 20260926
MIN_TRAIN_ROWS = 80
MIN_POSITIVE_ROWS = 25
FEATURE_SETS = {"fixture": ("value", "other", "trajectory_state")}
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

from __future__ import annotations
import json, math, importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import minimize

OUT=Path('/mnt/data/fsffl_partial_pooling_challenger_20260919'); OUT.mkdir(exist_ok=True)
PANEL=Path('/mnt/data/fsffl_phase2/future-state-phase2/phase2_player_season_panel.csv')
HIST=Path('/mnt/data/fsffl_diag/historical_predictions.csv')
MODPATH='/mnt/data/fsffl_revalidate_fit.py'
ORIGINS=list(range(2014,2023)); STATES=['depth','usable','starter','premium','elite']; UPPER={'starter','premium','elite'}; LOWER={'depth','usable'}
A=math.log(1.5); LAM_SHARED=.05; LAM_DEV=.05*(352/167)

spec=importlib.util.spec_from_file_location('revalfit',MODPATH); mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
panel=pd.read_csv(PANEL); rows=mod.build_rows(panel,2023); hist=pd.read_csv(HIST)

def crps(probs,support,y):
    p=np.asarray(probs,float); x=np.asarray(support,float); y=float(y)
    return float(np.sum(p*np.abs(x-y))-.5*np.sum((p[:,None]*p[None,:])*np.abs(x[:,None]-x[None,:])))
def qdisc(probs,support,q):
    p=np.asarray(probs,float); x=np.asarray(support,float); o=np.argsort(x); p=p[o]; x=x[o]; c=np.cumsum(p); return float(x[min(np.searchsorted(c,q),len(x)-1)])
def multipliers(p,u):
    a0,a1,d0,d1=p; z=2*(float(u)-.5); gu=a0+a1*z; gl=gu+d0+d1*z; return math.exp(A*math.tanh(gu)),math.exp(A*math.tanh(gl))
def fit_cal(train_active,d1):
    u=[]; lower=[]; y=[]
    for r in train_active.itertuples(index=False):
        m=max(1e-9,float(d1.predict_state(r,str(r.target_state))))
        u.append(float(r.source_percentile)); lower.append(str(r.target_state) in LOWER); y.append(math.log(max(1e-9,float(r.target_points))/m))
    u=np.asarray(u); lower=np.asarray(lower); y=np.asarray(y); z=2*(u-.5)
    def obj(p):
        gu=p[0]+p[1]*z; gl=gu+p[2]+p[3]*z; pred=A*np.tanh(np.where(lower,gl,gu))
        return float(np.mean((y-pred)**2)+LAM_SHARED*(p[0]**2+p[1]**2)+LAM_DEV*(p[2]**2+p[3]**2))
    cons=[{'type':'ineq','fun':lambda p:-(p[2]+p[3])},{'type':'ineq','fun':lambda p:-(p[2]-p[3])}]
    res=minimize(obj,np.zeros(4),method='SLSQP',constraints=cons,options={'maxiter':2000,'ftol':1e-12,'disp':False})
    p=np.asarray(res.x,float); cplus=p[2]+p[3]; cminus=p[2]-p[3]
    return p,dict(success=bool(res.success),message=str(res.message),objective=float(res.fun),n_train_active=len(train_active),constraint_d0_plus_d1=float(cplus),constraint_d0_minus_d1=float(cminus),binding_plus=bool(abs(cplus)<=1e-6),binding_minus=bool(abs(cminus)<=1e-6),fit_ok=bool(res.success and cplus<=1e-8 and cminus<=1e-8))

records=[]; fitrows=[]; parity=[]
for t in ORIGINS:
    train=rows[(rows.source_season<t)&(rows.source_season+3<=t-1)&(rows.horizon==3)].copy()
    d1=mod.ProductionModel('D1',3).fit(train)
    tr=train[(train.position=='RB')&(train.career_stage=='developmental')&(train.target_state!='out')].copy()
    p,meta=fit_cal(tr,d1); fitrows.append({'origin':t,'a0':p[0],'a1':p[1],'d0':p[2],'d1':p[3],**meta})
    if not meta['fit_ok']: raise RuntimeError((t,meta))
    test=rows[(rows.source_season==t)&(rows.horizon==3)&(rows.position=='RB')&(rows.career_stage=='developmental')].copy().sort_values('player_id')
    hh=hist[(hist.source_season==t)&(hist.horizon==3)&(hist.position=='RB')&(hist.career_stage=='developmental')].copy().sort_values('player_id')
    mm=test.merge(hh,on=['source_season','player_id','position','horizon'],suffixes=('_panel','_hist'),how='outer',indicator=True)
    pdiffs={}
    for fld in ['source_points','source_percentile','target_points']:
        pdiffs[fld]=float(np.nanmax(np.abs(pd.to_numeric(mm[fld+'_panel'],errors='coerce')-pd.to_numeric(mm[fld+'_hist'],errors='coerce'))))
    means_diffs={s:[] for s in STATES}
    for r in test.itertuples(index=False):
        hr=hh[hh.player_id.astype(str)==str(r.player_id)].iloc[0]
        for s in STATES: means_diffs[s].append(abs(float(d1.predict_state(r,s))-float(hr[f'd1_mean_{s}'])))
    parity.append({'origin':t,'rows_panel':len(test),'rows_hist':len(hh),'left_only':int((mm._merge=='left_only').sum()),'right_only':int((mm._merge=='right_only').sum()),**{f'maxdiff_{k}':v for k,v in pdiffs.items()},**{f'maxdiff_d1_mean_{s}':float(max(v) if v else 0.) for s,v in means_diffs.items()}})
    # Evaluate using exact durable historical D1 probabilities and means.
    for _,r in hh.iterrows():
        mu,ml=multipliers(p,float(r.source_percentile)); dmeans={s:float(r[f'd1_mean_{s}']) for s in STATES}; cmeans={s:dmeans[s]*(ml if s in LOWER else mu) for s in STATES}
        probs=[float(r.p_out)]+[float(r[f'p_{s}']) for s in STATES]; ds=[0.]+[dmeans[s] for s in STATES]; cs=[0.]+[cmeans[s] for s in STATES]; y=float(r.target_points)
        rec={'origin':t,'source_season':t,'player_id':str(r.player_id),'source_percentile':float(r.source_percentile),'source_points':float(r.source_points),'target_points':y,'target_state':str(r.target_state),'upper_multiplier':mu,'lower_multiplier':ml}
        rec['d1_crps']=crps(probs,ds,y); rec['challenger_crps']=crps(probs,cs,y); rec['crps_gain']=rec['d1_crps']-rec['challenger_crps']
        rec['d1_expected']=float(np.dot(probs,ds)); rec['challenger_expected']=float(np.dot(probs,cs)); rec['d1_abs_error']=abs(rec['d1_expected']-y); rec['challenger_abs_error']=abs(rec['challenger_expected']-y); rec['mae_gain']=rec['d1_abs_error']-rec['challenger_abs_error']
        for s,pr in zip(['out']+STATES,probs): rec[f'p_{s}']=pr
        for s in STATES: rec[f'd1_mean_{s}']=dmeans[s]; rec[f'challenger_mean_{s}']=cmeans[s]
        for pref,supp in [('d1',ds),('challenger',cs)]:
            q10=qdisc(probs,supp,.10); q25=qdisc(probs,supp,.25); q75=qdisc(probs,supp,.75); q90=qdisc(probs,supp,.90)
            rec[f'{pref}_q10']=q10; rec[f'{pref}_q25']=q25; rec[f'{pref}_q75']=q75; rec[f'{pref}_q90']=q90; rec[f'{pref}_cov10_90']=float(q10<=y<=q90); rec[f'{pref}_cov25_75']=float(q25<=y<=q75)
        if str(r.target_state)!='out':
            s=str(r.target_state); rec['realized_group']='lower' if s in LOWER else 'upper'; denom=max(1e-9,float(r.source_points)); rr=y/denom; dr=dmeans[s]/denom; cr=cmeans[s]/denom
            rec.update(realized_retention=rr,d1_realized_state_retention=dr,challenger_realized_state_retention=cr,d1_ret_bias=dr-rr,challenger_ret_bias=cr-rr,d1_point_bias_realized_state=dmeans[s]-y,challenger_point_bias_realized_state=cmeans[s]-y)
        else:
            rec.update(realized_group='out',realized_retention=np.nan,d1_realized_state_retention=np.nan,challenger_realized_state_retention=np.nan,d1_ret_bias=np.nan,challenger_ret_bias=np.nan,d1_point_bias_realized_state=np.nan,challenger_point_bias_realized_state=np.nan)
        records.append(rec)

row=pd.DataFrame(records).sort_values(['origin','player_id']).reset_index(drop=True)
fits=pd.DataFrame(fitrows); parity=pd.DataFrame(parity)
row.to_csv(OUT/'ROW_LEVEL_EVALUATION.csv',index=False); fits.to_csv(OUT/'ORIGIN_SPECIFIC_FITTED_PARAMETERS.csv',index=False); parity.to_csv(OUT/'EXACT_D1_REPLAY_PARITY.csv',index=False)
print('rows',len(row),'active',(row.target_state!='out').sum())
print(fits.to_string(index=False))
print('parity max',parity.filter(like='maxdiff_').max().max())
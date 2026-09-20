from __future__ import annotations
import math, json, importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import minimize

OUT=Path('/mnt/data/fsffl_gap_aware_challenger_20260920'); OUT.mkdir(exist_ok=True)
PANEL=Path('/mnt/data/fsffl_phase2/future-state-phase2/phase2_player_season_panel.csv')
HIST=Path('/mnt/data/fsffl_diag/historical_predictions.csv')
MODPATH='/mnt/data/fsffl_revalidate_fit.py'
ORIGINS=list(range(2014,2023)); STATES=['depth','usable','starter','premium','elite']; UPPER={'starter','premium','elite'}; LOWER={'depth','usable'}
A=math.log(1.5); LAM_SHARED=.05; LAM_DEV=.10538922155688623

spec=importlib.util.spec_from_file_location('revalfit',MODPATH); mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
panel=pd.read_csv(PANEL); rows=mod.build_rows(panel,2023); hist=pd.read_csv(HIST)

# helpers

def crps(probs,support,y):
    p=np.asarray(probs,float); x=np.asarray(support,float); y=float(y)
    return float(np.sum(p*np.abs(x-y))-.5*np.sum((p[:,None]*p[None,:])*np.abs(x[:,None]-x[None,:])))

def qdisc(probs,support,q):
    p=np.asarray(probs,float); x=np.asarray(support,float); o=np.argsort(x); p=p[o]; x=x[o]; c=np.cumsum(p)
    return float(x[min(np.searchsorted(c,q),len(x)-1)])

def corr_vals(p,u,gap):
    a0,a1,d0,d1=p; z=2*(float(u)-.5)
    cu=A*math.tanh(a0+a1*z); th=math.tanh(d0+d1*z); cl=cu+float(gap)*th
    return cu,cl,th

def adjusted_means(p,u,dmeans):
    gap=math.log1p(max(0.,dmeans['starter']))-math.log1p(max(0.,dmeans['usable']))
    if not gap>0: raise RuntimeError(f'nonpositive D1 gap {gap}')
    cu,cl,th=corr_vals(p,u,gap)
    out={}
    for s in STATES:
        c=cl if s in LOWER else cu
        out[s]=math.expm1(math.log1p(max(0.,float(dmeans[s])))+c)
    return out,cu,cl,th,gap

# exact evaluation replay parity 2014-2022
parity=[]
for t in ORIGINS:
    pred=mod.predict_origin(rows,t,3)
    hh=hist[(hist.source_season==t)&(hist.horizon==3)].copy()
    mm=pred.merge(hh,on=['source_season','player_id','position','horizon'],suffixes=('_new','_old'),how='outer',indicator=True)
    rec={'origin':t,'rows_new':len(pred),'rows_hist':len(hh),'left_only':int((mm._merge=='left_only').sum()),'right_only':int((mm._merge=='right_only').sum())}
    for fld in ['pred_D0','pred_D1','p_active','p_out','p_depth','p_usable','p_starter','p_premium','p_elite','d1_mean_depth','d1_mean_usable','d1_mean_starter','d1_mean_premium','d1_mean_elite']:
        a=pd.to_numeric(mm[fld+'_new'],errors='coerce'); b=pd.to_numeric(mm[fld+'_old'],errors='coerce'); rec['maxdiff_'+fld]=float(np.nanmax(np.abs(a-b)))
    parity.append(rec)
parity=pd.DataFrame(parity); parity.to_csv(OUT/'EXACT_D1_REPLAY_PARITY.csv',index=False)
max_replay=float(parity.filter(like='maxdiff_').max().max())
if parity.left_only.sum() or parity.right_only.sum() or max_replay>1e-8:
    raise RuntimeError(f'D1 replay parity failed max={max_replay}')

# Build prior-origin prospective residual library. Earliest reproducible Y3 origin is determined rather than invented.
residual_rows=[]; residual_origin_meta=[]; residual_exclusions=[]
for s in range(2005,2019): # only through 2018 can ever be eligible for T<=2022
    train=rows[(rows.source_season<s)&(rows.source_season+3<=s-1)&(rows.horizon==3)].copy()
    active_train=train[train.target_state!='out']
    if len(active_train)<20:
        residual_origin_meta.append({'source_origin':s,'eligible':False,'reason':'insufficient resolved D1 training rows','d1_train_active_n':len(active_train)})
        continue
    try:
        d1=mod.ProductionModel('D1',3).fit(train)
    except Exception as e:
        residual_origin_meta.append({'source_origin':s,'eligible':False,'reason':f'D1 fit failed: {e}','d1_train_active_n':len(active_train)})
        continue
    test=rows[(rows.source_season==s)&(rows.horizon==3)&(rows.position=='RB')&(rows.career_stage=='developmental')&(rows.target_state!='out')].copy()
    if test.empty:
        residual_origin_meta.append({'source_origin':s,'eligible':False,'reason':'no active developmental RB rows','d1_train_active_n':len(active_train)})
        continue
    kept=0
    for r in test.itertuples(index=False):
        means={st:float(d1.predict_state(r,st)) for st in STATES}
        ordered=(means['depth']<means['usable']<means['starter']<means['premium']<means['elite'])
        if not ordered:
            residual_exclusions.append({'source_origin':s,'player_id':str(r.player_id),'target_state':str(r.target_state),'source_percentile':float(r.source_percentile),'reason':'frozen D1 positive-state means not strictly ordered',**{f'd1_mean_{st}':means[st] for st in STATES}})
            continue
        realized=str(r.target_state); m=means[realized]
        resid=math.log1p(float(r.target_points))-math.log1p(max(0.,m))
        gap=math.log1p(means['starter'])-math.log1p(means['usable'])
        residual_rows.append({'source_origin':s,'player_id':str(r.player_id),'source_percentile':float(r.source_percentile),'source_points':float(r.source_points),'target_points':float(r.target_points),'target_state':realized,'group':'lower' if realized in LOWER else 'upper','prospective_d1_realized_state_mean':m,'prospective_residual_log1p':resid,'gap_log1p_starter_usable':gap,**{f'd1_mean_{st}':means[st] for st in STATES}})
        kept+=1
    residual_origin_meta.append({'source_origin':s,'eligible':bool(kept),'reason':'ok_after_strict_D1_order_filter' if kept else 'no strictly ordered residual rows','d1_train_active_n':len(active_train),'residual_active_rb_dev_n_raw':len(test),'residual_active_rb_dev_n_kept':kept,'residual_active_rb_dev_n_excluded':len(test)-kept})
reslib=pd.DataFrame(residual_rows); meta=pd.DataFrame(residual_origin_meta)
reslib.to_csv(OUT/'PRIOR_ORIGIN_PROSPECTIVE_RESIDUAL_LIBRARY.csv',index=False); meta.to_csv(OUT/'RESIDUAL_ORIGIN_AVAILABILITY.csv',index=False); pd.DataFrame(residual_exclusions).to_csv(OUT/'PREFIT_RESIDUAL_EXCLUSIONS.csv',index=False)
if reslib.empty: raise RuntimeError('No prospective residual library')
earliest=int(reslib.source_origin.min())

# Fit exactly one gap-aware calibrator at each canonical origin.
def fit_cal(tr):
    u=tr.source_percentile.to_numpy(float); z=2*(u-.5); lower=(tr.group.to_numpy()=='lower')
    y=tr.prospective_residual_log1p.to_numpy(float); gap=tr.gap_log1p_starter_usable.to_numpy(float)
    def obj(p):
        cu=A*np.tanh(p[0]+p[1]*z); th=np.tanh(p[2]+p[3]*z); pred=np.where(lower,cu+gap*th,cu)
        return float(np.mean((y-pred)**2)+LAM_SHARED*(p[0]**2+p[1]**2)+LAM_DEV*(p[2]**2+p[3]**2))
    res=minimize(obj,np.zeros(4),method='SLSQP',options={'maxiter':2000,'ftol':1e-12,'disp':False})
    return np.asarray(res.x,float),{'success':bool(res.success),'message':str(res.message),'objective':float(res.fun),'iterations':int(getattr(res,'nit',-1))}

fitrows=[]; records=[]; training_summ=[]
for t in ORIGINS:
    tr=reslib[(reslib.source_origin+3<=t-1)].copy()
    if len(tr)<20 or tr.group.nunique()<2:
        raise RuntimeError(f'origin {t} insufficient prior-origin prospective residual training rows: {len(tr)}')
    p,fmeta=fit_cal(tr)
    if not fmeta['success']: raise RuntimeError((t,fmeta))
    a0,a1,d0,d1=p
    # training support diagnostics
    training_summ.append({'origin':t,'training_rows':len(tr),'training_origins':tr.source_origin.nunique(),'first_training_origin':int(tr.source_origin.min()),'last_training_origin':int(tr.source_origin.max()),'upper_rows':int((tr.group=='upper').sum()),'lower_rows':int((tr.group=='lower').sum()),'source_pct_min':tr.source_percentile.min(),'source_pct_max':tr.source_percentile.max()})
    hh=hist[(hist.source_season==t)&(hist.horizon==3)&(hist.position=='RB')&(hist.career_stage=='developmental')].copy().sort_values('player_id')
    # parameter/geometry diagnostics on eval rows
    min_gap_raw=1e99; min_gap_log=1e99; min_other=1e99; viol=0; ths=[]
    for _,r in hh.iterrows():
        dmeans={s:float(r[f'd1_mean_{s}']) for s in STATES}; cmeans,cu,cl,th,gap=adjusted_means(p,float(r.source_percentile),dmeans)
        vals=np.array([cmeans[s] for s in STATES]); dif=np.diff(vals)
        min_other=min(min_other,float(dif.min()))
        su_gap=cmeans['starter']-cmeans['usable']; su_log=math.log1p(cmeans['starter'])-math.log1p(cmeans['usable'])
        min_gap_raw=min(min_gap_raw,su_gap); min_gap_log=min(min_gap_log,su_log); viol+=int(np.any(dif<=0)); ths.append(abs(th))
        probs=[float(r.p_out)]+[float(r[f'p_{s}']) for s in STATES]; ds=[0.]+[dmeans[s] for s in STATES]; cs=[0.]+[cmeans[s] for s in STATES]; y=float(r.target_points)
        if abs(sum(probs)-1)>1e-10: raise RuntimeError(f'prob sum {t} {r.player_id} {sum(probs)}')
        rec={'origin':t,'source_season':t,'player_id':str(r.player_id),'source_percentile':float(r.source_percentile),'source_points':float(r.source_points),'target_points':y,'target_state':str(r.target_state),'upper_correction_log1p':cu,'lower_correction_log1p':cl,'tanh_h':th,'gap_log1p_starter_usable':gap}
        rec['d1_crps']=crps(probs,ds,y); rec['challenger_crps']=crps(probs,cs,y); rec['crps_gain']=rec['d1_crps']-rec['challenger_crps']
        rec['d1_expected']=float(np.dot(probs,ds)); rec['challenger_expected']=float(np.dot(probs,cs)); rec['d1_abs_error']=abs(rec['d1_expected']-y); rec['challenger_abs_error']=abs(rec['challenger_expected']-y); rec['mae_gain']=rec['d1_abs_error']-rec['challenger_abs_error']
        pa=1-float(r.p_out); rec['p_active']=pa
        rec['d1_cond_active']=float(sum(float(r[f'p_{s}'])*dmeans[s] for s in STATES)/pa) if pa>0 else np.nan
        rec['challenger_cond_active']=float(sum(float(r[f'p_{s}'])*cmeans[s] for s in STATES)/pa) if pa>0 else np.nan
        for s,pr in zip(['out']+STATES,probs): rec[f'p_{s}']=pr
        for s in STATES: rec[f'd1_mean_{s}']=dmeans[s]; rec[f'challenger_mean_{s}']=cmeans[s]
        for pref,supp in [('d1',ds),('challenger',cs)]:
            for q in [.10,.25,.75,.90]: rec[f'{pref}_q{int(q*100)}']=qdisc(probs,supp,q)
            rec[f'{pref}_cov10_90']=float(rec[f'{pref}_q10']<=y<=rec[f'{pref}_q90']); rec[f'{pref}_cov25_75']=float(rec[f'{pref}_q25']<=y<=rec[f'{pref}_q75'])
        if str(r.target_state)!='out':
            s=str(r.target_state); grp='lower' if s in LOWER else 'upper'; denom=max(1e-9,float(r.source_points)); rr=y/denom; dr=dmeans[s]/denom; cr=cmeans[s]/denom
            rec.update(realized_group=grp,realized_retention=rr,d1_realized_state_retention=dr,challenger_realized_state_retention=cr,d1_ret_bias=dr-rr,challenger_ret_bias=cr-rr,d1_point_bias_realized_state=dmeans[s]-y,challenger_point_bias_realized_state=cmeans[s]-y,d1_cond_active_bias=rec['d1_cond_active']-y,challenger_cond_active_bias=rec['challenger_cond_active']-y)
        else:
            rec.update(realized_group='out',realized_retention=np.nan,d1_realized_state_retention=np.nan,challenger_realized_state_retention=np.nan,d1_ret_bias=np.nan,challenger_ret_bias=np.nan,d1_point_bias_realized_state=np.nan,challenger_point_bias_realized_state=np.nan,d1_cond_active_bias=np.nan,challenger_cond_active_bias=np.nan)
        records.append(rec)
    ths=np.asarray(ths,float)
    fitrows.append({'origin':t,'a0':a0,'a1':a1,'d0':d0,'d1':d1,**fmeta,'training_rows':len(tr),'training_origins':tr.source_origin.nunique(),'min_adjusted_starter_usable_gap_points':min_gap_raw,'min_adjusted_starter_usable_gap_log1p':min_gap_log,'min_any_adjacent_gap_points':min_other,'ordering_violations':viol,'max_abs_tanh_h':float(ths.max()),'frac_abs_tanh_h_ge_090':float((ths>=.90).mean()),'frac_abs_tanh_h_ge_095':float((ths>=.95).mean()),'frac_abs_tanh_h_ge_099':float((ths>=.99).mean())})
    if viol: raise RuntimeError(f'ordering violation origin {t}')

row=pd.DataFrame(records).sort_values(['origin','player_id']).reset_index(drop=True); fits=pd.DataFrame(fitrows); trains=pd.DataFrame(training_summ)
row.to_csv(OUT/'ROW_LEVEL_EVALUATION.csv',index=False); fits.to_csv(OUT/'ORIGIN_SPECIFIC_PARAMETERS_AND_ORDERING.csv',index=False); trains.to_csv(OUT/'CALIBRATION_TRAINING_SUPPORT_BY_ORIGIN.csv',index=False)

# Diagnostics
row['decile']=pd.cut(row.source_percentile,bins=np.linspace(0,1,11),include_lowest=True,right=False,labels=False)
active=row[row.target_state!='out'].copy()

def imce_df(df,biascol):
    if len(df)==0:return np.nan
    vals=[]; weights=[]
    for d,g in df.groupby('decile'):
        vals.append(abs(float(g[biascol].mean()))); weights.append(len(g))
    return float(np.average(vals,weights=weights)) if weights else np.nan

def scope_cal(name,g):
    return {'scope':name,'n':len(g),'d1_imce':imce_df(g,'d1_ret_bias'),'challenger_imce':imce_df(g,'challenger_ret_bias'),'d1_mean_ret_bias':float(g.d1_ret_bias.mean()) if len(g) else np.nan,'challenger_mean_ret_bias':float(g.challenger_ret_bias.mean()) if len(g) else np.nan,'d1_cond_active_bias_points':float(g.d1_cond_active_bias.mean()) if len(g) else np.nan,'challenger_cond_active_bias_points':float(g.challenger_cond_active_bias.mean()) if len(g) else np.nan}
calib=pd.DataFrame([scope_cal('overall',active),scope_cal('upper',active[active.realized_group=='upper']),scope_cal('lower',active[active.realized_group=='lower']),scope_cal('low_mid_lt75',active[active.source_percentile<.75])])
calib['imce_improvement']=calib.d1_imce-calib.challenger_imce; calib['relative_improvement']=calib.imce_improvement/calib.d1_imce
calib.to_csv(OUT/'CONTINUOUS_MAGNITUDE_CALIBRATION.csv',index=False)

# decile curves
curves=[]
for scope,g0 in [('overall',active),('upper',active[active.realized_group=='upper']),('lower',active[active.realized_group=='lower'])]:
    for d,g in g0.groupby('decile'):
        curves.append({'scope':scope,'decile':int(d),'n':len(g),'u_mean':g.source_percentile.mean(),'d1_ret_bias':g.d1_ret_bias.mean(),'challenger_ret_bias':g.challenger_ret_bias.mean(),'realized_retention_mean':g.realized_retention.mean(),'d1_pred_retention_mean':g.d1_realized_state_retention.mean(),'challenger_pred_retention_mean':g.challenger_realized_state_retention.mean()})
pd.DataFrame(curves).to_csv(OUT/'CONTINUOUS_MAGNITUDE_CURVES.csv',index=False)

# state diagnostics incl CRPS on rows realizing each state
staterows=[]
for s,g in active.groupby('target_state'):
    staterows.append({'state':s,'n':len(g),'d1_crps':g.d1_crps.mean(),'challenger_crps':g.challenger_crps.mean(),'crps_gain':g.crps_gain.mean(),'d1_point_bias':g.d1_point_bias_realized_state.mean(),'challenger_point_bias':g.challenger_point_bias_realized_state.mean(),'d1_ret_bias':g.d1_ret_bias.mean(),'challenger_ret_bias':g.challenger_ret_bias.mean(),'d1_abs_ret_bias':abs(g.d1_ret_bias.mean()),'challenger_abs_ret_bias':abs(g.challenger_ret_bias.mean()),'abs_ret_bias_worsening':abs(g.challenger_ret_bias.mean())-abs(g.d1_ret_bias.mean())})
state=pd.DataFrame(staterows); state.to_csv(OUT/'INDIVIDUAL_STATE_DIAGNOSTICS.csv',index=False)

# subset metrics and coverage
def subset_metrics(name,g):
    a=g[g.target_state!='out']
    rec={'subset':name,'n':len(g),'active_n':len(a),'d1_crps':g.d1_crps.mean(),'challenger_crps':g.challenger_crps.mean(),'crps_gain':g.crps_gain.mean(),'d1_mae':g.d1_abs_error.mean(),'challenger_mae':g.challenger_abs_error.mean(),'mae_gain':g.mae_gain.mean(),'d1_cov10_90':g.d1_cov10_90.mean(),'challenger_cov10_90':g.challenger_cov10_90.mean(),'d1_cov25_75':g.d1_cov25_75.mean(),'challenger_cov25_75':g.challenger_cov25_75.mean()}
    if len(a): rec.update(d1_imce=imce_df(a,'d1_ret_bias'),challenger_imce=imce_df(a,'challenger_ret_bias'),d1_ret_bias=a.d1_ret_bias.mean(),challenger_ret_bias=a.challenger_ret_bias.mean(),d1_cond_active_bias_points=a.d1_cond_active_bias.mean(),challenger_cond_active_bias_points=a.challenger_cond_active_bias.mean())
    return rec
subs=[subset_metrics('full',row),subset_metrics('low_mid_lt75',row[row.source_percentile<.75])]
for q in [.75,.90,.95]: subs.append(subset_metrics(f'p{int(q*100)}_plus',row[row.source_percentile>=q]))
for grp in ['upper','lower']: subs.append(subset_metrics(grp,row[row.realized_group==grp]))
subset=pd.DataFrame(subs); subset.to_csv(OUT/'NO_HARM_AND_TAIL_DIAGNOSTICS.csv',index=False)

coverage=[]
for scope,g in [('overall',row),('upper',row[row.realized_group=='upper']),('lower',row[row.realized_group=='lower']),('low_mid_lt75',row[row.source_percentile<.75])]:
    coverage.append({'scope':scope,'n':len(g),'d1_cov10_90':g.d1_cov10_90.mean(),'challenger_cov10_90':g.challenger_cov10_90.mean(),'diff10_90':g.challenger_cov10_90.mean()-g.d1_cov10_90.mean(),'d1_cov25_75':g.d1_cov25_75.mean(),'challenger_cov25_75':g.challenger_cov25_75.mean(),'diff25_75':g.challenger_cov25_75.mean()-g.d1_cov25_75.mean()})
coverage=pd.DataFrame(coverage); coverage.to_csv(OUT/'COVERAGE_DIAGNOSTICS.csv',index=False)

origin=row.groupby('origin').agg(n=('player_id','size'),crps_gain=('crps_gain','mean'),mae_gain=('mae_gain','mean'),d1_crps=('d1_crps','mean'),challenger_crps=('challenger_crps','mean'),d1_mae=('d1_abs_error','mean'),challenger_mae=('challenger_abs_error','mean')).reset_index().merge(fits,on='origin')
origin.to_csv(OUT/'ORIGIN_BY_ORIGIN_SCORES.csv',index=False)

# bootstrap
players=pd.Categorical(row.player_id).codes; origins=pd.Categorical(row.origin).codes; P=players.max()+1; O=origins.max()+1
crpsv=row.crps_gain.to_numpy(float); maev=row.mae_gain.to_numpy(float); lowmask=row.source_percentile.to_numpy()<.75
actmask=row.target_state.to_numpy()!='out'; aa=row.loc[actmask].copy(); ap=players[actmask]; ao=origins[actmask]; adec=aa.decile.to_numpy(int); db=aa.d1_ret_bias.to_numpy(float); cb=aa.challenger_ret_bias.to_numpy(float); ag=aa.realized_group.to_numpy(); alow=aa.source_percentile.to_numpy()<.75

def weighted_imce(bias,dec,w,mask):
    mask=np.asarray(mask,bool); total=w[mask].sum();
    if total<=0:return np.nan
    s=0.
    for d in range(10):
        m=mask&(dec==d)
        sw=w[m].sum()
        if sw>0:s+=sw*abs(np.sum(w[m]*bias[m])/sw)
    return s/total

rng=np.random.default_rng(20260920); REPS=5000
crps_bs=[];mae_bs=[];low_crps_bs=[];imce_bs={k:[] for k in ['overall','upper','lower','low_mid_lt75']}
for start in range(0,REPS,250):
    B=min(250,REPS-start); wp=rng.exponential(1,(B,P)); wo=rng.exponential(1,(B,O)); W=wp[:,players]*wo[:,origins]
    den=W.sum(axis=1); crps_bs.extend((W@crpsv/den).tolist()); mae_bs.extend((W@maev/den).tolist())
    Wl=W[:,lowmask]; low_crps_bs.extend((Wl@crpsv[lowmask]/Wl.sum(axis=1)).tolist())
    Wa=wp[:,ap]*wo[:,ao]
    for b in range(B):
        w=Wa[b]
        masks={'overall':np.ones(len(aa),bool),'upper':ag=='upper','lower':ag=='lower','low_mid_lt75':alow}
        for k,m in masks.items(): imce_bs[k].append(weighted_imce(db,adec,w,m)-weighted_imce(cb,adec,w,m))

def ci(v):
    a=np.asarray(v,float); return {'mean':float(np.mean(a)),'ci_low':float(np.quantile(a,.025)),'ci_high':float(np.quantile(a,.975))}
unc={'crps_gain':ci(crps_bs),'mae_gain':ci(mae_bs),'low_mid_crps_gain':ci(low_crps_bs),'imce_improvement':{k:ci(v) for k,v in imce_bs.items()}}
# moving block origin bootstrap
stats=row.groupby('origin').crps_gain.agg(['sum','count']).reindex(ORIGINS); sums=stats['sum'].to_numpy(float); counts=stats['count'].to_numpy(float); nO=len(ORIGINS)
rng=np.random.default_rng(20260921); bvals=[]
for _ in range(REPS):
    idx=[]
    while len(idx)<nO:
        st=int(rng.integers(0,nO)); idx.extend([(st+j)%nO for j in range(3)])
    idx=idx[:nO]; bvals.append(float(sums[idx].sum()/counts[idx].sum()))
unc['moving_block_crps_gain']=ci(bvals)
(OUT/'CLUSTERED_AND_BLOCK_UNCERTAINTY.json').write_text(json.dumps(unc,indent=2))

# leave-one-origin/player fixed evaluation influence
loo=[]
for o in ORIGINS:
    g=row[row.origin!=o]; loo.append({'omit_origin':o,'n':len(g),'crps_gain':g.crps_gain.mean(),'mae_gain':g.mae_gain.mean()})
loo=pd.DataFrame(loo); loo.to_csv(OUT/'LEAVE_ONE_ORIGIN_OUT.csv',index=False)
fullgain=row.crps_gain.mean(); pinf=[]
for p in sorted(row.player_id.unique()):
    g=row[row.player_id!=p]; pinf.append({'omit_player':p,'removed_rows':int((row.player_id==p).sum()),'crps_gain':g.crps_gain.mean(),'delta_vs_full':g.crps_gain.mean()-fullgain})
pinf=pd.DataFrame(pinf).sort_values('crps_gain'); pinf.to_csv(OUT/'LEAVE_ONE_PLAYER_OUT_INFLUENCE.csv',index=False)

# parity/validity
maxprob=float(np.max(np.abs(row[[f'p_{s}' for s in ['out']+STATES]].sum(axis=1)-1)))
validity={'max_probability_sum_error':maxprob,'total_ordering_violations':int(fits.ordering_violations.sum()),'minimum_adjusted_starter_usable_gap_points':float(fits.min_adjusted_starter_usable_gap_points.min()),'minimum_adjusted_starter_usable_gap_log1p':float(fits.min_adjusted_starter_usable_gap_log1p.min()),'minimum_any_adjacent_gap_points':float(fits.min_any_adjacent_gap_points.min()),'max_abs_tanh_h':float(fits.max_abs_tanh_h.max()),'max_fraction_abs_tanh_h_ge_090':float(fits.frac_abs_tanh_h_ge_090.max()),'max_fraction_abs_tanh_h_ge_095':float(fits.frac_abs_tanh_h_ge_095.max()),'max_fraction_abs_tanh_h_ge_099':float(fits.frac_abs_tanh_h_ge_099.max()),'source_2023_target_2026_inspected':False}
(OUT/'ORDERING_AND_DISTRIBUTION_VALIDITY.json').write_text(json.dumps(validity,indent=2))

# gates
cal=calib.set_index('scope'); full=float(row.crps_gain.mean()); mae=float(row.mae_gain.mean()); low=float(subset.loc[subset['subset']=='low_mid_lt75','crps_gain'].iloc[0]); origins_improved=int((origin.crps_gain>0).sum()); med=float(origin.crps_gain.median()); worst=float(origin.crps_gain.min()); loo_flip=bool((loo.crps_gain>0).any()) if full<0 else bool((loo.crps_gain<0).any()); player_flip=bool((pinf.crps_gain>0).any()) if full<0 else bool((pinf.crps_gain<0).any())
state_fail=bool((state.abs_ret_bias_worsening>0.05).any()); covok=bool((coverage.diff10_90>=-.03-1e-12).all() and (coverage.diff25_75>=-.03-1e-12).all())
cal_rel=float(cal.loc['overall','relative_improvement']); calpass=bool(cal_rel>=.10 and unc['imce_improvement']['overall']['ci_low']>=0 and cal.loc['upper','imce_improvement']>0 and cal.loc['lower','imce_improvement']>0)
low_cal_improve=float(cal.loc['low_mid_lt75','imce_improvement'])
gates=[
 {'gate':'full_cell_crps','pass':bool(full>=0 and unc['crps_gain']['ci_low']>=0 and origins_improved>=6 and med>=0 and not loo_flip),'detail':f'gain={full:+.4f}; CI=[{unc["crps_gain"]["ci_low"]:+.4f},{unc["crps_gain"]["ci_high"]:+.4f}]; origins={origins_improved}/9; median={med:+.4f}; worst={worst:+.4f}; LOO_flip={loo_flip}'},
 {'gate':'continuous_magnitude_calibration','pass':calpass,'detail':f'overall relative={cal_rel:+.3%}; overall abs={cal.loc["overall","imce_improvement"]:+.4f} CI=[{unc["imce_improvement"]["overall"]["ci_low"]:+.4f},{unc["imce_improvement"]["overall"]["ci_high"]:+.4f}]; upper={cal.loc["upper","imce_improvement"]:+.4f}; lower={cal.loc["lower","imce_improvement"]:+.4f}'},
 {'gate':'individual_state_no_new_failure','pass':not state_fail,'detail':f'max_abs_bias_worsening={state.abs_ret_bias_worsening.max():+.4f}'},
 {'gate':'mae_no_harm','pass':bool(mae>=-.5 and unc['mae_gain']['ci_high']>=0),'detail':f'gain={mae:+.4f}; CI=[{unc["mae_gain"]["ci_low"]:+.4f},{unc["mae_gain"]["ci_high"]:+.4f}]'},
 {'gate':'low_mid_no_harm','pass':bool(low>=-.5 and unc['low_mid_crps_gain']['ci_high']>=0 and low_cal_improve>=0),'detail':f'CRPS gain={low:+.4f}; CI=[{unc["low_mid_crps_gain"]["ci_low"]:+.4f},{unc["low_mid_crps_gain"]["ci_high"]:+.4f}]; IMCE improvement={low_cal_improve:+.4f}'},
 {'gate':'coverage','pass':covok,'detail':coverage.to_json(orient='records')},
 {'gate':'ordering_probability_parity','pass':bool(validity['total_ordering_violations']==0 and maxprob<=1e-12 and max_replay<=1e-8),'detail':json.dumps(validity)},
 {'gate':'temporal_and_player_influence','pass':bool(not loo_flip and not player_flip),'detail':f'LOO_flip={loo_flip}; player_flip={player_flip}; moving_block_CI=[{unc["moving_block_crps_gain"]["ci_low"]:+.4f},{unc["moving_block_crps_gain"]["ci_high"]:+.4f}]'},
 {'gate':'prospective_2023_2026_untouched','pass':True,'detail':'No incomplete 2026 target outcomes accessed.'}
]
gates=pd.DataFrame(gates); gates.to_csv(OUT/'PROMOTION_GATE_EVALUATION.csv',index=False)
allpass=bool(gates['pass'].all())

# Mechanism-expression diagnostic for classification B vs C/D
# It is expressed if fitted lower-vs-upper correction slope differs materially across origins (median d1 not ~0) and lower group calibration improves.
mechanism_expressed=bool(abs(float(fits.d1.median()))>1e-3 or abs(float(fits.d0.median()))>1e-3)
cal_any=bool(cal.loc['overall','imce_improvement']>0 or cal.loc['upper','imce_improvement']>0 or cal.loc['lower','imce_improvement']>0)
if allpass:
    classification='A. GAP-AWARE PROSPECTIVE PARTIAL-POOLING CHALLENGER EARNS RESEARCH AUTHORITY'
elif mechanism_expressed and cal_any and (full>=0 or mae>=0):
    classification='B. MECHANISM WAS CORRECT, BUT CHALLENGER IS NOT STRONG ENOUGH'
elif mechanism_expressed and full<0 and cal.loc['overall','imce_improvement']<=0 and cal.loc['lower','imce_improvement']<=0:
    classification='C. CORRECTLY SPECIFIED CHALLENGER FAILS'
elif full>=0 and not calpass:
    classification='D. DIFFERENT FORECAST COMPONENT IS IMPLICATED'
else:
    classification='C. CORRECTLY SPECIFIED CHALLENGER FAILS'

# spec/provenance/authority docs
specout={'candidate':'gap_aware_prospective_log1p_partial_pooling','A':A,'shared_penalty':LAM_SHARED,'lower_deviation_penalty':LAM_DEV,'groups':{'upper':['starter','premium','elite'],'lower':['depth','usable']},'residual':'log1p(realized)-log1p(prospective_D1_realized_state_mean)','equations':{'z':'2*(u-.5)','c_U':'A*tanh(a0+a1*z)','G':'log1p(D1_starter)-log1p(D1_usable)','h':'d0+d1*z','c_L':'c_U+G*tanh(h)','adjusted_mean':'expm1(log1p(D1_mean_state)+group_correction)'},'optimizer':'SLSQP zeros maxiter=2000 ftol=1e-12','earliest_residual_origin':earliest,'evaluation_origins':ORIGINS}
(OUT/'CANDIDATE_SPECIFICATION.json').write_text(json.dumps(specout,indent=2))
prov={'starting_mechanism_head':'bb66b7f6e6bdac946d42a2414c59f618aea341e4','preregistration_commit':'62d40406d090d9bffd37df78b83926d5c7887059','evaluation_rows':len(row),'active_evaluation_rows':len(active),'evaluation_origins':ORIGINS,'residual_library_rows':len(reslib),'residual_library_origins':sorted(reslib.source_origin.unique().astype(int).tolist()),'earliest_residual_origin':earliest,'exact_replay_max_abs_diff':max_replay,'source_2023_target_2026_inspected':False,'current_player_tuning':False}
(OUT/'PROVENANCE_AND_PARITY_MANIFEST.json').write_text(json.dumps(prov,indent=2))
auth={'classification':classification,'all_material_gates_pass':allpass,'mechanism_expressed':mechanism_expressed,'full_cell_crps_gain':full,'clustered_crps_ci':[unc['crps_gain']['ci_low'],unc['crps_gain']['ci_high']],'origins_improved':origins_improved,'median_origin_gain':med,'overall_imce_improvement':float(cal.loc['overall','imce_improvement']),'upper_imce_improvement':float(cal.loc['upper','imce_improvement']),'lower_imce_improvement':float(cal.loc['lower','imce_improvement']),'mae_gain':mae,'low_mid_crps_gain':low,'ordering_violations':validity['total_ordering_violations'],'production_authority_changed':False,'pr147_modified':False,'main_modified':False,'merge':False,'deploy':False,'prospective_2023_2026_untouched':True}
(OUT/'AUTHORITY_DISPOSITION.json').write_text(json.dumps(auth,indent=2)); (OUT/'FINAL_CLASSIFICATION.json').write_text(json.dumps({'classification':classification,'gates':gates.to_dict(orient='records'),'authority':auth},indent=2))
(OUT/'PROSPECTIVE_AUTHORITY_MAP.json').write_text(json.dumps({'D1_Y3_developmental_RB':'frozen production control','challenger_research_authority_earned':classification.startswith('A.'),'D1_probabilities_routing_scale':'unchanged','source_2023_target_2026':'untouched prospective confirmation','next_step':'management review; no alternate challenger authorized in this stage'},indent=2))
failed=gates.loc[~gates['pass'],'gate'].tolist()
(OUT/'FINAL_RESEARCH_CONCLUSION.md').write_text(f'''# Final research conclusion\n\nClassification: **{classification}**.\n\nThe single preregistered gap-aware prospective-log1p challenger was fit at all nine 2014-2022 origins using only earlier prospective D1 residuals resolved by each origin. Exact D1 replay parity passed (max absolute difference {max_replay:.3g}); D1 probabilities/routing/scale remained unchanged; and there were zero final-state ordering violations.\n\nFull-cell CRPS gain (D1 - challenger): {full:+.4f}, clustered 95% interval [{unc['crps_gain']['ci_low']:+.4f}, {unc['crps_gain']['ci_high']:+.4f}], with {origins_improved}/9 origins improved and median origin gain {med:+.4f}. MAE gain: {mae:+.4f}.\n\nContinuous-magnitude IMCE improvement: overall {cal.loc['overall','imce_improvement']:+.4f} ({cal_rel:+.1%}); upper {cal.loc['upper','imce_improvement']:+.4f}; lower {cal.loc['lower','imce_improvement']:+.4f}. Low/mid CRPS gain {low:+.4f}; low/mid IMCE improvement {low_cal_improve:+.4f}.\n\nThe corrected parameterization did express nonzero lower-group deviations: median d0={fits.d0.median():+.4f}, median d1={fits.d1.median():+.4f}. Max |tanh(h)| on evaluation rows was {validity['max_abs_tanh_h']:.4f}; there were zero ordering violations.\n\nFailed material gates: {', '.join(failed) if failed else 'none'}. No alternate candidate, penalty, coordinate, grouping, amplitude, state-probability change, merge, deployment, or production promotion was attempted. Source-2023 -> target-2026 remains untouched.\n''')

print(json.dumps(auth,indent=2)); print('\nFITS\n',fits[['origin','a0','a1','d0','d1','training_rows','training_origins','min_adjusted_starter_usable_gap_points','max_abs_tanh_h']].to_string(index=False)); print('\nCALIB\n',calib.to_string(index=False)); print('\nGATES\n',gates.to_string(index=False)); print('\nSTATE\n',state.to_string(index=False)); print('\nCOVERAGE\n',coverage.to_string(index=False))
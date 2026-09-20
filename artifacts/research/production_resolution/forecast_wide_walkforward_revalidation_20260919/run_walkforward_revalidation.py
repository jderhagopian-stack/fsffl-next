import json, math, hashlib
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path('/mnt/data/fsffl_walkforward_revalidation_20260919'); OUT.mkdir(exist_ok=True)
HIST=Path('/mnt/data/fsffl_diag/historical_predictions.csv')
Y23=Path('/mnt/data/fsffl_walkforward_audit_20260919/Y2_ORIGIN_2023_PREDICTIONS.csv')
SEED=20260919
STATES=['out','depth','usable','starter','premium','elite']
POSITIONS=['QB','RB','WR','TE']; STAGES=['developmental','established','veteran']
P0_Y3={
'QB|developmental':'D0','QB|established':'D1','QB|veteran':'D1',
'RB|developmental':'D1','RB|established':'D0','RB|veteran':'D0',
'WR|developmental':'D1','WR|established':'D1','WR|veteran':'D0',
'TE|developmental':'D1','TE|established':'D1','TE|veteran':'D0'}
RESEARCH_Y3=P0_Y3.copy(); RESEARCH_Y3['QB|developmental']='D1'; RESEARCH_Y3['RB|established']='D1'
PRIOR_STATUS={}
for p in POSITIONS:
  for h in [2,3]:
    for s in STAGES:
      key=(p,h,s)
      if h==2: PRIOR_STATUS[key]='P0_RETAINED_D1'
      else:
        k=f'{p}|{s}'
        if k=='QB|developmental': PRIOR_STATUS[key]='PROPER_SCORE_EARNED_D0_TO_D1'
        elif k=='RB|established': PRIOR_STATUS[key]='PROPER_SCORE_EARNED_D0_TO_D1'
        elif k=='RB|developmental': PRIOR_STATUS[key]='P0_D1_RETAINED_STRUCTURALLY_UNRESOLVED'
        else: PRIOR_STATUS[key]=f'P0_RETAINED_{RESEARCH_Y3[k]}'

def current_candidate(p,h,s): return 'D1' if h==2 else RESEARCH_Y3[f'{p}|{s}']
def p0_candidate(p,h,s): return 'D1' if h==2 else P0_Y3[f'{p}|{s}']

def crps_discrete(vals,probs,y):
    vals=np.asarray(vals,float); probs=np.asarray(probs,float); ss=probs.sum()
    if ss<=0 or not np.isfinite(ss): return np.nan
    probs=probs/ss
    return float(np.sum(probs*np.abs(vals-y))-.5*np.sum(probs[:,None]*probs[None,:]*np.abs(vals[:,None]-vals[None,:])))

def score_rows(df):
    rows=[]
    for r in df.itertuples(index=False):
      p0=float(r.p_out); pa=float(r.p_active); y=float(r.target_points); sp=float(r.source_points)
      d0v=np.array([0.,float(r.active_D0)]); d0p=np.array([p0,pa])
      d1v=np.array([0.,float(r.d1_mean_depth),float(r.d1_mean_usable),float(r.d1_mean_starter),float(r.d1_mean_premium),float(r.d1_mean_elite)])
      d1p=np.array([float(r.p_out),float(r.p_depth),float(r.p_usable),float(r.p_starter),float(r.p_premium),float(r.p_elite)])
      cond1=float(r.pred_D1)/max(pa,1e-15)
      rows.append((crps_discrete(d0v,d0p,y),crps_discrete(d1v,d1p,y),abs(float(r.pred_D0)-y),abs(float(r.pred_D1)-y),float(r.pred_D0)-y,float(r.pred_D1)-y,float(r.active_D0),cond1,y/sp if sp>0 else np.nan))
    z=pd.DataFrame(rows,columns=['crps_D0','crps_D1','mae_D0','mae_D1','err_D0','err_D1','cond_D0','cond_D1','realized_ret'])
    return pd.concat([df.reset_index(drop=True),z],axis=1)

def two_way_boot(df,arr,reps=2000,seed=SEED):
    arr=np.asarray(arr,float); seasons=pd.Categorical(df.source_season).codes; players=pd.Categorical(df.player_id).codes
    ns=seasons.max()+1; np_=players.max()+1; rng=np.random.default_rng(seed); vals=np.empty(reps)
    for i in range(reps):
      ws=rng.exponential(1.,ns); wp=rng.exponential(1.,np_); w=ws[seasons]*wp[players]; vals[i]=np.sum(w*arr)/np.sum(w)
    q=np.quantile(vals,[.025,.975]); return float(arr.mean()),float(q[0]),float(q[1])

def moving_block_boot(origin_df,block_len,reps=5000,seed=SEED):
    # origin_df columns origin, gain, n; row-weighted pooled gain under contiguous-origin block resampling.
    od=origin_df.sort_values('origin').reset_index(drop=True); years=od.origin.to_numpy(int); gains=od.gain.to_numpy(float); ns=od.n.to_numpy(float); n=len(od)
    if n==0: return np.nan,np.nan,np.nan
    if n<=block_len:
      v=np.average(gains,weights=ns); return float(v),np.nan,np.nan
    starts=np.arange(0,n-block_len+1); rng=np.random.default_rng(seed); vals=[]
    for _ in range(reps):
      picks=[]
      while len(picks)<n:
        st=int(rng.choice(starts)); picks.extend(range(st,st+block_len))
      picks=picks[:n]
      vals.append(np.average(gains[picks],weights=ns[picks]))
    q=np.quantile(vals,[.025,.975]); return float(np.average(gains,weights=ns)),float(q[0]),float(q[1])

def state_calibration(q):
    eps=1e-12; y=(q.target_state!='out').astype(float).to_numpy(); p=q.p_active.to_numpy(float)
    active_brier=float(np.mean((p-y)**2)); active_log=float(-np.mean(y*np.log(np.clip(p,eps,1-eps))+(1-y)*np.log(np.clip(1-p,eps,1-eps))))
    probs=q[[f'p_{s}' for s in STATES]].to_numpy(float); probs=np.clip(probs,eps,1); probs/=probs.sum(axis=1,keepdims=True); idx=np.array([STATES.index(s) for s in q.target_state]); oh=np.eye(6)[idx]
    return active_brier,active_log,float(np.mean(np.sum((probs-oh)**2,axis=1))),float(-np.mean(np.log(probs[np.arange(len(q)),idx])))

def ols_bic(y,X):
    y=np.asarray(y,float); X=np.asarray(X,float); mask=np.isfinite(y)&np.all(np.isfinite(X),axis=1); y=y[mask]; X=X[mask]
    n=len(y); k=X.shape[1]
    if n<=k+2: return np.nan,np.full(k,np.nan),np.nan
    beta=np.linalg.lstsq(X,y,rcond=None)[0]; resid=y-X@beta; rss=float(np.sum(resid**2)); rss=max(rss,1e-12); bic=n*np.log(rss/n)+k*np.log(n)
    return bic,beta,rss

def design_mag(q,form,knot=None,origin_fe=False):
    u=q.source_percentile.to_numpy(float); c=u-.5; cols=[np.ones(len(q)),c]
    if form=='quadratic': cols.append(c*c)
    if form=='piecewise': cols.append(np.maximum(0,u-float(knot)))
    if origin_fe:
      yrs=sorted(q.source_season.unique())
      for y in yrs[1:]: cols.append((q.source_season.to_numpy()==y).astype(float))
    return np.column_stack(cols)

def structural_diag(q, outcome='target_points', boot_reps=500):
    # all rows, primary absolute future points (including out) to avoid selection on survival.
    qq=q.copy(); y=qq[outcome].to_numpy(float)
    forms=[]
    for f in ['linear','quadratic']:
      bic,beta,_=ols_bic(y,design_mag(qq,f,origin_fe=True)); forms.append((f,None,bic,beta))
    for knot in [.60,.70,.80,.90]:
      bic,beta,_=ols_bic(y,design_mag(qq,'piecewise',knot,origin_fe=True)); forms.append(('piecewise',knot,bic,beta))
    pooled_best=min(forms,key=lambda x:x[2] if np.isfinite(x[2]) else 1e99)
    # per origin best and quadratic curvature signs
    per=[]
    for yr,g in qq.groupby('source_season'):
      if len(g)<20: continue
      yy=g[outcome].to_numpy(float); ff=[]
      for f in ['linear','quadratic']:
        bic,beta,_=ols_bic(yy,design_mag(g,f,origin_fe=False)); ff.append((f,None,bic,beta))
      for knot in [.60,.70,.80,.90]:
        bic,beta,_=ols_bic(yy,design_mag(g,'piecewise',knot,origin_fe=False)); ff.append(('piecewise',knot,bic,beta))
      best=min(ff,key=lambda x:x[2] if np.isfinite(x[2]) else 1e99)
      qb=[x for x in ff if x[0]=='quadratic'][0]
      per.append({'origin':int(yr),'n':len(g),'best_form':best[0],'best_knot':best[1],'best_bic':best[2],'quadratic_bic':qb[2],'quadratic_curvature':qb[3][2] if len(qb[3])>2 else np.nan,'linear_bic':[x for x in ff if x[0]=='linear'][0][2]})
    perdf=pd.DataFrame(per)
    # bootstrap best piecewise knot (fixed grid) over player x origin weights on pooled fixed effects not practical; use weighted RSS with simple no-FE fits after demeaning by origin.
    # Demean outcome and magnitude within origin, then compare piecewise grid on weighted bootstrap.
    knot_counts={k:0 for k in [.60,.70,.80,.90]}; rng=np.random.default_rng(SEED+len(q)+int(q.horizon.iloc[0])*1000)
    if len(qq)>=50 and qq.source_season.nunique()>=4:
      # bootstrap rows with product exponential player/year weights and weighted least squares, include year dummies.
      seasons=pd.Categorical(qq.source_season).codes; players=pd.Categorical(qq.player_id).codes; ns=seasons.max()+1; np_=players.max()+1
      mats={k:design_mag(qq,'piecewise',k,origin_fe=True) for k in knot_counts}
      for _ in range(boot_reps):
        w=rng.exponential(1.,ns)[seasons]*rng.exponential(1.,np_)[players]; sw=np.sqrt(w)
        bestk=None; bestbic=1e99
        for k,X in mats.items():
          Xw=X*sw[:,None]; yw=y*sw; n=len(y); kk=X.shape[1]
          beta=np.linalg.lstsq(Xw,yw,rcond=None)[0]; resid=y-X@beta; rss=float(np.sum(w*resid*resid)); rss=max(rss,1e-12); bic=n*np.log(rss/np.sum(w))+kk*np.log(n)
          if bic<bestbic: bestbic=bic; bestk=k
        knot_counts[bestk]+=1
    linear=[x for x in forms if x[0]=='linear'][0]; quad=[x for x in forms if x[0]=='quadratic'][0]; pieces=[x for x in forms if x[0]=='piecewise']; bestpiece=min(pieces,key=lambda x:x[2])
    adequate=len(perdf)
    qstable=0.; qsign=None
    if adequate:
      finite=perdf[np.isfinite(perdf.quadratic_curvature)]
      if len(finite):
        med=np.nanmedian(finite.quadratic_curvature); qsign=np.sign(med); qstable=float((np.sign(finite.quadratic_curvature)==qsign).mean())
    piece_recur=0.; samek=None
    if adequate:
      pp=perdf[perdf.best_form=='piecewise']
      if len(pp):
        vc=pp.best_knot.value_counts(); samek=float(vc.index[0]); piece_recur=float(vc.iloc[0]/adequate)
    boot_total=sum(knot_counts.values()); boot_share=max(knot_counts.values())/boot_total if boot_total else np.nan; boot_knot=max(knot_counts,key=knot_counts.get) if boot_total else np.nan
    # classification
    if adequate<4: classification='INSUFFICIENT_EVIDENCE'
    elif bestpiece[2]+6<min(linear[2],quad[2]) and piece_recur>=.60 and boot_share>=.60 and samek==boot_knot:
      classification=f'STABLE_CHANGE_POINT_{samek:.2f}'
    elif quad[2]+6<linear[2] and qstable>=.60:
      classification='SMOOTH_NONLINEAR'
    elif np.isfinite(linear[2]): classification='SMOOTH_MONOTONIC_OR_WEAK_NONLINEAR'
    else: classification='INSUFFICIENT_EVIDENCE'
    return {
      'classification':classification,'pooled_linear_bic':linear[2],'pooled_quadratic_bic':quad[2],'pooled_best_piecewise_bic':bestpiece[2],'pooled_best_piecewise_knot':bestpiece[1],
      'adequate_origins':adequate,'piecewise_origin_recurrence':piece_recur,'piecewise_origin_knot':samek,'bootstrap_best_knot':boot_knot,'bootstrap_best_knot_share':boot_share,'quadratic_curvature_sign_stability':qstable,
      'quadratic_curvature_pooled':quad[3][2] if len(quad[3])>2 else np.nan,
    },perdf,knot_counts

hist=pd.read_csv(HIST); y23=pd.read_csv(Y23)
# Ensure fields absent from generated 2023 are harmless.
for c in hist.columns:
    if c not in y23.columns: y23[c]=np.nan
y23=y23[hist.columns]
allpred=pd.concat([hist,y23],ignore_index=True)
allpred=score_rows(allpred)
# save parity/coordinate summary
coord={'Y2_origins':list(range(2014,2024)),'Y3_origins':list(range(2014,2023)),'Y2_rows':int(len(allpred[(allpred.horizon==2)&allpred.source_season.between(2014,2023)])),'Y3_rows':int(len(allpred[(allpred.horizon==3)&allpred.source_season.between(2014,2022)]))}
(OUT/'CANONICAL_COORDINATE.json').write_text(json.dumps(coord,indent=2))

origin_rows=[]; cell_rows=[]; loo_rows=[]; block_rows=[]; mag_bins=[]; struct_rows=[]; trans_rows=[]
for p in POSITIONS:
  for h in [2,3]:
    maxyr=2023 if h==2 else 2022
    for s in STAGES:
      q=allpred[(allpred.position==p)&(allpred.horizon==h)&(allpred.career_stage==s)&allpred.source_season.between(2014,maxyr)].copy()
      if len(q)==0: continue
      cur=current_candidate(p,h,s); alt='D0' if cur=='D1' else 'D1'; p0c=p0_candidate(p,h,s)
      q['gain']=q[f'crps_{alt}']-q[f'crps_{cur}'] # positive current better
      q['mae_gain']=q[f'mae_{alt}']-q[f'mae_{cur}']
      q['cur_crps']=q[f'crps_{cur}']; q['alt_crps']=q[f'crps_{alt}']; q['cur_mae']=q[f'mae_{cur}']; q['alt_mae']=q[f'mae_{alt}']
      q['cur_cond']=q[f'cond_{cur}']; q['cur_cond_ret']=q.cur_cond/q.source_points; q['cond_ret_bias']=np.where(q.target_state!='out',q.cur_cond_ret-q.realized_ret,np.nan)
      # origin summaries
      ors=[]
      for yr,g in q.groupby('source_season'):
        rec={'position':p,'horizon':h,'career_stage':s,'origin':int(yr),'n':len(g),'current':cur,'alternative':alt,'crps_gain_current_vs_alt':float(g.gain.mean()),'mae_gain_current_vs_alt':float(g.mae_gain.mean()),'current_crps':float(g.cur_crps.mean()),'alternative_crps':float(g.alt_crps.mean()),'current_mae':float(g.cur_mae.mean()),'alternative_mae':float(g.alt_mae.mean()),'active_n':int((g.target_state!='out').sum()),'p_active_mean':float(g.p_active.mean()),'actual_active_rate':float((g.target_state!='out').mean()),'conditional_active_retention_bias':float(np.nanmean(g.cond_ret_bias)) if np.isfinite(g.cond_ret_bias).any() else np.nan}
        origin_rows.append(rec); ors.append(rec)
      od=pd.DataFrame(ors)
      # pooled uncertainty
      gm,glo,ghi=two_way_boot(q,q.gain.to_numpy(),seed=SEED+hash((p,h,s))%100000)
      mm,mlo,mhi=two_way_boot(q,q.mae_gain.to_numpy(),seed=SEED+777+hash((p,h,s))%100000)
      bm,blo,bhi=moving_block_boot(od[['origin','n']].assign(gain=od.crps_gain_current_vs_alt),2 if h==2 else 3,seed=SEED+333+hash((p,h,s))%100000)
      improved=int((od.crps_gain_current_vs_alt>0).sum()); total=len(od); med=float(od.crps_gain_current_vs_alt.median()); worst=float(od.crps_gain_current_vs_alt.min())
      # LOO weighted row pooled
      loo=[]
      for yr in sorted(q.source_season.unique()):
        gg=q[q.source_season!=yr]; val=float(gg.gain.mean()); loo.append(val); loo_rows.append({'position':p,'horizon':h,'career_stage':s,'omitted_origin':int(yr),'n':len(gg),'crps_gain_current_vs_alt':val})
      loo_min=float(min(loo)); loo_max=float(max(loo)); loo_flip=bool(any(np.sign(x)!=np.sign(gm) and abs(x)>1e-12 for x in loo))
      ab,al,sb,sl=state_calibration(q)
      active=q[q.target_state!='out']; cb=float(np.nanmean(active.cond_ret_bias)) if len(active) else np.nan
      # structural diagnostic
      sd,per,kcounts=structural_diag(q,'target_points',boot_reps=300)
      struct_rows.append({'position':p,'horizon':h,'career_stage':s,'n':len(q),**sd})
      if len(per):
        for _,r in per.iterrows(): trans_rows.append({'position':p,'horizon':h,'career_stage':s,**r.to_dict()})
      # magnitude bins fixed deciles with adjacent pooling if low n? keep raw decile bins.
      q['mag_decile']=pd.cut(q.source_percentile,bins=np.linspace(0,1,11),include_lowest=True,right=True)
      for b,g in q.groupby('mag_decile',observed=True):
        aa=g[g.target_state!='out']
        mag_bins.append({'position':p,'horizon':h,'career_stage':s,'magnitude_bin':str(b),'n':len(g),'origins':int(g.source_season.nunique()),'source_percentile_mean':float(g.source_percentile.mean()),'source_points_mean':float(g.source_points.mean()),'target_points_mean':float(g.target_points.mean()),'active_rate':float((g.target_state!='out').mean()),'active_retention_mean':float(aa.realized_ret.mean()) if len(aa) else np.nan,'active_retention_median':float(aa.realized_ret.median()) if len(aa) else np.nan,'p_active_mean':float(g.p_active.mean()),'current_crps_mean':float(g.cur_crps.mean()),'alternative_crps_mean':float(g.alt_crps.mean()),'crps_gain_current_vs_alt':float(g.gain.mean()),'conditional_retention_bias_active':float(np.nanmean(aa.cond_ret_bias)) if len(aa) else np.nan})
      cell_rows.append({'position':p,'horizon':h,'career_stage':s,'p0_representation':p0c,'research_current':cur,'alternative':alt,'prior_status':PRIOR_STATUS[(p,h,s)],'n':len(q),'origins':total,'pooled_crps_gain_current_vs_alt':gm,'cluster_ci_low':glo,'cluster_ci_high':ghi,'block_boot_gain':bm,'block_ci_low':blo,'block_ci_high':bhi,'origins_improved':improved,'origin_share_improved':improved/total,'median_origin_gain':med,'worst_origin_regression':worst,'loo_gain_min':loo_min,'loo_gain_max':loo_max,'loo_sign_flip':loo_flip,'pooled_mae_gain_current_vs_alt':mm,'mae_ci_low':mlo,'mae_ci_high':mhi,'active_brier':ab,'active_logloss':al,'six_state_brier':sb,'six_state_logloss':sl,'conditional_active_retention_bias':cb,'magnitude_structure':sd['classification'],'struct_adequate_origins':sd['adequate_origins'],'best_piecewise_knot':sd['pooled_best_piecewise_knot'],'piecewise_origin_recurrence':sd['piecewise_origin_recurrence'],'bootstrap_knot_share':sd['bootstrap_best_knot_share']})

origin_df=pd.DataFrame(origin_rows); cell_df=pd.DataFrame(cell_rows); loo_df=pd.DataFrame(loo_rows); mag_df=pd.DataFrame(mag_bins); struct_df=pd.DataFrame(struct_rows); trans_df=pd.DataFrame(trans_rows)
# Determine dispositions with explicit rule, then RB dev structural unresolved override.
disps=[]
for _,r in cell_df.iterrows():
    strong_cur=(r.cluster_ci_low>0 and r.origin_share_improved>=.6 and not r.loo_sign_flip)
    strong_alt=(r.cluster_ci_high<0 and r.origin_share_improved<=.4 and not r.loo_sign_flip)
    same_dir=(r.pooled_crps_gain_current_vs_alt>0)
    if r.position=='RB' and r.horizon==3 and r.career_stage=='developmental':
        disp='UNRESOLVED'; reason='D1 remains strongly better than D0 on proper score, but continuous-magnitude structural concern remains unresolved by either frozen representation.'
    elif strong_cur:
        disp='CONFIRMED'; reason='Current frozen decision has positive clustered proper-score support, majority origin support, and no leave-one-origin sign reversal.'
    elif strong_alt:
        disp='REVERSED'; reason='Opposite frozen representation has negative current-vs-alt clustered interval, majority origin support, and no leave-one-origin sign reversal.'
    elif same_dir:
        disp='WEAKENED'; reason='Pooled direction still favors current decision but clustered and/or temporal stability criteria are weaker under expanded walk-forward.'
    else:
        disp='WEAKENED'; reason='Pooled proper-score direction no longer favors current decision, but evidence is not stable enough for a validation-stage reversal.'
    disps.append((disp,reason))
cell_df['revalidation_disposition']=[x[0] for x in disps]; cell_df['disposition_reason']=[x[1] for x in disps]
# Additional research flag
cell_df['additional_research_required']=cell_df.revalidation_disposition.isin(['REVERSED','UNRESOLVED']) | cell_df.prior_status.str.contains('EARNED') & (cell_df.revalidation_disposition!='CONFIRMED')

# developmental RB tail influence diagnostics continuous and p75/p90/p95 views.
rb=allpred[(allpred.position=='RB')&(allpred.horizon==3)&(allpred.career_stage=='developmental')&allpred.source_season.between(2014,2022)].copy()
rb['crps_D1_minus_D0']=rb.crps_D1-rb.crps_D0 # negative means D1 better
rb['d1_cond_ret']=rb.cond_D1/rb.source_points; rb['active_ret_bias_D1']=np.where(rb.target_state!='out',rb.d1_cond_ret-rb.realized_ret,np.nan)
tail=[]
for thr in [0,.75,.90,.95]:
 g=rb[rb.source_percentile>=thr]
 aa=g[g.target_state!='out']
 tail.append({'threshold':thr,'n':len(g),'origins':g.source_season.nunique(),'active_n':len(aa),'active_rate':(g.target_state!='out').mean(),'realized_active_retention_median':aa.realized_ret.median() if len(aa) else np.nan,'d1_active_retention_median':aa.d1_cond_ret.median() if len(aa) else np.nan,'d1_mean_active_retention_bias':aa.active_ret_bias_D1.mean() if len(aa) else np.nan,'D1_minus_D0_crps_mean':g.crps_D1.mean()-g.crps_D0.mean()})
# per-origin p90 influence and leave-one-origin full-cell bias
for yr,g in rb.groupby('source_season'):
 for thr in [.75,.90,.95]:
  q=g[g.source_percentile>=thr]; aa=q[q.target_state!='out']
  if len(q):
   block_rows.append({'kind':'RB_DEV_TAIL','origin':int(yr),'threshold':thr,'n':len(q),'active_n':len(aa),'active_rate':float((q.target_state!='out').mean()),'realized_active_retention_median':float(aa.realized_ret.median()) if len(aa) else np.nan,'d1_retention_bias':float(aa.active_ret_bias_D1.mean()) if len(aa) else np.nan,'D1_vs_D0_crps_gain':float(q.crps_D0.mean()-q.crps_D1.mean())})

pd.DataFrame(tail).to_csv(OUT/'DEVELOPMENTAL_RB_TAIL_WALKFORWARD_SUMMARY.csv',index=False)
pd.DataFrame(block_rows).to_csv(OUT/'DEVELOPMENTAL_RB_TAIL_BY_ORIGIN.csv',index=False)
origin_df.to_csv(OUT/'ORIGIN_BY_ORIGIN_SCORE_TABLE.csv',index=False)
cell_df.to_csv(OUT/'FORECAST_WIDE_AUTHORITY_MATRIX.csv',index=False)
loo_df.to_csv(OUT/'LEAVE_ONE_ORIGIN_OUT_RESULTS.csv',index=False)
mag_df.to_csv(OUT/'CONTINUOUS_MAGNITUDE_DIAGNOSTICS.csv',index=False)
struct_df.to_csv(OUT/'MAGNITUDE_STRUCTURE_SUMMARY.csv',index=False)
trans_df.to_csv(OUT/'TRANSITION_STABILITY_BY_ORIGIN.csv',index=False)
# compact transition bootstrap table inferred from struct summary
struct_df[['position','horizon','career_stage','classification','pooled_best_piecewise_knot','piecewise_origin_recurrence','bootstrap_best_knot','bootstrap_best_knot_share','quadratic_curvature_sign_stability']].to_csv(OUT/'TRANSITION_STABILITY_SUMMARY.csv',index=False)
# candidate-independent calibration by pos/h
cal=[]
for p in POSITIONS:
 for h in [2,3]:
  maxyr=2023 if h==2 else 2022; q=allpred[(allpred.position==p)&(allpred.horizon==h)&allpred.source_season.between(2014,maxyr)]
  ab,al,sb,sl=state_calibration(q); cal.append({'position':p,'horizon':h,'n':len(q),'origins':q.source_season.nunique(),'active_brier':ab,'active_logloss':al,'six_state_brier':sb,'six_state_logloss':sl,'actual_active_rate':(q.target_state!='out').mean(),'mean_p_active':q.p_active.mean()})
pd.DataFrame(cal).to_csv(OUT/'STATE_CALIBRATION_FORECAST_WIDE.csv',index=False)
# replay manifest
manifest={'schema_version':'fsffl-forecast-wide-walkforward-revalidation-v1','research_only':True,'candidate_fit':False,'coordinate':coord,'historical_predictions_sha256':hashlib.sha256(HIST.read_bytes()).hexdigest(),'y2_2023_prediction_sha256':hashlib.sha256(Y23.read_bytes()).hexdigest(),'p0_routes':P0_Y3,'research_y3_routes':RESEARCH_Y3,'bootstrap_reps':2000,'block_bootstrap_reps':5000,'structural_bootstrap_reps':300,'source_magnitude_knot_grid':[.6,.7,.8,.9],'production_authority_change':False,'pr147_change':False,'merge':False,'deploy':False}
(OUT/'REVALIDATION_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print('coord',coord)
print(cell_df[['position','horizon','career_stage','research_current','pooled_crps_gain_current_vs_alt','cluster_ci_low','cluster_ci_high','origin_share_improved','median_origin_gain','worst_origin_regression','loo_sign_flip','pooled_mae_gain_current_vs_alt','magnitude_structure','revalidation_disposition']].to_string(index=False))
import json, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logsumexp
from scipy.stats import norm

OUT=Path('/mnt/data/fsffl_mixture_20260919')
HIST=Path('/mnt/data/fsffl_diag/historical_predictions.csv')
Q3=Path('/mnt/data/fsffl_dist_shape_20260919/future-state-phase2/phase2_q3_age_state_rows.csv')
SEED=20260919
NBOOT=2000
NQ=199
BLOCKS={'early':(2014,2016,2013),'mid':(2017,2018,2016),'validation':(2019,2020,2018)}


def sha256(p):
    h=hashlib.sha256();
    with open(p,'rb') as f:
        for ch in iter(lambda:f.read(1<<20),b''): h.update(ch)
    return h.hexdigest()

# load/reconstruct source percentile for the full historical panel
q3=pd.read_csv(Q3)
q3['career_stage']=np.where(q3.experience<=3,'developmental',np.where(q3.experience<=8,'established','veteran'))
u=q3[(q3.horizon==1)&(q3.source_state!='out')][['source_season','player_id','position','source_points']].copy()
u['source_percentile']=np.nan
for _,idx in u.groupby(['source_season','position']).groups.items():
    v=u.loc[idx,'source_points']
    u.loc[idx,'source_percentile']=(v.rank(method='average')-0.5)/len(v)
q3=q3.merge(u[['source_season','player_id','position','source_percentile']],on=['source_season','player_id','position'],how='left')

hist=pd.read_csv(HIST)
keys=['source_season','player_id','position','horizon']
# parity on governed historical 2014-2022 prediction rows
par=hist[keys+['source_points','target_points']].merge(q3[keys+['source_points','target_points','source_percentile','experience','career_stage']],on=keys,suffixes=('_hist','_q3'),how='left',indicator=True)
assert (par._merge=='both').all()
assert np.max(np.abs(par.source_points_hist-par.source_points_q3))<1e-12
assert np.max(np.abs(par.target_points_hist-par.target_points_q3))<1e-12
# exact source percentile parity
assert np.max(np.abs(par.source_percentile-hist.source_percentile))<1e-12

# mixture fit

def logistic_fractional(X, r, beta, lam=1.0, max_iter=60):
    b=beta.copy().astype(float)
    for _ in range(max_iter):
        eta=X@b; p=expit(eta); w=np.maximum(p*(1-p),1e-9)
        grad=X.T@(r-p) - np.array([0.0,lam*b[1]])
        H=-(X.T@(w[:,None]*X)) - np.diag([0.0,lam])
        try: step=np.linalg.solve(H,grad)
        except np.linalg.LinAlgError: step=np.linalg.pinv(H)@grad
        nb=b-step
        if np.max(np.abs(nb-b))<1e-10: b=nb; break
        b=nb
    return b

def fit_m1(train, init=(0.30,0.70), lam=1.0):
    d=train[(train.target_points>0)&(train.source_points>0)].copy()
    y=np.log(d.target_points.to_numpy(float)/d.source_points.to_numpy(float))
    u=d.source_percentile.to_numpy(float)
    X=np.column_stack([np.ones(len(d)),u-0.5])
    mu=np.quantile(y,list(init)).astype(float)
    sd0=float(np.std(y,ddof=1)); sig=np.array([max(sd0,0.15),max(sd0,0.15)],float)
    beta=np.array([0.0,0.0])
    llprev=-np.inf
    for it in range(200):
        pi=expit(X@beta)
        logd=np.column_stack([
            np.log(np.maximum(1-pi,1e-15))+norm.logpdf(y,mu[0],sig[0]),
            np.log(np.maximum(pi,1e-15))+norm.logpdf(y,mu[1],sig[1])
        ])
        den=logsumexp(logd,axis=1)
        r=np.exp(logd[:,1]-den)
        w0=1-r; w1=r
        mu=np.array([(w0@y)/w0.sum(),(w1@y)/w1.sum()])
        var=np.array([(w0@((y-mu[0])**2))/w0.sum(),(w1@((y-mu[1])**2))/w1.sum()])
        sig=np.sqrt(np.maximum(var,1e-4))
        beta=logistic_fractional(X,r,beta,lam=lam)
        # label order
        if mu[0]>mu[1]:
            mu=mu[::-1]; sig=sig[::-1]; beta=-beta
        # penalized ll
        pi=expit(X@beta)
        logd=np.column_stack([
            np.log(np.maximum(1-pi,1e-15))+norm.logpdf(y,mu[0],sig[0]),
            np.log(np.maximum(pi,1e-15))+norm.logpdf(y,mu[1],sig[1])
        ])
        ll=float(logsumexp(logd,axis=1).sum()-0.5*lam*beta[1]**2)
        if np.isfinite(llprev) and abs(ll-llprev)<=1e-8*(1+abs(llprev)): break
        llprev=ll
    # final responsibilities/support
    pi=expit(X@beta)
    logd=np.column_stack([
        np.log(np.maximum(1-pi,1e-15))+norm.logpdf(y,mu[0],sig[0]),
        np.log(np.maximum(pi,1e-15))+norm.logpdf(y,mu[1],sig[1])
    ])
    den=logsumexp(logd,axis=1); r=np.exp(logd[:,1]-den)
    return {
        'mu_decline':float(mu[0]),'mu_survivor':float(mu[1]),
        'sigma_decline':float(sig[0]),'sigma_survivor':float(sig[1]),
        'beta0':float(beta[0]),'beta1':float(beta[1]),
        'n_active':int(len(d)),'ess_decline':float((1-r).sum()),'ess_survivor':float(r.sum()),
        'iterations':it+1,'penalized_loglik':ll,
        'source_percentile_min':float(u.min()),'source_percentile_max':float(u.max())
    }

def model_pi(m,u): return expit(m['beta0']+m['beta1']*(u-0.5))

qgrid=(np.arange(NQ)+0.5)/NQ
zgrid=norm.ppf(qgrid)

def weighted_crps(xs,ws,y):
    order=np.argsort(xs); x=np.asarray(xs)[order]; w=np.asarray(ws)[order]
    w=w/w.sum()
    e1=float(np.sum(w*np.abs(x-y)))
    cb=np.concatenate([[0.0],np.cumsum(w)[:-1]])
    e2=float(2*np.sum(w*x*(2*cb+w-1)))
    return e1-0.5*e2

def d1_support(row):
    vals=np.array([0.0,row.d1_mean_depth,row.d1_mean_usable,row.d1_mean_starter,row.d1_mean_premium,row.d1_mean_elite],float)
    ws=np.array([row.p_out,row.p_depth,row.p_usable,row.p_starter,row.p_premium,row.p_elite],float)
    ws=np.maximum(ws,0); ws=ws/ws.sum()
    return vals,ws

def m1_support(row,m):
    p0=float(row.p_out); pa=1-p0; pi=float(model_pi(m,float(row.source_percentile)))
    x0=float(row.source_points)*np.exp(m['mu_decline']+m['sigma_decline']*zgrid)
    x1=float(row.source_points)*np.exp(m['mu_survivor']+m['sigma_survivor']*zgrid)
    vals=np.concatenate([[0.0],x0,x1])
    ws=np.concatenate([[p0],np.full(NQ,pa*(1-pi)/NQ),np.full(NQ,pa*pi/NQ)])
    return vals,ws

def region_probs_from_support(vals,ws,source):
    r=np.asarray(vals)/float(source); w=np.asarray(ws)
    return np.array([w[vals==0].sum(),w[(vals>0)&(r<0.4)].sum(),w[(vals>0)&(r>=0.4)&(r<0.7)].sum(),w[(vals>0)&(r>=0.7)].sum()])

def m1_region_probs(row,m):
    p0=float(row.p_out); pa=1-p0; pi=float(model_pi(m,float(row.source_percentile)))
    # log retention ~ mixture normals
    t04=np.log(0.4); t07=np.log(0.7)
    c04=(1-pi)*norm.cdf((t04-m['mu_decline'])/m['sigma_decline'])+pi*norm.cdf((t04-m['mu_survivor'])/m['sigma_survivor'])
    c07=(1-pi)*norm.cdf((t07-m['mu_decline'])/m['sigma_decline'])+pi*norm.cdf((t07-m['mu_survivor'])/m['sigma_survivor'])
    return np.array([p0,pa*c04,pa*(c07-c04),pa*(1-c07)])

def observed_region(row):
    y=float(row.target_points); s=float(row.source_points)
    if y<=0:return 0
    rr=y/s
    if rr<.4:return 1
    if rr<.7:return 2
    return 3

def expected_m1(row,m):
    p0=float(row.p_out); pa=1-p0; pi=float(model_pi(m,float(row.source_percentile)))
    er=(1-pi)*math.exp(m['mu_decline']+0.5*m['sigma_decline']**2)+pi*math.exp(m['mu_survivor']+0.5*m['sigma_survivor']**2)
    return pa*float(row.source_points)*er

def pit_support(vals,ws,y):
    vals=np.asarray(vals); ws=np.asarray(ws); lt=ws[vals<y].sum(); eq=ws[np.isclose(vals,y,atol=1e-12)].sum(); return float(lt+0.5*eq)

def m1_cdf_mid(row,m):
    y=float(row.target_points); p0=float(row.p_out); pa=1-p0; pi=float(model_pi(m,float(row.source_percentile)))
    if y<=0:return 0.5*p0
    lr=math.log(y/float(row.source_points))
    c=(1-pi)*norm.cdf((lr-m['mu_decline'])/m['sigma_decline'])+pi*norm.cdf((lr-m['mu_survivor'])/m['sigma_survivor'])
    return p0+pa*c

def score_rows(ev,m,candidate='M1'):
    rows=[]
    for row in ev.itertuples(index=False):
        dvals,dw=d1_support(row); mvals,mw=m1_support(row,m)
        obs=observed_region(row); one=np.eye(4)[obs]
        pd1=region_probs_from_support(dvals,dw,row.source_points); pm=m1_region_probs(row,m)
        d1exp=float(np.sum(dvals*dw)); mexp=expected_m1(row,m)
        rows.append({
            'source_season':int(row.source_season),'player_id':row.player_id,'horizon':int(row.horizon),'source_points':float(row.source_points),'source_percentile':float(row.source_percentile),'target_points':float(row.target_points),
            'observed_region':obs,'d1_crps':weighted_crps(dvals,dw,row.target_points),'m1_crps':weighted_crps(mvals,mw,row.target_points),
            'd1_mae':abs(d1exp-row.target_points),'m1_mae':abs(mexp-row.target_points),'d1_expected':d1exp,'m1_expected':mexp,
            'd1_brier4':float(np.sum((pd1-one)**2)),'m1_brier4':float(np.sum((pm-one)**2)),
            'd1_logloss4':float(-math.log(max(pd1[obs],1e-12))),'m1_logloss4':float(-math.log(max(pm[obs],1e-12))),
            'd1_survivor_p':float(pd1[3]),'m1_survivor_p':float(pm[3]),'d1_downside_p':float(pd1[0]+pd1[1]),'m1_downside_p':float(pm[0]+pm[1]),
            'd1_pit':pit_support(dvals,dw,row.target_points),'m1_pit':m1_cdf_mid(row,m),
            'p_out':float(row.p_out),'m1_pi_survivor':float(model_pi(m,float(row.source_percentile))),
            'prob_norm_error':float(abs(pm.sum()-1.0)),
        })
    return pd.DataFrame(rows)

def block_summary(sc,block,horizon):
    d={
      'block':block,'horizon':horizon,'n':len(sc),
      'd1_crps':sc.d1_crps.mean(),'m1_crps':sc.m1_crps.mean(),'crps_gain':(sc.d1_crps-sc.m1_crps).mean(),
      'd1_brier4':sc.d1_brier4.mean(),'m1_brier4':sc.m1_brier4.mean(),'brier4_gain':(sc.d1_brier4-sc.m1_brier4).mean(),
      'd1_logloss4':sc.d1_logloss4.mean(),'m1_logloss4':sc.m1_logloss4.mean(),
      'd1_mae':sc.d1_mae.mean(),'m1_mae':sc.m1_mae.mean(),'mae_gain':(sc.d1_mae-sc.m1_mae).mean(),
      'mean_expected_change':(sc.m1_expected-sc.d1_expected).mean(),
      'max_prob_norm_error':sc.prob_norm_error.max(),
      'd1_pit_mean':sc.d1_pit.mean(),'m1_pit_mean':sc.m1_pit.mean(),
      'd1_pit_var':sc.d1_pit.var(ddof=0),'m1_pit_var':sc.m1_pit.var(ddof=0),
    }
    return d

def two_way_boot(df, cols, nboot=NBOOT, seed=SEED):
    rng=np.random.default_rng(seed)
    players=np.array(sorted(df.player_id.astype(str).unique())); seasons=np.array(sorted(df.source_season.unique()))
    base={c:float(df[c].mean()) for c in cols}
    vals={c:[] for c in cols}
    pidx={p:i for i,p in enumerate(players)}; sidx={s:i for i,s in enumerate(seasons)}
    pi=df.player_id.astype(str).map(pidx).to_numpy(); si=df.source_season.map(sidx).to_numpy()
    for _ in range(nboot):
        pc=np.bincount(rng.integers(0,len(players),len(players)),minlength=len(players))
        sc=np.bincount(rng.integers(0,len(seasons),len(seasons)),minlength=len(seasons))
        w=pc[pi]*sc[si]
        if w.sum()==0: continue
        for c in cols: vals[c].append(float(np.average(df[c].to_numpy(float),weights=w)))
    out={}
    for c in cols:
        a=np.array(vals[c]); out[c]={'mean':base[c],'ci_low':float(np.quantile(a,.025)),'ci_high':float(np.quantile(a,.975)),'nboot':len(a)}
    return out

# prepare selection evaluation rows from exact historical predictions
sel=hist[(hist.position=='RB')&(hist.career_stage=='developmental')&(hist.source_season.between(2014,2020))].copy()
# fit/evaluate block models
params=[]; sens=[]; score_parts=[]; summaries=[]
for block,(lo,hi,cutoff) in BLOCKS.items():
  for h in (2,3):
    maxsrc=cutoff-h
    train=q3[(q3.position=='RB')&(q3.career_stage=='developmental')&(q3.horizon==h)&(q3.source_season<=maxsrc)&(q3.source_state!='out')].copy()
    m=fit_m1(train,(.30,.70)); m_alt=fit_m1(train,(.25,.75))
    rec={'block':block,'horizon':h,'training_cutoff':cutoff,'training_source_max':maxsrc,**m}; params.append(rec)
    sens.append({'block':block,'horizon':h,
      'abs_mu_decline_diff':abs(m['mu_decline']-m_alt['mu_decline']),
      'abs_mu_survivor_diff':abs(m['mu_survivor']-m_alt['mu_survivor']),
      'abs_sigma_decline_diff':abs(m['sigma_decline']-m_alt['sigma_decline']),
      'abs_sigma_survivor_diff':abs(m['sigma_survivor']-m_alt['sigma_survivor']),
      'abs_beta0_diff':abs(m['beta0']-m_alt['beta0']),'abs_beta1_diff':abs(m['beta1']-m_alt['beta1']),
      'ess_decline':m['ess_decline'],'ess_survivor':m['ess_survivor']})
    ev=sel[(sel.horizon==h)&(sel.source_season.between(lo,hi))].copy()
    sc=score_rows(ev,m); sc['block']=block; score_parts.append(sc); summaries.append(block_summary(sc,block,h))
score=pd.concat(score_parts,ignore_index=True); sm=pd.DataFrame(summaries); pm=pd.DataFrame(params); sn=pd.DataFrame(sens)
score.to_csv(OUT/'SELECTION_ROW_SCORES.csv',index=False)
sm.to_csv(OUT/'SELECTION_BLOCK_METRICS.csv',index=False)
pm.to_csv(OUT/'M1_FITTED_PARAMETERS_SELECTION.csv',index=False)
sn.to_csv(OUT/'M1_INITIALIZATION_SENSITIVITY.csv',index=False)

# pooled bootstrap per horizon and subset
boot_rows=[]
for h in (2,3):
  g=score[score.horizon==h].copy()
  g['crps_gain']=g.d1_crps-g.m1_crps; g['brier4_gain']=g.d1_brier4-g.m1_brier4; g['mae_gain']=g.d1_mae-g.m1_mae
  g['survivor_brier_gain']=( ( (g.observed_region==3).astype(float)-g.d1_survivor_p)**2 - ((g.observed_region==3).astype(float)-g.m1_survivor_p)**2 )
  g['downside_brier_gain']=( ( (g.observed_region.isin([0,1])).astype(float)-g.d1_downside_p)**2 - ((g.observed_region.isin([0,1])).astype(float)-g.m1_downside_p)**2 )
  for subset,gg in [('full',g),('sub_p90',g[g.source_percentile<.9]),('p90plus',g[g.source_percentile>=.9]),('p95plus',g[g.source_percentile>=.95])]:
    if len(gg)==0: continue
    br=two_way_boot(gg,['crps_gain','brier4_gain','mae_gain','survivor_brier_gain','downside_brier_gain'],seed=SEED+h*100+len(subset))
    for metric,v in br.items(): boot_rows.append({'horizon':h,'subset':subset,'metric':metric,**v,'n':len(gg)})
boot=pd.DataFrame(boot_rows); boot.to_csv(OUT/'SELECTION_BOOTSTRAP_GAINS.csv',index=False)

# outcome mass / p95 tail calibration
def mass_table(sc,h,subset_name,mask):
    g=sc[(sc.horizon==h)&mask(sc)].copy(); n=len(g)
    obs=np.bincount(g.observed_region,minlength=4)/n
    d1=np.array([(g.observed_region*0 + 0).mean()]*4) # placeholder
    # predicted region means reconstruct from stored survivor/downside + need all categories from baseline candidate supports; recompute by joining hist/model block
    return g,obs

# Recompute predicted four-region probabilities rowwise using each row's block model, save columns not previously retained
# Extend score with full probs
model_map={(r['block'],int(r['horizon'])):r for r in params}
prob_rows=[]
for row in sel.itertuples(index=False):
    if row.source_season<=2016:block='early'
    elif row.source_season<=2018:block='mid'
    else:block='validation'
    m=model_map[(block,int(row.horizon))]
    dvals,dw=d1_support(row); pd1=region_probs_from_support(dvals,dw,row.source_points); pm1=m1_region_probs(row,m)
    prob_rows.append({'source_season':row.source_season,'player_id':row.player_id,'horizon':row.horizon,'source_percentile':row.source_percentile,'target_points':row.target_points,'source_points':row.source_points,'block':block,
                      **{f'd1_p{i}':pd1[i] for i in range(4)},**{f'm1_p{i}':pm1[i] for i in range(4)},'observed_region':observed_region(row)})
pr=pd.DataFrame(prob_rows); pr.to_csv(OUT/'SELECTION_REGION_PROBABILITIES.csv',index=False)
cal=[]
for h in (2,3):
  for subset,mask in [('full',lambda x:np.ones(len(x),dtype=bool)),('sub_p90',lambda x:x.source_percentile<.9),('p90plus',lambda x:x.source_percentile>=.9),('p95plus',lambda x:x.source_percentile>=.95)]:
    g=pr[(pr.horizon==h)&mask(pr)].copy()
    if len(g)==0: continue
    obs=np.bincount(g.observed_region,minlength=4)/len(g)
    for cand in ('D1','M1'):
      pred=np.array([g[f'{cand.lower()}_p{i}'].mean() for i in range(4)])
      cal.append({'horizon':h,'subset':subset,'candidate':cand,'n':len(g),
                  'obs_out':obs[0],'obs_decline':obs[1],'obs_middle':obs[2],'obs_survivor':obs[3],
                  'pred_out':pred[0],'pred_decline':pred[1],'pred_middle':pred[2],'pred_survivor':pred[3],
                  'downside_obs':obs[0]+obs[1],'downside_pred':pred[0]+pred[1],
                  'survivor_abs_error':abs(pred[3]-obs[3]),'downside_abs_error':abs(pred[0]+pred[1]-(obs[0]+obs[1])),
                  'combined_tail_abs_error':abs(pred[3]-obs[3])+abs(pred[0]+pred[1]-(obs[0]+obs[1]))})
cal=pd.DataFrame(cal); cal.to_csv(OUT/'SELECTION_OUTCOME_MASS_CALIBRATION.csv',index=False)

# p95 gate details
g=cal[(cal.horizon==3)&(cal['subset']=='p95plus')].set_index('candidate')
p95_imp=float(g.loc['D1','combined_tail_abs_error']-g.loc['M1','combined_tail_abs_error'])
# preholdout decisions
b3=boot[(boot.horizon==3)&(boot['subset']=='full')].set_index('metric')
b3sub=boot[(boot.horizon==3)&(boot['subset']=='sub_p90')].set_index('metric')
b2=boot[(boot.horizon==2)&(boot['subset']=='full')].set_index('metric')
all_crps=(sm[sm.horizon==3].crps_gain>0).all(); brier_neg=(sm[(sm.horizon==3)].brier4_gain<0).sum()
sens_pass=((sn.abs_mu_decline_diff<.10)&(sn.abs_mu_survivor_diff<.10)&(sn.abs_beta1_diff<.10)&(sn.ess_decline>=20)&(sn.ess_survivor>=20)).all()
pre={
 'schema_version':'fsffl-dev-rb-two-component-preholdout-v1','holdout_touched':False,'candidate':'M1',
 'M2':'NOT_AUTHORIZED_PRIOR_IDENTIFIABILITY_GATE_FAILED',
 'Y3':{
   'crps_all_blocks_positive':bool(all_crps),'full_crps_gain':b3.loc['crps_gain'].to_dict(),
   'full_brier4_gain':b3.loc['brier4_gain'].to_dict(),'brier_negative_blocks':int(brier_neg),
   'mae_gain':b3.loc['mae_gain'].to_dict(),'sub_p90_crps_gain':b3sub.loc['crps_gain'].to_dict(),
   'p95_tail_error_improvement':p95_imp,
   'p95_observed_survivor':float(g.loc['D1','obs_survivor']),'p95_D1_survivor':float(g.loc['D1','pred_survivor']),'p95_M1_survivor':float(g.loc['M1','pred_survivor']),
   'p95_observed_downside':float(g.loc['D1','downside_obs']),'p95_D1_downside':float(g.loc['D1','downside_pred']),'p95_M1_downside':float(g.loc['M1','downside_pred']),
   'initialization_and_support_pass':bool(sens_pass),'max_prob_norm_error':float(score[score.horizon==3].prob_norm_error.max())
 },
 'Y2_no_harm':{'crps_gain':b2.loc['crps_gain'].to_dict(),'mae_gain':b2.loc['mae_gain'].to_dict(),'max_block_crps_degradation':float(max(0,-sm[sm.horizon==2].crps_gain.min()))},
}
# Gates
reasons=[]
pass_crps=all_crps and b3.loc['crps_gain','ci_low']>0
pass_brier=(b3.loc['brier4_gain','ci_low']>0 and brier_neg<=1)
pass_tail=(p95_imp>=.05 and (float(g.loc['M1','pred_survivor'])>=float(g.loc['M1','obs_survivor'])-.05) and (float(g.loc['M1','downside_pred'])>=float(g.loc['M1','downside_obs'])-.05))
pass_mae=(b3.loc['mae_gain','mean']>=-1 and b3.loc['mae_gain','ci_high']>=0)
pass_sub=(b3sub.loc['crps_gain','mean']>=-1 and b3sub.loc['crps_gain','ci_high']>=0)
pass_y2=(b2.loc['crps_gain','mean']>=-1 and b2.loc['crps_gain','ci_high']>=0 and b2.loc['mae_gain','mean']>=-1 and b2.loc['mae_gain','ci_high']>=0 and pre['Y2_no_harm']['max_block_crps_degradation']<=1)
for name,val in [('crps',pass_crps),('brier',pass_brier),('p95_tail',pass_tail),('mae',pass_mae),('sub_p90',pass_sub),('support_sensitivity',sens_pass),('probability_normalization',pre['Y3']['max_prob_norm_error']<=1e-12),('Y2_no_harm',pass_y2)]:
    if not val: reasons.append(name)
pre['gate_results']={'CRPS':bool(pass_crps),'Brier4':bool(pass_brier),'p95_tail':bool(pass_tail),'MAE':bool(pass_mae),'sub_p90':bool(pass_sub),'support_sensitivity':bool(sens_pass),'probability_normalization':bool(pre['Y3']['max_prob_norm_error']<=1e-12),'Y2_no_harm':bool(pass_y2)}
pre['preholdout_decision']='PASS_PREHOLDOUT' if not reasons else 'FAIL_PREHOLDOUT'
pre['failure_reasons']=reasons
pre['holdout_rule']='Evaluate 2021-2022 exactly once after this file is persisted. Holdout cannot rescue or redesign a pre-holdout failure.'
with open(OUT/'PREHOLDOUT_DECISION.json','w') as f: json.dump(pre,f,indent=2,sort_keys=True)

# provenance
prov={
 'schema_version':'fsffl-dev-rb-two-component-provenance-v1','research_start_head':'acd0ede3f5e09cf1e559707d04ffc8baa86a0d13','preregistered_commit':'65340db8caff6a9fd16cb5334f3f9f6532987e51',
 'historical_predictions_sha256':sha256(HIST),'historical_predictions_rows':len(hist),'phase2_q3_sha256':sha256(Q3),'phase2_q3_rows':len(q3),
 'source_percentile_parity_max_abs':float(np.max(np.abs(par.source_percentile-hist.source_percentile))),
 'source_points_parity_max_abs':float(np.max(np.abs(par.source_points_hist-par.source_points_q3))),
 'target_points_parity_max_abs':float(np.max(np.abs(par.target_points_hist-par.target_points_q3))),
 'selection_source_seasons':[2014,2020],'holdout_source_seasons':[2021,2022],'holdout_touched':False,'quantile_grid_points':NQ,'bootstrap_reps':NBOOT,
 'candidate':'M1 two-component active log-retention mixture','M2':'not authorized because prior identifiability gate failed'
}
with open(OUT/'PROVENANCE_MANIFEST_PREHOLDOUT.json','w') as f: json.dump(prov,f,indent=2,sort_keys=True)
print(json.dumps(pre,indent=2))
print('\nParameters:'); print(pm.to_string(index=False))
print('\nBlock metrics:'); print(sm.to_string(index=False))
print('\nP95 calibration:'); print(g.to_string())
import json, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logsumexp
from scipy.stats import norm

OUT=Path('/mnt/data/fsffl_mixture_20260919')
HIST=Path('/mnt/data/fsffl_diag/historical_predictions.csv')
Q3=Path('/mnt/data/fsffl_dist_shape_20260919/future-state-phase2/phase2_q3_age_state_rows.csv')
SEED=20260919; NBOOT=2000; NQ=199
pre=json.load(open(OUT/'PREHOLDOUT_DECISION.json'))
assert pre['holdout_touched'] is False
# Confirm preholdout decision file existed before this process by checking its saved content only; no selection fitting here.
q3=pd.read_csv(Q3); q3['career_stage']=np.where(q3.experience<=3,'developmental',np.where(q3.experience<=8,'established','veteran'))
u=q3[(q3.horizon==1)&(q3.source_state!='out')][['source_season','player_id','position','source_points']].copy(); u['source_percentile']=np.nan
for _,idx in u.groupby(['source_season','position']).groups.items():
    v=u.loc[idx,'source_points']; u.loc[idx,'source_percentile']=(v.rank(method='average')-0.5)/len(v)
q3=q3.merge(u[['source_season','player_id','position','source_percentile']],on=['source_season','player_id','position'],how='left')
hist=pd.read_csv(HIST)

def logistic_fractional(X,r,beta,lam=1.0,max_iter=60):
    b=beta.copy().astype(float)
    for _ in range(max_iter):
        p=expit(X@b); w=np.maximum(p*(1-p),1e-9)
        grad=X.T@(r-p)-np.array([0.0,lam*b[1]])
        H=-(X.T@(w[:,None]*X))-np.diag([0.0,lam])
        try:step=np.linalg.solve(H,grad)
        except np.linalg.LinAlgError:step=np.linalg.pinv(H)@grad
        nb=b-step
        if np.max(np.abs(nb-b))<1e-10:b=nb;break
        b=nb
    return b

def fit_m1(train,init=(.30,.70),lam=1.0):
    d=train[(train.target_points>0)&(train.source_points>0)].copy(); y=np.log(d.target_points.to_numpy(float)/d.source_points.to_numpy(float)); u=d.source_percentile.to_numpy(float)
    X=np.column_stack([np.ones(len(d)),u-.5]); mu=np.quantile(y,list(init)).astype(float); sd0=float(np.std(y,ddof=1)); sig=np.array([max(sd0,.15),max(sd0,.15)],float); beta=np.array([0.,0.]); llprev=-np.inf
    for it in range(200):
        pi=expit(X@beta); ld=np.column_stack([np.log(np.maximum(1-pi,1e-15))+norm.logpdf(y,mu[0],sig[0]),np.log(np.maximum(pi,1e-15))+norm.logpdf(y,mu[1],sig[1])]); den=logsumexp(ld,axis=1); r=np.exp(ld[:,1]-den)
        w0=1-r;w1=r;mu=np.array([(w0@y)/w0.sum(),(w1@y)/w1.sum()]);var=np.array([(w0@((y-mu[0])**2))/w0.sum(),(w1@((y-mu[1])**2))/w1.sum()]);sig=np.sqrt(np.maximum(var,1e-4));beta=logistic_fractional(X,r,beta,lam)
        if mu[0]>mu[1]:mu=mu[::-1];sig=sig[::-1];beta=-beta
        pi=expit(X@beta);ld=np.column_stack([np.log(np.maximum(1-pi,1e-15))+norm.logpdf(y,mu[0],sig[0]),np.log(np.maximum(pi,1e-15))+norm.logpdf(y,mu[1],sig[1])]);ll=float(logsumexp(ld,axis=1).sum()-.5*lam*beta[1]**2)
        if np.isfinite(llprev) and abs(ll-llprev)<=1e-8*(1+abs(llprev)):break
        llprev=ll
    pi=expit(X@beta);ld=np.column_stack([np.log(np.maximum(1-pi,1e-15))+norm.logpdf(y,mu[0],sig[0]),np.log(np.maximum(pi,1e-15))+norm.logpdf(y,mu[1],sig[1])]);den=logsumexp(ld,axis=1);r=np.exp(ld[:,1]-den)
    return {'mu_decline':float(mu[0]),'mu_survivor':float(mu[1]),'sigma_decline':float(sig[0]),'sigma_survivor':float(sig[1]),'beta0':float(beta[0]),'beta1':float(beta[1]),'n_active':len(d),'ess_decline':float((1-r).sum()),'ess_survivor':float(r.sum()),'iterations':it+1}

def pi(m,u):return expit(m['beta0']+m['beta1']*(u-.5))
qgrid=(np.arange(NQ)+.5)/NQ;zgrid=norm.ppf(qgrid)
def crps(xs,ws,y):
    o=np.argsort(xs);x=np.asarray(xs)[o];w=np.asarray(ws)[o];w=w/w.sum();e1=np.sum(w*np.abs(x-y));cb=np.r_[0,np.cumsum(w)[:-1]];e2=2*np.sum(w*x*(2*cb+w-1));return float(e1-.5*e2)
def d1sup(r):
    x=np.array([0,r.d1_mean_depth,r.d1_mean_usable,r.d1_mean_starter,r.d1_mean_premium,r.d1_mean_elite],float);w=np.array([r.p_out,r.p_depth,r.p_usable,r.p_starter,r.p_premium,r.p_elite],float);w=np.maximum(w,0);w/=w.sum();return x,w
def m1sup(r,m):
    p0=float(r.p_out);pa=1-p0;p=float(pi(m,float(r.source_percentile)));x0=float(r.source_points)*np.exp(m['mu_decline']+m['sigma_decline']*zgrid);x1=float(r.source_points)*np.exp(m['mu_survivor']+m['sigma_survivor']*zgrid);x=np.r_[0,x0,x1];w=np.r_[p0,np.full(NQ,pa*(1-p)/NQ),np.full(NQ,pa*p/NQ)];return x,w
def probs_sup(x,w,s):
    rr=x/s;return np.array([w[x==0].sum(),w[(x>0)&(rr<.4)].sum(),w[(x>0)&(rr>=.4)&(rr<.7)].sum(),w[(x>0)&(rr>=.7)].sum()])
def probs_m1(r,m):
    p0=float(r.p_out);pa=1-p0;p=float(pi(m,float(r.source_percentile)));a=np.log(.4);b=np.log(.7);c4=(1-p)*norm.cdf((a-m['mu_decline'])/m['sigma_decline'])+p*norm.cdf((a-m['mu_survivor'])/m['sigma_survivor']);c7=(1-p)*norm.cdf((b-m['mu_decline'])/m['sigma_decline'])+p*norm.cdf((b-m['mu_survivor'])/m['sigma_survivor']);return np.array([p0,pa*c4,pa*(c7-c4),pa*(1-c7)])
def obsreg(r):
    if r.target_points<=0:return 0
    rr=r.target_points/r.source_points
    return 1 if rr<.4 else (2 if rr<.7 else 3)
def expm1(r,m):
    p=float(pi(m,float(r.source_percentile)));er=(1-p)*math.exp(m['mu_decline']+.5*m['sigma_decline']**2)+p*math.exp(m['mu_survivor']+.5*m['sigma_survivor']**2);return (1-r.p_out)*r.source_points*er

def score(ev,m):
    rows=[]
    for r in ev.itertuples(index=False):
        dx,dw=d1sup(r);mx,mw=m1sup(r,m);o=obsreg(r);one=np.eye(4)[o];pd1=probs_sup(dx,dw,r.source_points);pm=probs_m1(r,m);de=float(np.sum(dx*dw));me=expm1(r,m)
        rows.append({'source_season':r.source_season,'player_id':r.player_id,'horizon':r.horizon,'source_percentile':r.source_percentile,'source_points':r.source_points,'target_points':r.target_points,'observed_region':o,'d1_crps':crps(dx,dw,r.target_points),'m1_crps':crps(mx,mw,r.target_points),'d1_mae':abs(de-r.target_points),'m1_mae':abs(me-r.target_points),'d1_brier4':float(np.sum((pd1-one)**2)),'m1_brier4':float(np.sum((pm-one)**2)),'d1_logloss4':float(-math.log(max(pd1[o],1e-12))),'m1_logloss4':float(-math.log(max(pm[o],1e-12))),'d1_expected':de,'m1_expected':me,'d1_survivor_p':pd1[3],'m1_survivor_p':pm[3],'d1_downside_p':pd1[0]+pd1[1],'m1_downside_p':pm[0]+pm[1],'p_out':r.p_out,'pi_survivor':pi(m,r.source_percentile),'prob_norm_error':abs(pm.sum()-1)})
    return pd.DataFrame(rows)
def twoboot(df,cols,seed):
    rng=np.random.default_rng(seed);players=np.array(sorted(df.player_id.astype(str).unique()));seasons=np.array(sorted(df.source_season.unique()));pmap={p:i for i,p in enumerate(players)};smap={s:i for i,s in enumerate(seasons)};pii=df.player_id.astype(str).map(pmap).to_numpy();sii=df.source_season.map(smap).to_numpy();vals={c:[] for c in cols}
    for _ in range(NBOOT):
        pc=np.bincount(rng.integers(0,len(players),len(players)),minlength=len(players));sc=np.bincount(rng.integers(0,len(seasons),len(seasons)),minlength=len(seasons));w=pc[pii]*sc[sii]
        if w.sum()==0:continue
        for c in cols: vals[c].append(float(np.average(df[c],weights=w)))
    return {c:{'mean':float(df[c].mean()),'ci_low':float(np.quantile(vals[c],.025)),'ci_high':float(np.quantile(vals[c],.975)),'nboot':len(vals[c])} for c in cols}

hold=hist[(hist.position=='RB')&(hist.career_stage=='developmental')&(hist.source_season.between(2021,2022))].copy()
params=[];parts=[];sens=[]
for h in (2,3):
    maxsrc=2020-h
    tr=q3[(q3.position=='RB')&(q3.career_stage=='developmental')&(q3.horizon==h)&(q3.source_season<=maxsrc)&(q3.source_state!='out')].copy()
    m=fit_m1(tr,(.30,.70)); ma=fit_m1(tr,(.25,.75)); params.append({'horizon':h,'training_cutoff':2020,'training_source_max':maxsrc,**m});sens.append({'horizon':h,'abs_mu_decline_diff':abs(m['mu_decline']-ma['mu_decline']),'abs_mu_survivor_diff':abs(m['mu_survivor']-ma['mu_survivor']),'abs_beta1_diff':abs(m['beta1']-ma['beta1'])})
    sc=score(hold[hold.horizon==h],m);parts.append(sc)
sc=pd.concat(parts,ignore_index=True);pd.DataFrame(params).to_csv(OUT/'LOCKED_M1_PARAMETERS.csv',index=False);pd.DataFrame(sens).to_csv(OUT/'LOCKED_M1_INITIALIZATION_SENSITIVITY.csv',index=False);sc.to_csv(OUT/'LOCKED_2021_2022_ROW_SCORES.csv',index=False)
metrics=[];boots=[];cal=[]
for h in (2,3):
    g=sc[sc.horizon==h].copy();g['crps_gain']=g.d1_crps-g.m1_crps;g['brier4_gain']=g.d1_brier4-g.m1_brier4;g['mae_gain']=g.d1_mae-g.m1_mae
    metrics.append({'horizon':h,'n':len(g),'d1_crps':g.d1_crps.mean(),'m1_crps':g.m1_crps.mean(),'crps_gain':g.crps_gain.mean(),'d1_brier4':g.d1_brier4.mean(),'m1_brier4':g.m1_brier4.mean(),'brier4_gain':g.brier4_gain.mean(),'d1_mae':g.d1_mae.mean(),'m1_mae':g.m1_mae.mean(),'mae_gain':g.mae_gain.mean(),'mean_expected_change':(g.m1_expected-g.d1_expected).mean(),'max_prob_norm_error':g.prob_norm_error.max()})
    for subset,gg in [('full',g),('sub_p90',g[g.source_percentile<.9]),('p90plus',g[g.source_percentile>=.9]),('p95plus',g[g.source_percentile>=.95])]:
        if len(gg)==0:continue
        br=twoboot(gg,['crps_gain','brier4_gain','mae_gain'],SEED+h*100+len(subset))
        for met,v in br.items():boots.append({'horizon':h,'subset':subset,'metric':met,'n':len(gg),**v})
        obs=np.bincount(gg.observed_region,minlength=4)/len(gg)
        for cand in ['D1','M1']:
            surv=gg[f'{cand.lower()}_survivor_p'].mean();down=gg[f'{cand.lower()}_downside_p'].mean();outp=gg.p_out.mean(); decline=down-outp;middle=1-outp-decline-surv
            cal.append({'horizon':h,'subset':subset,'candidate':cand,'n':len(gg),'obs_out':obs[0],'obs_decline':obs[1],'obs_middle':obs[2],'obs_survivor':obs[3],'pred_out':outp,'pred_decline':decline,'pred_middle':middle,'pred_survivor':surv,'downside_obs':obs[0]+obs[1],'downside_pred':down,'combined_tail_abs_error':abs(surv-obs[3])+abs(down-(obs[0]+obs[1]))})
pd.DataFrame(metrics).to_csv(OUT/'LOCKED_2021_2022_BLOCK_METRICS.csv',index=False);pd.DataFrame(boots).to_csv(OUT/'LOCKED_2021_2022_BOOTSTRAP_GAINS.csv',index=False);cal=pd.DataFrame(cal);cal.to_csv(OUT/'LOCKED_2021_2022_OUTCOME_MASS_CALIBRATION.csv',index=False)
# final classification logic: preholdout failed; holdout cannot promote. Determine B vs C based on whether tail direction improves while proper-score/MAE fails.
selcal=pd.read_csv(OUT/'SELECTION_OUTCOME_MASS_CALIBRATION.csv');sp=selcal[(selcal.horizon==3)&(selcal['subset']=='p95plus')].set_index('candidate'); hp=cal[(cal.horizon==3)&(cal['subset']=='p95plus')].set_index('candidate')
sel_tail=float(sp.loc['D1','combined_tail_abs_error']-sp.loc['M1','combined_tail_abs_error']);hold_tail=float(hp.loc['D1','combined_tail_abs_error']-hp.loc['M1','combined_tail_abs_error'])
met3=pd.DataFrame(metrics).set_index('horizon').loc[3]
classification='B. MIXTURE DIRECTION SUPPORTED, BUT NO CANDIDATE EARNS AUTHORITY' if sel_tail>0 and hold_tail>=0 else 'C. TWO-COMPONENT REPRESENTATION NOT SUPPORTED'
final={'schema_version':'fsffl-dev-rb-two-component-final-v1','classification':classification,'preholdout_decision':pre['preholdout_decision'],'preholdout_failure_reasons':pre['failure_reasons'],'selection_p95_tail_error_improvement':sel_tail,'locked_p95_tail_error_improvement':hold_tail,'locked_Y3_crps_gain':float(met3.crps_gain),'locked_Y3_brier4_gain':float(met3.brier4_gain),'locked_Y3_mae_gain':float(met3.mae_gain),'basis':[]}
final['basis']=[
 'M1 materially improves exceptional-tail survivor/downside calibration in frozen selection evidence relative to D1, so the survivor/decline mixture direction carries signal.',
 'M1 fails pre-holdout because raw-point CRPS is worse in the governed chronology, expected-point MAE degrades severely, ordinary sub-p90 developmental RBs are harmed, and Y2 no-harm fails.',
 'The mixture likelihood produces a broad high-retention component whose lognormal mean materially raises expected production; this is an emergent fit result, not a hand-set uplift, but it violates the point and proper-score guardrails.',
 'Locked 2021-2022 is validation only and cannot rescue the failed candidate; its results determine only whether the directional tail signal replicates.',
 'M2 was not authorized because the prior governed identifiability audit found no stable additional conditioning dimension.'
]
with open(OUT/'FINAL_CLASSIFICATION.json','w') as f:json.dump(final,f,indent=2,sort_keys=True)
# contract
contract={'schema_version':'fsffl-dev-rb-two-component-simulation-contract-v1','research_only':True,'normalization':'p_out + (1-p_out)*(1-pi_survivor + pi_survivor) = 1','forecast_if_future_candidate_earns':['frozen D1 p_out/inactive probability','active mixture weight pi_survivor(source magnitude)','decline and survivor component distribution parameters/quantiles','overall expectation and uncertainty summaries','provenance/training cutoff/support metadata'],'simulation':['draw inactive vs active once from Forecast p_out','if active draw one component once from Forecast mixture weight','draw one production realization from that active component','do not add a second collapse or RB downside draw'],'value':['consume Forecast expectation/distribution','do not add a second collapse haircut'],'positive_state_note':'Existing D1 positive-state probabilities remain diagnostic metadata; M1 did not earn authority, so no production reconciliation is implemented here.'}
with open(OUT/'SIMULATION_COMPATIBILITY_CONTRACT_SKETCH.json','w') as f:json.dump(contract,f,indent=2,sort_keys=True)
# prospective map and provenance
mapj={'schema_version':'fsffl-dev-rb-two-component-authority-map-v1','Y3_developmental_RB':'P0/D1 remains frozen production control; M1 fails authority','Y2_developmental_RB':'D1 retained; M1 no-harm fails','M2':'not authorized','prior_earned':['proper distributional scoring methodology','Y3 developmental QB D0->D1','Y3 established RB D0->D1','WR/TE P0 retained'],'next_boundary':'Any further active-production distribution family requires separate management authorization and fresh preregistration; locked 2021-2022 may not be reused to tune it.'}
with open(OUT/'PROSPECTIVE_FORECAST_AUTHORITY_MAP.json','w') as f:json.dump(mapj,f,indent=2,sort_keys=True)
prov=json.load(open(OUT/'PROVENANCE_MANIFEST_PREHOLDOUT.json'));prov.update({'holdout_touched':True,'holdout_evaluation_count':1,'final_classification':classification});
with open(OUT/'FINAL_PROVENANCE_MANIFEST.json','w') as f:json.dump(prov,f,indent=2,sort_keys=True)
print(json.dumps(final,indent=2));print('\nHoldout metrics');print(pd.DataFrame(metrics).to_string(index=False));print('\nHoldout p95');print(hp.to_string())
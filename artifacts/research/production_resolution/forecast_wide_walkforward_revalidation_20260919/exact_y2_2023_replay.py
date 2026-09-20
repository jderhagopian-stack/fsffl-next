from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np, pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import BayesianRidge, LogisticRegression

POSITIONS=("QB","RB","WR","TE")
STATES=("out","depth","usable","starter","premium","elite")
POSITIVE_STATES=STATES[1:]
STATE_RANK={s:i for i,s in enumerate(STATES)}
THRESHOLDS=(("useful",2),("starter",3),("premium",4),("elite",5))
LOGIT_C=.25; LOGIT_SEED=20260915
BAYES_PARAMS=dict(max_iter=300,tol=1e-6,alpha_1=1e-6,alpha_2=1e-6,lambda_1=1e-6,lambda_2=1e-6,compute_score=False,fit_intercept=True,copy_X=True,verbose=False)

def quantile(values,p):
    xs=sorted(float(x) for x in values)
    if not xs:return 0.
    z=p*(len(xs)-1); lo,hi=int(math.floor(z)),int(math.ceil(z))
    if lo==hi:return xs[lo]
    f=z-lo; return xs[lo]*(1-f)+xs[hi]*f

def fit_state_boundaries(values,k=5,iterations=60):
    xs=sorted(math.log1p(max(0.,float(x))) for x in values if x>0)
    if len(xs)<k:
        c=sum(xs)/len(xs) if xs else 0.; centers=[c]*k
    else: centers=[quantile(xs,(i+.5)/k) for i in range(k)]
    for _ in range(iterations):
        groups=[[] for _ in range(k)]
        for x in xs:
            j=min(range(k),key=lambda q:abs(x-centers[q])); groups[j].append(x)
        new=[sum(g)/len(g) if g else centers[i] for i,g in enumerate(groups)]; new.sort()
        if max(abs(a-b) for a,b in zip(new,centers))<1e-9: centers=new; break
        centers=new
    raw=[max(0.,math.expm1(x)) for x in centers]
    return tuple(raw),tuple((raw[i]+raw[i+1])/2 for i in range(k-1))

def state_for_points(points,boundaries):
    if points<=0:return 'out'
    idx=0; thresholds=boundaries[1]
    while idx<len(thresholds) and points>thresholds[idx]: idx+=1
    return POSITIVE_STATES[idx]

def coarse_age_band(position,age):
    if not np.isfinite(age):return 'unknown'
    if position=='QB': return 'young' if age<=25 else ('prime' if age<=31 else 'aging')
    return 'young' if age<=23 else ('prime' if age<=27 else 'aging')

def exp_band(exp):
    exp=int(exp)
    if exp<=1:return '0_1'
    if exp<=3:return '2_3'
    if exp<=6:return '4_6'
    return '7_plus'

def career_stage(exp):
    exp=int(exp)
    if exp<=3:return 'developmental'
    if exp<=8:return 'established'
    return 'veteran'

def build_rows(panel,max_source_season=2023):
    df=panel.copy(); df=df[df.position.isin(POSITIONS)].copy(); df['season']=df.season.astype(int)
    df['fantasy_points']=pd.to_numeric(df.fantasy_points,errors='coerce').fillna(0.)
    df['age_years']=pd.to_numeric(df.age_years,errors='coerce'); df['experience_years']=pd.to_numeric(df.experience_years,errors='coerce').fillna(0).astype(int)
    df['role_band']=df.role_band.fillna('unknown'); df['opportunity_per_game']=pd.to_numeric(df.opportunity_per_game,errors='coerce'); df['games']=pd.to_numeric(df.games,errors='coerce')
    df=df.sort_values(['season','player_id','position']).reset_index(drop=True)
    by_season={int(s):g.copy() for s,g in df.groupby('season')}; key={(str(r.player_id),int(r.season)):r for r in df.itertuples(index=False)}
    source_info={}; age_state_info={}; cutoff_bounds={}
    for t in range(2004,max_source_season+1):
        prior=df[df.season<t]; cur=by_season.get(t)
        if prior.empty or cur is None: continue
        bounds={}; state_stats={}; age_state_stats={}
        for p in POSITIONS:
            vals=prior.loc[(prior.position==p)&(prior.fantasy_points>0),'fantasy_points'].tolist()
            if len(vals)<20: continue
            b=fit_state_boundaries(vals); bounds[p]=b
            pp=prior[prior.position==p].copy(); pp['state']=[state_for_points(v,b) for v in pp.fantasy_points]; pp['age_band_tmp']=[coarse_age_band(p,float(a)) for a in pp.age_years]
            for st,g in pp.groupby('state'):
                a=g.fantasy_points.to_numpy(float); mu=float(a.mean()); sd=float(a.std(ddof=1)) if len(a)>1 else 0.
                if sd<1e-6: sd=max(1.,abs(mu)*.25)
                state_stats[(p,st)]=(len(a),mu,sd)
            for (ab,st),g in pp.groupby(['age_band_tmp','state']):
                a=g.fantasy_points.to_numpy(float); mu=float(a.mean()); sd=float(a.std(ddof=1)) if len(a)>1 else 0.
                if sd<1e-6: sd=max(1.,abs(mu)*.25)
                age_state_stats[(p,ab,st)]=(len(a),mu,sd)
        cutoff_bounds[t]=bounds
        for r in cur.itertuples(index=False):
            p=str(r.position)
            if p not in bounds: continue
            points=float(r.fantasy_points); st=state_for_points(points,bounds[p]); base=state_stats.get((p,st))
            if base is None or base[0]<10: continue
            _,mu,sd=base; age=float(r.age_years) if np.isfinite(r.age_years) else np.nan; ab=coarse_age_band(p,age); ast=age_state_stats.get((p,ab,st))
            if ast is not None and ast[0]>=10: _,amu,asd=ast
            else: amu,asd=mu,sd
            source_info[(str(r.player_id),t)]={'position':p,'source_state':st,'source_points':points,'current_resid_z':(points-mu)/sd,'current_age_state_resid_z':(points-amu)/asd,'age':age,'age_band':ab,'experience':int(r.experience_years),'source_role_band':str(r.role_band),'games':float(r.games) if np.isfinite(r.games) else np.nan,'opportunity_per_game':float(r.opportunity_per_game) if np.isfinite(r.opportunity_per_game) else np.nan}
            age_state_info[(str(r.player_id),t)]=(points-amu)/asd
    rows=[]; max_data_season=int(df.season.max())
    for t in range(2005,min(max_source_season,max_data_season)+1):
        bounds=cutoff_bounds.get(t,{})
        for r in by_season.get(t,pd.DataFrame()).itertuples(index=False):
            pid=str(r.player_id); src=source_info.get((pid,t))
            if src is None: continue
            p=src['position']; prior_row=key.get((pid,t-1)); prior1_points=None
            if prior_row is not None and str(prior_row.position)==p: prior1_points=float(prior_row.fantasy_points)
            prior_age1=age_state_info.get((pid,t-1),np.nan); prior_age2=age_state_info.get((pid,t-2),np.nan); prior2_cov=int(np.isfinite(prior_age1) and np.isfinite(prior_age2))
            prior2_mean=float((prior_age1+prior_age2)/2) if prior2_cov else np.nan; prior2_gap=float(abs(prior_age1-prior_age2)) if prior2_cov else np.nan
            for h in (1,2,3):
                if t+h>max_data_season: continue
                tr=key.get((pid,t+h)); present=tr is not None and str(tr.position)==p; target_points=float(tr.fantasy_points) if present else 0.; target_state=state_for_points(target_points,bounds[p]) if present else 'out'; target_role=str(tr.role_band) if present else 'missing'; role_loss=np.nan
                if present and src['source_role_band']=='established' and target_role in ('weak','established'): role_loss=float(target_role=='weak')
                rows.append({'source_season':t,'player_id':pid,'position':p,'horizon':h,'age':src['age'],'age_band':src['age_band'],'experience':src['experience'],'career_stage':career_stage(src['experience']),'source_state':src['source_state'],'source_points':src['source_points'],'current_resid_z':src['current_resid_z'],'current_age_state_resid_z':src['current_age_state_resid_z'],'prior_age_state_resid_z':prior_age1,'prior2_mean_age_state_z':prior2_mean,'prior2_gap_age_state_z':prior2_gap,'prior2_coverage':prior2_cov,'prior1_points':prior1_points,'prior1_coverage':int(prior1_points is not None),'source_role_band':src['source_role_band'],'games':src['games'],'opportunity_per_game':src['opportunity_per_game'],'target_present':int(present),'target_points':target_points,'target_state':target_state,'target_role_band':target_role,'role_loss':role_loss})
    ev=pd.DataFrame(rows); ev=ev[ev.source_state!='out'].copy()
    unique=ev[ev.horizon==1][['source_season','player_id','position','source_state','source_points']].copy(); unique['source_percentile']=np.nan; unique['state_percentile']=np.nan
    for _,idx in unique.groupby(['source_season','position']).groups.items():
        v=unique.loc[idx,'source_points']; unique.loc[idx,'source_percentile']=(v.rank(method='average')-.5)/len(v)
    for _,idx in unique.groupby(['source_season','position','source_state']).groups.items():
        v=unique.loc[idx,'source_points']; unique.loc[idx,'state_percentile']=(v.rank(method='average')-.5)/len(v)
    ev=ev.merge(unique[['source_season','player_id','source_percentile','state_percentile']],on=['source_season','player_id'],how='left')
    ev['deep_collapse']=(ev.target_points<=.25*ev.source_points).astype(int); ev['top10']=(ev.source_percentile>=.9).astype(int); ev['top5']=(ev.source_percentile>=.95).astype(int); ev['age_le25']=(ev.age<=25).astype(int); ev['prime_established']=((ev.career_stage=='established')&(ev.age_band=='prime')).astype(int)
    return ev.sort_values(['source_season','player_id','position','horizon']).reset_index(drop=True)

def prob_features(r,age_mode,add_c,add_d):
    p=str(r.position); h=int(r.horizon); exp=int(r.experience); d={f'p={p}':1,f's={r.source_state}':1,f'h={h}':1,f'e={exp_band(exp)}':1,'exp':min(15.,max(0.,float(exp)))/10.}
    if age_mode=='coarse': d[f'a={r.age_band}']=1
    elif age_mode=='a2':
        age=float(r.age); ref=31. if p=='QB' else 27.; d[f'age_exact_{p}']=(age-ref)/5.
        if p=='QB': d['age_late_QB']=max(0.,age-37.)/5.
        else:
            d[f'age_late_{p}']=max(0.,age-31.)/5.
            if p=='TE': d['age_young_TE']=max(0.,24.-age)/5.
    cur=max(0.,float(r.source_points)); prior=None if not int(r.prior1_coverage) else max(0.,float(r.prior1_points)); pv=0. if prior is None else prior
    d.update({'lp':math.log1p(cur)/6.,'lprev':math.log1p(pv)/6.,'dpts':max(-2.,min(2.,(cur-pv)/100.)),'prev_cov':0 if prior is None else 1})
    role=str(r.source_role_band) if pd.notna(r.source_role_band) else 'unknown'
    if role in ('weak','established') and pd.notna(r.opportunity_per_game) and pd.notna(r.games):
        d[f'role={role}']=1; d['u_cov']=1; d['lopg']=math.log1p(max(0.,float(r.opportunity_per_game)))/4.; d['lg']=math.log1p(max(0.,float(r.games)))/3.
    else: d.update({'role=unknown':1,'u_cov':0,'lopg':0.,'lg':0.})
    d.update({'r_cov':0,'i_cov':0,'part_cov':0})
    if add_c:
        mem=r.prior_age_state_resid_z; supported=(p=='QB' and r.age_band in ('prime','aging'))
        if supported:
            key=f'mem_{p}_{r.age_band}_h{h}'
            if pd.notna(mem): d[key]=float(mem); d[key+'_cov']=1
            else: d[key]=0.; d[key+'_cov']=0
    if add_d and pd.notna(r.state_percentile):
        pct=float(r.state_percentile); d[f'pct_{p}']=(pct-.5)*2.
        if r.source_state in ('premium','elite'):
            d[f'hi_{p}_{r.source_state}']=max(0.,(pct-.8)/.2); d[f'lo_{p}_{r.source_state}']=max(0.,(.2-pct)/.2)
    return d

class BinModel:
    def __init__(self): self.vec=DictVectorizer(sort=True); self.model=LogisticRegression(C=LOGIT_C,solver='lbfgs',max_iter=2000,random_state=LOGIT_SEED); self.ok=False
    def fit(self,feats,y):
        y=np.asarray(y,dtype=int); counts=np.bincount(y,minlength=2)
        if len(y)>=100 and counts.min()>=15: self.model.fit(self.vec.fit_transform(feats),y); self.ok=True
        return self
    def prob(self,feat): return float(self.model.predict_proba(self.vec.transform([feat]))[0,1])

class ProbLayer:
    def __init__(self,add_c): self.add_c=add_c; self.persist=BinModel(); self.ordered={name:BinModel() for name,_ in THRESHOLDS}
    def fit(self,train):
        pf=[prob_features(r,age_mode='a2',add_c=self.add_c,add_d=False) for r in train.itertuples()]; self.persist.fit(pf,(train.target_state!='out').astype(int).tolist()); pos=train[train.target_state!='out'].copy(); of=[prob_features(r,age_mode='coarse',add_c=self.add_c,add_d=True) for r in pos.itertuples()]
        for name,rank in THRESHOLDS: self.ordered[name].fit(of,[1 if STATE_RANK[s]>=rank else 0 for s in pos.target_state])
        return self
    def predict(self,r):
        p=self.persist.prob(prob_features(r,age_mode='a2',add_c=self.add_c,add_d=False)); feat=prob_features(r,age_mode='coarse',add_c=self.add_c,add_d=True); cum=[]; last=1.
        for name,_ in THRESHOLDS:
            q=self.ordered[name].prob(feat); q=min(last,max(0.,min(1.,q))); cum.append(q); last=q
        useful,starter,premium,elite=cum; cond={'depth':1-useful,'usable':useful-starter,'starter':starter-premium,'premium':premium-elite,'elite':elite}; out={'out':1-p}; out.update({s:p*cond[s] for s in POSITIVE_STATES}); z=sum(out.values()); return {s:out[s]/z for s in STATES}

@dataclass
class Scaler:
    mean:float; sd:float
    @classmethod
    def fit(cls,x):
        a=np.asarray(x,dtype=float); a=a[np.isfinite(a)]; mean=float(a.mean()) if len(a) else 0.; sd=float(a.std(ddof=0)) if len(a) else 1.; sd=1. if sd<1e-12 else sd; return cls(mean,sd)
    def z(self,x): return (float(x)-self.mean)/self.sd

class ProductionModel:
    def __init__(self,candidate,horizon): self.candidate=candidate; self.horizon=int(horizon); self.vec=DictVectorizer(sort=True); self.model=BayesianRidge(**BAYES_PARAMS); self.scalers={}
    def _fit_scalers(self,train):
        raw={'source_log':np.log1p(train.source_points.to_numpy(float)),'source_pct':train.source_percentile.to_numpy(float),'age':train.age.to_numpy(float),'experience':np.minimum(train.experience.to_numpy(float),15.)}
        for k,v in raw.items(): self.scalers[k]=Scaler.fit(v)
        cov=train[train.prior1_coverage==1]; self.scalers['prior1_log']=Scaler.fit(np.log1p(np.maximum(cov.prior1_points.to_numpy(float),0.))) if len(cov) else Scaler(0.,1.)
        if self.candidate=='D1':
            c2=train[train.prior2_coverage==1]; self.scalers['prior2_mean']=Scaler.fit(c2.prior2_mean_age_state_z.to_numpy(float)) if len(c2) else Scaler(0.,1.); self.scalers['prior2_gap']=Scaler.fit(c2.prior2_gap_age_state_z.to_numpy(float)) if len(c2) else Scaler(0.,1.)
    def _features(self,r,future_state=None):
        vals={'source_log':self.scalers['source_log'].z(math.log1p(max(0.,float(r.source_points)))),'source_pct':self.scalers['source_pct'].z(float(r.source_percentile)),'age':self.scalers['age'].z(float(r.age)),'experience':self.scalers['experience'].z(min(float(r.experience),15.)),'prior1_log':self.scalers['prior1_log'].z(math.log1p(max(0.,float(r.prior1_points)))) if int(r.prior1_coverage) else 0.}
        d={f'p={r.position}':1,f'src={r.source_state}':1,'prior1_cov':int(r.prior1_coverage)}
        for k,v in vals.items(): d[k]=v; d[f'{k}@p={r.position}']=v
        if self.candidate=='D1':
            if future_state is None: future_state=str(r.target_state)
            d[f'future={future_state}']=1; d[f'pstate={r.position}|{future_state}']=1; d[f'source_log@future={future_state}']=vals['source_log']; d[f'source_pct@future={future_state}']=vals['source_pct']
            if int(r.prior2_coverage): m=self.scalers['prior2_mean'].z(float(r.prior2_mean_age_state_z)); g=self.scalers['prior2_gap'].z(float(r.prior2_gap_age_state_z))
            else: m=g=0.
            d['prior2_cov']=int(r.prior2_coverage); d['prior2_mean_z']=m; d['prior2_gap_z']=g; d[f'prior2_mean_z@p={r.position}']=m; d[f'prior2_gap_z@p={r.position}']=g
        return d
    def fit(self,train):
        tr=train[(train.horizon==self.horizon)&(train.target_state!='out')].copy().sort_values(['source_season','player_id','position','horizon']); self._fit_scalers(tr); X=[self._features(r) for r in tr.itertuples()]; self.model.fit(self.vec.fit_transform(X).toarray(),tr.target_points.to_numpy(float)); return self
    def predict_active(self,r): return max(0.,float(self.model.predict(self.vec.transform([self._features(r)]).toarray())[0]))
    def predict_state(self,r,state): return max(0.,float(self.model.predict(self.vec.transform([self._features(r,state)]).toarray())[0]))

def fit_state_layers(train,horizon):
    st=train[train.horizon.isin([1,2])].copy() if horizon==2 else train[train.horizon==3].copy(); return {'qb':ProbLayer(True).fit(st),'nonqb':ProbLayer(False).fit(st)}
def state_probs(layers,r): return (layers['qb'] if r.position=='QB' else layers['nonqb']).predict(r)
def fit_candidates(train,horizon): return ProductionModel('D0',horizon).fit(train),ProductionModel('D1',horizon).fit(train)
def predict_row(r,layers,d0,d1):
    probs=state_probs(layers,r); active=d0.predict_active(r); pa=1-probs['out']; means={s:d1.predict_state(r,s) for s in POSITIVE_STATES}; rec={'source_season':int(r.source_season),'player_id':str(r.player_id),'position':str(r.position),'horizon':int(r.horizon),'age':float(r.age),'experience':int(r.experience),'career_stage':str(r.career_stage),'source_state':str(r.source_state),'source_points':float(r.source_points),'source_percentile':float(r.source_percentile),'target_points':float(r.target_points),'target_state':str(r.target_state),'target_present':int(r.target_present),'p_active':float(pa),'pred_D0':float(pa*active),'pred_D1':float(sum(probs[s]*means[s] for s in POSITIVE_STATES)),'active_D0':float(active)}
    for s in STATES: rec[f'p_{s}']=float(probs[s])
    for s in POSITIVE_STATES: rec[f'd1_mean_{s}']=float(means[s])
    return rec

def predict_origin(rows,t,h):
    if h==2:
        train=rows[(rows.source_season<t)&(rows.source_season+rows.horizon<=t-1)&(rows.horizon.isin([1,2]))].copy(); prod_train=rows[(rows.source_season<t)&(rows.source_season+2<=t-1)&(rows.horizon==2)].copy()
    else:
        train=rows[(rows.source_season<t)&(rows.source_season+3<=t-1)&(rows.horizon==3)].copy(); prod_train=train.copy()
    test=rows[(rows.source_season==t)&(rows.horizon==h)].copy(); layers=fit_state_layers(train,h); d0,d1=fit_candidates(prod_train,h); return pd.DataFrame([predict_row(r,layers,d0,d1) for r in test.itertuples()])

if __name__=='__main__':
    panel=pd.read_csv('/mnt/data/fsffl_phase2/future-state-phase2/phase2_player_season_panel.csv')
    rows=build_rows(panel,2023)
    p22=predict_origin(rows,2022,2)
    hist=pd.read_csv('/mnt/data/fsffl_diag/historical_predictions.csv')
    h22=hist[(hist.source_season==2022)&(hist.horizon==2)]
    m=p22.merge(h22,on=['source_season','player_id','position','horizon'],suffixes=('_new','_old'))
    print('parity rows',len(m),'pred_D0',np.max(np.abs(m.pred_D0_new-m.pred_D0_old)),'pred_D1',np.max(np.abs(m.pred_D1_new-m.pred_D1_old)),'pactive',np.max(np.abs(m.p_active_new-m.p_active_old)))
    p23=predict_origin(rows,2023,2)
    p23.to_csv('/mnt/data/fsffl_walkforward_audit_20260919/Y2_ORIGIN_2023_PREDICTIONS.csv',index=False)
    print('2023 rows',len(p23),p23.groupby('position').size().to_dict())
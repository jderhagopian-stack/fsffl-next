from __future__ import annotations
import json, math, warnings
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression, BayesianRidge
from sklearn.metrics import log_loss

warnings.filterwarnings('ignore')

STATES=("out","depth","usable","starter","premium","elite")
POSITIVE=STATES[1:]
STATE_RANK={s:i for i,s in enumerate(STATES)}
THRESHOLDS={"useful":2,"starter":3,"premium":4,"elite":5}
C=0.25
SEED=20260915


def exp_band(x):
    x=int(x)
    if x<=1:return '0_1'
    if x<=3:return '2_3'
    if x<=6:return '4_6'
    return '7_plus'


def base_features(r, *, age_mode='coarse', add_c=False, add_d=False):
    p=str(r.position); h=int(r.horizon); exp=int(r.experience)
    d={f'p={p}':1, f's={r.source_state}':1, f'h={h}':1, f'e={exp_band(exp)}':1,
       'exp':min(15.0,max(0.0,float(exp)))/10.0}
    if age_mode=='coarse':
        d[f'a={r.age_band}']=1
    elif age_mode in ('a1','a2'):
        age=float(r.age)
        ref=31.0 if p=='QB' else 27.0
        d[f'age_exact_{p}']=(age-ref)/5.0
        if age_mode=='a2':
            if p=='QB':
                d['age_late_QB']=max(0.0, age-37.0)/5.0
            else:
                d[f'age_late_{p}']=max(0.0, age-31.0)/5.0
                if p=='TE': d['age_young_TE']=max(0.0,24.0-age)/5.0
    else: raise ValueError(age_mode)
    cur=max(0.0,float(r.source_points)); prior=(None if pd.isna(r.prior_points) else max(0.0,float(r.prior_points)))
    pv=0.0 if prior is None else prior
    d.update({'lp':math.log1p(cur)/6.0,'lprev':math.log1p(pv)/6.0,
              'dpts':max(-2.0,min(2.0,(cur-pv)/100.0)), 'prev_cov':0 if prior is None else 1})
    role=str(r.source_role_band) if pd.notna(r.source_role_band) else 'unknown'
    if role in ('weak','established') and pd.notna(r.opportunity_per_game) and pd.notna(r.games):
        d[f'role={role}']=1; d['u_cov']=1
        d['lopg']=math.log1p(max(0.0,float(r.opportunity_per_game)))/4.0
        d['lg']=math.log1p(max(0.0,float(r.games)))/3.0
    else:
        d['role=unknown']=1; d['u_cov']=0; d['lopg']=0.0; d['lg']=0.0
    d.update({'r_cov':0,'i_cov':0,'part_cov':0})
    if add_c:
        mem=r.prior_age_state_resid_z
        supported=((p=='QB' and r.age_band in ('prime','aging')) or
                   (p=='WR' and r.age_band=='aging') or (p=='TE' and r.age_band=='aging'))
        if supported:
            key=f'mem_{p}_{r.age_band}_h{h}'
            if pd.notna(mem):
                d[key]=float(mem); d[key+'_cov']=1
            else:
                d[key]=0.0; d[key+'_cov']=0
    if add_d:
        pct=r.state_pct
        if pd.notna(pct):
            pct=float(pct)
            d[f'pct_{p}']=(pct-0.5)*2.0
            if r.source_state in ('premium','elite'):
                d[f'hi_{p}_{r.source_state}']=max(0.0,(pct-0.8)/0.2)
                d[f'lo_{p}_{r.source_state}']=max(0.0,(0.2-pct)/0.2)
    return d


class BinModel:
    def __init__(self):
        self.vec=DictVectorizer(sort=True); self.model=LogisticRegression(C=C,solver='lbfgs',max_iter=2000,random_state=SEED); self.ok=False
    def fit(self, feats, y):
        y=np.asarray(y,dtype=int)
        counts=np.bincount(y,minlength=2)
        if len(y)>=100 and counts.min()>=15:
            self.model.fit(self.vec.fit_transform(feats),y); self.ok=True
    def prob(self, feat):
        if not self.ok:return None
        return float(self.model.predict_proba(self.vec.transform([feat]))[0,1])


@dataclass
class ProbModel:
    age_mode:str='coarse'
    add_c:bool=False
    add_d:bool=False
    def fit(self, train):
        self.persist=BinModel()
        pf=[base_features(r,age_mode=self.age_mode,add_c=self.add_c,add_d=False) for r in train.itertuples()]
        self.persist.fit(pf,train.y_persist.astype(int).tolist())
        pos=train[train.y_persist==1].copy()
        self.ordered={}
        of=[base_features(r,age_mode='coarse',add_c=self.add_c,add_d=self.add_d) for r in pos.itertuples()]
        for nm,rank in THRESHOLDS.items():
            m=BinModel(); y=[1 if STATE_RANK[s]>=rank else 0 for s in pos.y_state]; m.fit(of,y); self.ordered[nm]=m
        return self
    def predict_row(self,r):
        p=self.persist.prob(base_features(r,age_mode=self.age_mode,add_c=self.add_c,add_d=False))
        if p is None: return None
        feat=base_features(r,age_mode='coarse',add_c=self.add_c,add_d=self.add_d)
        cum=[]; last=1.0
        for nm in ('useful','starter','premium','elite'):
            q=self.ordered[nm].prob(feat)
            if q is None:return None
            q=min(last,max(0.0,min(1.0,q))); cum.append(q); last=q
        useful,starter,prem,elite=cum
        cond={'depth':1-useful,'usable':useful-starter,'starter':starter-prem,'premium':prem-elite,'elite':elite}
        out={'out':1-p}; out.update({s:p*cond[s] for s in POSITIVE})
        z=sum(out.values()); return {s:out[s]/z for s in STATES}


class StateStats:
    def __init__(self, train):
        self.groups={}
        for keys,g in train.groupby(['position','horizon','y_state']):
            a=g.target_points.astype(float).to_numpy(); self.groups[('phs',)+tuple(keys)]=(len(a),float(a.mean()),float(a.std(ddof=1)) if len(a)>1 else 0.0)
        for keys,g in train.groupby(['position','y_state']):
            a=g.target_points.astype(float).to_numpy(); self.groups[('ps',)+tuple(keys)]=(len(a),float(a.mean()),float(a.std(ddof=1)) if len(a)>1 else 0.0)
        for keys,g in train.groupby(['horizon','y_state']):
            a=g.target_points.astype(float).to_numpy(); self.groups[('hs',)+tuple(keys)]=(len(a),float(a.mean()),float(a.std(ddof=1)) if len(a)>1 else 0.0)
        for st,g in train.groupby('y_state'):
            a=g.target_points.astype(float).to_numpy(); self.groups[('s',st)]=(len(a),float(a.mean()),float(a.std(ddof=1)) if len(a)>1 else 0.0)
    def get(self,p,h,s):
        for k,minn in [(('phs',p,h,s),10),(('ps',p,s),10),(('hs',h,s),10),(('s',s),5)]:
            if k in self.groups and self.groups[k][0]>=minn:
                n,mu,sd=self.groups[k];
                if sd<1e-6: sd=max(1.0,abs(mu)*0.25)
                return mu,sd
        return 0.0,1.0


B_SUPPORT=set()
for stage in ('young','prime','aging'):
    for h in (1,2,3):B_SUPPORT.add(('QB',stage,h))
B_SUPPORT.add(('RB','prime',1))
B_SUPPORT.update({('WR','aging',1),('WR','aging',3),('TE','aging',1),('TE','aging',2),('TE','prime',1)})

class BCarry:
    def fit(self, train):
        self.mods={}
        for cell in B_SUPPORT:
            p,stage,h=cell
            g=train[(train.position==p)&(train.age_band==stage)&(train.horizon==h)&(train.y_persist==1)&train.current_resid_z.notna()&train.target_resid_z.notna()]
            if len(g)>=30 and g.source_season.nunique()>=3:
                m=BayesianRidge(); m.fit(g[['current_resid_z']].to_numpy(),g.target_resid_z.to_numpy()); self.mods[cell]=m
        return self
    def adj(self,r):
        m=self.mods.get((r.position,r.age_band,int(r.horizon)))
        if m is None or pd.isna(r.current_resid_z):return 0.0
        return float(m.predict([[float(r.current_resid_z)]])[0])


def expected_points(prob,r,stats,bcarry=None):
    adj=0.0 if bcarry is None else bcarry.adj(r)
    tot=0.0
    for s in STATES:
        mu,sd=stats.get(r.position,int(r.horizon),s)
        if s!='out' and bcarry is not None: mu=max(0.0,mu+adj*sd)
        tot+=prob[s]*mu
    return max(0.0,tot)


def fit_predict_year(df,t,variant):
    # Separate h1/h2 and direct h3, mirroring frozen architecture split.
    out=[]
    for group in ('h12','h3'):
        hs=(1,2) if group=='h12' else (3,)
        train=df[df.horizon.isin(hs) & (df.source_season < t) & ((df.source_season+df.horizon)<=t-1)].copy()
        test=df[(df.source_season==t)&df.horizon.isin(hs)].copy()
        if train.empty or test.empty: continue
        age_mode='coarse'; add_c=False; add_d=False; use_b=False
        if 'A1' in variant: age_mode='a1'
        if 'A2' in variant: age_mode='a2'
        if 'C' in variant: add_c=True
        if 'D' in variant: add_d=True
        if 'B' in variant: use_b=True
        pm=ProbModel(age_mode=age_mode,add_c=add_c,add_d=add_d).fit(train)
        st=StateStats(train); bc=BCarry().fit(train) if use_b else None
        for r in test.itertuples():
            prob=pm.predict_row(r)
            if prob is None: continue
            rec={k:getattr(r,k) for k in ['source_season','player_id','position','horizon','age','age_band','exact_age_bin','experience','source_state','source_points','current_resid_z','prior_age_state_resid_z','state_pct','tail_group','source_role_band','target_role_band','role_loss','target_points','y_state','y_persist']}
            rec.update({f'p_{s}':prob[s] for s in STATES})
            rec['pred_points']=expected_points(prob,r,st,bc); rec['variant']=variant
            out.append(rec)
    return out


def metrics(g):
    if len(g)==0:return {'n':0}
    y=g.y_persist.to_numpy(float); p=(1-g.p_out.to_numpy(float)); eps=1e-12
    pb=float(np.mean((p-y)**2)); pll=float(-np.mean(y*np.log(np.clip(p,eps,1-eps))+(1-y)*np.log(np.clip(1-p,eps,1-eps))))
    probs=g[[f'p_{s}' for s in STATES]].to_numpy(float)
    Y=np.zeros_like(probs)
    for i,s in enumerate(g.y_state): Y[i,STATE_RANK[s]]=1
    sb=float(np.mean(np.sum((probs-Y)**2,axis=1)))
    sll=float(-np.mean(np.log(np.clip(probs[np.arange(len(g)),[STATE_RANK[s] for s in g.y_state]],eps,1))))
    ae=np.abs(g.pred_points-g.target_points)
    active=g.y_persist==1
    return {'n':int(len(g)),'persist_brier':pb,'persist_logloss':pll,'persist_bias':float(p.mean()-y.mean()),
            'state_brier':sb,'state_logloss':sll,'points_mae':float(ae.mean()),'points_bias':float((g.pred_points-g.target_points).mean()),
            'active_points_mae':float(ae[active].mean()) if active.any() else None,'active_n':int(active.sum())}


def grouped_metrics(df):
    out={'overall':metrics(df),'position':{},'horizon':{},'position_horizon':{},'stage':{}}
    for p,g in df.groupby('position'):out['position'][p]=metrics(g)
    for h,g in df.groupby('horizon'):out['horizon'][str(h)]=metrics(g)
    for (p,h),g in df.groupby(['position','horizon']):out['position_horizon'][f'{p}_h{h}']=metrics(g)
    for (p,st),g in df.groupby(['position','age_band']):out['stage'][f'{p}_{st}']=metrics(g)
    return out


def role_diag(df):
    rows=[]
    for t in range(2014,2023):
        train=df[(df.source_season<t)&((df.source_season+df.horizon)<=t-1)&(df.source_role_band=='established')&df.role_loss.notna()& (df.y_persist==1)]
        test=df[(df.source_season==t)&(df.source_role_band=='established')&df.role_loss.notna()&(df.y_persist==1)]
        if len(train)<100 or test.empty:continue
        for name,addc in [('base',False),('C',True)]:
            m=BinModel(); feats=[base_features(r,age_mode='coarse',add_c=addc,add_d=False) for r in train.itertuples()]
            m.fit(feats,train.role_loss.astype(int).tolist())
            for r in test.itertuples():
                pr=m.prob(base_features(r,age_mode='coarse',add_c=addc,add_d=False))
                if pr is not None:rows.append({'season':t,'position':r.position,'horizon':r.horizon,'variant':name,'y':int(r.role_loss),'p':pr})
    rr=pd.DataFrame(rows); out={}
    for split,mask in [('development',rr.season.between(2014,2018)),('validation',rr.season.between(2019,2020)),('holdout',rr.season.between(2021,2022))]:
        out[split]={}
        for v,g in rr[mask].groupby('variant'):
            y=g.y.to_numpy(float);p=g.p.to_numpy(float);eps=1e-12
            out[split][v]={'n':len(g),'brier':float(np.mean((p-y)**2)),'logloss':float(-np.mean(y*np.log(np.clip(p,eps,1-eps))+(1-y)*np.log(np.clip(1-p,eps,1-eps))))}
    return out,rr


def production_memory_diag(df):
    rows=[]
    support=lambda r: ((r.position=='QB' and r.age_band in ('prime','aging')) or (r.position=='WR' and r.age_band=='aging') or (r.position=='TE' and r.age_band=='aging'))
    for t in range(2014,2023):
        train=df[(df.source_season<t)&((df.source_season+df.horizon)<=t-1)&(df.y_persist==1)&df.current_resid_z.notna()&df.target_resid_z.notna()].copy()
        test=df[(df.source_season==t)&(df.y_persist==1)&df.current_resid_z.notna()&df.target_resid_z.notna()].copy()
        train=train[train.apply(support,axis=1)];test=test[test.apply(support,axis=1)]
        for cell,gt in train.groupby(['position','age_band','horizon']):
            ge=test[(test.position==cell[0])&(test.age_band==cell[1])&(test.horizon==cell[2])]
            if len(gt)<30 or ge.empty:continue
            m1=BayesianRidge().fit(gt[['current_resid_z']].to_numpy(),gt.target_resid_z.to_numpy())
            gm=gt.dropna(subset=['prior_age_state_resid_z']); gem=ge.dropna(subset=['prior_age_state_resid_z'])
            m2=None
            if len(gm)>=30: m2=BayesianRidge().fit(gm[['current_resid_z','prior_age_state_resid_z']].to_numpy(),gm.target_resid_z.to_numpy())
            for _,r in ge.iterrows():
                rows.append({'season':t,'position':cell[0],'stage':cell[1],'horizon':cell[2],'variant':'current_only','err':abs(float(m1.predict([[r.current_resid_z]])[0])-r.target_resid_z)})
            if m2 is not None:
                for _,r in gem.iterrows():
                    rows.append({'season':t,'position':cell[0],'stage':cell[1],'horizon':cell[2],'variant':'current_plus_memory','err':abs(float(m2.predict([[r.current_resid_z,r.prior_age_state_resid_z]])[0])-r.target_resid_z)})
    rr=pd.DataFrame(rows); out={}
    for split,mask in [('development',rr.season.between(2014,2018)),('validation',rr.season.between(2019,2020)),('holdout',rr.season.between(2021,2022))]:
        out[split]={}
        for v,g in rr[mask].groupby('variant'):out[split][v]={'n':len(g),'mae_z':float(g.err.mean())}
    return out,rr


def tail_summary(g):
    x=g[(g.source_state.isin(['premium','elite'])) & g.tail_group.notna()].copy(); out={}
    for keys,gg in x.groupby(['position','horizon','source_state','tail_group']):
        if len(gg)<10:continue
        actual_elite=(gg.y_state=='elite').mean(); pred_elite=gg.p_elite.mean()
        actual_prem=gg.y_state.isin(['premium','elite']).mean(); pred_prem=(gg.p_premium+gg.p_elite).mean()
        out['|'.join(map(str,keys))]={'n':len(gg),'elite_pred':float(pred_elite),'elite_actual':float(actual_elite),'elite_gap':float(pred_elite-actual_elite),
                                          'premium_plus_pred':float(pred_prem),'premium_plus_actual':float(actual_prem),'premium_plus_gap':float(pred_prem-actual_prem)}
    if out:
        n=sum(v['n'] for v in out.values())
        out['_weighted_abs_gap']={'n':n,'elite':sum(v['n']*abs(v['elite_gap']) for k,v in out.items() if not k.startswith('_'))/n,
                                  'premium_plus':sum(v['n']*abs(v['premium_plus_gap']) for k,v in out.items() if not k.startswith('_'))/n}
    return out


def age_calibration(g):
    x=g.copy(); out={}
    for keys,gg in x.groupby(['position','horizon','exact_age_bin']):
        if len(gg)<10:continue
        pred=(1-gg.p_out).mean(); act=gg.y_persist.mean()
        out['|'.join(map(str,keys))]={'n':len(gg),'pred':float(pred),'actual':float(act),'gap':float(pred-act)}
    return out


def build_table():
    base=Path('/mnt/data/phase34_work/future-state-phase2')
    q3=pd.read_csv(base/'phase2_q3_age_state_rows.csv')
    panel=pd.read_csv(base/'phase2_player_season_panel.csv')
    static=q3[q3.horizon==1][['source_season','player_id','position','age','age_band','exact_age_bin','experience','source_state','source_points','current_resid_z','prior_age_state_resid_z','source_role_band']].copy()
    psrc=panel[['player_id','season','fantasy_points','games','opportunity_per_game']].copy(); psrc=psrc.rename(columns={'season':'source_season','fantasy_points':'panel_points'})
    static=static.merge(psrc,on=['player_id','source_season'],how='left')
    prior=panel[['player_id','season','fantasy_points']].copy(); prior['source_season']=prior.season+1; prior=prior.rename(columns={'fantasy_points':'prior_points'})[['player_id','source_season','prior_points']]
    static=static.merge(prior,on=['player_id','source_season'],how='left')
    static['state_pct']=np.nan
    for (yr,p,st),idx in static.groupby(['source_season','position','source_state']).groups.items():
        vals=static.loc[idx,'source_points']; ranks=vals.rank(method='average'); static.loc[idx,'state_pct']=(ranks-0.5)/len(vals)
    static['tail_group']=pd.cut(static.state_pct,[-np.inf,.33,.80,np.inf],labels=['lower','middle','extreme_upper']).astype(object)
    ev=q3.merge(static[['source_season','player_id','prior_points','games','opportunity_per_game','state_pct','tail_group']],on=['source_season','player_id'],how='left')
    ev['y_state']=np.where(ev.target_state.isin(STATES),ev.target_state,'out')
    ev['y_persist']=(ev.y_state!='out').astype(int)
    ev=ev[(ev.source_state!='out') & ev.source_season.between(2005,2022)].copy()
    return ev


def main():
    ev=build_table(); print('evaluation rows',len(ev),'source players',ev[['source_season','player_id']].drop_duplicates().shape[0])
    variants=['baseline','A1','A2','B','C','D']
    all_rows=[]
    for v in variants:
        print('running',v,flush=True)
        for t in range(2014,2023): all_rows.extend(fit_predict_year(ev,t,v))
    pred=pd.DataFrame(all_rows)
    val=pred[pred.source_season.between(2019,2020)]
    val_metrics={v:metrics(val[val.variant==v]) for v in ('baseline','A1','A2')}
    a_selected=min(('A1','A2'),key=lambda v:(val_metrics[v]['persist_brier'],val_metrics[v]['persist_logloss']))
    print('A selected',a_selected,val_metrics,flush=True)
    combos=[a_selected+'+B',a_selected+'+C',a_selected+'+D',a_selected+'+B+C+D']
    for v in combos:
        print('running combo',v,flush=True)
        for t in range(2014,2023): all_rows.extend(fit_predict_year(ev,t,v))
    pred=pd.DataFrame(all_rows)
    splits={'development':(2014,2018),'validation':(2019,2020),'holdout':(2021,2022),'all_eval':(2014,2022)}
    res={'study':'future-state-resolution-phase34-bounded-challengers-v1','protocol':'future_state_phase34_protocol.md','A_selected_on_validation':a_selected,'A_validation_metrics':val_metrics,'splits':{},'tail':{},'age_calibration':{}}
    for sn,(lo,hi) in splits.items():
        res['splits'][sn]={}
        ss=pred[pred.source_season.between(lo,hi)]
        for v,g in ss.groupby('variant'):res['splits'][sn][v]=grouped_metrics(g)
        res['tail'][sn]={v:tail_summary(g) for v,g in ss.groupby('variant') if v in ('baseline','D',a_selected+'+D',a_selected+'+B+C+D')}
        res['age_calibration'][sn]={v:age_calibration(g) for v,g in ss.groupby('variant') if v in ('baseline','A1','A2',a_selected+'+B',a_selected+'+C',a_selected+'+D',a_selected+'+B+C+D')}
    role,role_rows=role_diag(ev); prodmem,prodmem_rows=production_memory_diag(ev)
    res['C_role_loss_diagnostic']=role; res['C_production_memory_diagnostic']=prodmem
    outdir=Path('/mnt/data/phase34_results');outdir.mkdir(exist_ok=True)
    pred.to_csv(outdir/'phase34_prediction_rows.csv',index=False)
    role_rows.to_csv(outdir/'phase34_role_rows.csv',index=False)
    prodmem_rows.to_csv(outdir/'phase34_production_memory_rows.csv',index=False)
    with open(outdir/'phase34_results.json','w') as f:json.dump(res,f,indent=2,allow_nan=False)
    print('wrote',outdir)

if __name__=='__main__': main()

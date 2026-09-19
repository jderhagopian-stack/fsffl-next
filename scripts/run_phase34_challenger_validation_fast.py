from __future__ import annotations
import json, math, warnings
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression, BayesianRidge
warnings.filterwarnings('ignore')

STATES=("out","depth","usable","starter","premium","elite"); POSITIVE=STATES[1:]
STATE_RANK={s:i for i,s in enumerate(STATES)}; THRESHOLDS={"useful":2,"starter":3,"premium":4,"elite":5}
C=0.25; SEED=20260915
FOLDS=[('early',2014,2016,2013),('mid',2017,2018,2016),('validation',2019,2020,2018),('holdout',2021,2022,2020)]

def exp_band(x):
    x=int(x)
    return '0_1' if x<=1 else ('2_3' if x<=3 else ('4_6' if x<=6 else '7_plus'))

def features(r,age_mode='coarse',add_c=False,add_d=False):
    p=str(r.position); h=int(r.horizon); ex=int(r.experience)
    d={f'p={p}':1,f's={r.source_state}':1,f'h={h}':1,f'e={exp_band(ex)}':1,'exp':min(15.,max(0.,float(ex)))/10.}
    if age_mode=='coarse': d[f'a={r.age_band}']=1
    else:
        age=float(r.age); ref=31. if p=='QB' else 27.; d[f'age_exact_{p}']=(age-ref)/5.
        if age_mode=='a2':
            if p=='QB': d['age_late_QB']=max(0.,age-37.)/5.
            else:
                d[f'age_late_{p}']=max(0.,age-31.)/5.
                if p=='TE': d['age_young_TE']=max(0.,24.-age)/5.
    cur=max(0.,float(r.source_points)); prior=None if pd.isna(r.prior_points) else max(0.,float(r.prior_points)); pv=0. if prior is None else prior
    d.update({'lp':math.log1p(cur)/6.,'lprev':math.log1p(pv)/6.,'dpts':max(-2.,min(2.,(cur-pv)/100.)),'prev_cov':0 if prior is None else 1})
    role=str(r.source_role_band) if pd.notna(r.source_role_band) else 'unknown'
    if role in ('weak','established') and pd.notna(r.opportunity_per_game) and pd.notna(r.games):
        d[f'role={role}']=1; d['u_cov']=1; d['lopg']=math.log1p(max(0.,float(r.opportunity_per_game)))/4.; d['lg']=math.log1p(max(0.,float(r.games)))/3.
    else: d.update({'role=unknown':1,'u_cov':0,'lopg':0.,'lg':0.})
    d.update({'r_cov':0,'i_cov':0,'part_cov':0})
    if add_c:
        supported=((p=='QB' and r.age_band in ('prime','aging')) or (p=='WR' and r.age_band=='aging') or (p=='TE' and r.age_band=='aging'))
        if supported:
            k=f'mem_{p}_{r.age_band}_h{h}'; v=r.prior_age_state_resid_z
            d[k]=0. if pd.isna(v) else float(v); d[k+'_cov']=0 if pd.isna(v) else 1
    if add_d and pd.notna(r.state_pct):
        pct=float(r.state_pct); d[f'pct_{p}']=(pct-.5)*2.
        if r.source_state in ('premium','elite'):
            d[f'hi_{p}_{r.source_state}']=max(0.,(pct-.8)/.2); d[f'lo_{p}_{r.source_state}']=max(0.,(.2-pct)/.2)
    return d

class Bin:
    def __init__(self): self.v=DictVectorizer(sort=True); self.m=LogisticRegression(C=C,solver='lbfgs',max_iter=2000,random_state=SEED); self.ok=False
    def fit(self,feats,y):
        y=np.asarray(y,int); c=np.bincount(y,minlength=2)
        if len(y)>=100 and c.min()>=15: self.m.fit(self.v.fit_transform(feats),y); self.ok=True
    def probs(self,feats):
        if not self.ok: return None
        return self.m.predict_proba(self.v.transform(feats))[:,1]

class Model:
    def __init__(self,age_mode='coarse',add_c=False,add_d=False): self.age_mode=age_mode; self.add_c=add_c; self.add_d=add_d
    def fit(self,tr):
        f=[features(r,self.age_mode,self.add_c,False) for r in tr.itertuples()]; self.persist=Bin(); self.persist.fit(f,tr.y_persist)
        pos=tr[tr.y_persist==1]; of=[features(r,'coarse',self.add_c,self.add_d) for r in pos.itertuples()]; self.ord={}
        for nm,rank in THRESHOLDS.items():
            m=Bin(); m.fit(of,[STATE_RANK[s]>=rank for s in pos.y_state]); self.ord[nm]=m
        return self
    def predict(self,te):
        rows=list(te.itertuples()); pf=[features(r,self.age_mode,self.add_c,False) for r in rows]; p=self.persist.probs(pf)
        if p is None:return None
        of=[features(r,'coarse',self.add_c,self.add_d) for r in rows]; vals=[]; last=np.ones(len(rows))
        for nm in ('useful','starter','premium','elite'):
            q=self.ord[nm].probs(of)
            if q is None:return None
            q=np.minimum(last,np.clip(q,0,1)); vals.append(q); last=q
        u,st,pr,el=vals; cond=np.column_stack([1-u,u-st,st-pr,pr-el,el]); probs=np.column_stack([1-p,p[:,None]*cond]); return probs

class Stats:
    def __init__(self,tr):
        self.d={}
        for pref,cols in [('phs',['position','horizon','y_state']),('ps',['position','y_state']),('hs',['horizon','y_state']),('s',['y_state'])]:
            for key,g in tr.groupby(cols):
                if not isinstance(key,tuple):key=(key,)
                a=g.target_points.astype(float).to_numpy(); self.d[(pref,)+key]=(len(a),float(a.mean()),float(a.std(ddof=1)) if len(a)>1 else 0.)
    def get(self,p,h,s):
        for k,nmin in [(('phs',p,h,s),10),(('ps',p,s),10),(('hs',h,s),10),(('s',s),5)]:
            if k in self.d and self.d[k][0]>=nmin:
                n,mu,sd=self.d[k]; return mu,(sd if sd>1e-6 else max(1.,abs(mu)*.25))
        return 0.,1.

B_SUPPORT={(p,st,h) for p in ['QB'] for st in ['young','prime','aging'] for h in [1,2,3]}
B_SUPPORT|={('RB','prime',1),('WR','aging',1),('WR','aging',3),('TE','aging',1),('TE','aging',2),('TE','prime',1)}
class Carry:
    def __init__(self,tr):
        self.m={}
        for cell in B_SUPPORT:
            p,st,h=cell; g=tr[(tr.position==p)&(tr.age_band==st)&(tr.horizon==h)&(tr.y_persist==1)&tr.current_resid_z.notna()&tr.target_resid_z.notna()]
            if len(g)>=30 and g.source_season.nunique()>=3:self.m[cell]=BayesianRidge().fit(g[['current_resid_z']],g.target_resid_z)
    def val(self,r):
        m=self.m.get((r.position,r.age_band,int(r.horizon))); return 0. if m is None or pd.isna(r.current_resid_z) else float(m.predict([[r.current_resid_z]])[0])

def predict_fold(df,lo,hi,train_max,variant):
    outs=[]
    for hs in [(1,2),(3,)]:
        # outcomes must be observed by train_max; ensures no target leakage for h2/h3
        tr=df[df.horizon.isin(hs)&(df.source_season+df.horizon<=train_max)].copy(); te=df[df.horizon.isin(hs)&df.source_season.between(lo,hi)].copy()
        am='a2' if 'A2' in variant else ('a1' if 'A1' in variant else 'coarse'); ac='C' in variant; ad='D' in variant; ub='B' in variant
        mod=Model(am,ac,ad).fit(tr); pr=mod.predict(te)
        if pr is None:continue
        ss=Stats(tr); bc=Carry(tr) if ub else None; rows=list(te.itertuples()); pp=[]
        for i,r in enumerate(rows):
            adj=0. if bc is None else bc.val(r); ep=0.
            for j,s in enumerate(STATES):
                mu,sd=ss.get(r.position,int(r.horizon),s)
                if s!='out' and bc is not None:mu=max(0.,mu+adj*sd)
                ep+=pr[i,j]*mu
            pp.append(ep)
        keep=['source_season','player_id','position','horizon','age','age_band','exact_age_bin','experience','source_state','source_points','current_resid_z','prior_age_state_resid_z','state_pct','tail_group','source_role_band','target_role_band','role_loss','target_points','y_state','y_persist']
        o=te[keep].copy();
        for j,s in enumerate(STATES):o[f'p_{s}']=pr[:,j]
        o['pred_points']=pp;o['variant']=variant;outs.append(o)
    return pd.concat(outs,ignore_index=True) if outs else pd.DataFrame()

def metrics(g):
    if len(g)==0:return {'n':0}
    y=g.y_persist.to_numpy(float);p=1-g.p_out.to_numpy(float);eps=1e-12
    probs=g[[f'p_{s}' for s in STATES]].to_numpy(float); yi=np.array([STATE_RANK[s] for s in g.y_state]); Y=np.zeros_like(probs);Y[np.arange(len(g)),yi]=1
    ae=np.abs(g.pred_points-g.target_points); active=g.y_persist==1
    return {'n':int(len(g)),'persist_brier':float(np.mean((p-y)**2)),'persist_logloss':float(-np.mean(y*np.log(np.clip(p,eps,1-eps))+(1-y)*np.log(np.clip(1-p,eps,1-eps)))),'persist_bias':float(p.mean()-y.mean()),'state_brier':float(np.mean(np.sum((probs-Y)**2,axis=1))),'state_logloss':float(-np.mean(np.log(np.clip(probs[np.arange(len(g)),yi],eps,1)))),'points_mae':float(ae.mean()),'points_bias':float((g.pred_points-g.target_points).mean()),'active_points_mae':float(ae[active].mean()) if active.any() else None,'active_n':int(active.sum())}
def grouped(g):
    z={'overall':metrics(g),'position':{},'horizon':{},'position_horizon':{},'stage':{}}
    for k,x in g.groupby('position'):z['position'][k]=metrics(x)
    for k,x in g.groupby('horizon'):z['horizon'][str(k)]=metrics(x)
    for (p,h),x in g.groupby(['position','horizon']):z['position_horizon'][f'{p}_h{h}']=metrics(x)
    for (p,s),x in g.groupby(['position','age_band']):z['stage'][f'{p}_{s}']=metrics(x)
    return z

def agecal(g):
    out={}
    for k,x in g.groupby(['position','horizon','exact_age_bin']):
        if len(x)>=10:
            pred=(1-x.p_out).mean();act=x.y_persist.mean();out['|'.join(map(str,k))]={'n':len(x),'pred':float(pred),'actual':float(act),'gap':float(pred-act)}
    return out

def tails(g):
    out={};x=g[g.source_state.isin(['premium','elite'])&g.tail_group.notna()]
    for k,z in x.groupby(['position','horizon','source_state','tail_group']):
        if len(z)>=10:
            ea=(z.y_state=='elite').mean();ep=z.p_elite.mean();pa=z.y_state.isin(['premium','elite']).mean();pp=(z.p_premium+z.p_elite).mean()
            out['|'.join(map(str,k))]={'n':len(z),'elite_pred':float(ep),'elite_actual':float(ea),'elite_gap':float(ep-ea),'premium_plus_pred':float(pp),'premium_plus_actual':float(pa),'premium_plus_gap':float(pp-pa)}
    if out:
        n=sum(v['n'] for v in out.values());out['_weighted_abs_gap']={'n':n,'elite':sum(v['n']*abs(v['elite_gap']) for v in out.values() if 'elite_gap'in v)/n,'premium_plus':sum(v['n']*abs(v['premium_plus_gap']) for v in out.values() if 'premium_plus_gap'in v)/n}
    return out

def build():
    b=Path('/mnt/data/phase34_work/future-state-phase2');q=pd.read_csv(b/'phase2_q3_age_state_rows.csv');p=pd.read_csv(b/'phase2_player_season_panel.csv')
    st=q[q.horizon==1][['source_season','player_id','position','age','age_band','exact_age_bin','experience','source_state','source_points','current_resid_z','prior_age_state_resid_z','source_role_band']].copy()
    ps=p[['player_id','season','games','opportunity_per_game']].rename(columns={'season':'source_season'});st=st.merge(ps,on=['player_id','source_season'],how='left')
    pr=p[['player_id','season','fantasy_points']].copy();pr['source_season']=pr.season+1;pr=pr.rename(columns={'fantasy_points':'prior_points'})[['player_id','source_season','prior_points']];st=st.merge(pr,on=['player_id','source_season'],how='left')
    st['state_pct']=np.nan
    for _,idx in st.groupby(['source_season','position','source_state']).groups.items():
        ranks=st.loc[idx,'source_points'].rank(method='average');st.loc[idx,'state_pct']=(ranks-.5)/len(ranks)
    st['tail_group']=pd.cut(st.state_pct,[-np.inf,.33,.80,np.inf],labels=['lower','middle','extreme_upper']).astype(object)
    ev=q.merge(st[['source_season','player_id','prior_points','games','opportunity_per_game','state_pct','tail_group']],on=['source_season','player_id'],how='left')
    ev['y_state']=np.where(ev.target_state.isin(STATES),ev.target_state,'out');ev['y_persist']=(ev.y_state!='out').astype(int)
    return ev[(ev.source_state!='out')&ev.source_season.between(2005,2022)].copy()

def run_variants(ev,variants):
    arr=[]
    for v in variants:
        print('running',v,flush=True)
        for _,lo,hi,tmax in FOLDS:arr.append(predict_fold(ev,lo,hi,tmax,v))
    return pd.concat(arr,ignore_index=True)

def role_memory_diagnostics(ev):
    # One fixed pre-validation and pre-holdout comparison, preserving chronological separation.
    out={'role':{},'production':{}}
    for split,lo,hi,tmax in [('validation',2019,2020,2018),('holdout',2021,2022,2020)]:
        # role loss
        tr=ev[(ev.source_season+ev.horizon<=tmax)&(ev.source_role_band=='established')&ev.role_loss.notna()&(ev.y_persist==1)];te=ev[ev.source_season.between(lo,hi)&(ev.source_role_band=='established')&ev.role_loss.notna()&(ev.y_persist==1)]
        out['role'][split]={}
        for name,ac in [('base',False),('C',True)]:
            m=Bin();m.fit([features(r,'coarse',ac,False) for r in tr.itertuples()],tr.role_loss.astype(int)); pp=m.probs([features(r,'coarse',ac,False) for r in te.itertuples()])
            if pp is not None:
                y=te.role_loss.to_numpy(float);eps=1e-12;out['role'][split][name]={'n':len(te),'brier':float(np.mean((pp-y)**2)),'logloss':float(-np.mean(y*np.log(np.clip(pp,eps,1-eps))+(1-y)*np.log(np.clip(1-pp,eps,1-eps))))}
        # production memory supported cells
        rows=[]
        for cell,gtr in tr.groupby(['position','age_band','horizon']):
            p,stage,h=cell;support=(p=='QB' and stage in ('prime','aging')) or (p in ('WR','TE') and stage=='aging')
            if not support:continue
            gtr=gtr[gtr.current_resid_z.notna()&gtr.target_resid_z.notna()];gte=te[(te.position==p)&(te.age_band==stage)&(te.horizon==h)&te.current_resid_z.notna()&te.target_resid_z.notna()]
            if len(gtr)<30 or gte.empty:continue
            m1=BayesianRidge().fit(gtr[['current_resid_z']],gtr.target_resid_z); g2=gtr.dropna(subset=['prior_age_state_resid_z']);t2=gte.dropna(subset=['prior_age_state_resid_z'])
            if len(g2)<30:continue
            m2=BayesianRidge().fit(g2[['current_resid_z','prior_age_state_resid_z']],g2.target_resid_z)
            e1=np.abs(m1.predict(t2[['current_resid_z']])-t2.target_resid_z);e2=np.abs(m2.predict(t2[['current_resid_z','prior_age_state_resid_z']])-t2.target_resid_z)
            rows.append((len(t2),e1.sum(),e2.sum()))
        n=sum(x[0] for x in rows);out['production'][split]={'n':n,'current_only_mae_z':sum(x[1] for x in rows)/n if n else None,'current_plus_memory_mae_z':sum(x[2] for x in rows)/n if n else None}
    return out

def main():
    ev=build();print('rows',len(ev),flush=True)
    first=run_variants(ev,['baseline','A1','A2','B','C','D'])
    val=first[first.source_season.between(2019,2020)]; vm={v:metrics(val[val.variant==v]) for v in ['baseline','A1','A2']};asel=min(['A1','A2'],key=lambda v:(vm[v]['persist_brier'],vm[v]['persist_logloss']));print('A selected',asel,flush=True)
    combos=run_variants(ev,[asel+'+B',asel+'+C',asel+'+D',asel+'+B+C+D']);pred=pd.concat([first,combos],ignore_index=True)
    res={'study':'future-state-resolution-phase34-bounded-challengers-v2-blocked-oos','A_selected_on_validation':asel,'A_validation_metrics':vm,'folds':{},'age_calibration':{},'tail_calibration':{},'C_diagnostics':role_memory_diagnostics(ev)}
    for name,lo,hi,_ in FOLDS:
        ss=pred[pred.source_season.between(lo,hi)];res['folds'][name]={v:grouped(g) for v,g in ss.groupby('variant')}
        res['age_calibration'][name]={v:agecal(g) for v,g in ss.groupby('variant') if v in ['baseline','A1','A2',asel+'+B',asel+'+C',asel+'+D',asel+'+B+C+D']}
        res['tail_calibration'][name]={v:tails(g) for v,g in ss.groupby('variant') if v in ['baseline','D',asel+'+D',asel+'+B+C+D']}
    o=Path('/mnt/data/phase34_results_fast');o.mkdir(exist_ok=True);pred.to_csv(o/'phase34_prediction_rows.csv',index=False);json.dump(res,open(o/'phase34_results.json','w'),indent=2,allow_nan=False);print('WROTE',o,flush=True)
if __name__=='__main__':main()

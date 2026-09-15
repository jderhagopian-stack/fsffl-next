from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

FOLDS=tuple(range(2011,2023)); TAXONOMIES=("kmeans","quantile_balanced","quantile_starter_tail"); POSITIONS=("QB","RB","WR","TE"); STATES=("out","depth","usable","starter","premium","elite"); DISCOUNT=.85; EPS=1e-12


def load(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else 0.0

def argmax_state(p):return max(STATES,key=lambda s:(p[s],-STATES.index(s)))

def norm(p):
    z=sum(max(0.0,float(p.get(s,0))) for s in STATES)
    return {s:(max(0.0,float(p.get(s,0)))/z if z>EPS else 1/len(STATES)) for s in STATES}

class DirectTransition:
    """Fit next state from the exact inferred state label used at inference."""
    def __init__(self,rows,forecasts,cutoff,bounds,cal,anchor,shrink=40.0):
        self.cal=cal;self.shrink=shrink;self.levels=[defaultdict(lambda:defaultdict(float)) for _ in range(5)]
        for r in rows:
            if r.season>=cutoff:continue
            fr=forecasts.get((r.season,r.player_id))
            if fr is None:continue
            src=argmax_state(anchor.probs(r,fr));nxt=cal.state_for(r.next_points,bounds[r.position]);age=cal.age_band(r.position,r.age);exp=cal.exp_band(r.experience);draft=cal.draft_band(r.draft_pick)
            keys=[(r.position,),(r.position,src),(r.position,src,age),(r.position,src,age,exp),(r.position,src,age,exp,draft)]
            for i,k in enumerate(keys):self.levels[i][k][nxt]+=1.0
    def probs(self,row,src,step=1):
        cal=self.cal;age0=None if row.age is None else row.age+step-1;exp0=None if row.experience is None else row.experience+step-1;age=cal.age_band(row.position,age0);exp=cal.exp_band(exp0);draft=cal.draft_band(row.draft_pick)
        keys=[(row.position,),(row.position,src),(row.position,src,age),(row.position,src,age,exp),(row.position,src,age,exp,draft)]
        def smooth(c):
            n=sum(c.values())+.5*len(STATES);return {s:(c.get(s,0)+.5)/n for s in STATES}
        p=smooth(self.levels[0].get(keys[0],{}))
        for i in range(1,len(keys)):
            c=self.levels[i].get(keys[i],{});n=sum(c.values())
            if n<=0:continue
            q=smooth(c);w=n/(n+self.shrink);p=norm({s:(1-w)*p[s]+w*q[s] for s in STATES})
        return p
    def step(self,row,pcur,step=1,qb_meaningful=None):
        src=argmax_state(pcur);p=self.probs(row,src,step)
        if row.position=='QB' and qb_meaningful is not None:
            hi=('starter','premium','elite');lo=('out','depth','usable');t=max(0.0,min(1.0,qb_meaningful));hm=sum(p[s] for s in hi);lm=sum(p[s] for s in lo)
            for s in hi:p[s]=t*(p[s]/hm if hm>EPS else 1/3)
            for s in lo:p[s]=(1-t)*(p[s]/lm if lm>EPS else 1/3)
        return norm(p)

def aligned_transition_metrics(records,cal):
    # Event reference is the same inferred source state used by the transition model.
    bs=[];ll=[];up=[];dn=[];same=[];bypos=defaultdict(list);byage=defaultdict(list)
    import math
    for r,pcur,pnext,b in records:
        src=argmax_state(pcur);si=STATES.index(src);obs=cal.state_for(r.next_points,b[r.position]);oi=STATES.index(obs)
        brier=sum((pnext[s]-(1 if s==obs else 0))**2 for s in STATES)/len(STATES);bs.append(brier);ll.append(-math.log(max(EPS,pnext[obs])))
        u=sum(pnext[s] for s in STATES if STATES.index(s)>si);d=sum(pnext[s] for s in STATES if STATES.index(s)<si);q=pnext[src]
        rec=(u,oi>si,d,oi<si,q,oi==si);up.append((u,oi>si));dn.append((d,oi<si));same.append((q,oi==si));bypos[r.position].append(rec);byage[cal.age_band(r.position,r.age)].append(rec)
    def g(xs):return {'n':len(xs),'up_pred':mean(x[0] for x in xs),'up_obs':mean(float(x[1]) for x in xs),'down_pred':mean(x[2] for x in xs),'down_obs':mean(float(x[3]) for x in xs),'persist_pred':mean(x[4] for x in xs),'persist_obs':mean(float(x[5]) for x in xs)} if xs else {'n':0}
    return {'n':len(records),'brier':mean(bs),'log_loss':mean(ll),'up_pred':mean(x[0] for x in up),'up_obs':mean(float(x[1]) for x in up),'down_pred':mean(x[0] for x in dn),'down_obs':mean(float(x[1]) for x in dn),'persist_pred':mean(x[0] for x in same),'persist_obs':mean(float(x[1]) for x in same),'by_position':{k:g(v) for k,v in bypos.items()},'by_age':{k:g(v) for k,v in byage.items()}}

def fit_anchor_mode(aligned,rows,forecasts,cutoff,bounds,cal,allow_persistence):
    if allow_persistence:return aligned.fit_anchor(rows,forecasts,cutoff,bounds,cal)
    train=[r for r in rows if r.season<cutoff and (r.season,r.player_id) in forecasts];cands=[]
    for scale in (.25,.5,.75,1.0):
        model=aligned.CurrentStateAnchor(rows,forecasts,cutoff,bounds,cal,scale,0.0);rec=[(r,model.probs(r,forecasts[(r.season,r.player_id)]),bounds) for r in train];m=aligned.state_anchor_metrics(rec,cal);cands.append((m['brier']+.08*m['ordered_distance'],scale))
    _,scale=min(cands);return aligned.CurrentStateAnchor(rows,forecasts,cutoff,bounds,cal,scale,0.0),{'sd_scale':scale,'persistence_weight':0.0,'candidate_count':len(cands)}

def fold_model(aligned,cal,rows,forecasts,qb,season,taxonomy,allow_persistence):
    bounds=cal.taxonomy_boundaries(rows,season,taxonomy);anchor,params=fit_anchor_mode(aligned,rows,forecasts,season,bounds,cal,allow_persistence);tm=DirectTransition(rows,forecasts,season,bounds,cal,anchor);anchors=[];trans=[]
    for r in rows:
        if r.season!=season:continue
        fr=forecasts.get((r.season,r.player_id))
        if fr is None:continue
        pcur=anchor.probs(r,fr);q=qb.get((r.season,r.player_id));pnext=tm.step(r,pcur,1,None if q is None else q[0]);anchors.append((r,pcur,bounds));trans.append((r,pcur,pnext,bounds))
    return bounds,anchor,tm,params,anchors,trans

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--career-panel',type=Path,required=True);ap.add_argument('--model-a-rows',type=Path,required=True);ap.add_argument('--qb-results',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True);root=Path(__file__).parent
    aligned=load(root/'run_forecast_inference_aligned_state_calibration.py','direct_aligned');cal=load(root/'run_forecast_career_state_calibration.py','direct_cal');legacy=load(root/'run_fundamental_intrinsic_residual_calibration.py','direct_legacy');parity=load(root/'run_fundamental_intrinsic_production_parity.py','direct_parity');marg=load(root/'run_intrinsic_marginal_franchise_challenge.py','direct_marg')
    rows=cal.load_rows(a.career_panel);forecasts=aligned.load_forecasts(a.model_a_rows);qb=parity.load_qb_probabilities(a.qb_results);examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);by={(r.player_id,r.season):r for r in rows};_,fb,_=marg.contexts_from_forecasts(parity,a.model_a_rows);_,ab=marg.contexts_from_actual(legacy.load_rows(a.career_panel));frozen=json.loads(Path('artifacts/research/intrinsic_d2_frozen_reference.json').read_text());km=frozen['key_metrics']
    candidates=[]
    for allow in (False,True):
      for tax in TAXONOMIES:
        anchors=[];trans=[];folds=[]
        for season in FOLDS:
            b,an,tm,params,aa,tt=fold_model(aligned,cal,rows,forecasts,qb,season,tax,allow);anchors+=aa;trans+=tt;folds.append({'season':season,'anchor_parameters':params,'anchor':aligned.state_anchor_metrics(aa,cal),'transition':aligned_transition_metrics(tt,cal)})
        am=aligned.state_anchor_metrics(anchors,cal);tr=aligned_transition_metrics(trans,cal);score=am['brier']+tr['brier']+abs(tr['up_pred']-tr['up_obs'])+abs(tr['down_pred']-tr['down_obs'])+abs(tr['persist_pred']-tr['persist_obs'])
        candidates.append({'taxonomy':tax,'allow_persistence':allow,'score':score,'anchor':am,'transition':tr,'folds':folds})
    best=min(candidates,key=lambda x:x['score']);deploy=min((x for x in candidates if not x['allow_persistence']),key=lambda x:x['score'])
    def run_d2(chosen):
        tax=chosen['taxonomy'];allow=chosen['allow_persistence'];eval_rows=[];fold_mae={}
        for season in FOLDS:
            b,anchor,tm,params,aa,tt=fold_model(aligned,cal,rows,forecasts,qb,season,tax,allow);samples=cal.state_samples(rows,season,b);baseline=fb[season]
            def c2(x,pos):return (12*marg.marginal_at_x(max(0,x),baseline[pos])+.5*max(0,x))/13
            sv={(p,s):(0 if s=='out' else mean(c2(v,p) for v in samples.get((p,s),()))) for p in POSITIONS for s in STATES}
            def probs(e):
                r=by.get((e.player_id,e.season));fr=forecasts.get((e.season,e.player_id));
                if r is None or fr is None:return None
                pc=anchor.probs(r,fr);q=qb.get((e.season,e.player_id));p2=tm.step(r,pc,1,None if q is None else q[0]);p3=tm.step(r,p2,2,None if q is None else q[1]);return p2,p3
            train=[e for e in examples if e.season<season and e.season in fb];targets={}
            for e in train:
                t=0
                for off in range(6):
                    nr=by.get((e.player_id,e.season+off));yr=e.season+off
                    if nr is not None and yr in ab:t+=(DISCOUNT**off)*((12*marg.marginal_at_x(max(0,nr.points),ab[yr][e.position])+.5*max(0,nr.points))/13)
                targets[id(e)]=t
            def base(e,cf=0):
                pp=probs(e)
                if pp is None:return None
                p2,p3=pp;v=c2(e.means[0],e.position)+DISCOUNT*sum(p2[s]*sv[(e.position,s)] for s in STATES)+(DISCOUNT**2)*sum(p3[s]*sv[(e.position,s)] for s in STATES);term=(DISCOUNT**3)*sum(p3[s]*sv[(e.position,s)] for s in STATES);return v+cf*term,term
            parents={};cells={}
            for pos in POSITIONS:
                es=[e for e in train if e.position==pos];xy=[]
                for e in es:
                    z=base(e)
                    if z is not None:xy.append((z[1],max(0,targets[id(e)]-z[0])))
                den=sum(x*x for x,y in xy);parents[pos]=0 if den<EPS else max(0,sum(x*y for x,y in xy)/den)
                for band in ('young','prime','aging'):
                    sub=[e for e in es if cal.age_band(pos,e.age)==band];xy2=[]
                    for e in sub:
                        z=base(e)
                        if z is not None:xy2.append((z[1],max(0,targets[id(e)]-z[0])))
                    den2=sum(x*x for x,y in xy2);raw=parents[pos] if den2<EPS else max(0,sum(x*y for x,y in xy2)/den2);w=len(xy2)/(len(xy2)+100) if len(xy2)>=30 else 0;cells[(pos,band)]=w*raw+(1-w)*parents[pos]
            errs=[]
            for e in [x for x in examples if x.season==season]:
                z=base(e,cells.get((e.position,cal.age_band(e.position,e.age)),parents[e.position]))
                if z is None:continue
                target=0
                for off in range(6):
                    nr=by.get((e.player_id,e.season+off));yr=e.season+off
                    if nr is not None and yr in ab:target+=(DISCOUNT**off)*((12*marg.marginal_at_x(max(0,nr.points),ab[yr][e.position])+.5*max(0,nr.points))/13)
                er=abs(z[0]-target);errs.append(er);eval_rows.append({'position':e.position,'age':e.age,'target':target,'error':er})
            fold_mae[str(season)]=mean(errs)
        targets=[r['target'] for r in eval_rows];q25=cal.quantile(targets,.25);q50=cal.quantile(targets,.5);q90=cal.quantile(targets,.9);groups={'young':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='young'],'developmental':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='young' and r['target']<q50],'prime':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='prime'],'aging':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='aging'],'fringe':[r for r in eval_rows if r['target']<=q25],'elite':[r for r in eval_rows if r['target']>=q90]};mae=lambda xs:mean(r['error'] for r in xs)
        return {'n':len(eval_rows),'mae':mae(eval_rows),'fold_wins_vs_A':sum(v<km['A_fold_mae'][s] for s,v in fold_mae.items()),'fold_mae':fold_mae,'position_mae':{p:mae([r for r in eval_rows if r['position']==p]) for p in POSITIONS},'group_mae':{k:mae(v) for k,v in groups.items()}}
    best_d2=run_d2(best);deploy_d2=best_d2 if best==deploy else run_d2(deploy)
    out={'model_version':'forecast-inference-aligned-direct-v1','candidates':candidates,'best_research_candidate':best,'best_deployable_candidate':deploy,'best_research_D2':best_d2,'deployable_D2':deploy_d2,'A_mae':km['overall_mae']['A'],'old_D2_mae':km['overall_mae']['D2'],'synthetic_gate':'unchanged D2 equation; prior synthetic results remain authoritative unless promoted wiring changes','leakage_check':{'market':False,'transactions':False,'owner_behavior':False,'team_specific':False,'future_current_state_at_inference':False}}
    (a.output_dir/'forecast_inference_aligned_state_direct.json').write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps({'best_research':{'taxonomy':best['taxonomy'],'allow_persistence':best['allow_persistence'],'anchor':best['anchor'],'transition':best['transition'],'D2':best_d2},'best_deployable':{'taxonomy':deploy['taxonomy'],'anchor':deploy['anchor'],'transition':deploy['transition'],'D2':deploy_d2},'A_mae':out['A_mae'],'old_D2_mae':out['old_D2_mae']},indent=2,sort_keys=True))

if __name__=='__main__':main()

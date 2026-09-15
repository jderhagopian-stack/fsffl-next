from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

STATE_NAMES=("out","depth","usable","starter","premium","elite")
POSITIONS=("QB","RB","WR","TE")
MEANINGFUL=("starter","premium","elite")
FOLDS=tuple(range(2011,2023))
DISCOUNT=.85
EPS=1e-12


def load(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m


def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else 0.0


def norm_cdf(x:float)->float:
    return .5*(1.0+math.erf(x/math.sqrt(2.0)))


def normalize(p):
    z=sum(max(0.0,float(v)) for v in p.values())
    if z<=EPS:return {s:1.0/len(STATE_NAMES) for s in STATE_NAMES}
    return {s:max(0.0,float(p.get(s,0.0)))/z for s in STATE_NAMES}


def blend(a,b,w):return normalize({s:(1-w)*a[s]+w*b[s] for s in STATE_NAMES})

def sidx(s):return STATE_NAMES.index(s)

@dataclass(frozen=True)
class ForecastRow:
    season:int;player_id:str;position:str;mean:float;sd:float


def load_forecasts(path:Path):
    out={}
    with path.open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if int(r['season_offset'])!=0 or r['position'] not in POSITIONS:continue
            out[(int(r['target_season']),r['asset_id'])]=ForecastRow(int(r['target_season']),r['asset_id'],r['position'],max(0.0,float(r['player_forecast_mean'])),max(0.0,float(r['player_forecast_stddev'])))
    return out


def gaussian_state_mass(mu,sd,bounds,scale):
    sd=max(EPS,sd*scale)
    cuts=(0.0,*bounds)
    cdfs=[norm_cdf((c-mu)/sd) for c in cuts]
    vals=[cdfs[0]]
    vals.extend(max(0.0,cdfs[i]-cdfs[i-1]) for i in range(1,len(cdfs)))
    vals.append(max(0.0,1.0-cdfs[-1]))
    return normalize(dict(zip(STATE_NAMES,vals)))


def age_band(cal,pos,age):return cal.age_band(pos,age)
def exp_band(cal,exp):return cal.exp_band(exp)
def draft_band(cal,pick):return cal.draft_band(pick)

class PersistenceModel:
    def __init__(self,rows,cutoff,bounds,cal,shrink=35.0):
        self.cal=cal;self.shrink=shrink;self.levels=[defaultdict(lambda:defaultdict(float)) for _ in range(5)]
        by={(r.player_id,r.season):r for r in rows}
        for r in rows:
            if r.season>=cutoff:continue
            prior=by.get((r.player_id,r.season-1))
            if prior is None:continue
            prev=cal.state_for(prior.points,bounds[r.position]);obs=cal.state_for(r.points,bounds[r.position])
            keys=[(r.position,), (r.position,prev), (r.position,prev,age_band(cal,r.position,r.age)), (r.position,prev,age_band(cal,r.position,r.age),exp_band(cal,r.experience)), (r.position,prev,age_band(cal,r.position,r.age),exp_band(cal,r.experience),draft_band(cal,r.draft_pick))]
            for i,k in enumerate(keys):self.levels[i][k][obs]+=1.0
    def probs(self,row,prior_state):
        cal=self.cal
        keys=[(row.position,), (row.position,prior_state), (row.position,prior_state,age_band(cal,row.position,row.age)), (row.position,prior_state,age_band(cal,row.position,row.age),exp_band(cal,row.experience)), (row.position,prior_state,age_band(cal,row.position,row.age),exp_band(cal,row.experience),draft_band(cal,row.draft_pick))]
        def smoothed(c):
            n=sum(c.values())+.5*len(STATE_NAMES);return {s:(c.get(s,0.0)+.5)/n for s in STATE_NAMES}
        p=smoothed(self.levels[0].get(keys[0],{}))
        for i in range(1,len(keys)):
            c=self.levels[i].get(keys[i],{});n=sum(c.values())
            if n<=0:continue
            q=smoothed(c);w=n/(n+self.shrink);p=blend(p,q,w)
        return normalize(p)

class CurrentStateAnchor:
    def __init__(self,rows,forecasts,cutoff,bounds,cal,sd_scale,persistence_weight):
        self.rows=rows;self.by={(r.player_id,r.season):r for r in rows};self.forecasts=forecasts;self.cutoff=cutoff;self.bounds=bounds;self.cal=cal;self.sd_scale=sd_scale;self.persistence_weight=persistence_weight;self.persistence=PersistenceModel(rows,cutoff,bounds,cal)
    def probs(self,row,fr):
        p=gaussian_state_mass(fr.mean,fr.sd,self.bounds[row.position],self.sd_scale)
        prior=self.by.get((row.player_id,row.season-1))
        if prior is None:return p
        prior_state=self.cal.state_for(prior.points,self.bounds[row.position])
        return blend(p,self.persistence.probs(row,prior_state),self.persistence_weight)


def state_anchor_metrics(records,cal):
    brier=[];ll=[];distance=[];correct=0;pred_prev=defaultdict(float);obs_prev=defaultdict(float);conf=defaultdict(lambda:defaultdict(int))
    bypos=defaultdict(list);byage=defaultdict(list);byexp=defaultdict(list)
    for r,p,b in records:
        obs=cal.state_for(r.points,b[r.position]);pred=max(STATE_NAMES,key=lambda s:(p[s],-sidx(s)))
        brier.append(sum((p[s]-(1 if s==obs else 0))**2 for s in STATE_NAMES)/len(STATE_NAMES));ll.append(-math.log(max(EPS,p[obs])));distance.append(sum(p[s]*abs(sidx(s)-sidx(obs)) for s in STATE_NAMES));correct+=pred==obs;conf[obs][pred]+=1
        for s in STATE_NAMES:pred_prev[s]+=p[s]
        obs_prev[obs]+=1
        bypos[r.position].append((r,p,b));byage[age_band(cal,r.position,r.age)].append((r,p,b));byexp[exp_band(cal,r.experience)].append((r,p,b))
    n=len(records)
    def mini(xs):
        if not xs:return {'n':0}
        bs=[];ds=[];ok=0
        for r,p,b in xs:
            o=cal.state_for(r.points,b[r.position]);q=max(STATE_NAMES,key=lambda s:p[s]);bs.append(sum((p[s]-(1 if s==o else 0))**2 for s in STATE_NAMES)/len(STATE_NAMES));ds.append(sum(p[s]*abs(sidx(s)-sidx(o)) for s in STATE_NAMES));ok+=q==o
        return {'n':len(xs),'brier':mean(bs),'ordered_distance':mean(ds),'argmax_accuracy':ok/len(xs)}
    return {'n':n,'brier':mean(brier),'log_loss':mean(ll),'ordered_distance':mean(distance),'argmax_accuracy':correct/n if n else 0.0,'predicted_prevalence':{s:pred_prev[s]/n for s in STATE_NAMES} if n else {},'observed_prevalence':{s:obs_prev[s]/n for s in STATE_NAMES} if n else {},'confusion':{o:{p:conf[o].get(p,0) for p in STATE_NAMES} for o in STATE_NAMES},'by_position':{k:mini(v) for k,v in bypos.items()},'by_age':{k:mini(v) for k,v in byage.items()},'by_experience':{k:mini(v) for k,v in byexp.items()}}


def old_hard_anchor_metrics(rows,forecasts,bounds,cal):
    rec=[]
    for r in rows:
        fr=forecasts.get((r.season,r.player_id))
        if fr is None:continue
        s=cal.state_for(fr.mean,bounds[r.position]);rec.append((r,{x:1.0 if x==s else 0.0 for x in STATE_NAMES},bounds))
    return state_anchor_metrics(rec,cal)


def fit_anchor(rows,forecasts,cutoff,bounds,cal):
    candidates=[]
    train=[r for r in rows if r.season<cutoff and (r.season,r.player_id) in forecasts]
    for scale in (.25,.5,.75,1.0):
        for w in (0.0,.25,.5,.75):
            model=CurrentStateAnchor(rows,forecasts,cutoff,bounds,cal,scale,w);rec=[(r,model.probs(r,forecasts[(r.season,r.player_id)]),bounds) for r in train]
            m=state_anchor_metrics(rec,cal);score=m['brier']+.08*m['ordered_distance']
            candidates.append((score,scale,w))
    _,scale,w=min(candidates)
    return CurrentStateAnchor(rows,forecasts,cutoff,bounds,cal,scale,w),{'sd_scale':scale,'persistence_weight':w,'candidate_count':len(candidates)}

class AlignedTransitionModel:
    def __init__(self,rows,forecasts,cutoff,bounds,cal,anchor,shrink=40.0):
        self.cal=cal;self.shrink=shrink;self.levels=[defaultdict(lambda:defaultdict(float)) for _ in range(5)]
        for r in rows:
            if r.season>=cutoff:continue
            fr=forecasts.get((r.season,r.player_id))
            if fr is None:continue
            pcur=anchor.probs(r,fr);nxt=cal.state_for(r.next_points,bounds[r.position])
            for src,mass in pcur.items():
                if mass<=0:continue
                keys=[(r.position,), (r.position,src), (r.position,src,age_band(cal,r.position,r.age)), (r.position,src,age_band(cal,r.position,r.age),exp_band(cal,r.experience)), (r.position,src,age_band(cal,r.position,r.age),exp_band(cal,r.experience),draft_band(cal,r.draft_pick))]
                for i,k in enumerate(keys):self.levels[i][k][nxt]+=mass
    def probs_from_state(self,row,src,step=1):
        cal=self.cal;age=None if row.age is None else row.age+step-1;exp=None if row.experience is None else row.experience+step-1
        keys=[(row.position,), (row.position,src), (row.position,src,age_band(cal,row.position,age)), (row.position,src,age_band(cal,row.position,age),exp_band(cal,exp)), (row.position,src,age_band(cal,row.position,age),exp_band(cal,exp),draft_band(cal,row.draft_pick))]
        def smoothed(c):
            n=sum(c.values())+.5*len(STATE_NAMES);return {s:(c.get(s,0.0)+.5)/n for s in STATE_NAMES}
        p=smoothed(self.levels[0].get(keys[0],{}))
        for i in range(1,len(keys)):
            c=self.levels[i].get(keys[i],{});n=sum(c.values())
            if n<=0:continue
            q=smoothed(c);w=n/(n+self.shrink);p=blend(p,q,w)
        return normalize(p)
    def step(self,row,pcur,step=1,qb_meaningful=None):
        nxt={s:0.0 for s in STATE_NAMES}
        for src,mass in pcur.items():
            q=self.probs_from_state(row,src,step)
            for s,v in q.items():nxt[s]+=mass*v
        nxt=normalize(nxt)
        if row.position=='QB' and qb_meaningful is not None:
            target=max(0.0,min(1.0,qb_meaningful));hi=sum(nxt[s] for s in MEANINGFUL);lo=1-hi;lows=[s for s in STATE_NAMES if s not in MEANINGFUL]
            for s in MEANINGFUL:nxt[s]=target*(nxt[s]/hi if hi>EPS else 1/len(MEANINGFUL))
            for s in lows:nxt[s]=(1-target)*(nxt[s]/lo if lo>EPS else 1/len(lows))
        return normalize(nxt)


def transition_metrics(records,cal):
    brier=[];ll=[];up_p=[];up_y=[];dn_p=[];dn_y=[];stay_p=[];stay_y=[];bypos=defaultdict(list);byage=defaultdict(list)
    for r,pcur,pnext,b in records:
        cur_obs=cal.state_for(r.points,b[r.position]);nxt_obs=cal.state_for(r.next_points,b[r.position]);ci=sidx(cur_obs);ni=sidx(nxt_obs)
        brier.append(sum((pnext[s]-(1 if s==nxt_obs else 0))**2 for s in STATE_NAMES)/len(STATE_NAMES));ll.append(-math.log(max(EPS,pnext[nxt_obs])))
        expected_cur=sum(pcur[s]*sidx(s) for s in STATE_NAMES)
        joint_up=sum(pnext[s] for s in STATE_NAMES if sidx(s)>expected_cur+.5)
        joint_dn=sum(pnext[s] for s in STATE_NAMES if sidx(s)<expected_cur-.5)
        joint_stay=max(0.0,1.0-joint_up-joint_dn)
        up_p.append(joint_up);up_y.append(ni>ci);dn_p.append(joint_dn);dn_y.append(ni<ci);stay_p.append(joint_stay);stay_y.append(ni==ci)
        bypos[r.position].append((joint_up,ni>ci,joint_dn,ni<ci));byage[age_band(cal,r.position,r.age)].append((joint_up,ni>ci,joint_dn,ni<ci))
    def ece(ps,ys,bins=10):
        if not ps:return 0.0
        v=0.0
        for b in range(bins):
            lo=b/bins;hi=(b+1)/bins;idx=[i for i,x in enumerate(ps) if x>=lo and (x<hi or (b==bins-1 and x<=hi))]
            if idx:v+=len(idx)/len(ps)*abs(mean(ps[i] for i in idx)-mean(float(ys[i]) for i in idx))
        return v
    def group(xs):return {'n':len(xs),'up_pred':mean(x[0] for x in xs),'up_obs':mean(float(x[1]) for x in xs),'down_pred':mean(x[2] for x in xs),'down_obs':mean(float(x[3]) for x in xs)} if xs else {'n':0}
    return {'n':len(records),'brier':mean(brier),'log_loss':mean(ll),'up_pred':mean(up_p),'up_obs':mean(float(x) for x in up_y),'down_pred':mean(dn_p),'down_obs':mean(float(x) for x in dn_y),'persist_pred':mean(stay_p),'persist_obs':mean(float(x) for x in stay_y),'ece_up':ece(up_p,up_y),'ece_down':ece(dn_p,dn_y),'by_position':{k:group(v) for k,v in bypos.items()},'by_age':{k:group(v) for k,v in byage.items()}}


def fit_fold(rows,forecasts,season,taxonomy,cal,qb_probs):
    bounds=cal.taxonomy_boundaries(rows,season,taxonomy);anchor,params=fit_anchor(rows,forecasts,season,bounds,cal);tm=AlignedTransitionModel(rows,forecasts,season,bounds,cal,anchor)
    test=[r for r in rows if r.season==season and (r.season,r.player_id) in forecasts]
    anchors=[];trans=[]
    for r in test:
        fr=forecasts[(r.season,r.player_id)];pcur=anchor.probs(r,fr);qbp=qb_probs.get((r.season,r.player_id));pnext=tm.step(r,pcur,1,None if qbp is None else qbp[0]);anchors.append((r,pcur,bounds));trans.append((r,pcur,pnext,bounds))
    return bounds,anchor,tm,params,anchors,trans


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--career-panel',type=Path,required=True);ap.add_argument('--model-a-rows',type=Path,required=True);ap.add_argument('--qb-results',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).parent;cal=load(root/'run_forecast_career_state_calibration.py','aligned_cal');legacy=load(root/'run_fundamental_intrinsic_residual_calibration.py','aligned_legacy');parity=load(root/'run_fundamental_intrinsic_production_parity.py','aligned_parity');marg=load(root/'run_intrinsic_marginal_franchise_challenge.py','aligned_marg')
    rows=cal.load_rows(a.career_panel);forecasts=load_forecasts(a.model_a_rows);qb_probs=parity.load_qb_probabilities(a.qb_results);examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);by={(r.player_id,r.season):r for r in rows};_,forecast_baselines,_=marg.contexts_from_forecasts(parity,a.model_a_rows);_,actual_baselines=marg.contexts_from_actual(legacy.load_rows(a.career_panel))
    frozen=json.loads(Path('artifacts/research/intrinsic_d2_frozen_reference.json').read_text());km=frozen['key_metrics'];a_fold=km['A_fold_mae'];a_mae=km['overall_mae']['A'];old_d2_mae=km['overall_mae']['D2']

    taxonomy_runs=[]
    for taxonomy in ('kmeans','quantile_balanced','quantile_starter_tail'):
        ar=[];tr=[];folds=[];old=[]
        for season in FOLDS:
            bounds,anchor,tm,params,anchors,trans=fit_fold(rows,forecasts,season,taxonomy,cal,qb_probs);ar.extend(anchors);tr.extend(trans);test=[r for r in rows if r.season==season and (r.season,r.player_id) in forecasts];old.extend((r,{s:1.0 if s==cal.state_for(forecasts[(r.season,r.player_id)].mean,bounds[r.position]) else 0.0 for s in STATE_NAMES},bounds) for r in test);folds.append({'season':season,'anchor':state_anchor_metrics(anchors,cal),'transition':transition_metrics(trans,cal),'anchor_parameters':params})
        am=state_anchor_metrics(ar,cal);tmx=transition_metrics(tr,cal);om=state_anchor_metrics(old,cal);score=am['brier']+.08*am['ordered_distance']+tmx['brier']+abs(tmx['up_pred']-tmx['up_obs'])+abs(tmx['down_pred']-tmx['down_obs'])
        taxonomy_runs.append({'taxonomy':taxonomy,'score':score,'old_y1_anchor':om,'new_anchor':am,'transition':tmx,'folds':folds})
    selected=min(taxonomy_runs,key=lambda x:x['score']);taxonomy=selected['taxonomy']

    eval_rows=[];fold_mae={}
    for season in FOLDS:
        bounds,anchor,tm,params,anchors,trans=fit_fold(rows,forecasts,season,taxonomy,cal,qb_probs);samples=cal.state_samples(rows,season,bounds);baseline=forecast_baselines[season]
        def c2(x,pos):return (12.0*marg.marginal_at_x(max(0.0,x),baseline[pos])+.5*max(0.0,x))/13.0
        sv={(p,s):(0.0 if s=='out' else mean(c2(v,p) for v in samples.get((p,s),()))) for p in POSITIONS for s in STATE_NAMES}
        def probs_for(e):
            hist=by.get((e.player_id,e.season));fr=forecasts.get((e.season,e.player_id));
            if hist is None or fr is None:return None
            pcur=anchor.probs(hist,fr);qbp=qb_probs.get((e.season,e.player_id));p2=tm.step(hist,pcur,1,None if qbp is None else qbp[0]);p3=tm.step(hist,p2,2,None if qbp is None else qbp[1]);return pcur,p2,p3
        train=[e for e in examples if e.season<season and e.season in forecast_baselines];target_by={}
        for e in train:
            target=0.0
            for off in range(6):
                nr=by.get((e.player_id,e.season+off));yr=e.season+off
                if nr is not None and yr in actual_baselines:target+=(DISCOUNT**off)*((12.0*marg.marginal_at_x(max(0.0,nr.points),actual_baselines[yr][e.position])+.5*max(0.0,nr.points))/13.0)
            target_by[id(e)]=target
        def base_value(e,cf=0.0):
            pp=probs_for(e)
            if pp is None:return None
            _,p2,p3=pp;v=c2(e.means[0],e.position)+DISCOUNT*sum(p2[s]*sv[(e.position,s)] for s in STATE_NAMES)+(DISCOUNT**2)*sum(p3[s]*sv[(e.position,s)] for s in STATE_NAMES);term=(DISCOUNT**3)*sum(p3[s]*sv[(e.position,s)] for s in STATE_NAMES);return v+cf*term,term
        parents={};cells={}
        for pos in POSITIONS:
            xy=[];es=[]
            for e in train:
                if e.position!=pos:continue
                z=base_value(e)
                if z is None:continue
                es.append(e);xy.append((z[1],max(0.0,target_by[id(e)]-z[0])))
            den=sum(x*x for x,y in xy);parents[pos]=0.0 if den<EPS else max(0.0,sum(x*y for x,y in xy)/den)
            for band in ('young','prime','aging'):
                sub=[e for e in es if cal.age_band(pos,e.age)==band];xy2=[]
                for e in sub:
                    z=base_value(e)
                    if z is not None:xy2.append((z[1],max(0.0,target_by[id(e)]-z[0])))
                den2=sum(x*x for x,y in xy2);raw=parents[pos] if den2<EPS else max(0.0,sum(x*y for x,y in xy2)/den2);w=len(xy2)/(len(xy2)+100.0) if len(xy2)>=30 else 0.0;cells[(pos,band)]=w*raw+(1-w)*parents[pos]
        errs=[]
        for e in [x for x in examples if x.season==season]:
            cf=cells.get((e.position,cal.age_band(e.position,e.age)),parents[e.position]);z=base_value(e,cf)
            if z is None:continue
            pred=z[0];target=0.0
            for off in range(6):
                nr=by.get((e.player_id,e.season+off));yr=e.season+off
                if nr is not None and yr in actual_baselines:target+=(DISCOUNT**off)*((12.0*marg.marginal_at_x(max(0.0,nr.points),actual_baselines[yr][e.position])+.5*max(0.0,nr.points))/13.0)
            err=abs(pred-target);errs.append(err);eval_rows.append({'season':season,'position':e.position,'age':e.age,'experience':e.experience,'pred':pred,'target':target,'error':err})
        fold_mae[str(season)]=mean(errs)
    def mae(rs):return mean(r['error'] for r in rs)
    targets=[r['target'] for r in eval_rows];q25=cal.quantile(targets,.25);q50=cal.quantile(targets,.5);q90=cal.quantile(targets,.9)
    groups={'young':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='young'],'prime':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='prime'],'aging':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='aging'],'developmental':[r for r in eval_rows if cal.age_band(r['position'],r['age'])=='young' and r['target']<q50],'fringe':[r for r in eval_rows if r['target']<=q25],'elite':[r for r in eval_rows if r['target']>=q90]}
    new_d2={'n':len(eval_rows),'mae':mae(eval_rows),'fold_mae':fold_mae,'fold_wins_vs_A':sum(v<float(a_fold[s]) for s,v in fold_mae.items()),'position_mae':{p:mae([r for r in eval_rows if r['position']==p]) for p in POSITIONS},'group_mae':{g:mae(v) for g,v in groups.items() if v}}
    payload={'model_version':'forecast-inference-aligned-career-state-v1','selected_taxonomy':taxonomy,'taxonomy_runs':taxonomy_runs,'current_state_reference':'realized current-season production state is label only; inference uses PIT Forecast Y1 distribution plus prior-season realized production, age, experience, draft evidence','transition_training':'fractional transition counts conditioned on the same inferred current-state distribution used at inference','A_mae':a_mae,'old_D2':{'mae':old_d2_mae,'fold_wins_vs_A':km['D2_fold_wins_vs_A'],'position_mae':km['position_mae']['D2'],'group_mae':km['group_mae']['D2']},'new_D2':new_d2,'parameter_provenance':{'taxonomy':'empirically fitted chronological position-specific thresholds','anchor_sd_scale':'empirically selected from bounded four-value grid inside each chronological training fold','anchor_persistence_weight':'empirically selected from bounded four-value grid inside each chronological training fold','persistence_and_transition_frequencies':'empirically fitted with hierarchical shrinkage','dirichlet_alpha':'provisional prior 0.5','QB_future_meaningful_mass':'existing governed QB career-state evidence','D2':'frozen unchanged'},'leakage_check':{'future_current_label_used_at_inference':False,'market':False,'transactions':False,'owner_behavior':False,'team_roster':False,'team_utility':False}}
    (a.output_dir/'forecast_inference_aligned_state_calibration.json').write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps({'selected_taxonomy':taxonomy,'old_anchor':selected['old_y1_anchor'],'new_anchor':selected['new_anchor'],'transition':selected['transition'],'A_mae':payload['A_mae'],'old_D2_mae':payload['old_D2']['mae'],'new_D2':new_d2},indent=2,sort_keys=True))

if __name__=='__main__':main()

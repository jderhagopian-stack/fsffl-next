from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

STATE_NAMES=("out","depth","usable","starter","premium","elite")
MEANINGFUL=("starter","premium","elite")
POSITIONS=("QB","RB","WR","TE")
DISCOUNT=0.85
FOLDS=tuple(range(2011,2023))
EPS=1e-12


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m


def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else 0.0


def quantile(xs,p):
    ys=sorted(float(x) for x in xs)
    if not ys:return 0.0
    z=p*(len(ys)-1);lo=int(math.floor(z));hi=int(math.ceil(z))
    return ys[lo] if lo==hi else ys[lo]*(hi-z)+ys[hi]*(z-lo)


def age_band(pos,age):
    if age is None:return "unknown"
    if pos=="QB":return "young" if age<=25 else ("prime" if age<=31 else "aging")
    return "young" if age<=23 else ("prime" if age<=27 else "aging")


def exp_band(exp):
    if exp is None:return "unknown"
    e=int(exp)
    if e<=0:return "rookie"
    if e<=2:return "1-2"
    if e<=5:return "3-5"
    return "6+"


def draft_band(pick):
    if pick is None:return "unknown"
    try:p=float(pick)
    except:return "unknown"
    if p<=0:return "unknown"
    if p<=50:return "top50"
    if p<=100:return "51-100"
    if p<=180:return "101-180"
    return "late"

@dataclass(frozen=True)
class Row:
    player_id:str;season:int;position:str;points:float;next_points:float;age:float|None;experience:int|None;draft_pick:float|None;prior_pct:float|None


def load_rows(path:Path):
    out=[]
    with path.open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['position'] not in POSITIONS:continue
            def fl(k):
                v=r.get(k,'');return None if v in ('',None,'NA') else float(v)
            exp=fl('experience_years')
            out.append(Row(r['player_id'],int(r['season']),r['position'],float(r['fantasy_points']),float(r['next_fantasy_points']),fl('age_years'),None if exp is None else int(exp),fl('draft_pick'),fl('prior_production_percentile')))
    return out


def taxonomy_boundaries(rows,cutoff,mode):
    if mode=='kmeans':
        vals={p:[r.points for r in rows if r.position==p and r.season<cutoff and r.points>0] for p in POSITIONS}
        out={}
        for p,xs in vals.items():
            logs=sorted(math.log1p(x) for x in xs);centers=[quantile(logs,(i+.5)/5) for i in range(5)]
            for _ in range(40):
                groups=[[] for _ in range(5)]
                for x in logs:groups[min(range(5),key=lambda i:abs(x-centers[i]))].append(x)
                new=[mean(g) if g else centers[i] for i,g in enumerate(groups)];new.sort()
                if max(abs(a-b) for a,b in zip(new,centers))<1e-8:centers=new;break
                centers=new
            c=[math.expm1(x) for x in centers];out[p]=tuple((c[i]+c[i+1])/2 for i in range(4))
        return out
    qs={'quantile_balanced':(.25,.50,.75,.90),'quantile_starter_tail':(.35,.60,.80,.95)}[mode]
    return {p:tuple(quantile([r.points for r in rows if r.position==p and r.season<cutoff and r.points>0],q) for q in qs) for p in POSITIONS}


def state_for(points,bounds):
    if points<=0:return 'out'
    i=0
    while i<len(bounds) and points>bounds[i]:i+=1
    return STATE_NAMES[i+1]


def sidx(s):return STATE_NAMES.index(s)


def normalize(counts,alpha=.5):
    n=sum(counts.values())+alpha*len(STATE_NAMES)
    return {s:(counts.get(s,0.0)+alpha)/n for s in STATE_NAMES}


def blend(a,b,w):return {s:w*a[s]+(1-w)*b[s] for s in STATE_NAMES}

class TransitionModel:
    def __init__(self, rows, cutoff, bounds, shrink=40.0):
        self.shrink=shrink;self.levels=[defaultdict(lambda:defaultdict(float)) for _ in range(5)]
        for r in rows:
            if r.season>=cutoff:continue
            cur=state_for(r.points,bounds[r.position]);nxt=state_for(r.next_points,bounds[r.position])
            keys=[
                (r.position,),
                (r.position,cur),
                (r.position,cur,age_band(r.position,r.age)),
                (r.position,cur,age_band(r.position,r.age),exp_band(r.experience)),
                (r.position,cur,age_band(r.position,r.age),exp_band(r.experience),draft_band(r.draft_pick)),
            ]
            for i,k in enumerate(keys):self.levels[i][k][nxt]+=1.0
    def probs(self,pos,cur,age,exp,pick):
        keys=[(pos,),(pos,cur),(pos,cur,age_band(pos,age)),(pos,cur,age_band(pos,age),exp_band(exp)),(pos,cur,age_band(pos,age),exp_band(exp),draft_band(pick))]
        p=normalize(self.levels[0].get(keys[0],{}))
        for i in range(1,5):
            c=self.levels[i].get(keys[i],{});n=sum(c.values())
            if n<=0:continue
            q=normalize(c);w=n/(n+self.shrink);p=blend(q,p,w)
        z=sum(p.values());return {s:p[s]/z for s in STATE_NAMES}


def propagate(model,row,bounds,horizon=2,qb_meaningful=None):
    cur=state_for(row.points,bounds[row.position]);p={cur:1.0}
    for step in range(1,horizon+1):
        nxt={s:0.0 for s in STATE_NAMES}
        for src,mass in p.items():
            q=model.probs(row.position,src,None if row.age is None else row.age+step-1,None if row.experience is None else row.experience+step-1,row.draft_pick)
            for s,v in q.items():nxt[s]+=mass*v
        if row.position=='QB' and qb_meaningful is not None and step<=len(qb_meaningful):
            target=max(0.0,min(1.0,qb_meaningful[step-1]));hi=sum(nxt[s] for s in MEANINGFUL);lo=1-hi
            for s in MEANINGFUL:nxt[s]=target*(nxt[s]/hi if hi>EPS else 1/3)
            lows=[s for s in STATE_NAMES if s not in MEANINGFUL]
            for s in lows:nxt[s]=(1-target)*(nxt[s]/lo if lo>EPS else 1/len(lows))
        p=nxt
    return p


def calibration(rows,preds):
    brier=[];logloss=[];up_p=[];up_y=[];dn_p=[];dn_y=[];persist_p=[];persist_y=[]
    subgroup=defaultdict(list)
    for r,p,bounds in preds:
        cur=state_for(r.points,bounds[r.position]);obs=state_for(r.next_points,bounds[r.position]);ci=sidx(cur);oi=sidx(obs)
        brier.append(sum((p[s]-(1.0 if s==obs else 0.0))**2 for s in STATE_NAMES)/len(STATE_NAMES));logloss.append(-math.log(max(EPS,p[obs])))
        up=sum(v for s,v in p.items() if sidx(s)>ci);dn=sum(v for s,v in p.items() if sidx(s)<ci);stay=p[cur]
        up_p.append(up);up_y.append(1.0 if oi>ci else 0.0);dn_p.append(dn);dn_y.append(1.0 if oi<ci else 0.0);persist_p.append(stay);persist_y.append(1.0 if oi==ci else 0.0)
        subgroup[(r.position,age_band(r.position,r.age),exp_band(r.experience))].append((up,up_y[-1],dn,dn_y[-1],stay,persist_y[-1]))
    def ece(ps,ys,bins=10):
        total=len(ps);v=0.0
        for b in range(bins):
            lo=b/bins;hi=(b+1)/bins;idx=[i for i,x in enumerate(ps) if (x>=lo and (x<hi or (b==bins-1 and x<=hi)))]
            if idx:v+=len(idx)/total*abs(mean(ps[i] for i in idx)-mean(ys[i] for i in idx))
        return v
    groups={}
    for k,xs in subgroup.items():
        groups['|'.join(k)]={'n':len(xs),'up_pred':mean(x[0] for x in xs),'up_obs':mean(x[1] for x in xs),'down_pred':mean(x[2] for x in xs),'down_obs':mean(x[3] for x in xs),'persist_pred':mean(x[4] for x in xs),'persist_obs':mean(x[5] for x in xs)}
    return {'n':len(preds),'brier':mean(brier),'log_loss':mean(logloss),'ece_up':ece(up_p,up_y),'ece_down':ece(dn_p,dn_y),'up_pred':mean(up_p),'up_obs':mean(up_y),'down_pred':mean(dn_p),'down_obs':mean(dn_y),'persist_pred':mean(persist_p),'persist_obs':mean(persist_y),'subgroups':groups}


def state_samples(rows,cutoff,bounds):
    d=defaultdict(list)
    for r in rows:
        if r.season<cutoff:d[(r.position,state_for(r.points,bounds[r.position]))].append(max(0.0,r.points))
    return d


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--career-panel',type=Path,required=True);ap.add_argument('--model-a-rows',type=Path,required=True);ap.add_argument('--qb-results',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True);root=Path(__file__).parent
    base=load_module(root/'run_intrinsic_explicit_state_challenge.py','forecast_state_base');d2=load_module(root/'run_intrinsic_explicit_state_challenge_d2.py','forecast_state_d2');marg=load_module(root/'run_intrinsic_marginal_franchise_challenge.py','forecast_state_marg');legacy=load_module(root/'run_fundamental_intrinsic_residual_calibration.py','forecast_state_legacy');parity=load_module(root/'run_fundamental_intrinsic_production_parity.py','forecast_state_parity')
    rows=load_rows(a.career_panel);examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);qb_probs=parity.load_qb_probabilities(a.qb_results)
    _,forecast_baselines,_=marg.contexts_from_forecasts(parity,a.model_a_rows);_,actual_baselines=marg.contexts_from_actual(legacy.load_rows(a.career_panel))
    old=json.loads((Path('artifacts/management/latest_intrinsic_result.json')).read_text())
    candidates=[]
    for taxonomy in ('kmeans','quantile_balanced','quantile_starter_tail'):
      fold_records=[];all_cal=[]
      for season in FOLDS:
        bounds=taxonomy_boundaries(rows,season,taxonomy);tm=TransitionModel(rows,season,bounds)
        test=[r for r in rows if r.season==season]
        preds=[]
        for r in test:
            qbp=qb_probs.get((r.season,r.player_id));p=propagate(tm,r,bounds,1,qbp);preds.append((r,p,bounds))
        all_cal.extend(preds)
        fold_records.append({'season':season,**calibration(test,preds)})
      cal=calibration([x[0] for x in all_cal],all_cal)
      score=cal['brier']+cal['ece_up']+cal['ece_down']+abs(cal['up_pred']-cal['up_obs'])+abs(cal['down_pred']-cal['down_obs'])
      candidates.append({'taxonomy':taxonomy,'score':score,'calibration':cal,'folds':fold_records})
    selected=min(candidates,key=lambda x:x['score']);taxonomy=selected['taxonomy']

    # Chronological D2 with selected repaired state model; D2 contribution itself is unchanged.
    bykey={(r.player_id,r.season):r for r in rows};eval_rows=[];fold_metrics={}
    for season in FOLDS:
        bounds=taxonomy_boundaries(rows,season,taxonomy);tm=TransitionModel(rows,season,bounds);samples=state_samples(rows,season,bounds);baseline=forecast_baselines[season]
        def c2_x(x,pos):return (12.0*marg.marginal_at_x(max(0.0,x),baseline[pos])+0.5*max(0.0,x))/13.0
        state_value={(p,s):(0.0 if s=='out' else mean(c2_x(v,p) for v in samples.get((p,s),()))) for p in POSITIONS for s in STATE_NAMES}
        # Fit continuation only from seasons strictly before holdout, using repaired states and same D2 target.
        train=[e for e in examples if e.season<season and e.season in forecast_baselines];parents={};cells={}
        target_by_id={id(e):sum((DISCOUNT**off)*((12.0*marg.marginal_at_x(max(0.0,(nr:=bykey.get((e.player_id,e.season+off))).points),actual_baselines[e.season+off][e.position])+0.5*max(0.0,nr.points))/13.0) for off in range(6) if (nr:=bykey.get((e.player_id,e.season+off))) is not None and e.season+off in actual_baselines) for e in train}
        def repaired_value(e,include_cont=False,cf=0.0):
            rr=bykey.get((e.player_id,e.season));cur=state_for(e.means[0],bounds[e.position]);v=c2_x(e.means[0],e.position);p2=propagate(tm,Row(e.player_id,e.season,e.position,e.means[0],0,e.age,e.experience,None,None),bounds,1,qb_probs.get((e.season,e.player_id)));p3=propagate(tm,Row(e.player_id,e.season,e.position,e.means[0],0,e.age,e.experience,None,None),bounds,2,qb_probs.get((e.season,e.player_id)))
            v+=DISCOUNT*sum(p2[s]*state_value[(e.position,s)] for s in STATE_NAMES)+(DISCOUNT**2)*sum(p3[s]*state_value[(e.position,s)] for s in STATE_NAMES)
            term=(DISCOUNT**3)*sum(p3[s]*state_value[(e.position,s)] for s in STATE_NAMES)
            return v+(term*cf if include_cont else 0.0),term
        for pos in POSITIONS:
            es=[e for e in train if e.position==pos];xy=[]
            for e in es:
                v,t=repaired_value(e);xy.append((t,max(0.0,target_by_id[id(e)]-v)))
            den=sum(x*x for x,y in xy);parents[pos]=0.0 if den<EPS else max(0.0,sum(x*y for x,y in xy)/den)
            for band in ('young','prime','aging'):
                sub=[e for e in es if age_band(pos,e.age)==band];xy2=[]
                for e in sub:
                    v,t=repaired_value(e);xy2.append((t,max(0.0,target_by_id[id(e)]-v)))
                den2=sum(x*x for x,y in xy2);raw=parents[pos] if den2<EPS else max(0.0,sum(x*y for x,y in xy2)/den2);w=len(sub)/(len(sub)+100.0) if len(sub)>=30 else 0.0;cells[(pos,band)]=w*raw+(1-w)*parents[pos]
        hold=[e for e in examples if e.season==season]
        errs=[]
        for e in hold:
            cf=cells.get((e.position,age_band(e.position,e.age)),parents[e.position]);pred,_=repaired_value(e,True,cf);target=0.0
            for off in range(6):
                nr=bykey.get((e.player_id,e.season+off));yr=e.season+off
                if nr is None or yr not in actual_baselines:continue
                target+=(DISCOUNT**off)*((12.0*marg.marginal_at_x(max(0.0,nr.points),actual_baselines[yr][e.position])+0.5*max(0.0,nr.points))/13.0)
            errs.append(abs(pred-target));eval_rows.append({'season':season,'position':e.position,'age':e.age,'pred':pred,'target':target})
        fold_metrics[str(season)]=mean(errs)
    def mae(rs):return mean(abs(r['pred']-r['target']) for r in rs)
    groups={
      'young':[r for r in eval_rows if age_band(r['position'],r['age'])=='young'],
      'prime':[r for r in eval_rows if age_band(r['position'],r['age'])=='prime'],
      'aging':[r for r in eval_rows if age_band(r['position'],r['age'])=='aging'],
    }
    ts=[r['target'] for r in eval_rows];q25=quantile(ts,.25);q50=quantile(ts,.50);q90=quantile(ts,.90)
    groups['developmental']=[r for r in eval_rows if age_band(r['position'],r['age'])=='young' and r['target']<q50];groups['fringe']=[r for r in eval_rows if r['target']<=q25];groups['elite']=[r for r in eval_rows if r['target']>=q90]
    repaired={'n':len(eval_rows),'mae':mae(eval_rows),'fold_mae':fold_metrics,'fold_wins_vs_A':sum(1 for s,v in fold_metrics.items() if v<old['key_metrics']['A_fold_mae'][s]),'position_mae':{p:mae([r for r in eval_rows if r['position']==p]) for p in POSITIONS},'group_mae':{g:mae(rs) for g,rs in groups.items() if rs}}
    payload={'model_version':'forecast-career-state-calibration-v1','state_taxonomy_candidates':candidates,'selected_taxonomy':taxonomy,'selected_transition_model':'hierarchical empirical one-step transitions with position/current-state/age/experience/draft-capital shrinkage; QB meaningful-starter mass constrained by governed QB career-state probabilities','before_state_calibration':old['key_metrics']['state_calibration'],'after_state_calibration':selected['calibration'],'old_D2':{'mae':old['key_metrics']['overall_mae']['D2'],'fold_wins_vs_A':old['key_metrics']['D2_fold_wins_vs_A'],'position_mae':old['key_metrics']['position_mae']['D2'],'group_mae':old['key_metrics']['group_mae']['D2']},'repaired_D2':repaired,'A_mae':old['key_metrics']['overall_mae']['A'],'A_fold_mae':old['key_metrics']['A_fold_mae'],'parameter_provenance':{'taxonomy':'empirically fitted chronological position-specific production thresholds; selected only by probability calibration','transition_probabilities':'empirically fitted chronological hierarchical frequencies','dirichlet_alpha':'provisional prior=0.5','shrinkage_strength':'provisional prior=40 effective observations','QB_meaningful_state_mass':'existing governed QB career-state Forecast evidence','D2_contribution':'frozen; unchanged'},'leakage_check':{'market':False,'transactions':False,'owner_behavior':False,'team_roster':False,'team_utility':False}}
    (a.output_dir/'forecast_career_state_calibration.json').write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps({'selected_taxonomy':taxonomy,'before':payload['before_state_calibration'],'after':payload['after_state_calibration'],'old_D2':payload['old_D2']['mae'],'repaired_D2':repaired['mae'],'fold_wins_vs_A':repaired['fold_wins_vs_A']},indent=2))

if __name__=='__main__':main()

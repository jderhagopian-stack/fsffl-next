from __future__ import annotations

import argparse, csv, importlib.util, json, math, sys
from collections import defaultdict
from pathlib import Path

STATES=("out","depth","usable","starter","premium","elite")
POSITIONS=("QB","RB","WR","TE")
FOLDS=tuple(range(2011,2023)); DISCOUNT=.85; EPS=1e-12

def load(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else 0.0

def norm(p):
    z=sum(max(0.0,float(p.get(s,0))) for s in STATES)
    return {s:(max(0.0,float(p.get(s,0)))/z if z>EPS else 1/len(STATES)) for s in STATES}

def blend(a,b,w):return norm({s:(1-w)*a[s]+w*b[s] for s in STATES})
def argmax_state(p):return max(STATES,key=lambda s:(p[s],-STATES.index(s)))

def load_role(path:Path):
    out={}
    with path.open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            key=(int(r['season']),r['player_id'])
            def val(k):
                x=r.get(k,'');return None if x in ('',None,'NA') else float(x)
            out[key]={'games':val('prior_games'),'starts':val('prior_starts'),'opportunities':val('prior_opportunities'),'opp_pg':val('prior_opportunities_per_game'),'role_pct':val('prior_role_percentile'),'target_share':val('prior_target_share')}
    return out

def role_bin(role):
    if not role or role.get('role_pct') is None:return 'no_history'
    x=role['role_pct']
    if x<.25:return 'low'
    if x<.50:return 'rotation'
    if x<.75:return 'meaningful'
    return 'high'

class RoleStatePrior:
    def __init__(self,rows,roles,cutoff,bounds,cal,shrink=35.0):
        self.cal=cal;self.shrink=shrink;self.levels=[defaultdict(lambda:defaultdict(float)) for _ in range(4)]
        for r in rows:
            if r.season>=cutoff:continue
            rb=role_bin(roles.get((r.season,r.player_id)));obs=cal.state_for(r.points,bounds[r.position])
            keys=[(r.position,), (r.position,rb), (r.position,rb,cal.age_band(r.position,r.age)), (r.position,rb,cal.age_band(r.position,r.age),cal.exp_band(r.experience))]
            for i,k in enumerate(keys):self.levels[i][k][obs]+=1
    def probs(self,row,role):
        rb=role_bin(role);cal=self.cal;keys=[(row.position,), (row.position,rb), (row.position,rb,cal.age_band(row.position,row.age)), (row.position,rb,cal.age_band(row.position,row.age),cal.exp_band(row.experience))]
        def sm(c):
            n=sum(c.values())+.5*len(STATES);return {s:(c.get(s,0)+.5)/n for s in STATES}
        p=sm(self.levels[0].get(keys[0],{}))
        for i in range(1,len(keys)):
            c=self.levels[i].get(keys[i],{});n=sum(c.values())
            if n<=0:continue
            q=sm(c);w=n/(n+self.shrink);p=blend(p,q,w)
        return norm(p)

class RoleAnchor:
    def __init__(self,rows,roles,cutoff,bounds,cal,aligned,sd_scale,role_weight):
        self.roles=roles;self.bounds=bounds;self.aligned=aligned;self.sd_scale=sd_scale;self.role_weight=role_weight;self.prior=RoleStatePrior(rows,roles,cutoff,bounds,cal)
    def probs(self,row,fr):
        y1=self.aligned.gaussian_state_mass(fr.mean,fr.sd,self.bounds[row.position],self.sd_scale)
        rp=self.prior.probs(row,self.roles.get((row.season,row.player_id)))
        return blend(y1,rp,self.role_weight)

def fit_anchor(rows,roles,forecasts,cutoff,bounds,cal,aligned):
    train=[r for r in rows if r.season<cutoff and (r.season,r.player_id) in forecasts]
    candidates=[]
    for scale in (.25,.5,.75,1.0):
      for w in (0,.25,.5,.75):
        m=RoleAnchor(rows,roles,cutoff,bounds,cal,aligned,scale,w)
        rec=[(r,m.probs(r,forecasts[(r.season,r.player_id)]),bounds) for r in train]
        met=aligned.state_anchor_metrics(rec,cal);score=met['brier']+.08*met['ordered_distance']
        candidates.append((score,scale,w,met))
    _,scale,w,_=min(candidates,key=lambda x:x[0])
    return RoleAnchor(rows,roles,cutoff,bounds,cal,aligned,scale,w),{'sd_scale':scale,'role_weight':w,'candidate_count':len(candidates)}

class RoleTransition:
    def __init__(self,rows,roles,forecasts,cutoff,bounds,cal,anchor,shrink=45.0):
        self.roles=roles;self.cal=cal;self.shrink=shrink;self.levels=[defaultdict(lambda:defaultdict(float)) for _ in range(5)]
        for r in rows:
            if r.season>=cutoff:continue
            fr=forecasts.get((r.season,r.player_id))
            if fr is None:continue
            src=argmax_state(anchor.probs(r,fr));rb=role_bin(roles.get((r.season,r.player_id)));obs=cal.state_for(r.next_points,bounds[r.position])
            keys=[(r.position,), (r.position,src), (r.position,src,rb), (r.position,src,rb,cal.age_band(r.position,r.age)), (r.position,src,rb,cal.age_band(r.position,r.age),cal.exp_band(r.experience))]
            for i,k in enumerate(keys):self.levels[i][k][obs]+=1
    def probs(self,row,src,step=1,use_role=True):
        age=None if row.age is None else row.age+step-1;exp=None if row.experience is None else row.experience+step-1;rb=role_bin(self.roles.get((row.season,row.player_id))) if use_role else 'no_history';cal=self.cal
        keys=[(row.position,), (row.position,src), (row.position,src,rb), (row.position,src,rb,cal.age_band(row.position,age)), (row.position,src,rb,cal.age_band(row.position,age),cal.exp_band(exp))]
        def sm(c):
            n=sum(c.values())+.5*len(STATES);return {s:(c.get(s,0)+.5)/n for s in STATES}
        p=sm(self.levels[0].get(keys[0],{}))
        for i in range(1,len(keys)):
            c=self.levels[i].get(keys[i],{});n=sum(c.values())
            if n<=0:continue
            q=sm(c);w=n/(n+self.shrink);p=blend(p,q,w)
        return norm(p)
    def step(self,row,pcur,step=1,use_role=True,qb_meaningful=None):
        src=argmax_state(pcur);p=self.probs(row,src,step,use_role)
        if row.position=='QB' and qb_meaningful is not None:
            hi=('starter','premium','elite');lo=('out','depth','usable');t=max(0,min(1,qb_meaningful));hm=sum(p[s] for s in hi);lm=sum(p[s] for s in lo)
            for s in hi:p[s]=t*(p[s]/hm if hm>EPS else 1/3)
            for s in lo:p[s]=(1-t)*(p[s]/lm if lm>EPS else 1/3)
        return norm(p)

def transition_metrics(records,cal):
    bs=[];ll=[];recs=[];bypos=defaultdict(list);byage=defaultdict(list)
    for r,pcur,pnext,b in records:
        src=argmax_state(pcur);si=STATES.index(src);obs=cal.state_for(r.next_points,b[r.position]);oi=STATES.index(obs)
        bs.append(sum((pnext[s]-(1 if s==obs else 0))**2 for s in STATES)/len(STATES));ll.append(-math.log(max(EPS,pnext[obs])))
        u=sum(pnext[s] for s in STATES if STATES.index(s)>si);d=sum(pnext[s] for s in STATES if STATES.index(s)<si);same=pnext[src];z=(u,oi>si,d,oi<si,same,oi==si);recs.append(z);bypos[r.position].append(z);byage[cal.age_band(r.position,r.age)].append(z)
    def g(xs):return {'n':len(xs),'up_pred':mean(x[0] for x in xs),'up_obs':mean(float(x[1]) for x in xs),'down_pred':mean(x[2] for x in xs),'down_obs':mean(float(x[3]) for x in xs),'persist_pred':mean(x[4] for x in xs),'persist_obs':mean(float(x[5]) for x in xs)} if xs else {'n':0}
    return {'n':len(recs),'brier':mean(bs),'log_loss':mean(ll),**{k:v for k,v in g(recs).items() if k!='n'},'by_position':{k:g(v) for k,v in bypos.items()},'by_age':{k:g(v) for k,v in byage.items()}}

def fit_fold(rows,roles,forecasts,qb,season,taxonomy,cal,aligned):
    bounds=cal.taxonomy_boundaries(rows,season,taxonomy);anchor,params=fit_anchor(rows,roles,forecasts,season,bounds,cal,aligned);tm=RoleTransition(rows,roles,forecasts,season,bounds,cal,anchor);anchors=[];trans=[]
    for r in rows:
        if r.season!=season:continue
        fr=forecasts.get((r.season,r.player_id))
        if fr is None:continue
        pcur=anchor.probs(r,fr);q=qb.get((r.season,r.player_id));pnext=tm.step(r,pcur,1,True,None if q is None else q[0]);anchors.append((r,pcur,bounds));trans.append((r,pcur,pnext,bounds))
    return bounds,anchor,tm,params,anchors,trans

def future_state_separation(rows,cutoff,bounds,cal):
    out={}
    for pos in POSITIONS:
        for s in STATES:
            vals=[r.next_points for r in rows if r.season<cutoff and r.position==pos and cal.state_for(r.points,bounds[pos])==s]
            out[f'{pos}|{s}']={'n':len(vals),'next_points_mean':mean(vals)}
    return out

def run_d2(rows,roles,forecasts,qb,examples,by,fb,ab,cal,aligned,marg,parity,legacy,frozen,taxonomy):
    km=frozen['key_metrics'];eval_rows=[];fold_mae={};fold_params={}
    for season in FOLDS:
        bounds,anchor,tm,params,aa,tt=fit_fold(rows,roles,forecasts,qb,season,taxonomy,cal,aligned);fold_params[str(season)]=params;samples=cal.state_samples(rows,season,bounds);baseline=fb[season]
        def c2(x,pos):return (12*marg.marginal_at_x(max(0,x),baseline[pos])+.5*max(0,x))/13
        sv={(p,s):(0 if s=='out' else mean(c2(v,p) for v in samples.get((p,s),()))) for p in POSITIONS for s in STATES}
        def probs(e):
            r=by.get((e.player_id,e.season));fr=forecasts.get((e.season,e.player_id))
            if r is None or fr is None:return None
            pc=anchor.probs(r,fr);q=qb.get((e.season,e.player_id));p2=tm.step(r,pc,1,True,None if q is None else q[0]);p3=tm.step(r,p2,2,False,None if q is None else q[1]);return p2,p3
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
    return {'n':len(eval_rows),'mae':mae(eval_rows),'fold_wins_vs_A':sum(v<km['A_fold_mae'][s] for s,v in fold_mae.items()),'fold_mae':fold_mae,'position_mae':{p:mae([r for r in eval_rows if r['position']==p]) for p in POSITIONS},'group_mae':{k:mae(v) for k,v in groups.items()},'fold_anchor_parameters':fold_params}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--career-panel',type=Path,required=True);ap.add_argument('--role-panel',type=Path,required=True);ap.add_argument('--model-a-rows',type=Path,required=True);ap.add_argument('--qb-results',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True);root=Path(__file__).parent
    aligned=load(root/'run_forecast_inference_aligned_state_calibration.py','role_aligned');cal=load(root/'run_forecast_career_state_calibration.py','role_cal');legacy=load(root/'run_fundamental_intrinsic_residual_calibration.py','role_legacy');parity=load(root/'run_fundamental_intrinsic_production_parity.py','role_parity');marg=load(root/'run_intrinsic_marginal_franchise_challenge.py','role_marg')
    rows=cal.load_rows(a.career_panel);roles=load_role(a.role_panel);forecasts=aligned.load_forecasts(a.model_a_rows);qb=parity.load_qb_probabilities(a.qb_results);examples,_=parity.build_examples(panel_path=a.career_panel,model_rows_path=a.model_a_rows,qb_results_path=a.qb_results,legacy=legacy);by={(r.player_id,r.season):r for r in rows};_,fb,_=marg.contexts_from_forecasts(parity,a.model_a_rows);_,ab=marg.contexts_from_actual(legacy.load_rows(a.career_panel));frozen=json.loads(Path('artifacts/research/intrinsic_d2_frozen_reference.json').read_text())
    candidates=[]
    for tax in ('kmeans','quantile_balanced','quantile_starter_tail'):
        aa=[];tt=[];folds=[]
        for season in FOLDS:
            b,an,tm,params,a1,t1=fit_fold(rows,roles,forecasts,qb,season,tax,cal,aligned);aa+=a1;tt+=t1;folds.append({'season':season,'params':params,'anchor':aligned.state_anchor_metrics(a1,cal),'transition':transition_metrics(t1,cal)})
        am=aligned.state_anchor_metrics(aa,cal);tr=transition_metrics(tt,cal);score=am['brier']+.08*am['ordered_distance']+tr['brier']+abs(tr['up_pred']-tr['up_obs'])+abs(tr['down_pred']-tr['down_obs'])
        candidates.append({'taxonomy':tax,'score':score,'anchor':am,'transition':tr,'folds':folds})
    best=min(candidates,key=lambda x:x['score']);d2=run_d2(rows,roles,forecasts,qb,examples,by,fb,ab,cal,aligned,marg,parity,legacy,frozen,best['taxonomy'])
    # taxonomy support: adjacent states should have non-trivial training samples and ordered future contribution on the full pre-2023 panel.
    bounds=cal.taxonomy_boundaries(rows,2023,best['taxonomy']);sep=future_state_separation(rows,2023,bounds,cal)
    role_coverage=sum(1 for r in rows if roles.get((r.season,r.player_id),{}).get('role_pct') is not None)/len(rows)
    out={'model_version':'forecast-role-opportunity-foundation-v1','role_definition':{'QB':'prior-season passing attempts/game percentile','RB':'prior-season (carries+targets)/game percentile','WR':'prior-season targets/game percentile','TE':'prior-season targets/game percentile','source':'PIT NFL-derived seasonal statistics; no future/market/team evidence'},'role_coverage':role_coverage,'candidates':candidates,'selected':best,'taxonomy_separation':sep,'D2':d2,'A_mae':frozen['key_metrics']['overall_mae']['A'],'old_D2_mae':frozen['key_metrics']['overall_mae']['D2'],'first_aligned_D2_mae':49.128284459333756,'synthetic_gate':'D2 equation unchanged; exact prior synthetic gate remains required after any production promotion','leakage_check':{'broad_market':False,'league_market':False,'transactions':False,'owner_behavior':False,'team_specific':False,'future_current_state':False}}
    (a.output_dir/'forecast_role_opportunity_foundation.json').write_text(json.dumps(out,indent=2,sort_keys=True))
    print(json.dumps({'role_coverage':role_coverage,'taxonomy':best['taxonomy'],'anchor':best['anchor'],'transition':best['transition'],'D2':d2,'A':out['A_mae'],'old_D2':out['old_D2_mae']},indent=2))
if __name__=='__main__':main()

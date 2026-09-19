from __future__ import annotations
import argparse, hashlib, json, math, platform
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
import redevelopment_v1 as rv

SCHEMA='fsffl-redeveloped-forecast-fit-v1'


def _route(sel,h,p,cs):
    return sel[str(int(h))]['selected_route'][f'{p}|{cs}']


def fit_once(rows: pd.DataFrame, sel: dict):
    package={
        'schema_version':SCHEMA,
        'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},
        'implementation_sha256':rv.sha256_file(Path(rv.__file__)),
        'selection':sel,
        'replay_tolerance':{'probabilities':rv.REPLAY_PROB_TOL,'points':rv.REPLAY_POINT_TOL},
        'horizons':{}
    }
    audit=[]
    fit_counts={'state_layer_fits':0,'production_model_fits':0}
    for h,maxs in ((2,2023),(3,2022)):
        if h==2:
            state_train=rows[(rows.source_season<=maxs)&(rows.horizon.isin([1,2]))&(rows.source_season+rows.horizon<=2025)].copy()
            prod_train=rows[(rows.source_season<=maxs)&(rows.horizon==2)&(rows.source_season+2<=2025)].copy()
        else:
            state_train=rows[(rows.source_season<=maxs)&(rows.horizon==3)&(rows.source_season+3<=2025)].copy()
            prod_train=state_train.copy()
        layers=rv.fit_state_layers(state_train,h); fit_counts['state_layer_fits']+=2
        required=sorted(set(_route(sel,h,p,cs) for p in rv.POSITIONS for cs in ('developmental','established','veteran')))
        models={}
        for cand in required:
            models[cand]=rv.ProductionModel(cand,h).fit(prod_train); fit_counts['production_model_fits']+=1
        package['horizons'][str(h)]={
            'max_source_season':maxs,'max_target_season':2025,
            'state_train_n':int(len(state_train)),'prod_train_n':int(len(prod_train)),
            'required_treatments':required,
            'state_qb':layers['qb'].package(),'state_nonqb':layers['nonqb'].package(),
            'production_models':{k:v.package() for k,v in models.items()}
        }
        score_rows=rows[(rows.horizon==h)&(rows.source_season<=maxs)&(rows.source_season+h<=2025)].copy()
        for r in score_rows.itertuples():
            probs=rv.state_probs(layers,r); chosen=_route(sel,h,r.position,r.career_stage)
            rec={'source_season':int(r.source_season),'player_id':str(r.player_id),'position':str(r.position),'horizon':h,
                 'career_stage':str(r.career_stage),'target_points':float(r.target_points),'route':chosen}
            for s in rv.STATES: rec[f'p_{s}']=float(probs[s])
            for cand,m in models.items():
                if cand=='D0': pts=(1-probs['out'])*m.predict_active(r)
                else: pts=sum(probs[s]*m.predict_state(r,s) for s in rv.POSITIVE_STATES)
                rec[f'pred_{cand}']=float(pts)
            rec['pred_route']=rec[f'pred_{chosen}']
            audit.append(rec)
    package['fit_counts']=fit_counts
    return package,pd.DataFrame(audit)


def vec(feat,names): return np.asarray([float(feat.get(n,0.0)) for n in names],dtype=float)
def sigmoid(z):
    if z>=0: return 1/(1+math.exp(-z))
    ez=math.exp(z); return ez/(1+ez)

def score_bin(pkg,feat): return sigmoid(float(pkg['intercept'][0])+float(np.dot(np.asarray(pkg['coef'],float),vec(feat,pkg['features']))))
def score_prob(layer_pkg,r):
    add_c=bool(layer_pkg['add_c'])
    p=score_bin(layer_pkg['persistence'],rv.prob_features(r,age_mode='a2',add_c=add_c,add_d=False))
    feat=rv.prob_features(r,age_mode='coarse',add_c=add_c,add_d=True)
    cum=[]; last=1.0
    for name,_ in rv.THRESHOLDS:
        q=score_bin(layer_pkg['ordered'][name],feat); q=min(last,max(0.0,min(1.0,q))); cum.append(q); last=q
    useful,starter,premium,elite=cum
    cond={'depth':1-useful,'usable':useful-starter,'starter':starter-premium,'premium':premium-elite,'elite':elite}
    out={'out':1-p}; out.update({s:p*cond[s] for s in rv.POSITIVE_STATES}); z=sum(out.values())
    return {s:out[s]/z for s in rv.STATES}

def zval(pkg,k,x): return (float(x)-float(pkg['scalers'][k]['mean']))/float(pkg['scalers'][k]['sd'])

def prod_feat(pkg,r,state=None):
    vals={
        'source_log':zval(pkg,'source_log',math.log1p(max(0.0,float(r.source_points)))),
        'source_pct':zval(pkg,'source_pct',float(r.source_percentile)),
        'age':zval(pkg,'age',float(r.age)),
        'experience':zval(pkg,'experience',min(float(r.experience),15.0)),
        'prior1_log':zval(pkg,'prior1_log',math.log1p(max(0.0,float(r.prior1_points)))) if int(r.prior1_coverage) else 0.0,
    }
    d={f'p={r.position}':1,f'src={r.source_state}':1,'prior1_cov':int(r.prior1_coverage)}
    for k,v in vals.items(): d[k]=v; d[f'{k}@p={r.position}']=v
    if pkg['candidate']=='D1':
        state = state or str(r.target_state); d[f'future={state}']=1; d[f'pstate={r.position}|{state}']=1
        d[f'source_log@future={state}']=vals['source_log']; d[f'source_pct@future={state}']=vals['source_pct']
        if int(r.prior2_coverage):
            m=zval(pkg,'prior2_mean',float(r.prior2_mean_age_state_z)); g=zval(pkg,'prior2_gap',float(r.prior2_gap_age_state_z))
        else: m=g=0.0
        d['prior2_cov']=int(r.prior2_coverage); d['prior2_mean_z']=m; d['prior2_gap_z']=g
        d[f'prior2_mean_z@p={r.position}']=m; d[f'prior2_gap_z@p={r.position}']=g
    return d

def score_prod(pkg,r,state=None):
    return max(0.0,float(pkg['intercept'])+float(np.dot(np.asarray(pkg['coef'],float),vec(prod_feat(pkg,r,state),pkg['features']))))

def replay(rows,package,audit):
    expected={(int(r.source_season),str(r.player_id),str(r.position),int(r.horizon)):r for r in audit.itertuples()}
    max_prob=max_point=0.0; n=0; route_mismatch=0
    for htxt,hp in package['horizons'].items():
        h=int(htxt); maxs=int(hp['max_source_season']); subset=rows[(rows.horizon==h)&(rows.source_season<=maxs)&(rows.source_season+h<=2025)]
        for r in subset.itertuples():
            key=(int(r.source_season),str(r.player_id),str(r.position),h); old=expected[key]
            lp=hp['state_qb'] if r.position=='QB' else hp['state_nonqb']; probs=score_prob(lp,r)
            for s in rv.STATES: max_prob=max(max_prob,abs(probs[s]-float(getattr(old,f'p_{s}'))))
            chosen=_route(package['selection'],h,r.position,r.career_stage)
            route_mismatch += int(chosen!=old.route)
            pm=hp['production_models'][chosen]
            if chosen=='D0': pred=(1-probs['out'])*score_prod(pm,r)
            else: pred=sum(probs[s]*score_prod(pm,r,s) for s in rv.POSITIVE_STATES)
            max_point=max(max_point,abs(pred-float(old.pred_route))); n+=1
    return {'schema_version':'fsffl-redeveloped-forecast-replay-v1','rows':n,'max_probability_diff':max_prob,'max_point_diff':max_point,
            'route_mismatches':route_mismatch,'probability_tolerance':rv.REPLAY_PROB_TOL,'point_tolerance':rv.REPLAY_POINT_TOL,
            'pass':max_prob<=rv.REPLAY_PROB_TOL and max_point<=rv.REPLAY_POINT_TOL and route_mismatch==0}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('mode',choices=['fit','replay']); ap.add_argument('--panel',required=True); ap.add_argument('--q3',required=True); ap.add_argument('--selection',required=True); ap.add_argument('--outdir',required=True); ap.add_argument('--package'); ap.add_argument('--audit')
    args=ap.parse_args(); out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)
    rows=rv.build_rows(pd.read_csv(args.panel),2023); parity=rv.parity_check(rows,pd.read_csv(args.q3))
    if not parity['pass']: raise SystemExit('source reconstruction parity failure')
    if args.mode=='fit':
        sel=json.loads(Path(args.selection).read_text()); package,audit=fit_once(rows,sel)
        raw=json.dumps(package,indent=2,sort_keys=True,allow_nan=False)+'\n'; (out/'FINAL_FITTED_PACKAGE.json').write_text(raw); audit.to_csv(out/'FINAL_FIT_REPLAY_COORDINATE.csv',index=False)
        (out/'FINAL_FIT_MANIFEST.json').write_text(json.dumps({'package_sha256':hashlib.sha256(raw.encode()).hexdigest(),'audit_sha256':rv.sha256_file(out/'FINAL_FIT_REPLAY_COORDINATE.csv'),'audit_rows':len(audit),'fit_counts':package['fit_counts']},indent=2)+'\n')
    else:
        package=json.loads(Path(args.package).read_text()); audit=pd.read_csv(args.audit); result=replay(rows,package,audit); (out/'FINAL_REPLAY_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()

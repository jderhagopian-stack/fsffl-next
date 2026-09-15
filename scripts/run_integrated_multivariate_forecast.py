from __future__ import annotations
import argparse, importlib.util, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

POS=("QB","RB","WR","TE"); STATES=("out","depth","usable","starter","premium","elite"); PST=STATES[1:]
USE=set(STATES[2:]); START=set(STATES[3:]); PREM=set(STATES[4:]); CS=(.25,1.,4.); SEED=20260915
DEV=(2014,2015,2016,2017,2018); VAL=(2019,2020); TEST=(2021,2022); MINN=100; MINC=15

def load(p,n):
 s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); sys.modules[n]=m; s.loader.exec_module(m); return m

def avg(xs):
 xs=[float(x) for x in xs if x is not None and not pd.isna(x)]; return sum(xs)/len(xs) if xs else 0.
def eb(x):
 if x is None or pd.isna(x): return "unknown"
 x=int(x); return "0_1" if x<=1 else "2_3" if x<=3 else "4_6" if x<=6 else "7_plus"
def era(y): return "early_2014_2016" if y<=2016 else "middle_2017_2019" if y<=2019 else "recent_2020_2022"
def brier(p,y): return (float(p)-float(y))**2
def ll(p,y): p=min(1-1e-12,max(1e-12,float(p))); return -math.log(p if y else 1-p)
def sb(probs,y,states=STATES): return sum((probs.get(s,0)-(1 if s==y else 0))**2 for s in states)/len(states)
def sl(probs,y): return -math.log(max(1e-12,probs.get(y,0)))
def tprob(p,S): return sum(p.get(s,0) for s in S)
def auc(y,p):
 try: return float(roc_auc_score(y,p)) if len(set(y))>1 and len(y)>=20 else None
 except: return None

def feat(pos,age,state,h,pts,prev,exp,u,e,drop=frozenset()):
 d={f"p={pos}":1,f"a={age}":1,f"s={state}":1,f"h={h}":1,f"e={eb(exp)}":1,"exp":min(15,max(0,float(exp or 0)))/10}
 if "production" not in drop:
  p=max(0,float(pts or 0)); q=max(0,float(prev or 0)); d|={"lp":math.log1p(p)/6,"lprev":math.log1p(q)/6,"dpts":max(-2,min(2,(p-q)/100)),"prev_cov":1 if prev is not None else 0}
 if "role" not in drop:
  if u: d|={f"role={u.get('role_band') or 'unknown'}":1,"u_cov":1,"lopg":math.log1p(max(0,float(u.get('opportunity_per_game',0))))/4,"lg":math.log1p(max(0,float(u.get('games',0))))/3}
  else: d|={"role=unknown":1,"u_cov":0,"lopg":0,"lg":0}
 if not e: d|={"r_cov":0,"i_cov":0,"part_cov":0}; return d
 d|={"r_cov":1 if float(e.get('roster_weeks',0) or 0)>0 else 0,"i_cov":1 if float(e.get('injury_report_weeks',0) or 0)>0 else 0,"part_cov":1 if float(e.get('participation_weeks',0) or 0)>0 else 0}
 if "continuity" not in drop:
  for f in ("active_share","released_share","practice_share","reserve_share","last_status_active","last_status_attached","last_status_release","last_status_practice","last_status_reserve"): d[f]=float(e.get(f,0) or 0)
  for f in ("status_change_count","team_change_count","active_return_count","release_entry_count","practice_entry_count","reserve_entry_count"): d["l"+f]=math.log1p(max(0,float(e.get(f,0) or 0)))/3
  d["young_active"]=(age=="young")*float(e.get("active_share",0) or 0); d["low_release"]=(state in {"depth","usable"})*float(e.get("released_share",0) or 0)
 if "availability" not in drop:
  for f in ("injury_limited_weeks","non_ir_injury_limited_weeks","inactive_injury_limited_weeks","reserve_injury_limited_weeks"): d["l"+f]=math.log1p(max(0,float(e.get(f,0) or 0)))/3
  d["nonir"]=float(e.get("non_ir_injury_flag",0) or 0); d["inactiveinj"]=float(e.get("inactive_injury_flag",0) or 0); d["inj_attached"]=d["nonir"]*float(e.get("last_status_attached",0) or 0)
 if "participation" not in drop:
  for f in ("participation_weeks","stats_weeks","snap_play_weeks"): d["l"+f]=math.log1p(max(0,float(e.get(f,0) or 0)))/3
 return d

class Bin:
 def __init__(self,C): self.v=DictVectorizer(sort=True); self.m=LogisticRegression(C=C,solver="lbfgs",max_iter=2000,random_state=SEED); self.ok=False
 def fit(self,X,y):
  c=Counter(y)
  if len(y)>=MINN and min(c.get(0,0),c.get(1,0))>=MINC: self.m.fit(self.v.fit_transform(X),y); self.ok=True
 def p(self,x): return float(self.m.predict_proba(self.v.transform([x]))[0,1]) if self.ok else None
class Multi:
 def __init__(self,C): self.v=DictVectorizer(sort=True); self.m=LogisticRegression(C=C,solver="lbfgs",max_iter=2000,random_state=SEED); self.ok=False
 def fit(self,X,y):
  if len(y)>=MINN and len(set(y))>=3: self.m.fit(self.v.fit_transform(X),y); self.ok=True
 def p(self,x):
  if not self.ok:return None
  z={s:0. for s in STATES}
  for k,v in zip(self.m.classes_,self.m.predict_proba(self.v.transform([x]))[0]):z[str(k)]=float(v)
  t=sum(z.values()); return {k:v/t for k,v in z.items()}
class Ordered:
 def __init__(self,C): self.ms=[Bin(C) for _ in range(4)]
 def fit(self,X,y):
  cuts=[USE,START,PREM,{"elite"}]
  for m,S in zip(self.ms,cuts):m.fit(X,[1 if s in S else 0 for s in y])
 def p(self,x):
  q=[]; last=1.
  for m in self.ms:
   v=m.p(x)
   if v is None:return None
   v=min(last,max(0,min(1,v)));q.append(v);last=v
  a,b,c,d=q;return {"depth":1-a,"usable":a-b,"starter":b-c,"premium":c-d,"elite":d}
class Prior:
 def __init__(self,R,posonly=False):
  self.posonly=posonly;self.c=defaultdict(Counter)
  for r in R:
   if posonly and not r["persist"]:continue
   for k in self.keys(r):self.c[k][r["state"]]+=1
 def keys(self,r):return [(r["position"],r["age"],r["current"],r["h"]),(r["position"],r["current"],r["h"]),(r["position"],r["h"])]
 def p(self,pos,age,cur,h):
  allow=PST if self.posonly else STATES
  for k in [(pos,age,cur,h),(pos,cur,h),(pos,h)]:
   c=self.c[k];n=sum(c.values())
   if n>=30:
    z=n+.5*len(allow);return {s:(c.get(s,0)+.5)/z for s in allow}
  return None
class Means:
 def __init__(self,R):
  self.d=[defaultdict(list) for _ in range(4)]
  for r in R:
   for D,k in zip(self.d,[(r["position"],r["h"],r["state"]),(r["position"],r["state"]),(r["h"],r["state"]),(r["state"],)]):D[k].append(r["points"])
 def g(self,pos,h,s):
  for D,k,mn in zip(self.d,[(pos,h,s),(pos,s),(h,s),(s,)],(10,10,10,5)):
   if len(D[k])>=mn:return avg(D[k])
  return 0.
 def exp(self,p,pos,h):return sum(p.get(s,0)*self.g(pos,h,s) for s in STATES)

def records(pf,base,panel,by,cut,bounds,usage,ev):
 R=[]
 for x in panel:
  if x.position not in POS or x.season<2012 or x.season>=cut:continue
  cur=base.state_for_points(x.points,bounds[x.position]);age=base.age_band(x.position,x.age);pr=by.get((x.player_id,x.season-1));prev=None if pr is None else float(pr.points)
  for h in (1,2):
   if x.season+h>=cut:continue
   t=pf.target_truth(base,by,ev["roster_year"],ev["injury_map"],x.player_id,x.season,x.position,h,bounds)
   if not t["resolved"]:continue
   a=by.get((x.player_id,x.season+h));pts=max(0,float(a.points)) if a else 0.;e=ev["source"].get((x.player_id,x.season))
   R.append({"position":x.position,"age":age,"current":cur,"h":h,"points":pts,"srcpts":float(x.points),"prev":prev,"exp":x.experience,"u":usage.get((x.player_id,x.season)),"e":e,"cov":bool(e and float(e.get("roster_weeks",0) or 0)>0),"persist":int(t["persist"]),"state":t["state"]})
 return R

def fitmodel(R,C,arch,drop=frozenset()):
 def F(r,rich):return feat(r["position"],r["age"],r["current"],r["h"],r["srcpts"],r["prev"],r["exp"],r["u"],r["e"] if rich else None,drop)
 full=[r for r in R if r["cov"]];B={"arch":arch,"means":Means(R),"pa":Prior(R,False),"pp":Prior(R,True),"drop":drop}
 if arch=="I1":
  for nm,G,rich in (("full",full,True),("red",R,False)):
   pm=Bin(C);pm.fit([F(r,rich) for r in G],[r["persist"] for r in G]); P=[r for r in G if r["persist"]]; sm=Ordered(C);sm.fit([F(r,rich) for r in P],[r["state"] for r in P]);B[nm]=(pm,sm)
 else:
  for nm,G,rich in (("full",full,True),("red",R,False)):
   m=Multi(C);m.fit([F(r,rich) for r in G],[r["state"] for r in G]);B[nm]=m
 return B

def pred(B,r,b0):
 rich=bool(r["e"] and float(r["e"].get("roster_weeks",0) or 0)>0);nm="full" if rich else "red";x=feat(r["position"],r["age"],r["current"],r["h"],r["srcpts"],r["prev"],r["exp"],r["u"],r["e"] if rich else None,B["drop"])
 if B["arch"]=="I1":
  pm,sm=B[nm];q=pm.p(x);c=sm.p(x)
  if q is None or c is None:return b0,"b0_fallback"
  z={"out":1-q};z|={s:q*c[s] for s in PST}
 else:
  z=B[nm].p(x)
  if z is None:z=B["pa"].p(r["position"],r["age"],r["current"],r["h"])
  if z is None:return b0,"b0_fallback"
 t=sum(z.values());return {k:v/t for k,v in z.items()},nm

def evalfold(pf,prior,base,panel,by,examples,usage,qb,ev,season,C1,C2,arches=("I1","I2"),drop=frozenset()):
 test=[e for e in examples if e.season==season and (e.player_id,season) in by];bounds=base.fit_state_boundaries(panel,season);c0=base.fit_transition_counts(panel,season,bounds);pt=pf.build_training_rows(base,panel,by,season,bounds,usage,ev["source"],ev["roster_year"],ev["injury_map"]);st=pf.fit_stage1(pt);R=records(pf,base,panel,by,season,bounds,usage,ev);B={}
 if "I1" in arches:B["I1"]=fitmodel(R,C1,"I1",drop)
 if "I2" in arches:B["I2"]=fitmodel(R,C2,"I2",drop)
 lowthr=prior.low_thresholds(panel,season);ps=defaultdict(list)
 for x in panel:ps[x.player_id].append(x.season)
 for k in ps:ps[k].sort()
 rows=[]
 for e in test:
  x=by[(e.player_id,season)];cur=base.state_for_points(x.points,bounds[e.position]);age=base.age_band(e.position,e.age);u=usage.get((e.player_id,season));se=ev["source"].get((e.player_id,season));pr=by.get((e.player_id,season-1));prev=None if pr is None else float(pr.points);low=x.points>0 and x.points<=lowthr[e.position]
  for h in (1,2):
   _,p0=prior.probs(base,c0,e,bounds,qb,h);cond=pf.normalize_positive(p0);q,path=pf.predict_persistence(st,"m2",e.position,age,cur,h,x.points,e.experience,u,se,1-p0["out"]);p1=pf.combine_persistence(q,cond);inp={"position":e.position,"age":age,"current":cur,"h":h,"srcpts":float(x.points),"prev":prev,"exp":e.experience,"u":u,"e":se};P={"b0_":(p0,"base"),"b1_":(p1,path)}
   for a,pref in (("I1","i1_"),("I2","i2_")):
    if a in B:P[pref]=pred(B[a],inp,p0)
   t=pf.target_truth(base,by,ev["roster_year"],ev["injury_map"],e.player_id,season,e.position,h,bounds);act=by.get((e.player_id,season+h));ap=max(0,float(act.points)) if act else (0. if t["resolved"] else None);ls=prior.actual_state(base,by,e.player_id,season+h,e.position,bounds);later=act is None and any(s>season+h for s in ps[e.player_id]);tr=ev["roster_year"].get((e.player_id,season+h),{});sts=set(tr.get("terminal_statuses",set())) if tr else set();ti=ev["injury_map"].get((e.player_id,season+h),{});ni=act is None and float(ti.get("non_ir_injury_flag",0) or 0)>0;rp=act is None and bool(sts & {"DEV","PUP","RSN","RES","E14"});an=act is None and bool(sts & {"ACT","INA"}) and not ni
   r={"season":season,"horizon":h,"position":e.position,"age_band":age,"exp_band":eb(e.experience),"era":era(season),"low_end":bool(low),"legacy_useful":ls in USE,"true_dev":bool(low and age=="young" and ls in USE),"factual_state":t["state"] if t["resolved"] else None,"factual_persist":t["persist"] if t["resolved"] else None,"actual_points":ap,"later_return":later,"non_ir_injury":ni,"reserve_practice":rp,"active_no_prod":an}
   for pref,(p,path) in P.items():
    r[pref+"path"]=path;r[pref+"persist"]=1-p["out"];r[pref+"useful"]=tprob(p,USE);r[pref+"starter"]=tprob(p,START);r[pref+"premium"]=tprob(p,PREM);pp=max(0,float(e.means[h])) if pref in ("b0_","b1_") else B["I1" if pref=="i1_" else "I2"]["means"].exp(p,e.position,h);r[pref+"points"]=pp
    if t["resolved"]:
     r[pref+"pb"]=brier(r[pref+"persist"],t["persist"]);r[pref+"pll"]=ll(r[pref+"persist"],t["persist"]);r[pref+"sb"]=sb(p,t["state"]);r[pref+"sll"]=sl(p,t["state"]);r[pref+"ub"]=brier(r[pref+"useful"],1 if t["state"] in USE else 0);r[pref+"stb"]=brier(r[pref+"starter"],1 if t["state"] in START else 0);r[pref+"prb"]=brier(r[pref+"premium"],1 if t["state"] in PREM else 0);r[pref+"ae"]=abs(pp-ap);r[pref+"bias"]=pp-ap
     if t["persist"]:
      c={s:p[s]/max(1e-12,1-p["out"]) for s in PST};r[pref+"csb"]=sb(c,t["state"],PST)
     else:r[pref+"csb"]=None
    else:
     for k in ("pb","pll","sb","sll","ub","stb","prb","ae","bias","csb"):r[pref+k]=None
   rows.append(r)
 return rows

def summary(R,p):
 X=[r for r in R if r["factual_state"] is not None]
 if not X:return {"n":0}
 yout=[1-r["factual_persist"] for r in X];pout=[1-r[p+"persist"] for r in X];yu=[r["factual_state"] in USE for r in X];ys=[r["factual_state"] in START for r in X];yp=[r["factual_state"] in PREM for r in X]
 return {"n":len(X),"pb":avg(r[p+"pb"] for r in X),"pll":avg(r[p+"pll"] for r in X),"sb":avg(r[p+"sb"] for r in X),"sll":avg(r[p+"sll"] for r in X),"ub":avg(r[p+"ub"] for r in X),"stb":avg(r[p+"stb"] for r in X),"prb":avg(r[p+"prb"] for r in X),"mae":avg(r[p+"ae"] for r in X),"bias":avg(r[p+"bias"] for r in X),"csb":avg(r[p+"csb"] for r in X if r[p+"csb"] is not None),"pred_out":avg(1-r[p+"persist"] for r in X),"real_out":avg(yout),"auc_out":auc(yout,pout),"auc_use":auc(yu,[r[p+"useful"] for r in X]),"auc_start":auc(ys,[r[p+"starter"] for r in X]),"auc_prem":auc(yp,[r[p+"premium"] for r in X])}
def dev(R,p):
 L=[r for r in R if r["low_end"]];T=[r for r in L if r["true_dev"]];N=[r for r in L if not r["legacy_useful"]];rec=avg(r[p+"useful"]>=.5 for r in T);fn=avg(r["legacy_useful"] and r[p+"useful"]<.5 for r in L);fp=avg((not r["legacy_useful"]) and r[p+"useful"]>=.5 for r in L);spec=avg(r[p+"useful"]<.5 for r in N);return {"n":len(L),"true_n":len(T),"recall":rec,"fn":fn,"fp":fp,"bal_acc":(rec+spec)/2}
def safety(R,p,f):
 G=[r for r in R if r[f]];X=[r for r in G if r["factual_state"] is not None];return {"n":len(G),"resolved":len(X),"persist":avg(r[p+"persist"] for r in G),"below_05":avg(r[p+"persist"]<.5 for r in G),"pb":avg(r[p+"pb"] for r in X) if X else None}
def profile(R,p,b="b0_"):
 s=summary(R,p);bs=summary(R,b);D=dev(R,p);SF={f:safety(R,p,f) for f in ("later_return","non_ir_injury","reserve_practice","active_no_prod")};disc=avg(x for x in (s["auc_out"],s["auc_use"],s["auc_start"],s["auc_prem"]) if x is not None);cal=avg((s["pb"]/bs["pb"],s["sb"]/bs["sb"],s["ub"]/bs["ub"],s["sll"]/bs["sll"]));state=avg((s["csb"]/max(bs["csb"],1e-12),s["mae"]/bs["mae"]));safe=avg(x["pb"] for x in SF.values() if x["pb"] is not None);groups=[]
 for pos in POS:
  x=summary([r for r in R if r["position"]==pos],p)
  if x["n"]>=30:groups.append(x["sb"])
 for er in ("early_2014_2016","middle_2017_2019","recent_2020_2022"):
  x=summary([r for r in R if r["era"]==er],p)
  if x["n"]>=30:groups.append(x["sb"])
 return {"calibration":cal,"discrimination":disc,"development":D["bal_acc"],"state_quality":state,"safety":safe,"robustness":avg(groups),"summary":s,"dev":D,"safety_detail":SF}
def ranks(P):
 dims=[("calibration",False),("discrimination",True),("development",True),("state_quality",False),("safety",False),("robustness",False)];R={n:{} for n in P}
 for d,hi in dims:
  for i,n in enumerate(sorted(P,key=lambda n:P[n][d],reverse=hi),1):R[n][d]=i
 for n in R:R[n]["mean"]=avg(R[n].values())
 return R

def chooseC(*args,arch):
 Q={}
 for C in CS:
  R=[]
  for y in VAL:R+=evalfold(*args,y,C,C,arches=(arch,))
  Q[str(C)]=profile(R,"i1_" if arch=="I1" else "i2_")
 K=ranks(Q);c=min(Q,key=lambda x:(K[x]["mean"],float(x)));return float(c),Q,K

def main():
 a=argparse.ArgumentParser();a.add_argument("--career-panel",type=Path,required=True);a.add_argument("--usage-panel",type=Path,required=True);a.add_argument("--model-a-rows",type=Path,required=True);a.add_argument("--qb-results",type=Path,required=True);a.add_argument("--prior-forecast-json",type=Path,required=True);a.add_argument("--prior-event-json",type=Path,required=True);a.add_argument("--prior-persistence-json",type=Path,required=True);a.add_argument("--output-dir",type=Path,required=True);z=a.parse_args();z.output_dir.mkdir(parents=True,exist_ok=True);H=Path(__file__).parent
 pf=load(H/"run_persistence_first_forecast_calibration.py","im_pf");prior=load(H/"run_forecast_low_end_career_calibration.py","im_pr");legacy=load(H/"run_fundamental_intrinsic_residual_calibration.py","im_lg");parity=load(H/"run_fundamental_intrinsic_production_parity.py","im_pa");base=load(H/"run_intrinsic_explicit_state_challenge.py","im_bs");evt=load(H/"reconstruct_event_time_absence_cause_evidence.py","im_ev");F=json.loads(z.prior_forecast_json.read_text());E=json.loads(z.prior_event_json.read_text());P=json.loads(z.prior_persistence_json.read_text())
 checks={"c0":abs(F["summaries"]["low_end"]["c0_"]["state_brier"]-.17558645736306655)<1e-10,"resolution":abs(E["overall_resolution"]["resolved_share"]-685/925)<1e-10,"p145":P["conclusion"]=="P4. TWO-STAGE PERSISTENCE-FIRST DECOMPOSITION DOES NOT IMPROVE THE PROBLEM"}
 if not all(checks.values()):raise RuntimeError("baseline parity failed "+json.dumps(checks))
 ex,_=parity.build_examples(panel_path=z.career_panel,model_rows_path=z.model_a_rows,qb_results_path=z.qb_results,legacy=legacy);panel=legacy.load_rows(z.career_panel);by={(r.player_id,r.season):r for r in panel};usage=pf.load_usage(z.usage_panel);qb=parity.load_qb_probabilities(z.qb_results);ev=pf.source_evidence_map(evt,list(range(2012,2025)));A=(pf,prior,base,panel,by,ex,usage,qb,ev)
 c1,v1,vr1=chooseC(*A,arch="I1");c2,v2,vr2=chooseC(*A,arch="I2");D=[]
 for y in DEV:D+=evalfold(*A,y,1,1)
 V=[]
 for y in VAL:V+=evalfold(*A,y,c1,c2)
 T=[]
 for y in TEST:T+=evalfold(*A,y,c1,c2)
 pref={"B0":"b0_","B1":"b1_","I1":"i1_","I2":"i2_"};PF={n:profile(T,p) for n,p in pref.items()};RK=ranks(PF);best=min(("I1","I2"),key=lambda n:RK[n]["mean"]);top2=sum(1 for k,v in RK[best].items() if k!="mean" and v<=2);core=(PF[best]["calibration"]<.98)+(PF[best]["discrimination"]>PF["B0"]["discrimination"]+.01)+(PF[best]["development"]>PF["B0"]["development"]+.01)+(PF[best]["state_quality"]<.98);prom=RK[best]["mean"]<RK["B0"]["mean"] and RK[best]["mean"]<RK["B1"]["mean"] and top2>=4 and core>=2;status="PROMOTABLE FOR MANAGEMENT REVIEW" if prom else "NO PROMOTABLE CANDIDATE";sel=best if prom else None
 AB={};bc=c1 if best=="I1" else c2
 for f in ("production","role","continuity","availability","participation"):
  R=[]
  for y in TEST:R+=evalfold(*A,y,bc,bc,arches=(best,),drop=frozenset({f}))
  AB[f]=profile(R,"i1_" if best=="I1" else "i2_")
 S={"study":"integrated-multivariate-forecast-v1","protocol":"artifacts/research/integrated_multivariate_forecast_protocol.md","phase0":checks,"C":{"I1":c1,"I2":c2,"I1_validation":v1,"I2_validation":v2,"I1_ranks":vr1,"I2_ranks":vr2},"holdout":{"seasons":list(TEST),"profiles":PF,"ranks":RK,"best_integrated":best,"selected":sel,"status":status,"top2_dimensions":top2,"core_improvements":int(core)},"development_profiles":{n:profile(D,p) for n,p in pref.items()},"validation_profiles":{n:profile(V,p) for n,p in pref.items()},"development":{n:dev(T,p) for n,p in pref.items()},"safety":{f:{n:safety(T,p,f) for n,p in pref.items()} for f in ("later_return","non_ir_injury","reserve_practice","active_no_prod")},"coverage":{"holdout_rows":len(T),"resolved":sum(r["factual_state"] is not None for r in T),"resolved_share":avg(r["factual_state"] is not None for r in T),"paths":{n:dict(Counter(r[p+"path"] for r in T)) for n,p in pref.items()}},"ablation":AB,"architecture":{"provider_specific_model_fields":[],"canonical_contract":True,"future_leakage":False,"market_owner_value_shapley_inputs":False,"research_rights":E["gates"]["H_commercial_governance"]},"production_replaceability":{"football_state_source_needed":["NFL roster/attachment","injury/practice","transaction/status continuity","snap/depth/participation"],"could_become_internal_or_uploaded":["realized fantasy production","career-state calibration from accumulated governed outcomes"],"prohibited":["owner behavior","trades","market prices"]},"anticipated_production":{"integrated_candidates":"chronological state-probability x state-mean coordinate","controls":"frozen Model A means","blanket_haircut":False},"downstream_shapley":{"authorized":bool(prom),"run":False}}
 pd.DataFrame(D+V+T).to_csv(z.output_dir/"integrated_multivariate_oos_rows.csv",index=False);(z.output_dir/"integrated_multivariate_forecast_results.json").write_text(json.dumps(S,indent=2,sort_keys=True));print(json.dumps({"status":status,"selected":sel,"best":best,"C":{"I1":c1,"I2":c2},"ranks":RK,"development":S["development"],"coverage":S["coverage"]},indent=2))
if __name__=="__main__":main()

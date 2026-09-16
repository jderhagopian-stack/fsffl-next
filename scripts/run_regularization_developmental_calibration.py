from __future__ import annotations
import argparse, importlib.util, json, sys
from collections import Counter
from pathlib import Path
import pandas as pd

CS=(0.0625,0.125,0.25,0.5,1.0)
EXT=0.03125
SEASONS=tuple(range(2014,2023))
USE={"usable","starter","premium","elite"}


def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m

def avg(xs):
 xs=[float(x) for x in xs if x is not None and not pd.isna(x)];return sum(xs)/len(xs) if xs else None

def examples(panel,legacy):
 out=[]
 for r in panel:
  if r.position not in ("QB","RB","WR","TE") or r.season<2014 or r.season>2023 or r.age is None:continue
  p=max(0.,float(r.points))
  out.append(legacy.Example(season=int(r.season),player_id=r.player_id,position=r.position,age=float(r.age),experience=int(r.experience),pedigree=legacy.pedigree_score(r.draft_pick),survival=1.,means=(p,p,p),sds=(0.,0.,0.),realized=0.))
 return out

def dev(r):return bool(r.get("low_end") and r.get("age_band")=="young")
def dev_summary(rows,p="i1_"):
 R=[r for r in rows if r.get("factual_state") is not None and dev(r)];tp=fp=tn=fn=0
 for r in R:
  y=r["factual_state"] in USE;q=float(r[p+"useful"])>=.5
  if y and q:tp+=1
  elif y:fn+=1
  elif q:fp+=1
  else:tn+=1
 return {"n":len(R),"success_n":tp+fn,"tp":tp,"fn":fn,"fp":fp,"tn":tn,"recall":tp/(tp+fn) if tp+fn else None,"precision":tp/(tp+fp) if tp+fp else None,"useful_brier":avg(r[p+"ub"] for r in R),"state_brier":avg(r[p+"sb"] for r in R)}
def summary(im,rows,p="i1_"):
 s=im.summary(rows,p);return {"n":s.get("n",0),"state_brier":s.get("sb"),"state_logloss":s.get("sll"),"persistence_brier":s.get("pb"),"useful_brier":s.get("ub"),"starter_brier":s.get("stb"),"premium_brier":s.get("prb"),"production_mae":s.get("mae"),"production_bias":s.get("bias"),"conditional_state_brier":s.get("csb"),"dev":dev_summary(rows,p),"paths":dict(Counter(r.get(p+"path") for r in rows))}
def run_rows(im,A,C,seasons=SEASONS):
 R=[]
 for y in seasons:R+=im.evalfold(*A,y,C,C,arches=("I1",))
 return R
def mix(g,d):
 if len(g)!=len(d):raise RuntimeError("row count mismatch")
 out=[]
 for a,b in zip(g,d):
  if (a["season"],a["horizon"],a["position"],a["factual_state"],a["actual_points"])!=(b["season"],b["horizon"],b["position"],b["factual_state"],b["actual_points"]):raise RuntimeError("row alignment mismatch")
  r=dict(a)
  if dev(a):
   for k in [k for k in a if k.startswith("i1_")]:r[k]=b[k]
   r["i1_path"]="stage_dev:"+str(b.get("i1_path"))
  else:r["i1_path"]="stage_global:"+str(a.get("i1_path"))
  out.append(r)
 return out

def add_meta(rows,**kw):
 return [{**r,**kw} for r in rows]
def folds(im,rows):
 return {str(y):summary(im,[r for r in rows if int(r["season"])==y]) for y in sorted({int(r["season"]) for r in rows})}
def coverage(rows):
 out=[]
 for y in sorted({int(r["season"]) for r in rows}):
  for h in (1,2):
   F=[r for r in rows if int(r["season"])==y and int(r["horizon"])==h]
   if not F:continue
   R=[r for r in F if r.get("factual_state") is not None];D=[r for r in R if dev(r)]
   out.append({"season":y,"horizon":h,"rows":len(F),"resolved":len(R),"developmental":len(D),"developmental_successes":sum(r["factual_state"] in USE for r in D),"full":sum(r.get("i1_path")=="full" for r in F),"reduced":sum(r.get("i1_path")=="red" for r in F),"fallback":sum(r.get("i1_path")=="b0_fallback" for r in F)})
 return out

def context(args):
 H=Path(__file__).parent;im=load(H/"run_integrated_multivariate_forecast.py","rr_im");pf=load(H/"run_persistence_first_forecast_calibration.py","rr_pf");prior=load(H/"run_forecast_low_end_career_calibration.py","rr_prior");legacy=load(H/"run_fundamental_intrinsic_residual_calibration.py","rr_legacy");parity=load(H/"run_fundamental_intrinsic_production_parity.py","rr_parity");base=load(H/"run_intrinsic_explicit_state_challenge.py","rr_base");evt=load(H/"reconstruct_event_time_absence_cause_evidence.py","rr_evt")
 I=json.loads(args.prior_integrated_json.read_text());E=json.loads(args.prior_event_json.read_text());P=json.loads(args.prior_persistence_json.read_text());checks={"i1_selected":I["holdout"]["selected"]=="I1","i1_C":float(I["C"]["I1"])==.25,"prior_dev_true_n":int(I["development"]["I1"]["true_n"]),"event_resolution":abs(E["overall_resolution"]["resolved_share"]-685/925)<1e-10,"persistence":bool(P.get("conclusion"))}
 if not checks["i1_selected"] or not checks["i1_C"] or not checks["event_resolution"]:raise RuntimeError("baseline parity failed "+json.dumps(checks))
 panel=legacy.load_rows(args.career_panel);by={(r.player_id,r.season):r for r in panel};ex=examples(panel,legacy);usage=pf.load_usage(args.usage_panel);qb=parity.load_qb_probabilities(args.qb_results);ev=pf.source_evidence_map(evt,list(range(2012,2025)));A=(pf,prior,base,panel,by,ex,usage,qb,ev)
 return im,A,checks

def global_mode(args,im,A,checks):
 cs=list(CS)+([EXT] if args.include_extension else []);allrows=[];S={}
 for C in sorted(cs):
  R=run_rows(im,A,C);S[str(C)]={"overall":summary(im,R),"folds":folds(im,R)};allrows+=add_meta(R,mode="global",global_C=C,treatment="global")
 base=run_rows(im,A,.25);pd.DataFrame(coverage(base)).to_csv(args.output_dir/"rolling_fold_coverage.csv",index=False);pd.DataFrame(allrows).to_csv(args.output_dir/"global_candidate_rows.csv",index=False)
 out={"mode":"global","checks":checks,"grid":sorted(cs),"extension_included":args.include_extension,"results":S,"coverage":coverage(base)};(args.output_dir/"global_regularization_results.json").write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps({"grid":sorted(cs),"state_brier":{c:S[str(c)]["overall"]["state_brier"] for c in sorted(cs)}},indent=2))
def stage_mode(args,im,A,checks,freeze):
 if not freeze.get("global_frozen"):raise RuntimeError("global selection not frozen")
 Cg=float(freeze["global_C"]);cds=[]
 for m in (2.,4.):
  c=min(1.,Cg*m)
  if c>Cg and c not in cds:cds.append(c)
 G=run_rows(im,A,Cg);allrows=add_meta(G,mode="stage",global_C=Cg,developmental_C=Cg,treatment="global_control");S={"global_control":{"overall":summary(im,G),"folds":folds(im,G)}}
 for Cd in cds:
  D=run_rows(im,A,Cd);M=mix(G,D);S[str(Cd)]={"overall":summary(im,M),"folds":folds(im,M)};allrows+=add_meta(M,mode="stage",global_C=Cg,developmental_C=Cd,treatment="stage_aware")
 pd.DataFrame(allrows).to_csv(args.output_dir/"stage_candidate_rows.csv",index=False);out={"mode":"stage","checks":checks,"global_C":Cg,"developmental_candidates":cds,"results":S};(args.output_dir/"developmental_stage_results.json").write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps({"global_C":Cg,"candidates":cds,"dev":{k:v["overall"]["dev"] for k,v in S.items()}},indent=2))
def confirm_mode(args,im,A,checks,freeze):
 if not freeze.get("stage_frozen"):raise RuntimeError("stage selection not frozen")
 Cg=float(freeze["global_C"]);Cd=freeze.get("developmental_C");G=[r for r in im.evalfold(*A,2023,Cg,Cg,arches=("I1",)) if int(r["horizon"])==1];B=[r for r in im.evalfold(*A,2023,.25,.25,arches=("I1",)) if int(r["horizon"])==1]
 if Cd is None:S=G
 else:
  D=[r for r in im.evalfold(*A,2023,float(Cd),float(Cd),arches=("I1",)) if int(r["horizon"])==1];S=mix(G,D)
 rows=add_meta(B,confirmation_role="provisional_0_25")+add_meta(G,confirmation_role="global_control")+add_meta(S,confirmation_role="selected");pd.DataFrame(rows).to_csv(args.output_dir/"confirmation_rows.csv",index=False);out={"mode":"confirm","checks":checks,"global_C":Cg,"developmental_C":Cd,"provisional_0_25":summary(im,B),"global_control":summary(im,G),"selected":summary(im,S)};(args.output_dir/"confirmation_results.json").write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps({"global_C":Cg,"developmental_C":Cd,"selected":out["selected"]},indent=2))
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=("global","stage","confirm"),required=True);ap.add_argument("--career-panel",type=Path,required=True);ap.add_argument("--usage-panel",type=Path,required=True);ap.add_argument("--qb-results",type=Path,required=True);ap.add_argument("--prior-integrated-json",type=Path,required=True);ap.add_argument("--prior-event-json",type=Path,required=True);ap.add_argument("--prior-persistence-json",type=Path,required=True);ap.add_argument("--freeze",type=Path);ap.add_argument("--include-extension",action="store_true");ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True);im,A,checks=context(a);freeze=json.loads(a.freeze.read_text()) if a.freeze and a.freeze.exists() else {}
 if a.mode=="global":global_mode(a,im,A,checks)
 elif a.mode=="stage":stage_mode(a,im,A,checks,freeze)
 else:confirm_mode(a,im,A,checks,freeze)
if __name__=="__main__":main()

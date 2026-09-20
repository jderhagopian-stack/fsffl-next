from pathlib import Path
import numpy as np, pandas as pd
OUT=Path('/mnt/data/fsffl_walkforward_revalidation_20260919')
hist=pd.read_csv('/mnt/data/fsffl_diag/historical_predictions.csv')
y23=pd.read_csv('/mnt/data/fsffl_walkforward_audit_20260919/Y2_ORIGIN_2023_PREDICTIONS.csv')
for c in hist.columns:
    if c not in y23.columns:y23[c]=np.nan
y23=y23[hist.columns]
df=pd.concat([hist,y23],ignore_index=True)
P0_Y3={'QB|developmental':'D0','QB|established':'D1','QB|veteran':'D1','RB|developmental':'D1','RB|established':'D0','RB|veteran':'D0','WR|developmental':'D1','WR|established':'D1','WR|veteran':'D0','TE|developmental':'D1','TE|established':'D1','TE|veteran':'D0'}
R=P0_Y3.copy();R['QB|developmental']='D1';R['RB|established']='D1'

def current(p,h,s):return 'D1' if h==2 else R[f'{p}|{s}']
def slope_fe(q,ycol):
    g=q[[ycol,'source_percentile','source_season']].dropna();
    if len(g)<20:return np.nan
    u=g.source_percentile.to_numpy(float)-.5; cols=[np.ones(len(g)),u]
    yrs=sorted(g.source_season.unique())
    for yy in yrs[1:]:cols.append((g.source_season.to_numpy()==yy).astype(float))
    X=np.column_stack(cols); y=g[ycol].to_numpy(float); b=np.linalg.lstsq(X,y,rcond=None)[0];return float(b[1])
def boot_slope(q,ycol,reps=600,seed=20260919):
    g=q[[ycol,'source_percentile','source_season','player_id']].dropna().reset_index(drop=True)
    if len(g)<20:return (np.nan,np.nan,np.nan)
    seasons=pd.Categorical(g.source_season).codes; players=pd.Categorical(g.player_id).codes; ns=seasons.max()+1;np_=players.max()+1
    u=g.source_percentile.to_numpy(float)-.5; yrs=sorted(g.source_season.unique()); cols=[np.ones(len(g)),u]
    for yy in yrs[1:]:cols.append((g.source_season.to_numpy()==yy).astype(float))
    X=np.column_stack(cols); y=g[ycol].to_numpy(float); rng=np.random.default_rng(seed); vals=[]
    for _ in range(reps):
      w=rng.exponential(1.,ns)[seasons]*rng.exponential(1.,np_)[players]; sw=np.sqrt(w); b=np.linalg.lstsq(X*sw[:,None],y*sw,rcond=None)[0]; vals.append(float(b[1]))
    qv=np.quantile(vals,[.025,.975]);return float(np.linalg.lstsq(X,y,rcond=None)[0][1]),float(qv[0]),float(qv[1])
rows=[]
for p in ['QB','RB','WR','TE']:
 for h in [2,3]:
  maxyr=2023 if h==2 else 2022
  for s in ['developmental','established','veteran']:
   q=df[(df.position==p)&(df.horizon==h)&(df.career_stage==s)&df.source_season.between(2014,maxyr)].copy()
   if not len(q):continue
   cur=current(p,h,s)
   q['actual_active']=(q.target_state!='out').astype(float)
   q['expected_ret']=q.target_points/q.source_points
   q['active_ret']=np.where(q.target_state!='out',q.target_points/q.source_points,np.nan)
   q['cur_cond']=q.active_D0 if cur=='D0' else q.pred_D1/np.maximum(q.p_active,1e-15)
   q['cur_cond_ret']=q.cur_cond/q.source_points
   q['cond_ret_bias']=np.where(q.target_state!='out',q.cur_cond_ret-q.active_ret,np.nan)
   q['cond_point_bias']=np.where(q.target_state!='out',q.cur_cond-q.target_points,np.nan)
   bs,blo,bhi=boot_slope(q,'cond_ret_bias',seed=20260919+len(q)+h*100)
   # per-origin bias slopes
   os=[]
   for yr,g in q.groupby('source_season'):
    aa=g.dropna(subset=['cond_ret_bias'])
    if len(aa)>=10:
     x=aa.source_percentile.to_numpy(float); y=aa.cond_ret_bias.to_numpy(float); X=np.column_stack([np.ones(len(x)),x-.5]); os.append(float(np.linalg.lstsq(X,y,rcond=None)[0][1]))
   rows.append({'position':p,'horizon':h,'career_stage':s,'n':len(q),'active_n':int(q.actual_active.sum()),'origins':q.source_season.nunique(),'actual_active_slope':slope_fe(q,'actual_active'),'p_active_slope':slope_fe(q.assign(pactive=q.p_active),'pactive'),'expected_retention_slope':slope_fe(q,'expected_ret'),'active_retention_slope':slope_fe(q,'active_ret'),'conditional_predicted_retention_slope':slope_fe(q,'cur_cond_ret'),'conditional_retention_bias_slope':bs,'conditional_retention_bias_slope_ci_low':blo,'conditional_retention_bias_slope_ci_high':bhi,'conditional_point_bias_slope':slope_fe(q,'cond_point_bias'),'origin_bias_slope_n':len(os),'origin_bias_slope_negative_share':float(np.mean(np.array(os)<0)) if os else np.nan,'origin_bias_slope_median':float(np.median(os)) if os else np.nan})
pd.DataFrame(rows).to_csv(OUT/'CONTINUOUS_MAGNITUDE_SLOPES.csv',index=False)
print(pd.DataFrame(rows)[lambda x:(x.position=='RB')&(x.horizon==3)].to_string(index=False))
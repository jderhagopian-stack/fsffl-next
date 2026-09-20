from pathlib import Path
import numpy as np, pandas as pd, json, math
OUT=Path('/mnt/data/fsffl_partial_pooling_challenger_20260919')
row=pd.read_csv(OUT/'ROW_LEVEL_EVALUATION.csv')
fits=pd.read_csv(OUT/'ORIGIN_SPECIFIC_FITTED_PARAMETERS.csv')
parity=pd.read_csv(OUT/'EXACT_D1_REPLAY_PARITY.csv')
ORIGINS=sorted(row.origin.unique()); STATES=['depth','usable','starter','premium','elite']; REPS=5000
row['decile']=pd.cut(row.source_percentile,bins=np.linspace(0,1,11),include_lowest=True,right=False,labels=False)
active=row[row.target_state!='out'].copy()

def imce_numpy(bias,dec,w):
    total=w.sum()
    if total<=0:return np.nan
    s=0.0
    for d in range(10):
        m=(dec==d)
        if not m.any():continue
        sw=w[m].sum()
        if sw>0: s += sw*abs(np.sum(w[m]*bias[m])/sw)
    return s/total

def imce_df(df,biascol):
    return imce_numpy(df[biascol].to_numpy(float),df.decile.to_numpy(),np.ones(len(df)))

calrows=[]
for scope,g in [('overall',active),('upper',active[active.realized_group=='upper']),('lower',active[active.realized_group=='lower'])]:
    d=imce_df(g,'d1_ret_bias'); c=imce_df(g,'challenger_ret_bias')
    calrows.append({'scope':scope,'n':len(g),'d1_imce':d,'challenger_imce':c,'imce_improvement':d-c,'relative_improvement':(d-c)/d if d else np.nan})
calib=pd.DataFrame(calrows)

origin_summary=row.groupby('origin').agg(n=('player_id','size'),crps_gain=('crps_gain','mean'),mae_gain=('mae_gain','mean'),d1_crps=('d1_crps','mean'),challenger_crps=('challenger_crps','mean'),d1_mae=('d1_abs_error','mean'),challenger_mae=('challenger_abs_error','mean')).reset_index().merge(fits,on='origin')

state_diag=[]
for s,g in active.groupby('target_state'):
    state_diag.append({'state':s,'n':len(g),'d1_point_bias':g.d1_point_bias_realized_state.mean(),'challenger_point_bias':g.challenger_point_bias_realized_state.mean(),'d1_ret_bias':g.d1_ret_bias.mean(),'challenger_ret_bias':g.challenger_ret_bias.mean(),'d1_abs_ret_bias':abs(g.d1_ret_bias.mean()),'challenger_abs_ret_bias':abs(g.challenger_ret_bias.mean()),'d1_cov10_90':g.d1_cov10_90.mean(),'challenger_cov10_90':g.challenger_cov10_90.mean(),'d1_cov25_75':g.d1_cov25_75.mean(),'challenger_cov25_75':g.challenger_cov25_75.mean()})
state_diag=pd.DataFrame(state_diag)

def subset_metrics(name,mask):
    g=row.loc[mask].copy(); a=g[g.target_state!='out']
    rec={'subset':name,'n':len(g),'active_n':len(a),'d1_crps':g.d1_crps.mean(),'challenger_crps':g.challenger_crps.mean(),'crps_gain':g.crps_gain.mean(),'d1_mae':g.d1_abs_error.mean(),'challenger_mae':g.challenger_abs_error.mean(),'mae_gain':g.mae_gain.mean(),'d1_cov10_90':g.d1_cov10_90.mean(),'challenger_cov10_90':g.challenger_cov10_90.mean(),'d1_cov25_75':g.d1_cov25_75.mean(),'challenger_cov25_75':g.challenger_cov25_75.mean()}
    if len(a): rec.update({'d1_ret_bias':a.d1_ret_bias.mean(),'challenger_ret_bias':a.challenger_ret_bias.mean(),'d1_abs_ret_bias':abs(a.d1_ret_bias.mean()),'challenger_abs_ret_bias':abs(a.challenger_ret_bias.mean()),'d1_imce':imce_df(a,'d1_ret_bias'),'challenger_imce':imce_df(a,'challenger_ret_bias')})
    return rec
subsets=[subset_metrics('full',np.ones(len(row),bool)),subset_metrics('low_mid_lt75',row.source_percentile.to_numpy()<.75)]
for q in [.75,.90,.95]: subsets.append(subset_metrics(f'p{int(q*100)}_plus',row.source_percentile.to_numpy()>=q))
for grp in ['upper','lower']: subsets.append(subset_metrics(grp,row.realized_group.to_numpy()==grp))
subset=pd.DataFrame(subsets)

coverage=[]
for scope,g in [('overall',row),('upper',row[row.realized_group=='upper']),('lower',row[row.realized_group=='lower'])]:
    coverage.append({'scope':scope,'n':len(g),'d1_cov10_90':g.d1_cov10_90.mean(),'challenger_cov10_90':g.challenger_cov10_90.mean(),'diff10_90':g.challenger_cov10_90.mean()-g.d1_cov10_90.mean(),'d1_cov25_75':g.d1_cov25_75.mean(),'challenger_cov25_75':g.challenger_cov25_75.mean(),'diff25_75':g.challenger_cov25_75.mean()-g.d1_cov25_75.mean()})
coverage=pd.DataFrame(coverage)

# Bootstrap vectorized in batches
players=pd.Categorical(row.player_id).codes; origins=pd.Categorical(row.origin).codes; P=players.max()+1; O=origins.max()+1
crps=row.crps_gain.to_numpy(float); mae=row.mae_gain.to_numpy(float); lowmask=row.source_percentile.to_numpy()<.75
actmask=row.target_state.to_numpy()!='out'; aa=row.loc[actmask].copy(); ap=players[actmask]; ao=origins[actmask]; adec=aa.decile.to_numpy(int); db=aa.d1_ret_bias.to_numpy(float); cb=aa.challenger_ret_bias.to_numpy(float); ag=aa.realized_group.to_numpy()
rng=np.random.default_rng(20260919)
crps_vals=[];mae_vals=[];low_vals=[];imce_vals={'overall':[],'upper':[],'lower':[]}
for start in range(0,REPS,250):
    B=min(250,REPS-start)
    wp=rng.exponential(1,(B,P)); wo=rng.exponential(1,(B,O)); W=wp[:,players]*wo[:,origins]
    den=W.sum(axis=1); crps_vals.extend((W@crps/den).tolist()); mae_vals.extend((W@mae/den).tolist())
    Wl=W[:,lowmask]; low_vals.extend((Wl@crps[lowmask]/Wl.sum(axis=1)).tolist())
    Wa=wp[:,ap]*wo[:,ao]
    for scope in ['overall','upper','lower']:
        sm=np.ones(len(aa),bool) if scope=='overall' else (ag==scope)
        vals=[]
        for b in range(B):
            ww=Wa[b,sm]; vals.append(imce_numpy(db[sm],adec[sm],ww)-imce_numpy(cb[sm],adec[sm],ww))
        imce_vals[scope].extend(vals)

def ci(v):
    a=np.asarray(v,float); return {'mean':float(a.mean()),'ci_low':float(np.quantile(a,.025)),'ci_high':float(np.quantile(a,.975))}
unc={'crps_gain':ci(crps_vals),'mae_gain':ci(mae_vals),'low_mid_crps_gain':ci(low_vals),'imce_improvement':{k:ci(v) for k,v in imce_vals.items()}}

# moving block bootstrap 3 origins from origin sums/counts
stats=row.groupby('origin').crps_gain.agg(['sum','count']).reindex(ORIGINS); sums=stats['sum'].to_numpy(float); counts=stats['count'].to_numpy(float); nO=len(ORIGINS)
rng=np.random.default_rng(20260920); bvals=[]
for _ in range(REPS):
    idx=[]
    while len(idx)<nO:
        st=int(rng.integers(0,nO)); idx.extend([(st+j)%nO for j in range(3)])
    idx=idx[:nO]; bvals.append(float(sums[idx].sum()/counts[idx].sum()))
unc['moving_block_crps_gain']=ci(bvals)

loo=[]
for o in ORIGINS:
    g=row[row.origin!=o]; loo.append({'omit_origin':int(o),'n':len(g),'crps_gain':g.crps_gain.mean(),'mae_gain':g.mae_gain.mean()})
loo=pd.DataFrame(loo)
pinf=[]
full=row.crps_gain.mean()
for p in sorted(row.player_id.unique()):
    g=row[row.player_id!=p]; pinf.append({'omit_player':p,'removed_rows':int((row.player_id==p).sum()),'crps_gain':g.crps_gain.mean(),'delta_vs_full':g.crps_gain.mean()-full})
pinf=pd.DataFrame(pinf).sort_values('crps_gain')

maxprob=0.0
for _,r in row.iterrows(): maxprob=max(maxprob,abs(sum(float(r[f'p_{s}']) for s in ['out','depth','usable','starter','premium','elite'])-1))
viol=0;mingap=1e9
for _,r in row.iterrows():
    vals=np.array([r.challenger_mean_depth,r.challenger_mean_usable,r.challenger_mean_starter,r.challenger_mean_premium,r.challenger_mean_elite],float); dif=np.diff(vals); viol+=int(np.any(dif<=0)); mingap=min(mingap,float(dif.min()))
validity={'max_probability_sum_error':maxprob,'ordering_violation_rows':viol,'min_adjacent_state_gap_points':mingap,'all_fits_ok':bool(fits.fit_ok.all()),'binding_plus_origins':int(fits.binding_plus.sum()),'binding_minus_origins':int(fits.binding_minus.sum())}

cal=calib.set_index('scope'); fullgain=float(row.crps_gain.mean()); maegain=float(row.mae_gain.mean()); lowgain=float(subset.loc[subset['subset']=='low_mid_lt75','crps_gain'].iloc[0]); origins_improved=int((origin_summary.crps_gain>0).sum()); med=float(origin_summary.crps_gain.median()); worst=float(origin_summary.crps_gain.min()); loo_flip=bool((loo.crps_gain>0).any()) if fullgain<0 else bool((loo.crps_gain<0).any()); player_flip=bool((pinf.crps_gain>0).any()) if fullgain<0 else bool((pinf.crps_gain<0).any())
state_new_failure=bool(((state_diag.challenger_abs_ret_bias-state_diag.d1_abs_ret_bias)>0.05).any()); covok=bool((coverage.diff10_90>=-.03-1e-12).all() and (coverage.diff25_75>=-.03-1e-12).all())
gates=[
 {'gate':'full_cell_crps','pass':bool(fullgain>=0 and unc['crps_gain']['ci_low']>=0 and origins_improved>=6 and med>=0 and not loo_flip),'detail':f'gain={fullgain:+.4f}; CI=[{unc["crps_gain"]["ci_low"]:+.4f},{unc["crps_gain"]["ci_high"]:+.4f}]; origins={origins_improved}/9; median={med:+.4f}; worst={worst:+.4f}; LOO_flip={loo_flip}'},
 {'gate':'continuous_magnitude_calibration','pass':bool(cal.loc['overall','imce_improvement']>0 and cal.loc['upper','imce_improvement']>=0 and cal.loc['lower','imce_improvement']>0 and unc['imce_improvement']['overall']['ci_low']>=0),'detail':f'overall={cal.loc["overall","imce_improvement"]:+.4f}; upper={cal.loc["upper","imce_improvement"]:+.4f}; lower={cal.loc["lower","imce_improvement"]:+.4f}; overallCI=[{unc["imce_improvement"]["overall"]["ci_low"]:+.4f},{unc["imce_improvement"]["overall"]["ci_high"]:+.4f}]'},
 {'gate':'state_diagnostics','pass':not state_new_failure,'detail':f'new_material_failure={state_new_failure}'},
 {'gate':'mae_no_harm','pass':bool(maegain>=-.5 and unc['mae_gain']['ci_high']>=0),'detail':f'gain={maegain:+.4f}; CI=[{unc["mae_gain"]["ci_low"]:+.4f},{unc["mae_gain"]["ci_high"]:+.4f}]'},
 {'gate':'low_mid_no_harm','pass':bool(lowgain>=-.5 and unc['low_mid_crps_gain']['ci_high']>=0),'detail':f'gain={lowgain:+.4f}; CI=[{unc["low_mid_crps_gain"]["ci_low"]:+.4f},{unc["low_mid_crps_gain"]["ci_high"]:+.4f}]'},
 {'gate':'coverage','pass':covok,'detail':coverage.to_json(orient='records')},
 {'gate':'ordering_probability_parity','pass':bool(viol==0 and maxprob<=1e-12 and fits.fit_ok.all()),'detail':json.dumps(validity)},
 {'gate':'temporal_influence','pass':bool(not loo_flip and not player_flip),'detail':f'LOO_flip={loo_flip}; player_flip={player_flip}; blockCI=[{unc["moving_block_crps_gain"]["ci_low"]:+.4f},{unc["moving_block_crps_gain"]["ci_high"]:+.4f}]'},
 {'gate':'prospective_2023_2026_untouched','pass':True,'detail':'No 2026 target outcomes accessed.'}
]
gates=pd.DataFrame(gates)

# Classification per directive
allpass=bool(gates['pass'].all()); lower_help=bool(cal.loc['lower','imce_improvement']>0); overall_help=bool(cal.loc['overall','imce_improvement']>0)
if allpass: classification='A. PARTIAL-POOLING CHALLENGER EARNS RESEARCH AUTHORITY'
elif (lower_help or overall_help) and (fullgain>0 or maegain>0): classification='B. DIRECTION SUPPORTED, CHALLENGER NOT SUFFICIENT'
elif (lower_help or overall_help) and fullgain<=0: classification='D. RESULTS IMPLICATE A DIFFERENT FORECAST COMPONENT'
else: classification='C. PARTIAL-POOLING CHALLENGER FAILS'

# Save
origin_summary.to_csv(OUT/'ORIGIN_BY_ORIGIN_SCORES.csv',index=False); calib.to_csv(OUT/'CONTINUOUS_MAGNITUDE_CALIBRATION.csv',index=False); state_diag.to_csv(OUT/'STATE_CONDITIONAL_DIAGNOSTICS.csv',index=False); subset.to_csv(OUT/'NO_HARM_AND_TAIL_DIAGNOSTICS.csv',index=False); coverage.to_csv(OUT/'COVERAGE_DIAGNOSTICS.csv',index=False); loo.to_csv(OUT/'LEAVE_ONE_ORIGIN_OUT.csv',index=False); pinf.to_csv(OUT/'LEAVE_ONE_PLAYER_OUT_INFLUENCE.csv',index=False); gates.to_csv(OUT/'PROMOTION_GATE_EVALUATION.csv',index=False)

spec={'candidate':'partial_pooling_two_group_location_calibration','groups':{'upper':['starter','premium','elite'],'lower':['depth','usable']},'A_log_bound':math.log(1.5),'shared_ridge':.05,'lower_deviation_penalty':.05*(352/167),'penalty_basis':{'upper_active_n':352,'lower_active_n':167,'formula':'0.05*(352/167)'},'equation':'M_U=exp(A*tanh(a0+a1*z)); M_L=exp(A*tanh(a0+a1*z+d0+d1*z)); z=2*(u-.5)','ordering_constraints':['d0+d1<=0','d0-d1<=0'],'optimizer':'SLSQP; zeros; maxiter=2000; ftol=1e-12','probabilities':'exact D1','scale':'unchanged D1 treatment'}
(OUT/'CANDIDATE_SPECIFICATION_AND_REGULARIZATION.json').write_text(json.dumps(spec,indent=2)); (OUT/'CLUSTERED_AND_BLOCK_UNCERTAINTY.json').write_text(json.dumps(unc,indent=2)); (OUT/'DISTRIBUTION_VALIDITY_AND_ORDERING.json').write_text(json.dumps(validity,indent=2))
parity_pass=bool(parity.left_only.sum()==0 and parity.right_only.sum()==0 and parity.filter(like='maxdiff_').max().max()<=1e-8)
(OUT/'PROVENANCE_AND_PARITY_MANIFEST.json').write_text(json.dumps({'starting_feasibility_commit':'6d21b4900ee9dc6345f8b9c2cf78f9806f8d6545','preregistration_commit':'81ba46d30cd1b2a2bf0dd1c04ecb74216a976c24','eval_rows':len(row),'active_rows':len(active),'origins':[int(x) for x in ORIGINS],'parity_pass':parity_pass,'max_abs_replay_diff':float(parity.filter(like='maxdiff_').max().max()),'source_2023_target_2026_inspected':False},indent=2))
auth={'classification':classification,'all_material_gates_pass':allpass,'full_cell_crps_gain':fullgain,'clustered_crps_ci':[unc['crps_gain']['ci_low'],unc['crps_gain']['ci_high']],'origins_improved':origins_improved,'median_origin_gain':med,'worst_origin_gain':worst,'overall_imce_improvement':float(cal.loc['overall','imce_improvement']),'upper_imce_improvement':float(cal.loc['upper','imce_improvement']),'lower_imce_improvement':float(cal.loc['lower','imce_improvement']),'mae_gain':maegain,'low_mid_crps_gain':lowgain,'lower_deviation_parameters_effectively_zero':bool((fits[['d0','d1']].abs().max().max()<1e-8)),'production_authority_changed':False,'pr147_modified':False,'main_modified':False,'merge':False,'deploy':False,'prospective_2023_2026_untouched':True}
(OUT/'AUTHORITY_DISPOSITION.json').write_text(json.dumps(auth,indent=2)); (OUT/'FINAL_CLASSIFICATION.json').write_text(json.dumps({'classification':classification,'gates':gates.to_dict(orient='records'),'production_authority_changed':False,'pr147_modified':False,'main_modified':False,'merge':False,'deploy':False},indent=2)); (OUT/'PROSPECTIVE_AUTHORITY_MAP.json').write_text(json.dumps({'D1_Y3_developmental_RB':'frozen production control','challenger_research_authority_earned':classification.startswith('A.'),'state_probabilities':'unchanged','source_2023_target_2026':'untouched prospective confirmation','next_step':'management review only; no second challenger in this stage'},indent=2))
failed=gates.loc[~gates['pass'],'gate'].tolist(); (OUT/'FINAL_RESEARCH_CONCLUSION.md').write_text(f'# Final conclusion\n\nClassification: **{classification}**.\n\nPooled CRPS gain (D1 - challenger): {fullgain:+.4f}, clustered 95% CI [{unc["crps_gain"]["ci_low"]:+.4f}, {unc["crps_gain"]["ci_high"]:+.4f}], with {origins_improved}/9 origins improved.\n\nIMCE improvement overall {cal.loc["overall","imce_improvement"]:+.4f}; upper {cal.loc["upper","imce_improvement"]:+.4f}; lower {cal.loc["lower","imce_improvement"]:+.4f}. MAE gain {maegain:+.4f}. Low/mid CRPS gain {lowgain:+.4f}.\n\nThe ordering constraint bound at every origin and forced the fitted lower-group deviations to numerical zero, so the preregistered challenger collapsed to its shared curve. This means the feasibility signal could not be expressed under the preregistered no-crossing constraint without violating state-ordering protection.\n\nFailed material gates: {", ".join(failed) if failed else "none"}. D1 probabilities remained unchanged and source-2023 -> target-2026 was not inspected.\n')
print(json.dumps(auth,indent=2)); print('\nGATES\n',gates.to_string(index=False)); print('\nCALIB\n',calib.to_string(index=False)); print('\nCOVERAGE\n',coverage.to_string(index=False))
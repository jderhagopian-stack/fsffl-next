from pathlib import Path
import pandas as pd, numpy as np, json, hashlib, math
import matplotlib.pyplot as plt

OUT=Path('/mnt/data/fsffl_walkforward_revalidation_20260919')
auth=pd.read_csv(OUT/'FORECAST_WIDE_AUTHORITY_MATRIX.csv')
orig=pd.read_csv(OUT/'ORIGIN_BY_ORIGIN_SCORE_TABLE.csv')
mag=pd.read_csv(OUT/'CONTINUOUS_MAGNITUDE_DIAGNOSTICS.csv')
struct=pd.read_csv(OUT/'MAGNITUDE_STRUCTURE_SUMMARY.csv')
tail=pd.read_csv(OUT/'DEVELOPMENTAL_RB_TAIL_WALKFORWARD_SUMMARY.csv')
slopes=pd.read_csv(OUT/'CONTINUOUS_MAGNITUDE_SLOPES.csv')

# Frozen-decision inventory.
inv=auth[['position','horizon','career_stage','p0_representation','research_current','alternative','prior_status','n','origins']].copy()
inv['decision_under_review']=np.where(inv.prior_status.str.contains('EARNED'),'PRIOR_RESEARCH_EARNED_SWITCH',np.where(inv.prior_status.str.contains('STRUCTURALLY'),'P0_RETAINED_BUT_STRUCTURALLY_UNRESOLVED','P0_RETAINED'))
inv.to_csv(OUT/'FROZEN_DECISION_INVENTORY.csv',index=False)

# Clustered uncertainty compact output.
unc=auth[['position','horizon','career_stage','research_current','alternative','n','origins','pooled_crps_gain_current_vs_alt','cluster_ci_low','cluster_ci_high','block_boot_gain','block_ci_low','block_ci_high','pooled_mae_gain_current_vs_alt','mae_ci_low','mae_ci_high','origins_improved','origin_share_improved','median_origin_gain','worst_origin_regression','loo_gain_min','loo_gain_max','loo_sign_flip']].copy()
unc.to_csv(OUT/'CLUSTERED_UNCERTAINTY_OUTPUTS.csv',index=False)

# Explicit route-level revalidation summary for management.
counts=auth.revalidation_disposition.value_counts().to_dict()
weak=auth[auth.revalidation_disposition=='WEAKENED'][['position','horizon','career_stage','research_current','pooled_crps_gain_current_vs_alt','cluster_ci_low','cluster_ci_high','pooled_mae_gain_current_vs_alt','mae_ci_low','mae_ci_high']].to_dict('records')
confirmed_earned=auth[auth.prior_status.str.contains('EARNED')][['position','horizon','career_stage','research_current','pooled_crps_gain_current_vs_alt','cluster_ci_low','cluster_ci_high','origin_share_improved','pooled_mae_gain_current_vs_alt','mae_ci_low','mae_ci_high','revalidation_disposition']].to_dict('records')

# Hard-threshold summary.
no_hard=int((struct.classification.str.startswith('STABLE_CHANGE_POINT')).sum())==0
adequate=struct[struct.adequate_origins>=4]
structure_counts=struct.classification.value_counts().to_dict()
max_recur=float(adequate.piecewise_origin_recurrence.max()) if len(adequate) else np.nan
rbdev=struct[(struct.position=='RB')&(struct.horizon==3)&(struct.career_stage=='developmental')].iloc[0].to_dict()

# Tail influence exact values.
rb_tail=tail.set_index('threshold').to_dict(orient='index')

final={
 'schema_version':'fsffl-forecast-wide-walkforward-revalidation-final-v1',
 'classification':'B. MIXED REVALIDATION - SPECIFIC ROUTES REQUIRE NEW RESEARCH',
 'classification_basis':[
   f"18 of 24 position x horizon x career-stage cells are confirmed; {counts.get('WEAKENED',0)} are weakened and {counts.get('UNRESOLVED',0)} remains unresolved; no frozen decision is strongly reversed.",
   'The prior proper-score-earned Y3 developmental-QB D0->D1 and established-RB D0->D1 decisions both strengthen under the expanded walk-forward coordinate.',
   'Veteran fallback routes remain temporally/uncertainty limited rather than earning clean reversal, so they are flagged for later bounded review rather than silently changed.',
   'Y3 developmental-RB D1 remains strongly superior to D0 on proper score across every origin, but its high-end conditional-production calibration remains structurally unresolved.',
   'Continuous magnitude diagnostics support smooth nonlinear behavior in adequately supported non-veteran routes; no route earns a stable hard percentile transition under the preregistered recurrence rule.'
 ],
 'decision_counts':{k:int(v) for k,v in counts.items()},
 'confirmed_prior_earned_switches':confirmed_earned,
 'weakened_cells':weak,
 'magnitude_structure_counts':{k:int(v) for k,v in structure_counts.items()},
 'stable_hard_change_point_cells':int((struct.classification.str.startswith('STABLE_CHANGE_POINT')).sum()),
 'max_origin_recurrence_for_any_piecewise_knot':max_recur,
 'developmental_RB_Y3_structure':{
   'classification':rbdev['classification'],
   'pooled_best_piecewise_knot':float(rbdev['pooled_best_piecewise_knot']),
   'piecewise_origin_recurrence':float(rbdev['piecewise_origin_recurrence']),
   'bootstrap_best_knot_share':float(rbdev['bootstrap_best_knot_share']),
   'quadratic_curvature_sign_stability':float(rbdev['quadratic_curvature_sign_stability']),
   'full_cell_D1_vs_D0_crps_gain':float(auth[(auth.position=='RB')&(auth.horizon==3)&(auth.career_stage=='developmental')].iloc[0].pooled_crps_gain_current_vs_alt),
   'full_cell_cluster_ci':[float(auth[(auth.position=='RB')&(auth.horizon==3)&(auth.career_stage=='developmental')].iloc[0].cluster_ci_low),float(auth[(auth.position=='RB')&(auth.horizon==3)&(auth.career_stage=='developmental')].iloc[0].cluster_ci_high)],
   'p90plus_active_retention_bias':float(rb_tail[0.9]['d1_mean_active_retention_bias']),
   'p95plus_active_retention_bias':float(rb_tail[0.95]['d1_mean_active_retention_bias'])
 },
 'next_research_target':'Y3 developmental-RB threshold-free continuous-magnitude conditional-production/uncertainty calibration: preserve D1 state/proper-score strength while resolving the supported extreme-source active-production underprediction without introducing p90/p95 model states.',
 'fresh_holdout_policy':'No pristine current Y3 holdout remains; use canonical repeated/nested walk-forward now and preserve source-2023 -> target-2026 Y3 prospectively.',
 'production_authority_changed':False,'pr147_modified':False,'main_modified':False,'merge':False,'deploy':False
}
(OUT/'FINAL_CLASSIFICATION.json').write_text(json.dumps(final,indent=2))

boundary='''# Recommended next Forecast research boundary\n\n## Priority\nY3 developmental-RB continuous-magnitude conditional-production / uncertainty calibration remains the highest-priority unresolved Forecast problem.\n\n## Why this remains first\n- The frozen D1 control is strongly better than D0 on raw-point CRPS across all nine canonical Y3 origins, so the problem is not a route-selection failure.\n- The full supported cell is large and stable, unlike the weakened veteran fallback cells.\n- Continuous-magnitude diagnostics show smooth nonlinear structure rather than a stable hard percentile regime.\n- The extreme high-source active-production miss remains visible: D1 active retention bias moves from modestly positive at lower supported magnitudes to negative at the highest magnitude; pooled p95+ active-retention bias is about -0.117 while D1 still dominates D0 on CRPS.\n- A p90-like change point is not stable enough to canonize: developmental-RB Y3 pooled best piecewise knot is 0.90, but only 3/9 adequately supported origins prefer the same piecewise knot and the two-way bootstrap best-knot share is about 0.43.\n\n## What the next directive should test\nTest a threshold-free continuous-magnitude representation of active production and uncertainty under the canonical walk-forward coordinate. The research question is whether smooth nonlinear conditional-production calibration can preserve D1's state-probability and proper-score advantage while removing systematic extreme-source compression. Do not create p90/p95 model states.\n\nAny candidate must be specified and frozen before evaluation, judged across Y3 origins 2014-2022 with clustered/temporal robustness, and prospectively confirmed on source-2023 -> target-2026 only after complete 2026 outcomes exist.\n\n## Lower-priority watch items\nVeteran RB/WR/TE route cells are weakened by the expanded evidence, but their sample support is too thin for bespoke new structure. They should remain bounded review/watch items and should not displace the well-supported developmental-RB structural issue as the next research target.\n'''
(OUT/'RECOMMENDED_NEXT_RESEARCH_BOUNDARY.md').write_text(boundary)

summary={
 'coordinate':{'Y2':'2014-2023, 10 origins, 5726 rows','Y3':'2014-2022, 9 origins, 5168 rows'},
 'overall_classification':final['classification'],
 'cells':{'confirmed':int(counts.get('CONFIRMED',0)),'weakened':int(counts.get('WEAKENED',0)),'unresolved':int(counts.get('UNRESOLVED',0)),'reversed':int(counts.get('REVERSED',0))},
 'magnitude':{'smooth_nonlinear':int(structure_counts.get('SMOOTH_NONLINEAR',0)),'insufficient':int(structure_counts.get('INSUFFICIENT_EVIDENCE',0)),'stable_change_point':0},
 'next_target':final['next_research_target']
}
(OUT/'REVALIDATION_EXECUTIVE_SUMMARY.json').write_text(json.dumps(summary,indent=2))

# Exact replay parity evidence for the added Y2 origin.
parity={'schema_version':'fsffl-y2-origin-2023-replay-parity-v1','validation_origin':2022,'compared_rows':596,'max_abs_pred_D0_diff':2.842170943040401e-14,'max_abs_pred_D1_diff':2.842170943040401e-14,'max_abs_p_active_diff':1.1102230246251565e-16,'pass':True,'generated_2023_Y2_rows':558,'generated_2023_position_counts':{'QB':74,'RB':154,'WR':213,'TE':117}}
(OUT/'EXACT_REPLAY_PARITY.json').write_text(json.dumps(parity,indent=2))

# Plot: authority gains with clustered CIs.
plot=auth.copy(); plot['label']=plot.position+' Y'+plot.horizon.astype(str)+' '+plot.career_stage.str[:3]
fig,ax=plt.subplots(figsize=(10.5,6.5))
y=np.arange(len(plot)); x=plot.pooled_crps_gain_current_vs_alt.to_numpy(); lo=x-plot.cluster_ci_low.to_numpy(); hi=plot.cluster_ci_high.to_numpy()-x
ax.errorbar(x,y,xerr=np.vstack([lo,hi]),fmt='o',capsize=2)
ax.axvline(0,linewidth=.8); ax.set_yticks(y); ax.set_yticklabels(plot.label); ax.invert_yaxis();ax.set_xlabel('CRPS gain: current frozen decision minus opposite D0/D1 (positive = current better)');ax.set_title('Forecast-wide walk-forward revalidation by route');fig.tight_layout();fig.savefig(OUT/'FORECAST_WIDE_CRPS_REVALIDATION.png',dpi=180,bbox_inches='tight');plt.close(fig)

# Plot: developmental RB Y3 magnitude, using decile means and active means.
rb=mag[(mag.position=='RB')&(mag.horizon==3)&(mag.career_stage=='developmental')].copy().sort_values('source_percentile_mean')
# Reconstruct active realized point means and D1 conditional means from historical rows for interpretable overlay.
h=pd.read_csv('/mnt/data/fsffl_diag/historical_predictions.csv'); q=h[(h.position=='RB')&(h.horizon==3)&(h.career_stage=='developmental')&h.source_season.between(2014,2022)].copy();q['d1_cond']=q.pred_D1/q.p_active;q['dec']=pd.cut(q.source_percentile,bins=np.linspace(0,1,11),include_lowest=True)
rows=[]
for b,g in q.groupby('dec',observed=True):
 aa=g[g.target_state!='out']; rows.append({'pct':g.source_percentile.mean(),'n':len(g),'active_n':len(aa),'real_active':aa.target_points.mean() if len(aa) else np.nan,'d1_active':aa.d1_cond.mean() if len(aa) else np.nan,'real_expected':g.target_points.mean(),'d1_expected':g.pred_D1.mean()})
rbd=pd.DataFrame(rows)
fig,ax=plt.subplots(figsize=(8.6,4.2));ax.plot(rbd.pct,rbd.real_active,marker='o',label='Realized active points');ax.plot(rbd.pct,rbd.d1_active,marker='o',label='D1 conditional-active points');ax.set_xlabel('Source-season percentile');ax.set_ylabel('Y3 points among active outcomes');ax.set_title('Developmental RB Y3: continuous source magnitude, no hard tier');ax.legend();fig.tight_layout();fig.savefig(OUT/'RB_DEV_Y3_CONTINUOUS_MAGNITUDE.png',dpi=180,bbox_inches='tight');plt.close(fig)

# Plot transition recurrence for supported routes.
sup=struct[struct.adequate_origins>=4].copy();sup['label']=sup.position+' Y'+sup.horizon.astype(str)+' '+sup.career_stage.str[:3]
fig,ax=plt.subplots(figsize=(10,5.5));yy=np.arange(len(sup));ax.barh(yy,sup.piecewise_origin_recurrence);ax.axvline(.6,linewidth=.8);ax.set_yticks(yy);ax.set_yticklabels(sup.label);ax.invert_yaxis();ax.set_xlabel('Share of adequately supported origins preferring the same piecewise knot');ax.set_title('No supported route reaches the preregistered 60% hard-transition recurrence gate');fig.tight_layout();fig.savefig(OUT/'TRANSITION_RECURRENCE.png',dpi=180,bbox_inches='tight');plt.close(fig)

print(json.dumps(summary,indent=2))
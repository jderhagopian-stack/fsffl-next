"""Research empirical trajectory prior fitted from historical cohort labels.

Equal class frequency is an empirical estimator, not expert-source weighting.
Returned scenario dispersion is uncalibrated. No Career/tail or production model
is authorized here. Missing classes never disappear through complete-case fitting.
"""
from math import fsum

from scripts.evaluate_native_pick_baseline import evaluate
from fsffl.value.native_pick_research import NativePickAnnualOutcome,NativePickJointScenario,NativePickSlotForecast


def fit(document, *, release_season, draft_season, round_number, team_count, complete_through,
        selection_policy_ref, corroborated_gaps=(), absence_assumption_ref=None):
    if not selection_policy_ref.strip():raise ValueError('explicit selection-policy qualification required')
    if draft_season<release_season or round_number<1 or team_count<1 or complete_through>=release_season:
        raise ValueError('invalid prospective calendar or cohort scope')
    if corroborated_gaps and not absence_assumption_ref:
        raise ValueError('source-corroborated absence still requires an explicit research assumption')
    allowed=set()
    for gap in corroborated_gaps:
        if gap['status']!='corroborated_source_absence_not_verified_zero' or not gap.get('source_sha256'):
            raise ValueError('only fingerprinted corroborated-absence evidence can support this sensitivity')
        key=gap['player_id'],gap['season']
        if key in allowed:raise ValueError('duplicate corroborated-absence evidence')
        allowed.add(key)
    evaluate(document,horizon=3,discount=.85,heldout_classes=[release_season],
             max_slots=round_number*team_count,complete_through=complete_through)
    cases=[]
    for case in document['cases']:
        lookup={(r['draft_season'],r['rank']):r for r in case['selections']}
        classes=sorted({y for y,s in lookup if y+2<release_season and y+2<=complete_through})
        forecasts=[];unsupported=[];assumed=[]
        for slot in range(1,team_count+1):
            rank=(round_number-1)*team_count+slot;trajectories=[];slot_assumptions=[]
            for year in classes:
                row=lookup.get((year,rank))
                annual=row['raw_observed'].get('3') if row and row.get('player_id') else None
                if annual is None or len(annual)!=3:break
                values=[]
                for i,value in enumerate(annual):
                    if value is None and (row['player_id'],year+i) in allowed:
                        value=0.;slot_assumptions.append(dict(player_id=row['player_id'],season=year+i,
                                                             rank=rank,basis='assumed_source_corroborated_absence'))
                    values.append(value)
                if any(v is None for v in values):break
                trajectories.append(values)
            if not classes or len(trajectories)!=len(classes):
                unsupported.append(slot);continue
            scenarios=tuple(NativePickJointScenario(probability=1/len(classes),annual=tuple(
                NativePickAnnualOutcome(season=draft_season+i,raw_shapley=v) for i,v in enumerate(values)))
                for values in trajectories)
            forecasts.append(NativePickSlotForecast(slot_in_round=slot,scenarios=scenarios))
            assumed.extend(slot_assumptions)
        cases.append(dict(economic_coordinate=case['economic_coordinate'],training_classes=classes,
            source_limitations=case.get('selection_evidence_limitations',[]),
            forecasts=[f.model_dump(mode='json') for f in forecasts],unsupported_slots=unsupported,
            assumed_training_seasons=assumed,selection_policy_ref=selection_policy_ref,
            absence_assumption_ref=absence_assumption_ref,career_available=False))
    return dict(status='fitted_empirical_cohort_prior_research_only',production_eligible=False,
        forecast_model_version='empirical_native_cohort_trajectory_research_v1',release_season=release_season,
        draft_season=draft_season,round=round_number,team_count=team_count,
        trajectory_policy='uniform_empirical_class_frequency_preserve_annual_dependence',
        uncertainty='uncalibrated_empirical_dispersion_not_estimation_confidence',cases=cases)

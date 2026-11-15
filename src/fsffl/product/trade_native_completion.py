"""Bind already-published native evidence to the existing final Decision owner."""
from copy import deepcopy
from math import isfinite
from fsffl.trade_decision.disposition import TradeDecisionDisposition
from fsffl.trade_decision.material_assessment import BilateralMaterialAssessment
from fsffl.trade_decision.package_economics import PackageEconomicAssessment
from fsffl.trade_decision.native_completion import NativeHorizonChange, complete_native_trade_decision


def finalize_published_trade_decision(runtime, proposal, result):
    # Fast analysis and provisional scenarios retain their established authority.
    if not result.get('disposition') or (result.get('scenario_computation') or {}).get('authoritative') is not True:
        return result
    horizons=result.get('horizon_asset_economics') or {}
    source=horizons.get('source') or {}
    reason=None
    missing_code='native_horizon_evidence'
    try:
        from .scenario_cache import ScenarioComputationStage, scenario_stage_simulation_count
        if int(result.get('scenario_simulation_count',0)) < scenario_stage_simulation_count(ScenarioComputationStage.CONFIRMATION):
            missing_code='authoritative_simulation_confirmation'
            raise ValueError('Confirmed Simulation count is required for final Decision')
        state=runtime.league_state
        state_id=state.state_id if state is not None else None
        if (state is None or result.get('state_id_before')!=state_id
                or not runtime.publication_generation_id
                or source.get('league_state_id')!=state_id
                or source.get('publication_generation_id')!=runtime.publication_generation_id
                or horizons.get('side_a_team_id')!=proposal.side_a.team_id
                or horizons.get('side_b_team_id')!=proposal.side_b.team_id):
            raise ValueError('Matching published native-horizon evidence is unavailable')
        focal=result['focal_team_id']
        if focal!=runtime.selected_team_id or focal not in (proposal.side_a.team_id,proposal.side_b.team_id):
            raise ValueError('Native completion does not match the managed team')
        focal_key='side_a' if focal==proposal.side_a.team_id else 'side_b'
        changes=[]
        cut_rows={r['team_id']:r for r in result.get('roster_legality',())}
        for horizon in ('three_year','career'):
            row=horizons.get(horizon) or {}
            adjusted=row.get('roster_adjusted') or {}
            if row.get('status')!='complete' or adjusted.get('proposal_id')!=proposal.proposal_id:
                raise ValueError(f'Complete {horizon} trade and cut evidence is unavailable')
            for key,leg in (('side_a',proposal.side_a),('side_b',proposal.side_b)):
                raw=row.get(key) or {};net=adjusted.get(key) or {}
                if (raw.get('status')!='complete' or net.get('status')!='complete'
                        or net.get('team_id')!=leg.team_id
                        or net.get('scale')!=raw.get('scale')):
                    raise ValueError(f'Complete {horizon} evidence for both teams is required')
                cuts=cut_rows.get(leg.team_id)
                if (cuts is None or cuts.get('status') not in ('resolved','not_required')
                        or sorted(net.get('cut_player_ids',()))!=sorted(c['player_id'] for c in cuts.get('cuts',()))):
                    raise ValueError('Native cut evidence does not match the legal roster resolution')
                scale=net.get('scale') or {}
                prefix=f"raw-shapley:{horizon}:{state_id}:{source.get('input_fingerprint')}"
                releases=sorted({str(p['release_id']) for p in source.get('pick_sources',{}).values() if p.get('release_id')})
                allowed={prefix}
                if releases:
                    allowed.add(prefix+':frozen-prior:'+':'.join(releases))
                if (not source.get('input_fingerprint') or scale.get('scale_id') not in allowed
                        or scale.get('version')!=source.get('contract_version')):
                    raise ValueError('Native horizon scale does not match its source identity')
                bound=NativeHorizonChange(horizon=horizon,scale=net['scale'],delta=net['roster_adjusted_intrinsic_delta'])
                if not isfinite(bound.delta):
                    raise ValueError('Both teams require finite native changes')
                if key==focal_key:changes.append(bound)
        objective=(result.get('objective_assessment') or {}).get(focal_key) or {}
        context=objective.get('context') or {}
        if context.get('team_id')!=focal or not context.get('objectives'):
            raise ValueError('Complete matching priority evidence is required')
        material=BilateralMaterialAssessment.model_validate(result['material_assessment'])
        if material.proposal_id!=proposal.proposal_id or result['disposition'].get('proposal_id')!=proposal.proposal_id:
            raise ValueError('Final Decision does not match the proposal')
        side=material.side_a if material.side_a.team_id==focal else material.side_b
        package=PackageEconomicAssessment.model_validate(result['package_economics']) if result.get('package_economics') else None
        if package is not None and package.proposal_id!=proposal.proposal_id:
            raise ValueError('Package evidence does not match the proposal')
        completed=complete_native_trade_decision(TradeDecisionDisposition.model_validate(result['disposition']),
            material_side=side,native_changes=tuple(changes),objectives=tuple(context['objectives']),
            strategy=objective.get('transaction_strategy') or {},package_economics=package)
    except (ValueError,KeyError,TypeError) as exc:
        reason=str(exc)
    if reason is not None:
        disposition=deepcopy(result['disposition'])
        disposition['disposition']='insufficient_evidence'
        evidence=disposition.setdefault('evidence',{})
        evidence['unavailable_metrics']=tuple(dict.fromkeys((
            *(x for x in evidence.get('unavailable_metrics',()) if x!='intrinsic_value'),missing_code)))
        dimensions=deepcopy(result.get('decision_dimensions') or {})
        confidence=dimensions.setdefault('confidence',{})
        missing=tuple(dict.fromkeys((*confidence.get('missing_dimensions',()),missing_code)))
        confidence.update(missing_dimensions=missing,evidence_completeness='partial')
        dimensions['long_term_franchise_value']={'available':False,'status':'unavailable','reason':reason}
        return {**result,'disposition':disposition,'decision_dimensions':dimensions,
            'availability':{**result.get('availability',{}),'final_trade_disposition':False},
            'decision_completeness':{**result.get('decision_completeness',{}),
                'status':'simulation_backed_incomplete','final_disposition_available':False,
                'missing_authorities':missing},
            'native_completion':{'status':'unavailable','reason':reason}}
    output={**result,'disposition':completed.model_dump(mode='json'),
        'authority':{**result.get('authority',{}),'final_native_decision':'NEXT-5 material Current/Market and separate native-horizon strategic review'},
        'native_completion':{'status':'complete','policy_version':completed.model_version,
            'assessment_basis':'material_current_and_market_plus_separate_directional_native_horizons'}}
    dimensions=deepcopy(result.get('decision_dimensions') or {})
    dimensions['long_term_franchise_value']={'available':True,'status':'complete',
        'concept':'separate_native_asset_contribution_horizons','authority':'NEXT-3 Value / NEXT-5 cut accounting',
        'horizons':{n.horizon:n.model_dump(mode='json') for n in changes},
        'net_delta':None,'scale':None,'combined_value':None,
        'native_materiality_status':'directional_only_not_calibrated'}
    confidence=dimensions.setdefault('confidence',{})
    missing=tuple(x for x in confidence.get('missing_dimensions',()) if x!='long_term_franchise_value')
    missing=tuple(dict.fromkeys((*missing,*completed.evidence.unavailable_metrics)))
    confidence.update(missing_dimensions=missing,evidence_completeness='complete' if not missing else 'partial')
    ready=not missing and completed.disposition.value!='insufficient_evidence'
    output['decision_dimensions']=dimensions
    output['decision_completeness']={**result.get('decision_completeness',{}),
        'status':'complete_native_horizon_review' if ready else 'simulation_backed_incomplete',
        'final_disposition_available':ready,'decision_scope':'native_horizon_strategic_trade_review',
        'missing_authorities':missing}
    output['availability']={**result.get('availability',{}),'final_trade_disposition':ready}
    return output

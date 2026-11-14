from datetime import timedelta
from unittest.mock import patch

import pytest

from fsffl.state.models import PickAsset, PlayerAsset
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
from fsffl.trade_decision.native_pick_research_binding import (
    BASIS, ResearchEconomicContext, ResearchPlayerPublication, ResearchPickAttachment,
    ResearchCompatibilityAssessment, prepare_research_mixed_read, bind_research_trade, scoring_signature,
)
from fsffl.value.career_tail import lineup_capacity_signature
from fsffl.value.models import ValueScale
from fsffl.value.native_pick_curve_releases import freeze_native_pick_research_curve, fingerprint
from tests.test_native_pick_curve_releases import release
from tests.test_native_pick_research import evidence, NOW
from tests.test_trade_decision_scenario import _state


def fixture(*, horizon='three_year', mode='frozen_prior_approximation', game='live-game'):
    state=_state().model_copy(update={'as_of':NOW})
    scope=dict(evaluation_season=2026,team_count=2,rules_signature=lineup_capacity_signature(state.league.rules),
        scoring_signature=scoring_signature(state),economic_scope_id='shared-eligible-universe',native_coordinate_id='native-coordinate')
    source=evidence(team_count=2,rules_signature=scope['rules_signature'],scoring_signature=scope['scoring_signature'],
        original_team_id='A',slot_evidence=evidence().slot_evidence.model_copy(update={'original_team_id':'A'}))
    curve=freeze_native_pick_research_curve(source,release(**scope))
    context=ResearchEconomicContext(**scope,horizon=horizon,horizon_basis=BASIS[horizon],
        point_basis='expected_mean',allocation_basis='joint_game',current_season_basis='governed_full_season',
        eligibility_policy_id='rookie-and-eligible-veteran-test-policy',population_policy_id='live-policy',
        model_policy_id='player-model-v1',game_fingerprint=game)
    prior=context.model_copy(update={'population_policy_id':'prior-policy','model_policy_id':'prior-model-v1',
        'game_fingerprint':'prior-game'})
    pub=ResearchPlayerPublication(user_id='u',league_id=state.league.league_id,state_id=state.state_id,
        generation_id='g1',as_of=NOW,context=context,source_fingerprint='player-source',
        source_scale=ValueScale(scale_id='raw-shapley:'+horizon+':source',version='1',unit_label='raw points'),
        values=(('p1',100.),('p2',200.)))
    attachment=ResearchPickAttachment(pick_id=state.draft_picks[0].pick_id,state_id=state.state_id,as_of=NOW,
        availability='available',inventory_evidence_ref='synthetic-state-inventory',curve=curve,prior_context=prior,
        probabilities=source.slot_evidence,probability_source_state_id=state.state_id,probability_as_of=NOW,
        probability_round=1)
    assessment=ResearchCompatibilityAssessment(curve_id=curve.curve_id,prior_context_fingerprint=fingerprint(prior.model_dump(mode='json')),
        live_policy_key=context.policy_key,horizon=horizon,mode=mode,reviewed_at=NOW,
        evidence_refs=('synthetic-research-assessment-not-production-approval',))
    proposal=BilateralTradeProposal(proposal_id='mixed',as_of=NOW,
        side_a=TradeLeg(team_id='A',sends=(PickAsset(pick_id=attachment.pick_id),)),
        side_b=TradeLeg(team_id='B',sends=(PlayerAsset(player_id='p2'),)))
    return state,pub,attachment,assessment,proposal


def prepare(state,pub,attachment,assessment):
    return prepare_research_mixed_read(state,user_id='u',generation_id='g1',players=pub,picks=(attachment,),
        assessments=(assessment,) if assessment else ())


def bind(state,proposal,read,**changes):
    return bind_research_trade(state,proposal,read,**dict(user_id='u',generation_id='g1',**changes))


def test_qualified_frozen_prior_uses_existing_mean_arithmetic_only_in_separate_research_scale():
    state,pub,attachment,assessment,proposal=fixture()
    before=pub.model_dump(mode='json'),attachment.model_dump(mode='json'),state.model_dump(mode='json')
    read=prepare(state,pub,attachment,assessment);result=bind(state,proposal,read)
    assert result['net']['side_a']['intrinsic']['mean_delta']==pytest.approx(200-142.8)
    assert result['net']['side_b']['intrinsic']['mean_delta']==pytest.approx(142.8-200)
    assert result['pick_qualifications'][0]['mode']=='frozen_prior_approximation'
    assert result['production_eligible'] is result['live_ledger_eligible'] is False
    assert result['package_uncertainty'] is None and result['roster_adjusted'] is None
    assert read.scale.scale_id.startswith('research-mixed-native:') and read.scale!=pub.source_scale
    assert before==(pub.model_dump(mode='json'),attachment.model_dump(mode='json'),state.model_dump(mode='json'))
    with pytest.raises(TypeError):read.provenance['context']['native_coordinate_id']='changed'


def test_without_assessment_same_units_cannot_complete_a_mixed_package():
    state,pub,a,_,proposal=fixture();result=bind(state,proposal,prepare(state,pub,a,None))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None
    assert result['pick_qualifications'][0]['reason']=='compatibility_assessment_missing_or_ambiguous'


def test_exact_game_assessment_cannot_be_reused_when_live_game_changes():
    state,pub,a,r,proposal=fixture(mode='shared_game',game='prior-game')
    read=prepare(state,pub,a,r)
    assert bind(state,proposal,read)['net']['side_a']['intrinsic']['mean_delta'] is not None
    changed=pub.model_copy(update={'context':pub.context.model_copy(update={'game_fingerprint':'new-game'})})
    result=bind(state,proposal,prepare(state,changed,a,r))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None
    assert result['pick_qualifications'][0]['reason']=='shared_game_not_established'


def test_approximation_assessment_scopes_to_policy_not_live_forecast_values():
    state,pub,a,r,proposal=fixture();curve_id=a.curve.curve_id
    newer=NOW+timedelta(days=1)
    state=state.model_copy(update={'as_of':newer})
    changed=pub.model_copy(update={'context':pub.context.model_copy(update={'game_fingerprint':'new-game'}),
        'source_fingerprint':'new-player-source','values':(('p1',100.),('p2',250.)),
        'state_id':state.state_id,'as_of':newer,'generation_id':'g2'})
    a=a.model_copy(update={'state_id':state.state_id,'as_of':newer,'probability_source_state_id':state.state_id,
        'probability_as_of':newer})
    proposal=proposal.model_copy(update={'as_of':newer})
    def evaluate(source):
        read=prepare_research_mixed_read(state,user_id='u',generation_id='g2',players=source,picks=(a,),assessments=(r,))
        return bind_research_trade(state,proposal,read,user_id='u',generation_id='g2')
    result=evaluate(changed)
    assert result['net']['side_a']['intrinsic']['mean_delta']==pytest.approx(250-142.8)
    assert a.curve.curve_id==curve_id
    wrong=changed.model_copy(update={'context':changed.context.model_copy(update={'model_policy_id':'new-method'})})
    assert evaluate(wrong)['net']['side_a']['intrinsic']['mean_delta'] is None


@pytest.mark.parametrize('field',['user_id','league_id','state_id','generation_id','as_of'])
def test_request_scope_must_match_before_projection(field):
    state,pub,a,r,_=fixture()
    wrong=pub.model_copy(update={field:NOW+timedelta(days=1) if field=='as_of' else 'wrong'})
    with pytest.raises(ValueError,match='current request'):prepare(state,wrong,a,r)


@pytest.mark.parametrize('change',[{'probability_source_state_id':'old'},{'probability_round':2},
    {'probability_as_of':NOW+timedelta(days=1)}])
def test_probability_state_round_and_cutoff_are_not_borrowed(change):
    state,pub,a,r,proposal=fixture();wrong=a.model_copy(update=change)
    result=bind(state,proposal,prepare(state,pub,wrong,r))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None


def test_market_source_cannot_be_relabelled_raw_native():
    state,pub,a,r,_=fixture()
    source={**pub.model_dump(),'source_scale':ValueScale(scale_id='market',version='1',unit_label='market')}
    with pytest.raises(ValueError,match='native raw'):ResearchPlayerPublication(**source)


def test_exercised_or_unknown_rights_never_become_a_zero_valued_pick():
    for status in ('exercised','expired','unknown'):
        state,pub,a,r,proposal=fixture();a=a.model_copy(update={'availability':status})
        result=bind(state,proposal,prepare(state,pub,a,r))
        assert result['net']['side_a']['intrinsic']['mean_delta'] is None
        assert result['pick_qualifications'][0]['reason']=='selection_right_'+status


def test_calendar_zero_needs_no_curve_probabilities_or_model_but_never_implies_zero_career():
    state,pub,a,_,proposal=fixture()
    pick=state.draft_picks[0].model_copy(update={'season':2030})
    state=state.model_copy(update={'draft_picks':(pick,*state.draft_picks[1:])})
    pub=pub.model_copy(update={'state_id':state.state_id})
    a=a.model_copy(update={'state_id':state.state_id,'curve':None,'prior_context':None,'probabilities':None})
    result=bind(state,proposal,prepare(state,pub,a,None))
    assert result['net']['side_a']['intrinsic']['sent_mean']==0
    assert result['pick_qualifications'][0]['mode']=='calendar_structural_zero'
    career=pub.model_copy(update={'context':pub.context.model_copy(update={'horizon':'career','horizon_basis':BASIS['career']})})
    assert bind(state,proposal,prepare(state,career,a,None))['net']['side_a']['intrinsic']['mean_delta'] is None


def test_repeated_packages_do_not_remix_refit_fetch_or_retain_source_curves():
    state,pub,a,r,proposal=fixture()
    import fsffl.trade_decision.native_pick_research_binding as module
    with patch.object(module,'apply_frozen_native_pick_curve',wraps=module.apply_frozen_native_pick_curve) as mix:
        read=prepare(state,pub,a,r)
        with patch('fsffl.value.native_pick_curve_releases.native_slot_research_distribution',side_effect=AssertionError('refit')):
            for _ in range(100):bind(state,proposal,read)
        assert mix.call_count==1
    assert 'slots' not in str(read.provenance)


def test_ownership_and_new_snapshot_fences_survive_research_binding():
    state,pub,a,r,proposal=fixture();read=prepare(state,pub,a,r)
    wrong=proposal.model_copy(update={'side_a':TradeLeg(team_id='B',sends=proposal.side_a.sends),
        'side_b':TradeLeg(team_id='A',sends=(PlayerAsset(player_id='p1'),))})
    with pytest.raises(ValueError,match='does not own'):bind(state,wrong,read)
    with pytest.raises(ValueError,match='current request'):bind(state.model_copy(),proposal,read)


def test_accepted_reference_append_policy_is_qualified_comparison_not_joint_game():
    state,pub,a,r,proposal=fixture()
    context=pub.context.model_copy(update={'allocation_basis':'frozen_reference_append','game_fingerprint':None})
    pub=pub.model_copy(update={'context':context})
    r=r.model_copy(update={'live_policy_key':context.policy_key})
    result=bind(state,proposal,prepare(state,pub,a,r))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is not None
    assert result['pick_qualifications'][0]['mode']=='frozen_prior_approximation'
    exact=r.model_copy(update={'mode':'shared_game'})
    assert bind(state,proposal,prepare(state,pub,a,exact))['net']['side_a']['intrinsic']['mean_delta'] is None


def test_career_reference_cannot_be_mislabeled_a_probabilistic_mean():
    state,pub,a,r,proposal=fixture(horizon='career')
    pub=pub.model_copy(update={'context':pub.context.model_copy(update={'point_basis':'model_reference',
        'allocation_basis':'frozen_reference_append','game_fingerprint':None})})
    r=r.model_copy(update={'live_policy_key':pub.context.policy_key})
    result=bind(state,proposal,prepare(state,pub,a,r))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None
    assert result['pick_qualifications'][0]['reason']=='economic_semantics_mismatch'


def test_unknown_curve_version_origin_and_future_evidence_are_local_missingness():
    state,pub,a,r,proposal=fixture()
    wrong=a.model_copy(update={'probabilities':a.probabilities.model_copy(update={'original_team_id':'B'})})
    result=bind(state,proposal,prepare(state,pub,wrong,r))
    assert result['pick_qualifications'][0]['reason']=='curve_application_rejected'
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None


def test_mandatory_cut_cost_uses_existing_signed_native_accounting():
    from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution, MandatoryRosterCut, RosterLegalityStatus
    state,pub,a,r,proposal=fixture()
    pub=pub.model_copy(update={'values':(('p1',-5.),('p2',200.))})
    resolutions=(TeamRosterLegalityResolution(team_id='A',active_roster_before_resolution=2,roster_limit=1,
        required_cut_count=1,cuts=(MandatoryRosterCut(player_id='p1'),),status=RosterLegalityStatus.RESOLVED),
        TeamRosterLegalityResolution(team_id='B',active_roster_before_resolution=0,roster_limit=1,
        required_cut_count=0,status=RosterLegalityStatus.NOT_REQUIRED))
    result=bind_research_trade(state,proposal,prepare(state,pub,a,r),user_id='u',generation_id='g1',
        roster_resolutions=resolutions)
    adjusted=result['roster_adjusted']['side_a']
    assert adjusted['mandatory_cut_intrinsic_cost']==-5
    assert adjusted['roster_adjusted_intrinsic_delta']==pytest.approx(200-142.8+5)


def test_assessment_does_not_automatically_cover_a_different_release():
    state,pub,a,r,proposal=fixture()
    release=a.curve.release.model_copy(update={'stage':'correction','supersedes_curve_id':a.curve.curve_id,
        'correction_reason':'synthetic corrected source'})
    a=a.model_copy(update={'curve':a.curve.model_copy(update={'release':release})})
    result=bind(state,proposal,prepare(state,pub,a,r))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None


def test_career_reference_authorities_bind_without_fake_forecast_variance():
    from tests.test_native_pick_reference_research import curve as reference_curve
    state,pub,a,r,proposal=fixture(horizon='career')
    base=reference_curve()
    c=base.model_copy(update={'release':a.curve.release})
    context=pub.context.model_copy(update={'point_basis':'model_reference','allocation_basis':'frozen_reference_append',
        'game_fingerprint':None})
    prior=a.prior_context.model_copy(update={'point_basis':'model_reference','allocation_basis':'estimated_prior',
        'game_fingerprint':None})
    pub=pub.model_copy(update={'context':context})
    a=a.model_copy(update={'curve':c,'prior_context':prior})
    r=r.model_copy(update={'curve_id':c.curve_id,'prior_context_fingerprint':fingerprint(prior.model_dump(mode='json')),
        'live_policy_key':context.policy_key})
    result=bind(state,proposal,prepare(state,pub,a,r))
    assert result['net']['side_a']['intrinsic']['mean_delta']==170
    assert result['pick_qualifications'][0]['source_authority']['reference_center']==30
    assert result['pick_qualifications'][0]['source_authority']['low']==10
    assert result['pick_qualifications'][0]['point_basis']=='model_reference'
    assert result['package_uncertainty'] is None and result['production_eligible'] is False


def test_within_year_basis_mismatch_is_not_hidden_by_matching_horizon_name():
    state,pub,a,r,proposal=fixture()
    a=a.model_copy(update={'prior_context':a.prior_context.model_copy(update={'current_season_basis':'remaining_from_cutoff'})})
    result=bind(state,proposal,prepare(state,pub,a,r))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None


def test_owner_transfer_rebinds_existing_prior_while_probabilities_follow_original_team():
    from fsffl.state.models import PickOwnership
    state,pub,a,r,_=fixture();curve_id=a.curve.curve_id
    state=state.model_copy(update={'pick_ownership':tuple(PickOwnership(pick_id=o.pick_id,
        owner_team_id='B' if o.pick_id==a.pick_id else o.owner_team_id) for o in state.pick_ownership)})
    pub=pub.model_copy(update={'state_id':state.state_id,'generation_id':'g2'})
    a=a.model_copy(update={'state_id':state.state_id,'probability_source_state_id':state.state_id})
    read=prepare_research_mixed_read(state,user_id='u',generation_id='g2',players=pub,picks=(a,),assessments=(r,))
    proposal=BilateralTradeProposal(proposal_id='transfer',as_of=NOW,
        side_a=TradeLeg(team_id='A',sends=(PlayerAsset(player_id='p1'),)),
        side_b=TradeLeg(team_id='B',sends=(PickAsset(pick_id=a.pick_id),)))
    result=bind_research_trade(state,proposal,read,user_id='u',generation_id='g2')
    assert result['net']['side_a']['intrinsic']['mean_delta']==pytest.approx(142.8-100)
    assert a.curve.curve_id==curve_id and a.probabilities.original_team_id=='A'


def test_missing_pick_context_does_not_disable_unrelated_player_packages():
    state,pub,a,_,_=fixture();a=a.model_copy(update={'curve':None,'prior_context':None})
    read=prepare(state,pub,a,None)
    proposal=BilateralTradeProposal(proposal_id='players',as_of=NOW,
        side_a=TradeLeg(team_id='A',sends=(PlayerAsset(player_id='p1'),)),
        side_b=TradeLeg(team_id='B',sends=(PlayerAsset(player_id='p2'),)))
    result=bind(state,proposal,read)
    assert result['net']['side_a']['intrinsic']['mean_delta']==100
    assert result['pick_qualifications']==[]


def test_missing_mandatory_cut_value_withholds_only_adjusted_total():
    from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution, MandatoryRosterCut, RosterLegalityStatus
    state,pub,a,r,proposal=fixture();pub=pub.model_copy(update={'values':(('p1',None),('p2',200.))})
    cuts=(TeamRosterLegalityResolution(team_id='A',active_roster_before_resolution=2,roster_limit=1,
        required_cut_count=1,cuts=(MandatoryRosterCut(player_id='p1'),),status=RosterLegalityStatus.RESOLVED),
        TeamRosterLegalityResolution(team_id='B',active_roster_before_resolution=0,roster_limit=1,
        required_cut_count=0,status=RosterLegalityStatus.NOT_REQUIRED))
    result=bind_research_trade(state,proposal,prepare(state,pub,a,r),user_id='u',generation_id='g1',roster_resolutions=cuts)
    assert result['net']['side_a']['intrinsic']['mean_delta'] is not None
    assert result['roster_adjusted']['side_a']['roster_adjusted_intrinsic_delta'] is None


def test_annual_rollover_never_silently_reuses_an_old_three_year_window():
    state,pub,a,r,proposal=fixture()
    state=state.model_copy(update={'league':state.league.model_copy(update={'season':2027})})
    context=pub.context.model_copy(update={'evaluation_season':2027})
    pub=pub.model_copy(update={'state_id':state.state_id,'context':context})
    a=a.model_copy(update={'state_id':state.state_id,'probability_source_state_id':state.state_id})
    r=r.model_copy(update={'live_policy_key':context.policy_key})
    result=bind(state,proposal,prepare(state,pub,a,r))
    assert result['net']['side_a']['intrinsic']['mean_delta'] is None
    assert result['pick_qualifications'][0]['reason']=='economic_semantics_mismatch'


def test_state_fingerprint_is_computed_once_per_projection_and_never_per_package():
    from fsffl.state.models import LeagueState
    state,pub,a,r,proposal=fixture();original=LeagueState.state_id.fget;calls=[]
    def measured(snapshot):
        calls.append(1)
        return original(snapshot)
    with patch.object(LeagueState,'state_id',property(measured)):
        read=prepare(state,pub,a,r)
        for _ in range(20):bind(state,proposal,read)
    assert len(calls)==1


def test_changed_lineup_capacity_cannot_reuse_a_different_format_context():
    from fsffl.state.models import LeagueRules, LineupRequirement, RosterSlot
    state,pub,a,r,_=fixture()
    rules=LeagueRules(team_count=2,roster_size=3,lineup=(LineupRequirement(slot=RosterSlot.SUPERFLEX,count=1),),scoring=())
    state=state.model_copy(update={'league':state.league.model_copy(update={'rules':rules})})
    pub=pub.model_copy(update={'state_id':state.state_id})
    a=a.model_copy(update={'state_id':state.state_id,'probability_source_state_id':state.state_id})
    with pytest.raises(ValueError,match='rules/season'):prepare(state,pub,a,r)


def test_source_assumptions_and_scoring_limitations_survive_projection():
    state,pub,a,r,proposal=fixture()
    pub=pub.model_copy(update={'input_assumptions':(('p1','unrelated source assumption'),('p2','source-specific Year1 assumption')),
        'source_limitations':('accepted scoring-coordinate limitation',)})
    a=a.model_copy(update={'source_qualifications':('explicit synthetic prior limitation',)})
    result=bind(state,proposal,prepare(state,pub,a,r))
    assert result['source']['input_assumptions']=={'p2':'source-specific Year1 assumption'}
    assert result['source']['source_limitations']==['accepted scoring-coordinate limitation']
    assert result['source']['picks'][0]['source_qualifications']==['explicit synthetic prior limitation']


@pytest.mark.parametrize('assumptions',[(('p1','first'),('p1','second')),(('','source assumption'),),(('p1',''),)])
def test_publication_assumptions_cannot_silently_overwrite_or_be_blank(assumptions):
    state,pub,attachment,assessment,proposal=fixture()
    with pytest.raises(ValueError,match='assumption'):
        ResearchPlayerPublication.model_validate({**pub.model_dump(),'input_assumptions':assumptions})

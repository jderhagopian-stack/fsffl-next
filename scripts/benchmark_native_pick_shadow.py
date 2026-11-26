"""Bounded synthetic integration benchmark, never a hosted-performance claim.

370 players/108 picks in two 12-team formats. All values and probability masses
are explicitly synthetic; uniform masses here are NOT a runtime fallback.
Run from the checkout with PYTHONPATH=src:.; output contains no private inputs.
"""
from datetime import datetime, timezone
import json
import resource
from time import perf_counter
from unittest.mock import patch

from fsffl.state.models import (
    LeagueState, League, LeagueRules, LineupRequirement, RosterSlot, Team, TeamState,
    Player, Position, PlayerState, Provenance, RosterEntry, DraftPick, PickOwnership, PickAsset, PlayerAsset,
)
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
from fsffl.trade_decision import native_pick_research_binding as module
from fsffl.value.native_pick_curve_releases import NativePickCurveRelease, freeze_native_pick_research_curve, fingerprint
from fsffl.value.native_pick_reference_research import FrozenNativePickReferenceCurve, FrozenCareerReferenceSlot
from fsffl.value.native_pick_research import NativePickResearchEvidence
from fsffl.value.career_forward_intrinsic import CareerForwardModelAuthority
from fsffl.value.career_tail import lineup_capacity_signature
from fsffl.value.models import ValueScale
from fsffl.value.origin_aware_pick import OriginPickProbabilityEvidence

NOW=datetime(2026,11,14,tzinfo=timezone.utc)


def run_case(superflex: bool, packages: int = 100):
    start=perf_counter();league_id='synthetic-sf' if superflex else 'synthetic-1qb'
    lineup=[('QB',1),('RB',2),('WR',3),('TE',1),('FLEX',1)]+([('SUPERFLEX',1)] if superflex else [])
    rules=LeagueRules(team_count=12,roster_size=24,rookie_draft_rounds=3,
        lineup=tuple(LineupRequirement(slot=RosterSlot(s),count=n) for s,n in lineup),scoring=())
    teams=tuple(Team(team_id=f't{i}',league_id=league_id,display_name=f'Synthetic {i}') for i in range(12))
    players=tuple(Player(player_id=f'p{i}',full_name=f'Synthetic {i}',position=Position(('QB','RB','WR','TE')[i%4])) for i in range(370))
    provenance=Provenance(source='synthetic-benchmark',retrieved_at=NOW,effective_at=NOW)
    picks=tuple(DraftPick(pick_id=f'pick-{y}-{r}-{i}',league_id=league_id,season=y,round=r,original_team_id=f't{i}')
        for y in (2027,2028,2029) for r in (1,2,3) for i in range(12))
    state=LeagueState(league=League(league_id=league_id,name='Synthetic benchmark',season=2026,rules=rules),as_of=NOW,
        teams=teams,team_states=tuple(TeamState(team_id=f't{i}',roster=tuple(RosterEntry(player_id=f'p{24*i+j}',slot=RosterSlot.BENCH) for j in range(24))) for i in range(12)),
        players=players,player_states=tuple(PlayerState(player_id=p.player_id,as_of=NOW,provenance=provenance) for p in players),
        draft_picks=picks,pick_ownership=tuple(PickOwnership(pick_id=p.pick_id,owner_team_id=p.original_team_id) for p in picks))
    scope=dict(evaluation_season=2026,team_count=12,rules_signature=lineup_capacity_signature(rules),
        scoring_signature=module.scoring_signature(state),economic_scope_id='shared-synthetic',native_coordinate_id='synthetic-native')
    curves={};references={}
    def probabilities(pick):
        return OriginPickProbabilityEvidence(draft_season=pick.season,original_team_id=pick.original_team_id,
            slot_probabilities=tuple(dict(slot_in_round=i,probability=1/12) for i in range(1,13)),
            expected_slot=6.5,median_slot=6,early_probability=1/3,mid_probability=1/3,late_probability=1/3,
            simulation_count=100,simulation_model_version='synthetic',simulation_input_fingerprint='synthetic-slot-fp-'+pick.original_team_id,
            draft_order_policy_id='synthetic',draft_order_policy_version='1',draft_order_policy_authority='explicit_league_rule',
            draft_order_projection_model_version='synthetic',provenance='explicit synthetic input, not a fallback')
    for year in (2027,2028,2029):
        for rnd in (1,2,3):
            p=next(p for p in picks if p.season==year and p.round==rnd)
            release=NativePickCurveRelease(**scope,draft_season=year,round=rnd,stage='annual_baseline',released_at=NOW,event_evidence_refs=('synthetic-release',))
            evidence=NativePickResearchEvidence(**{k:v for k,v in scope.items() if k!='economic_scope_id'},pick_id=p.pick_id,
                original_team_id=p.original_team_id,owner_team_id=p.original_team_id,draft_season=year,round=rnd,
                evidence_as_of=NOW,forecast_model_version='synthetic',source_fingerprints=('synthetic',),slot_evidence=probabilities(p),
                slot_forecasts=tuple(dict(slot_in_round=s,scenarios=(dict(probability=1,
                    annual=tuple(dict(season=year+i,raw_shapley=100/(rnd+s+i)) for i in range(3)),
                    terminal_start_season=year+3,terminal_raw_shapley=10),)) for s in range(1,13)))
            curves[year,rnd]=freeze_native_pick_research_curve(evidence,release)
            references[year,rnd]=FrozenNativePickReferenceCurve(release=release,source_as_of=NOW,
                source_fingerprints=('synthetic-reference',),forecast_model_version='synthetic',authority_basis_model_versions=('synthetic-family',),
                slots=tuple(FrozenCareerReferenceSlot(slot_in_round=s,authority=CareerForwardModelAuthority(
                    low=50/(rnd+s),reference_center=100/(rnd+s),high=150/(rnd+s),width=100/(rnd+s))) for s in range(1,13)))
    generation_seconds=perf_counter()-start;outputs=[]
    for horizon in ('three_year','career'):
        context=module.ResearchEconomicContext(**scope,horizon=horizon,horizon_basis=module.BASIS[horizon],
            current_season_basis='governed_full_season',point_basis='expected_mean' if horizon=='three_year' else 'model_reference',
            allocation_basis='frozen_reference_append',eligibility_policy_id='synthetic',population_policy_id='reference-append',model_policy_id='synthetic-player')
        prior=context.model_copy(update={'allocation_basis':'estimated_prior','population_policy_id':'synthetic-prior','model_policy_id':'synthetic-pick'})
        pub=module.ResearchPlayerPublication(user_id='synthetic-user',league_id=league_id,state_id=state.state_id,generation_id='g',as_of=NOW,
            context=context,source_fingerprint='synthetic-source',source_scale=ValueScale(scale_id='raw-shapley:'+horizon,version='1',unit_label='synthetic native'),
            values=tuple((p.player_id,float(100+i)) for i,p in enumerate(players)))
        attachments=[];assessments=[]
        for (year,rnd),curve in (curves if horizon=='three_year' else references).items():
            assessments.append(module.ResearchCompatibilityAssessment(curve_id=curve.curve_id,
                prior_context_fingerprint=fingerprint(prior.model_dump(mode='json')),live_policy_key=context.policy_key,horizon=horizon,
                mode='frozen_prior_approximation',reviewed_at=NOW,evidence_refs=('synthetic-research-only',)))
        for p in picks:
            curve=(curves if horizon=='three_year' else references)[p.season,p.round]
            attachments.append(module.ResearchPickAttachment(pick_id=p.pick_id,state_id=state.state_id,as_of=NOW,availability='available',
                inventory_evidence_ref='synthetic-inventory',curve=curve,prior_context=prior,probabilities=probabilities(p),
                probability_source_state_id=state.state_id,probability_as_of=NOW,probability_round=p.round))
        prep_start=perf_counter()
        with patch('fsffl.value.native_pick_curve_releases.native_slot_research_distribution',side_effect=AssertionError('unexpected refit')):
            read=module.prepare_research_mixed_read(state,user_id='synthetic-user',generation_id='g',players=pub,picks=tuple(attachments),assessments=tuple(assessments))
            prepare_seconds=perf_counter()-prep_start;bind_start=perf_counter();last=None
            with patch.object(module,'apply_frozen_native_pick_curve',side_effect=AssertionError('unexpected mixture during binding')), \
                 patch.object(module,'apply_frozen_native_pick_reference_curve',side_effect=AssertionError('unexpected mixture during binding')):
                for i in range(packages):
                    p=picks[i%len(picks)];sender=p.original_team_id;other='t1' if sender!='t1' else 't0';player='p24' if other=='t1' else 'p0'
                    proposal=BilateralTradeProposal(proposal_id=f'synthetic-{i}',as_of=NOW,
                        side_a=TradeLeg(team_id=sender,sends=(PickAsset(pick_id=p.pick_id),)),
                        side_b=TradeLeg(team_id=other,sends=(PlayerAsset(player_id=player),)))
                    last=module.bind_research_trade(state,proposal,read,user_id='synthetic-user',generation_id='g')
            bind_seconds=perf_counter()-bind_start
        outputs.append(dict(horizon=horizon,prepare_seconds=prepare_seconds,bind_seconds=bind_seconds,packages=packages,
            read_metadata_json_bytes=len(json.dumps(module._thaw(read.provenance)).encode()),
            last_packet_json_bytes=len(json.dumps(last).encode()),bound_profile_count=len(read.profiles),
            model_refits_during_read_or_bind=0,slot_mixtures_during_bind=0,
            independent_player_shape=370,pick_count=108))
    return dict(superflex=superflex,static_fixture_generation_seconds=generation_seconds,results=outputs)


if __name__=='__main__':
    result=dict(evidence_kind='bounded_synthetic_research_binding_not_Render_or_model_accuracy',cases=[run_case(True),run_case(False)],
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    print(json.dumps(result,indent=2))

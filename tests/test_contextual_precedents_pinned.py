"""Recorded exchange coverage, not invented current trade utility or forecasts."""
import os
from collections import Counter
import pytest
from fsffl.behavioral.owner_resume import OwnerTenureAttestation,OwnerTenureBinding
from fsffl.product.historical_owner_delivery import build_historical_owner_delivery
from fsffl.trade_decision.owner_history import describe_owner_package_history
from fsffl.trade_decision.models import BilateralTradeProposal,TradeLeg
from fsffl.state.models import PlayerAsset,PickAsset
from tests.historical_circumstances_fixture import pinned_delivery_inputs


def test_recorded_exchanges_reach_shared_consumer_with_separate_campaign_context():
    root=os.getenv('FSFFL_RESEARCH_CIRCUMSTANCE_SOURCE')
    if not root:pytest.skip('optional disposable source cohort not mounted')
    inputs=pinned_delivery_inputs(root);sources=inputs['lineage'].sources
    tenure=OwnerTenureAttestation(league_family_id=sources[0].season.league_family_id,recorded_at=inputs['source_observed_at'],
        reference='fixture:declared-stable-owner-scope',bindings=tuple(OwnerTenureBinding(
            provider_league_id=s.provider_ref.external_id,season=s.season.season,roster_id=int(b.provider_roster_id),
            owner_id=b.provider_manager_id,source_sha256=s.source_content_sha256) for s in sources for b in s.roster_bindings))
    delivery=build_historical_owner_delivery(**inputs,tenure_attestation=tenure)
    assert len(delivery.cases)==sum(len(p.historical_trade_cases)for p in delivery.profiles)==291
    assert Counter(c.trade_phase for c in delivery.cases)=={'offseason':206,'regular_season':83,'unknown':2}
    assert sum(c.record_context is not None and c.record_context.season!=c.football_season for c in delivery.cases)==208
    matched=0;owners=set();unsupported=0
    for profile in delivery.profiles:
        for case in profile.historical_trade_cases:
            def assets(rows):return tuple(PlayerAsset(player_id=a.asset_ref.removeprefix('sleeper:player:'))if a.kind=='player'
                else PickAsset(pick_id=a.asset_ref)for a in rows if a.kind in ('player','pick'))
            incoming=assets(case.acquired_assets);outgoing=assets(case.disposed_assets)
            if not incoming or not outgoing:unsupported+=1;continue
            proposal=BilateralTradeProposal(proposal_id='recorded-exchange:'+case.case_id,as_of=profile.as_of,
                side_a=TradeLeg(team_id='sender',sends=incoming),side_b=TradeLeg(team_id='owner',sends=outgoing))
            positions={a.asset_ref.removeprefix('sleeper:player:'):a.position for a in (*case.acquired_assets,*case.disposed_assets)
                if a.kind=='player'and a.position}
            row=describe_owner_package_history(proposal,team_id='owner',profile=profile,
                player_positions=positions,source_state_id='recorded-cohort',current_record=None)
            precedents=row['contextual_precedents']
            if precedents:matched+=1;owners.add(profile.owner_id)
            assert all(p['match_type']=='directional'for p in precedents)  # No invented current record.
            assert all(p['case_id']in {c.case_id for c in profile.historical_trade_cases}for p in precedents)
            assert not row['willingness_inferred'] and row['acceptance_probability'] is None
    assert len(owners)==12 and matched>100
    print({'recorded_exchange_hypotheses_with_precedents':matched,'owners_with_precedents':len(owners),
        'unsupported_empty_economic_sides':unsupported,'current_production_trade_utility_claimed':False})

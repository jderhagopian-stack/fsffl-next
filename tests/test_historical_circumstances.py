from dataclasses import replace
from datetime import UTC, datetime, timedelta
import pytest
from fsffl.behavioral.historical_circumstances import build_historical_trade_circumstances
from fsffl.behavioral.context_inputs import context_feature_readiness
from fsffl.providers.sleeper_historical_context import build_sleeper_historical_context
from fsffl.providers.sleeper_historical_circumstances import normalize_legacy_historical_production, normalize_sleeper_historical_results
from fsffl.state.historical_coverage import HistoricalEvidenceReceipt, HistoricalEvidenceKind
from fsffl.state.historical_roster_context import _digest
from tests.historical_archive_context_fixture import declared_archive_context_inputs
from tests.test_historical_cross_season_context import provider_case, OBS
from fsffl.state.historical_season_lineage import build_historical_season_lineage, HistoricalSeasonLink, SeasonLinkProof


def fixture():
    data,source,_,spec = provider_case()
    source = source.model_copy(update={'raw_position_or_slot_codes':tuple(data['league']['roster_positions'])})
    old_season = source.season.model_copy(update={'season':2023,'league_id':'old-league'})
    old = source.model_copy(update={'season':old_season,
        'provider_ref':source.provider_ref.model_copy(update={'external_id':'old-league'}),
        'settings_receipt':source.settings_receipt.model_copy(update={'season':old_season,'evidence_id':'old-settings'})})
    link = HistoricalSeasonLink(previous=old.season,current=source.season,previous_provider_ref=old.provider_ref,
        observed_parent_provider_league_id='old-league',proof=SeasonLinkProof.VERIFIED_ARCHIVE,
        evidence=source.settings_receipt.model_copy(update={'kind':HistoricalEvidenceKind.OWNER_IDENTITY,'evidence_id':'parent'}))
    lineage = build_historical_season_lineage(sources=(old,source),links=(link,))
    result = build_sleeper_historical_context(seasons={source.season:data},lineage=lineage,rookie_drafts=(spec,),
        source_revision='fixture',source_observed_at=OBS)
    coverage = result.trades.rows[0];history = result.roster_histories[0]
    return data,old,source,lineage,coverage,history


def receipt(season,kind,eid,at,available=None):
    return HistoricalEvidenceReceipt(season=season,kind=kind,evidence_id=eid,effective_at=at,
        source='fixture',available_at=available,availability_basis='verified_archive' if available else None)


def production(old,*,season=None,at=datetime(2024,2,1,tzinfo=UTC)):
    season=season or old.season
    rows=[{'season':season.season,'player_id':'player-a','position':'WR','fsffl_points':220.,'games_with_stats':16},
        {'season':season.season,'player_id':'player-b','position':'RB','fsffl_points':0.,'games_with_stats':0}]
    return normalize_legacy_historical_production(rows,receipt=receipt(season,'player_production','actuals',at),
        scoring_rules_sha256='a'*64)


def week(source,n,at,*,scores=(100,90),eid=None):
    rows=[{'roster_id':1,'matchup_id':1,'points':scores[0],'custom_points':None},
        {'roster_id':2,'matchup_id':1,'points':scores[1],'custom_points':None}]
    return normalize_sleeper_historical_results(rows,week=n,source=source,
        receipt=receipt(source.season,'matchups',eid or f'week-{n}',at))


def build(f,**kwargs):
    _,old,source,lineage,coverage,history=f
    return build_historical_trade_circumstances(coverage=coverage,history=history,lineage=lineage,**kwargs)


def test_joins_prior_production_and_pre_action_results_without_inventing_active_context():
    f=fixture();_,old,source,_,coverage,_=f
    cutoff=coverage.request.completed_at
    out=build(f,prior_production=production(old),results=(week(source,1,cutoff-timedelta(days=7)),))
    a,b=out.teams
    assert a.prior_production[0].player_id=='player-a'  # Before the exchange, not incoming player-b.
    assert a.prior_production[0].fantasy_points==220
    assert a.prior_scoring_rules_sha256=='a'*64
    assert b.unknown_prior_production_count==1  # No prior games is unknown quality, not a failed player.
    assert a.records[0].wins==1 and b.records[0].losses==1
    assert a.records[0].weeks==(1,)
    assert out.created_at < out.completed_at and out.completed_at==cutoff
    assert not out.source_availability_verified and not out.eligible_for_owner_model_training
    report=context_feature_readiness(a.partial_model_inputs)
    assert len(report.missing_features)==14  # Seven evidenced numerical inputs; NOT all21.
    assert a.partial_model_inputs.positions[2].rostered_count is None  # Prior WR != current WR.
    assert a.partial_model_inputs.active_roster_size is None
    assert a.partial_model_inputs.owned_pick_count is None


def test_current_season_annual_outcomes_and_future_weeks_cannot_enter_pre_action_context():
    f=fixture();_,old,source,_,coverage,_=f;cutoff=coverage.request.completed_at
    out=build(f,prior_production=production(old,season=source.season),results=(
        week(source,1,cutoff-timedelta(days=1)),week(source,2,cutoff),week(source,3,cutoff+timedelta(days=1))))
    assert out.excluded_evidence_ids==('actuals','week-2','week-3')
    assert out.teams[0].prior_production==()
    assert out.teams[0].records[0].weeks==(1,)
    assert 'prior_production_unavailable' in out.issues


def test_prior_season_results_remain_separate_and_do_not_claim_current_owner_tenure():
    f=fixture();_,old,source,_,coverage,_=f;cutoff=coverage.request.completed_at
    out=build(f,results=(week(old,14,datetime(2023,12,20,tzinfo=UTC),scores=(80,80),eid='prior-week'),
        week(source,1,cutoff-timedelta(days=1))))
    records=out.teams[0].records
    assert [(r.season.season,r.weeks,r.ties)for r in records]==[(2023,(14,),1),(2024,(1,),0)]
    assert not hasattr(out.teams[0],'owner_id')


def test_partial_membership_keeps_results_but_does_not_publish_a_false_roster():
    f=list(fixture());f[4]=replace(f[4],player_membership_context_available=False)
    out=build(f,prior_production=production(f[1]),results=(week(f[2],1,f[4].request.completed_at-timedelta(days=1)),))
    assert out.teams[0].roster_size is None and out.teams[0].prior_production==()
    assert out.teams[0].unknown_prior_production_count is None
    assert out.teams[0].records[0].wins==1
    assert 'pre_completion_membership_unavailable' in out.issues


def test_wrong_source_snapshot_or_rules_cannot_be_joined():
    f=list(fixture())
    bad=f.copy();bad[4]=replace(f[4],roster_snapshot_id='wrong')
    with pytest.raises(ValueError,match='snapshot'):build(bad)
    bad=f.copy();bad[5]=f[5].model_copy(update={'source_sha256':'0'*64})
    with pytest.raises(ValueError,match='source cohort'):build(bad)
    bad=f.copy();bad[5]=f[5].model_copy(update={'raw_roster_slots':('RB',)})
    with pytest.raises(ValueError,match='source cohort'):build(bad)


def test_duplicate_revisions_and_unregistered_seasons_are_rejected():
    f=fixture();_,old,source,_,coverage,_=f
    w=week(source,1,coverage.request.completed_at-timedelta(days=1))
    with pytest.raises(ValueError,match='duplicate historical result week'):build(f,results=(w,w))
    p=production(old)
    unknown=p.receipt.season.model_copy(update={'league_family_id':'another-family'})
    with pytest.raises(ValueError,match='unregistered'):
        build(f,prior_production=replace(p,receipt=p.receipt.model_copy(update={'season':unknown})))


def test_missing_scores_are_not_zero_and_custom_score_overrides_are_respected():
    f=fixture();source=f[2];cutoff=f[4].request.completed_at
    rows=[{'roster_id':1,'matchup_id':1,'points':100,'custom_points':0},
        {'roster_id':2,'matchup_id':1,'points':90}]
    w=normalize_sleeper_historical_results(rows,week=1,source=source,
        receipt=receipt(source.season,'matchups','scores',cutoff-timedelta(days=1)))
    assert w.matchups[0].points_for==0
    assert build(f,results=(w,)).teams[0].records[0].losses==1
    rows[1].pop('points')
    partial=normalize_sleeper_historical_results(rows,week=1,source=source,receipt=w.receipt)
    assert partial.matchups==()
    out=build(f,results=(partial,))
    assert out.teams[0].records==() and 'incomplete_weekly_result' in out.issues


@pytest.mark.parametrize('points',[None,float('nan'),True])
def test_invalid_production_cannot_be_silently_zero_filled(points):
    old=fixture()[1]
    with pytest.raises(ValueError,match='points'):
        normalize_legacy_historical_production([{'season':2023,'player_id':'x','position':'WR',
            'fsffl_points':points,'games_with_stats':1}],receipt=production(old).receipt,scoring_rules_sha256='a'*64)


def test_missing_evidence_stays_unknown_and_does_not_authorize_model_training():
    out=build(fixture())
    assert {'prior_production_unavailable','completed_results_unavailable'}<=set(out.issues)
    assert all(t.unknown_prior_production_count is None for t in out.teams)
    with pytest.raises(ValueError,match='unavailable'):
        context_feature_readiness(out.teams[0].partial_model_inputs).require_complete()
    with pytest.raises(ValueError):
        replace(out,eligible_for_owner_model_training=True)


def test_equal_franchise_ids_in_unlinked_seasons_do_not_authorize_historical_context():
    f=list(fixture())
    f[3]=build_historical_season_lineage(sources=f[3].sources,links=())
    with pytest.raises(ValueError,match='unregistered'):
        build(f,prior_production=production(f[1]))


def test_used_facts_retain_exact_payload_and_historical_scoring_identity():
    f=fixture();p=production(f[1])
    out=build(f,prior_production=p)
    assert out.evidence_source_sha256==((p.receipt.evidence_id,p.source_sha256),)
    assert out.teams[0].prior_scoring_rules_sha256==p.scoring_rules_sha256


def test_source_capture_time_does_not_become_an_earlier_publication_certificate():
    f=fixture();p=production(f[1]);cutoff=f[4].request.completed_at
    p=replace(p,receipt=p.receipt.model_copy(update={'available_at':cutoff+timedelta(days=400),
        'availability_basis':'verified_archive'}))
    out=build(f,prior_production=p)
    assert out.teams[0].prior_production
    assert not out.source_availability_verified and not out.eligible_for_owner_model_training
    future=replace(p,receipt=p.receipt.model_copy(update={'effective_at':cutoff}))
    assert build(f,prior_production=future).teams[0].prior_production==()


def test_unknown_historical_positions_and_string_seasons_are_retained_without_reclassification():
    old=fixture()[1]
    p=normalize_legacy_historical_production([{'season':'2023','player_id':'player-a','position':None,
        'fsffl_points':100,'games_with_stats':10}],receipt=production(old).receipt,scoring_rules_sha256='a'*64)
    assert p.players[0].position is None and p.players[0].fantasy_points==100
    out=build(fixture(),prior_production=p)
    assert out.teams[0].prior_production==()
    assert out.teams[0].unknown_prior_production_count==1


def test_weekly_normalizer_uses_explicit_crosswalk_when_provider_rosters_change():
    f=fixture();old=f[1]
    changed=old.model_copy(update={'roster_bindings':tuple(b.model_copy(update={'provider_roster_id':str(int(b.provider_roster_id)+10)})
        for b in old.roster_bindings)})
    rows=[{'roster_id':11,'matchup_id':1,'points':75},{'roster_id':12,'matchup_id':1,'points':100}]
    w=normalize_sleeper_historical_results(rows,week=1,source=changed,
        receipt=receipt(old.season,'matchups','old-renumbered',datetime(2023,9,15,tzinfo=UTC)))
    assert w.matchups[0].team_id=='franchise-1' and w.matchups[1].team_id=='franchise-2'
    with pytest.raises(ValueError,match='unknown'):
        normalize_sleeper_historical_results(rows,week=1,source=old,receipt=w.receipt)

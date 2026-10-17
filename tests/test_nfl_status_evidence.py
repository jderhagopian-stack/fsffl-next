from datetime import UTC, datetime, timedelta
from dataclasses import replace
from types import SimpleNamespace

import pytest

from fsffl.product.p0_live_candidate_runtime import (
    recorded_status_based_zero_ros_evidence, _status_based_zero_ros,
    _year_one_raw_forecasts,
)
from fsffl.product.dynamic_career_composition import dynamic_career_fingerprint
from fsffl.providers.nfl_status_evidence import SEASON_UNAVAILABILITY_RECEIPTS
from fsffl.state.models import (
    League, LeagueRules, LeagueState, Player, PlayerState, Position, Provenance,
    RosterEntry, ScoringRule, Team, TeamState,
)
from fsffl.forecast.models import ForecastMetric
from fsffl.product.i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING


def _state():
    receipts = SEASON_UNAVAILABILITY_RECEIPTS
    # Synthetic league/teams; only the public receipt player identities are real.
    return LeagueState(
        league=League(league_id='fixture',name='Fixture',season=2026,
            rules=LeagueRules(team_count=2,roster_size=3,lineup=(),scoring=(
                *FROZEN_I1_STANDARD_SCORING,ScoringRule(stat='rec',points=.5),
                ScoringRule(stat='fum_rec',points=2.)))),
        as_of=datetime(2026,10,13,tzinfo=UTC),
        teams=(Team(team_id='a',league_id='fixture',display_name='A'),
               Team(team_id='b',league_id='fixture',display_name='B')),
        team_states=(TeamState(team_id='a',roster=tuple(
            RosterEntry(player_id=row.player_id,slot='BENCH') for row in receipts)),
            TeamState(team_id='b',roster=())),
        players=tuple(Player(player_id=row.player_id,full_name=row.player_name,
                             position=Position.WR) for row in receipts),
        player_states=tuple(PlayerState(player_id=row.player_id,
            as_of=datetime(2026,10,13,tzinfo=UTC),
            provenance=Provenance(source='fixture',
                retrieved_at=datetime(2026,10,13,tzinfo=UTC),
                effective_at=datetime(2026,10,13,tzinfo=UTC))) for row in receipts),
    )


def test_official_receipts_are_not_backdated_into_october_13_state():
    state = _state()
    assert recorded_status_based_zero_ros_evidence(state,as_of=state.as_of) == {}
    capture = SEASON_UNAVAILABILITY_RECEIPTS[0].captured_at
    assert recorded_status_based_zero_ros_evidence(state,as_of=capture-timedelta(microseconds=1)) == {}
    admitted = recorded_status_based_zero_ros_evidence(state,as_of=capture)
    assert set(admitted) == {row.player_id for row in SEASON_UNAVAILABILITY_RECEIPTS}
    for row in SEASON_UNAVAILABILITY_RECEIPTS:
        evidence = admitted[row.player_id]
        assert evidence.observed_at == row.captured_at
        assert evidence.source == row.source_url
        assert row.fingerprint in evidence.source_version
        assert evidence.no_expected_2026_participation
    assert not {'sleeper:player:3321','sleeper:player:4018','sleeper:player:6803'} & admitted.keys()


def test_receipts_are_roster_position_and_season_scoped():
    state = _state()
    capture = SEASON_UNAVAILABILITY_RECEIPTS[0].captured_at
    assert recorded_status_based_zero_ros_evidence(state.model_copy(update={
        'league':state.league.model_copy(update={'season':2027})}),as_of=capture) == {}
    assert recorded_status_based_zero_ros_evidence(state.model_copy(update={'team_states':()}),as_of=capture) == {}
    assert recorded_status_based_zero_ros_evidence(state.model_copy(update={
        'players':tuple(p.model_copy(update={'position':Position.RB}) for p in state.players)}),as_of=capture) == {}
    with pytest.raises(ValueError,match='timezone-aware'):
        recorded_status_based_zero_ros_evidence(state,as_of=capture.replace(tzinfo=None))


def test_admitted_receipt_changes_reuse_key_without_new_provider_polling(monkeypatch):
    state = _state()
    context = SimpleNamespace(league_state=state,forecast_evidence=None)
    capture = SEASON_UNAVAILABILITY_RECEIPTS[0].captured_at
    before = dynamic_career_fingerprint(context,now=capture-timedelta(seconds=1),include_freshness_epoch=False)
    after = dynamic_career_fingerprint(context,now=capture,include_freshness_epoch=False)
    assert before != after
    import fsffl.providers.nfl_status_evidence as provider
    monkeypatch.setattr(provider,'SEASON_UNAVAILABILITY_RECEIPTS',tuple(
        replace(row,source_url=row.source_url+'?revision=2') for row in provider.SEASON_UNAVAILABILITY_RECEIPTS))
    assert dynamic_career_fingerprint(context,now=capture,include_freshness_epoch=False) != after
    assert dynamic_career_fingerprint(context,now=capture-timedelta(seconds=1),include_freshness_epoch=False) == before


def test_verified_zero_ros_retains_actuals_and_rejects_another_season():
    state = _state()
    capture = SEASON_UNAVAILABILITY_RECEIPTS[0].captured_at
    for evidence in recorded_status_based_zero_ros_evidence(state,as_of=capture).values():
        ros = _status_based_zero_ros(league_state=state,evidence=evidence,as_of=capture)
        assert all(row.distribution.mean == 0 for row in ros)
        actual = next(row for row in ros if row.metric == ForecastMetric.REC_YARDS)
        actual = actual.model_copy(update={'distribution':actual.distribution.model_copy(update={'mean':7.})})
        year_one = _year_one_raw_forecasts(league_state=state,completed_actuals=(actual,),ros_forecasts=ros)
        assert next(row for row in year_one if row.metric == ForecastMetric.REC_YARDS).distribution.mean == 7.
        with pytest.raises(ValueError,match='season differs'):
            _status_based_zero_ros(league_state=state.model_copy(update={
                'league':state.league.model_copy(update={'season':2027})}),evidence=evidence,as_of=capture)


def test_whole_season_absence_prevents_phantom_residual_but_keeps_evidence_gates():
    from fsffl.product.p0_live_candidate_runtime import _score_season_points
    state = _state()
    capture = SEASON_UNAVAILABILITY_RECEIPTS[0].captured_at
    evidence = next(iter(recorded_status_based_zero_ros_evidence(state,as_of=capture).values()))
    ros = _status_based_zero_ros(league_state=state,evidence=evidence,as_of=capture)
    raw = _year_one_raw_forecasts(league_state=state,completed_actuals=(),ros_forecasts=ros)
    normal = _score_season_points(raw,league_state=state,standard=False)[0][evidence.player_id]
    assert normal.distribution.mean == .06
    for standard in (False,True):
        scored = _score_season_points(raw,league_state=state,standard=standard,
            nonparticipation_evidence=evidence)[0][evidence.player_id]
        assert scored.distribution.mean == scored.distribution.stddev == 0
        assert evidence.source_version in scored.model_version
    conflicting = (raw[0].model_copy(update={
        'distribution':raw[0].distribution.model_copy(update={'mean':1.})}),*raw[1:])
    with pytest.raises(ValueError,match='conflicts with Year-1 raw evidence'):
        _score_season_points(conflicting,league_state=state,standard=False,
            nonparticipation_evidence=evidence)
    unsupported = state.model_copy(update={'league':state.league.model_copy(update={
        'rules':state.league.rules.model_copy(update={'scoring':(
            *state.league.rules.scoring,ScoringRule(stat='unapproved_stat',points=1.))})})})
    with pytest.raises(ValueError,match='does not support complete'):
        _score_season_points(raw,league_state=unsupported,standard=False,
            nonparticipation_evidence=evidence)


def test_hosted_candidate_default_consumes_receipts_without_overriding_provider_rows(monkeypatch):
    """Fixture transports only; retain the real Year-1 and accepted P0 scorer."""
    from fsffl.product import p0_live_candidate_runtime as runtime
    from fsffl.providers.sleeper_weekly_stats import SleeperNflState

    state = _state()
    state = state.model_copy(update={'player_states':tuple(
        row.model_copy(update={'age_years':23.}) for row in state.player_states)})
    capture = SEASON_UNAVAILABILITY_RECEIPTS[0].captured_at
    nfl = SleeperNflState(season=2026,week=1,season_type='regular',captured_at=capture)
    stats = SimpleNamespace(fetch_nfl_state=lambda:nfl,
        fetch_season=lambda **_:(),fetch_week=lambda **_:())
    snapshot = SimpleNamespace(captured_at=capture,payload={'players':{
        player.player_id.rsplit(':',1)[-1]:{'years_exp':2} for player in state.players}})
    sleeper = SimpleNamespace(fetch_latest=lambda **_:snapshot)
    monkeypatch.setattr(runtime.SleeperSnapshotNormalizer,'normalize_snapshot',lambda *_,**__:state)
    raw = ()
    ros = SimpleNamespace(evaluation_as_of=capture,source_observations=(),raw_ensemble=raw,
        successful_source_ids=('cbs','razzball'),model_copy=lambda **_:SimpleNamespace())
    monkeypatch.setattr(runtime,'build_in_season_forecasts',lambda *_,**__:ros)
    monkeypatch.setattr('fsffl.forecast.in_season_orchestration.build_current_ros_fumbles_lost_supplement_observations',lambda *_,**__:())
    result = runtime.build_live_p0_rostered_candidate_forecasts(
        state,stats_source=stats,sleeper_source=sleeper,evaluation_as_of=capture,
        projection_history_as_of=capture)
    assert not result.failures
    assert result.future is not None
    assert len(result.future.contract.forecasts) == 6
    assert set(result.year_one_league) == {row.player_id for row in SEASON_UNAVAILABILITY_RECEIPTS}
    assert all(row.distribution.mean == 0 for row in result.year_one_league.values())
    assert all(mode.startswith('status_based_zero_ros:out_for_season:official-season-unavailability-v1:')
               for mode in result.year_one_evidence_modes.values())
    assert runtime.valid_live_source_manifest(result.source_manifest)
    original_manifest = result.source_manifest
    player_key = next(iter(snapshot.payload['players']))
    snapshot.payload['players'][player_key]['years_exp'] = 3
    corrected = runtime.build_live_p0_rostered_candidate_forecasts(
        state,stats_source=stats,sleeper_source=sleeper,evaluation_as_of=capture,
        projection_history_as_of=capture)
    assert corrected.source_manifest['fingerprints']['current_catalog'] != original_manifest['fingerprints']['current_catalog']
    assert corrected.source_manifest['fingerprints']['completed_week_stats'] == original_manifest['fingerprints']['completed_week_stats']
    # Existing complete provider authority remains first choice, even when the
    # independently recorded status receipt is present.
    evidence = next(iter(recorded_status_based_zero_ros_evidence(state,as_of=capture).values()))
    raw = _status_based_zero_ros(league_state=state,evidence=evidence,as_of=capture)
    ros.raw_ensemble = raw
    result = runtime.build_live_p0_rostered_candidate_forecasts(
        state,stats_source=stats,sleeper_source=sleeper,evaluation_as_of=capture,
        projection_history_as_of=capture)
    assert result.year_one_evidence_modes[evidence.player_id] == 'two_source'
    assert 'nonzero league points but zero frozen standard' in result.failures[evidence.player_id]
    assert result.future is not None
    assert len(result.future.contract.forecasts) == 4
    assert {row.player_id for row in result.future.contract.forecasts} == set(
        result.year_one_league)-{evidence.player_id}


def test_live_producer_releases_acquisition_payload_before_future_forecast(monkeypatch):
    import weakref
    import fsffl.product.p0_live_candidate_runtime as runtime
    from fsffl.providers.sleeper_weekly_stats import SleeperNflState
    state = _state()
    state = state.model_copy(update={'player_states':tuple(
        row.model_copy(update={'age_years':23.}) for row in state.player_states)})
    capture = SEASON_UNAVAILABILITY_RECEIPTS[0].captured_at
    stats = SimpleNamespace(fetch_nfl_state=lambda:SleeperNflState(
        season=2026,week=1,season_type='regular',captured_at=capture),
        fetch_season=lambda **_:(),fetch_week=lambda **_:())
    class Catalog(dict):
        pass
    references = []
    expected_digests = []
    def prior_stats(**kwargs):
        assert references[-1]() is None, 'whole acquisition catalog still overlaps stat acquisition'
        return ()
    stats.fetch_season = prior_stats
    def acquire(**kwargs):
        catalog = Catalog({player.player_id.rsplit(':',1)[-1]:{'years_exp':2}
                           for player in state.players})
        catalog['unused-public-source-row'] = {'evidence':'included in the full source fingerprint'}
        references.append(weakref.ref(catalog))
        expected_digests.append(runtime._input_digest(catalog))
        return SimpleNamespace(captured_at=capture,payload={'players':catalog})
    monkeypatch.setattr(runtime.SleeperSnapshotNormalizer,'normalize_snapshot',lambda *_,**__:state)
    ros = SimpleNamespace(evaluation_as_of=capture,source_observations=(),raw_ensemble=(),
        successful_source_ids=('cbs','razzball'),model_copy=lambda **_:SimpleNamespace())
    monkeypatch.setattr(runtime,'build_in_season_forecasts',lambda *_,**__:ros)
    monkeypatch.setattr('fsffl.forecast.in_season_orchestration.build_current_ros_fumbles_lost_supplement_observations',lambda *_,**__:())
    accepted = runtime.build_p0_future_forecast_contract
    def forecast(**kwargs):
        assert references[-1]() is None, 'whole acquisition catalog still overlaps future forecasting'
        return accepted(**kwargs)
    monkeypatch.setattr(runtime,'build_p0_future_forecast_contract',forecast)
    result = runtime.build_live_p0_rostered_candidate_forecasts(state,
        stats_source=stats,sleeper_source=SimpleNamespace(fetch_latest=acquire),
        evaluation_as_of=capture,projection_history_as_of=capture)
    assert not result.failures
    assert result.future is not None and len(result.future.contract.forecasts) == 6
    assert result.source_manifest['fingerprints']['current_catalog'] == expected_digests[0]
    assert runtime.valid_live_source_manifest(result.source_manifest)


def test_current_official_role_fences_backup_path_without_inventing_zero_or_backdating():
    from fsffl.providers.nfl_status_evidence import NFL_ROLE_RECEIPTS, recorded_nfl_role_receipts
    from fsffl.product.p0_live_candidate_runtime import _active_backup_player_ids
    receipt = NFL_ROLE_RECEIPTS[0]
    capture = receipt.captured_at
    state = _state().model_copy(update={
        'players': (Player(player_id=receipt.player_id, full_name='Brandon Aiyuk',
                           position=Position.WR, nfl_team='SF'),),
        'player_states': (PlayerState(player_id=receipt.player_id, as_of=capture,
            nfl_team='SF', provenance=Provenance(source='sleeper:current_player_universe',
                retrieved_at=capture, effective_at=capture)),),
        'team_states': (TeamState(team_id='a', roster=(RosterEntry(
            player_id=receipt.player_id, slot='BENCH'),)), TeamState(team_id='b', roster=())),
    })
    catalog = {'6803': {'team': 'SF', 'depth_chart_order': 2}}
    assert recorded_nfl_role_receipts(state, as_of=capture-timedelta(microseconds=1)) == {}
    assert recorded_nfl_role_receipts(state, as_of=capture) == {receipt.player_id: receipt}
    assert not _active_backup_player_ids(state, catalog, current_status_state=state, as_of=capture)
    assert receipt.player_id not in recorded_status_based_zero_ros_evidence(state, as_of=capture)
    assert recorded_nfl_role_receipts(state, as_of=capture+timedelta(hours=6)) == {}
    assert recorded_nfl_role_receipts(state.model_copy(update={'team_states': ()}), as_of=capture) == {}
    context = SimpleNamespace(league_state=state, forecast_evidence=None)
    assert dynamic_career_fingerprint(context, now=capture, include_freshness_epoch=False) != dynamic_career_fingerprint(
        context, now=capture-timedelta(microseconds=1), include_freshness_epoch=False)

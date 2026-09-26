from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from fsffl.forecast.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
    AnnualPreseasonProjectionSnapshot,
)
from fsffl.forecast.current_runtime import LiveForecastRuntimeResult
from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SOURCE,
    FirstPartyFumblesLostEvidenceTier,
    FirstPartyFumblesLostPlayerEvidence,
    FirstPartyFumblesLostSupplement,
)
from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.preseason_baseline import (
    PRESEASON_AUTHORITY_RUNTIME_VERSION,
    PRESEASON_BASELINE_MODEL_VERSION,
    baseline_from_runtime,
    build_runtime_from_preseason_baseline,
    state_is_preseason_capture_eligible,
)
from fsffl.persistence.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
    NFL_SEASON_SCOPE_KIND,
    annual_preseason_projection_snapshot_artifact,
)
from fsffl.persistence.runtime_cache import (
    LEAGUE_SEASON_SCOPE_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    decode_preseason_forecast_baseline,
    preseason_forecast_baseline_artifact,
)
from fsffl.product.forecast_resilience import (
    make_preseason_baseline_authority_loader,
    make_resilient_forecast_loader,
)
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    ScoringRule,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 9, 16, 0, tzinfo=UTC)


def _provenance() -> Provenance:
    return Provenance(source="test", retrieved_at=NOW, effective_at=NOW)


def _state(*, scored: bool = False) -> LeagueState:
    teams = (
        Team(team_id="a", league_id="league-1", display_name="A"),
        Team(team_id="b", league_id="league-1", display_name="B"),
    )
    matchups = (
        LeagueMatchup(
            week=1,
            team_a_id="a",
            team_b_id="b",
            team_a_points=100.0 if scored else None,
            team_b_points=90.0 if scored else None,
            provenance=_provenance(),
        ),
    )
    return LeagueState(
        league=League(
            league_id="league-1",
            name="Test",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(
                    ScoringRule(stat="pass_yd", points=0.04),
                    ScoringRule(stat="pass_td", points=4.0),
                    ScoringRule(stat="pass_int", points=-1.0),
                ),
            ),
        ),
        as_of=NOW,
        teams=teams,
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(
            Player(
                player_id="p1",
                full_name="Fixture Quarterback",
                position=Position.QB,
            ),
        ),
        player_states=(
            PlayerState(
                player_id="p1",
                as_of=NOW,
                provenance=_provenance(),
            ),
        ),
        matchups=matchups,
    )


def _observation(
    *,
    horizon: ForecastHorizon = ForecastHorizon.SEASON,
    metric: ForecastMetric = ForecastMetric.FANTASY_POINTS,
    mean: float = 300.0,
) -> ForecastObservation:
    return ForecastObservation(
        player_id="p1",
        position="QB",
        horizon=horizon,
        metric=metric,
        period_start=NOW + timedelta(days=1),
        period_end=NOW + timedelta(days=120),
        distribution=ForecastDistribution(mean=mean, stddev=20.0),
        source="fsffl:test-ensemble",
        model_version="test",
        as_of=NOW,
        provenance=_provenance(),
    )


def _runtime(*, sources=("fftoday", "razzball"), horizon=ForecastHorizon.SEASON):
    observation = _observation(horizon=horizon)
    return LiveForecastRuntimeResult(
        raw_ensemble=(observation,),
        fantasy_point_forecasts=(observation,),
        coverage=LiveEnsembleCoverage(
            independent_source_ids=tuple(sources),
            excluded_aggregate_source_ids=(),
            active_source_ids=tuple(sources),
            observation_count=1,
            minimum_independent_sources=2,
        ),
        successful_source_ids=tuple(sources),
        failed_sources=(),
        evaluation_as_of=NOW,
    )


def _raw_qb_runtime() -> LiveForecastRuntimeResult:
    observations = (
        _observation(metric=ForecastMetric.PASS_YARDS, mean=4000.0),
        _observation(metric=ForecastMetric.PASS_TD, mean=25.0),
        _observation(metric=ForecastMetric.INTERCEPTIONS, mean=10.0),
    )
    return LiveForecastRuntimeResult(
        raw_ensemble=observations,
        fantasy_point_forecasts=(),
        coverage=LiveEnsembleCoverage(
            independent_source_ids=("fftoday", "razzball"),
            excluded_aggregate_source_ids=(),
            active_source_ids=("fftoday", "razzball"),
            observation_count=6,
            minimum_independent_sources=2,
        ),
        successful_source_ids=("fftoday", "razzball"),
        failed_sources=(),
        evaluation_as_of=NOW,
    )


def _evidence(runtime: LiveForecastRuntimeResult) -> LiveForecastEvidence:
    return LiveForecastEvidence(
        raw_forecasts=runtime.raw_ensemble,
        league_scored_forecasts=runtime.fantasy_point_forecasts,
        successful_source_ids=runtime.successful_source_ids,
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=runtime,
    )


class _Store:
    def __init__(self, record=None, annual_record=None):
        self.record = record
        self.annual_record = annual_record
        self.puts = []

    def get_latest_reusable_artifact(self, **kwargs):
        if kwargs["artifact_kind"] == PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND:
            assert kwargs["scope_kind"] == LEAGUE_SEASON_SCOPE_KIND
            assert kwargs["model_version"] == PRESEASON_BASELINE_MODEL_VERSION
            return self.record
        if kwargs["artifact_kind"] == ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND:
            assert kwargs["scope_kind"] == NFL_SEASON_SCOPE_KIND
            assert kwargs["model_version"] == ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION
            return self.annual_record
        raise AssertionError(f"unexpected artifact lookup: {kwargs}")

    def put_artifact(self, record):
        self.puts.append(record)
        if record.key.artifact_kind == PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND:
            self.record = record
        elif record.key.artifact_kind == ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND:
            self.annual_record = record


def test_preseason_capture_closes_once_scoring_exists():
    assert state_is_preseason_capture_eligible(_state(scored=False))
    assert not state_is_preseason_capture_eligible(_state(scored=True))


def test_baseline_requires_two_sources_and_full_season_horizon():
    state = _state()
    with pytest.raises(ValueError, match="at least 2 independent sources"):
        baseline_from_runtime(state, _runtime(sources=("razzball",)))
    with pytest.raises(ValueError, match="only full-season"):
        baseline_from_runtime(state, _runtime(horizon=ForecastHorizon.WEEK))


def test_baseline_artifact_round_trips_without_changing_authority():
    state = _state()
    baseline = baseline_from_runtime(state, _runtime(), source_artifact_id="94")
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=baseline,
    )
    decoded = decode_preseason_forecast_baseline(dict(record.payload))
    assert decoded == baseline
    assert decoded.successful_source_ids == ("fftoday", "razzball")
    assert decoded.source_artifact_id == "94"


def test_resilient_loader_captures_valid_preseason_live_evidence_once():
    store = _Store()
    runtime = _runtime()
    loader = make_resilient_forecast_loader(store, live_loader=lambda _: _evidence(runtime))

    first = loader(_state())
    second = loader(_state())

    assert first.evidence_basis == "live_full_season"
    assert second.evidence_basis == "live_full_season"
    assert len(store.puts) == 1
    assert decode_preseason_forecast_baseline(dict(store.puts[0].payload)).successful_source_ids == (
        "fftoday",
        "razzball",
    )


def test_resilient_loader_does_not_create_baseline_after_scoring():
    store = _Store()
    runtime = _runtime()
    loader = make_resilient_forecast_loader(store, live_loader=lambda _: _evidence(runtime))

    loader(_state(scored=True))

    assert store.puts == []


def test_resilient_loader_uses_existing_baseline_when_live_full_season_sources_fail(monkeypatch):
    state = _state()
    baseline = baseline_from_runtime(state, _runtime(), source_artifact_id="94")
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=baseline,
    )
    store = _Store(record)
    rebuilt = _runtime()
    monkeypatch.setattr(
        "fsffl.product.forecast_resilience.build_runtime_from_preseason_baseline",
        lambda *_args, **_kwargs: rebuilt,
    )

    def fail(_):
        raise ValueError("provider pages have moved to weekly projections")

    evidence = make_resilient_forecast_loader(store, live_loader=fail)(state)

    assert evidence.evidence_basis == "preseason_baseline"
    assert evidence.successful_source_ids == ("fftoday", "razzball")
    assert "provider pages have moved to weekly projections" in evidence.failed_sources[0]


def test_resilient_loader_fails_closed_without_live_or_preserved_baseline():
    store = _Store()

    def fail(_):
        raise ValueError("only one live independent source")

    with pytest.raises(ValueError, match="only one live independent source"):
        make_resilient_forecast_loader(store, live_loader=fail)(_state(scored=True))


def test_concrete_baseline_materialization_uses_authority_runtime_version():
    state = _state()
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")

    result = build_runtime_from_preseason_baseline(state, baseline)

    assert result.model_version == PRESEASON_AUTHORITY_RUNTIME_VERSION
    assert result.evaluation_as_of == NOW
    assert result.successful_source_ids == ("fftoday", "razzball")
    assert result.failed_sources == ()
    assert len(result.fantasy_point_forecasts) == 1
    assert result.fantasy_point_forecasts[0].distribution.mean == pytest.approx(250.0)
    assert result.fantasy_point_forecasts[0].source == "fsffl:preseason_baseline_league_scored"


def test_preseason_authority_loader_is_independent_of_healthy_live_forecast():
    state = _state()
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=baseline,
    )
    store = _Store(record)

    authority = make_preseason_baseline_authority_loader(store)(state)
    live = make_resilient_forecast_loader(
        store,
        live_loader=lambda _: _evidence(_runtime()),
    )(state)

    assert authority.evidence_basis == "preseason_baseline"
    assert authority.runtime_result.evaluation_as_of == baseline.evaluation_as_of
    assert authority.runtime_result.model_version == PRESEASON_AUTHORITY_RUNTIME_VERSION
    assert authority.league_scored_forecasts[0].distribution.mean == pytest.approx(250.0)
    assert live.evidence_basis == "live_full_season"
    assert live.league_scored_forecasts[0].distribution.mean == pytest.approx(300.0)


def test_preseason_authority_loader_fails_closed_without_baseline():
    with pytest.raises(ValueError, match="valid preserved preseason Year-1 baseline is unavailable"):
        make_preseason_baseline_authority_loader(_Store())(_state(scored=True))


def test_preseason_authority_loader_replays_governed_annual_raw_snapshot_for_late_connect():
    state = _state(scored=True)
    runtime = _raw_qb_runtime()
    snapshot = AnnualPreseasonProjectionSnapshot(
        season=state.league.season,
        opener_date=date(2026, 9, 10),
        opener_coordinate_source="fixture_schedule",
        target_capture_date=date(2026, 8, 27),
        captured_at=NOW - timedelta(days=14),
        capture_offset_days_before_opener=14,
        provider_evidence=(),
        provider_failures=(),
        governed_raw_ensemble=runtime.raw_ensemble,
        governed_raw_ensemble_sha256="fixture-raw-ensemble",
        coverage=runtime.coverage,
        successful_source_ids=runtime.successful_source_ids,
        source_runtime_model_version=runtime.model_version,
    )
    annual = annual_preseason_projection_snapshot_artifact(snapshot=snapshot)

    evidence = make_preseason_baseline_authority_loader(
        _Store(annual_record=annual)
    )(state)

    assert evidence.evidence_basis == "preseason_baseline"
    assert evidence.successful_source_ids == ("fftoday", "razzball")
    assert evidence.runtime_result.evaluation_as_of == runtime.evaluation_as_of
    assert evidence.league_scored_forecasts[0].distribution.mean == pytest.approx(250.0)


def test_preseason_authority_loader_fails_closed_for_invalid_source_coverage():
    state = _state()
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")
    invalid = baseline.model_copy(update={"successful_source_ids": ("razzball",)})
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=invalid,
    )

    with pytest.raises(ValueError, match="independent-source authority"):
        make_preseason_baseline_authority_loader(_Store(record))(state)



def _state_scoring_fumbles_lost() -> LeagueState:
    state = _state(scored=True)
    rules = state.league.rules.model_copy(
        update={
            "scoring": state.league.rules.scoring
            + (ScoringRule(stat="fum_lost", points=-1.0),)
        }
    )
    return state.model_copy(
        update={
            "league": state.league.model_copy(update={"rules": rules}),
            "completed_through_week": 2,
        }
    )


def test_preseason_replay_emits_partial_instead_of_silently_dropping_fum_lost_players() -> None:
    state = _state_scoring_fumbles_lost()
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")

    result = build_runtime_from_preseason_baseline(state, baseline)

    assert result.fantasy_point_forecasts == ()
    assert len(result.partial_fantasy_point_forecasts) == 1
    partial = result.partial_fantasy_point_forecasts[0]
    assert partial.player_id == "p1"
    assert partial.omitted_rule_stats == ("fum_lost",)
    assert any(
        "fumbles_lost" in reason
        for reason in partial.omission_reasons
    )
    assert result.league_scoring_coverage is not None
    assert result.league_scoring_coverage.capability_status == "FULL"
    assert result.family_coverage[0].family == "player_offense"
    assert result.family_coverage[0].status == "FULL"
    assert result.simulation_authority_blockers == (
        "partial_player_scoring_coordinates_present",
    )
    assert result.model_version == PRESEASON_AUTHORITY_RUNTIME_VERSION


def test_resilient_preseason_fallback_keeps_partial_coverage_and_blocks_simulation_uncertainty() -> None:
    state = _state_scoring_fumbles_lost()
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=baseline,
    )
    store = _Store(record)

    def fail(_):
        raise ValueError("only one healthy live source")

    evidence = make_resilient_forecast_loader(
        store,
        live_loader=fail,
    )(state)

    assert evidence.evidence_basis == "preseason_baseline"
    assert evidence.league_scored_forecasts == ()
    assert len(evidence.runtime_result.partial_fantasy_point_forecasts) == 1
    assert evidence.runtime_result.partial_fantasy_point_forecasts[0].omitted_rule_stats == (
        "fum_lost",
    )
    assert evidence.runtime_result.simulation_authority_blockers == (
        "partial_player_scoring_coordinates_present",
    )
    assert evidence.uncertainty_ready is False


def test_preseason_replay_stays_full_when_fumbles_lost_is_not_scored() -> None:
    state = _state(scored=True)
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")

    result = build_runtime_from_preseason_baseline(state, baseline)

    assert len(result.fantasy_point_forecasts) == 1
    assert result.partial_fantasy_point_forecasts == ()
    assert result.simulation_authority_blockers == ()



def _fallback_fumbles_supplement(
    state: LeagueState,
    baseline,
) -> FirstPartyFumblesLostSupplement:
    first = baseline.raw_ensemble[0]
    observation = ForecastObservation(
        player_id=first.player_id,
        position=first.position,
        horizon=first.horizon,
        metric=ForecastMetric.FUMBLES_LOST,
        period_start=first.period_start,
        period_end=first.period_end,
        distribution=ForecastDistribution(mean=1.0, stddev=1.0),
        source=FIRST_PARTY_FUMBLES_LOST_SOURCE,
        model_version="next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate",
        as_of=state.as_of,
        provenance=Provenance(
            source=FIRST_PARTY_FUMBLES_LOST_SOURCE,
            retrieved_at=state.as_of + timedelta(seconds=2),
            effective_at=state.as_of,
            source_version="next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate",
        ),
    )
    player_evidence = FirstPartyFumblesLostPlayerEvidence(
        player_id=first.player_id,
        position=Position.QB,
        historical_gsis_id="00-test",
        identity_method="retained_gsis",
        evidence_tier=FirstPartyFumblesLostEvidenceTier.HISTORY_PLUS_CURRENT,
        history_games=17,
        history_opportunities=500.0,
        current_games=2,
        current_opportunities=70.0,
        historical_role_opportunities_per_game=500.0 / 17.0,
        role_opportunities_per_game=32.0,
        position_lost_fumble_per_opportunity=0.005,
        mean_fumbles_lost=1.0,
        predictive_stddev=1.0,
    )
    return FirstPartyFumblesLostSupplement(
        season=2026,
        league_state_id=state.state_id,
        completed_through_week=2,
        current_input_captured_at=state.as_of + timedelta(seconds=2),
        built_at=state.as_of + timedelta(seconds=2),
        authority_valid_from=state.as_of + timedelta(seconds=2),
        observed_schema_keys=("pass_att", "rec", "rush_att", "sack"),
        current_input_sha256="b" * 64,
        player_evidence=(player_evidence,),
        observations=(observation,),
    )


def test_preseason_replay_consumes_current_fumbles_supplement_without_mutating_raw_baseline() -> None:
    state = _state_scoring_fumbles_lost()
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")
    original_raw = baseline.raw_ensemble
    supplement = _fallback_fumbles_supplement(state, baseline)

    result = build_runtime_from_preseason_baseline(
        state,
        baseline,
        fumbles_lost_supplement=supplement,
    )

    assert result.raw_ensemble == original_raw
    assert len(result.fantasy_point_forecasts) == 1
    assert result.partial_fantasy_point_forecasts == ()
    assert result.simulation_authority_blockers == ()
    assert result.fumbles_lost_supplement_authority_fingerprint == supplement.authority_fingerprint
    assert result.fumbles_lost_supplement_player_count == 1
    assert result.first_party_fumbles_lost_supplement == supplement
    assert result.evaluation_as_of == state.as_of
    assert FIRST_PARTY_FUMBLES_LOST_SOURCE in result.fantasy_point_forecasts[0].provenance.source


def test_resilient_fallback_promotes_fumbles_scoring_when_current_supplement_is_available(monkeypatch) -> None:
    state = _state_scoring_fumbles_lost()
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="94")
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=baseline,
    )
    store = _Store(record)
    supplement = _fallback_fumbles_supplement(state, baseline)
    monkeypatch.setattr(
        "fsffl.product.forecast_resilience.build_first_party_fumbles_lost_supplement",
        lambda league_state, base_observations: supplement,
    )

    def fail(_):
        raise ValueError("only one healthy live source")

    evidence = make_resilient_forecast_loader(
        store,
        live_loader=fail,
    )(state)

    assert evidence.evidence_basis == "preseason_baseline"
    season_scored = tuple(
        row
        for row in evidence.league_scored_forecasts
        if row.horizon == ForecastHorizon.SEASON
    )
    assert len(season_scored) == 1
    assert evidence.runtime_result.partial_fantasy_point_forecasts == ()
    assert evidence.runtime_result.simulation_authority_blockers == ()
    assert evidence.runtime_result.fumbles_lost_supplement_authority_fingerprint
    assert evidence.runtime_result.fumbles_lost_supplement_player_count == 1
    assert evidence.uncertainty_ready is True
    assert evidence.raw_forecasts == baseline.raw_ensemble

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.current_runtime import LiveForecastRuntimeResult
from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.preseason_baseline import (
    PRESEASON_BASELINE_MODEL_VERSION,
    baseline_from_runtime,
    state_is_preseason_capture_eligible,
)
from fsffl.persistence.runtime_cache import (
    LEAGUE_SEASON_SCOPE_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    decode_preseason_forecast_baseline,
    preseason_forecast_baseline_artifact,
)
from fsffl.product.forecast_resilience import make_resilient_forecast_loader
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    Provenance,
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
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=NOW,
        teams=teams,
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(),
        player_states=(),
        matchups=matchups,
    )


def _observation(*, horizon: ForecastHorizon = ForecastHorizon.SEASON) -> ForecastObservation:
    return ForecastObservation(
        player_id="p1",
        position="QB",
        horizon=horizon,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=NOW + timedelta(days=1),
        period_end=NOW + timedelta(days=120),
        distribution=ForecastDistribution(mean=300.0, stddev=20.0),
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
    def __init__(self, record=None):
        self.record = record
        self.puts = []

    def get_latest_reusable_artifact(self, **kwargs):
        assert kwargs["artifact_kind"] == PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND
        assert kwargs["scope_kind"] == LEAGUE_SEASON_SCOPE_KIND
        assert kwargs["model_version"] == PRESEASON_BASELINE_MODEL_VERSION
        return self.record

    def put_artifact(self, record):
        self.puts.append(record)
        self.record = record


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

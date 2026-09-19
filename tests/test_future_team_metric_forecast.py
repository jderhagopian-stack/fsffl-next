from datetime import UTC, datetime

import pytest

from fsffl.forecast.models import ForecastDistribution
from fsffl.forecast.team_metric import TeamMetricForecastObservation, select_team_metric_forecasts
from fsffl.runtime.historical_team_metric import build_draft_metric_simulation_input
from fsffl.state.models import LeagueRules, Provenance


AS_OF = datetime(2023, 4, 10, 0, 48, 43, tzinfo=UTC)


def _provenance(effective_at: datetime = AS_OF) -> Provenance:
    return Provenance(
        source="historical-test",
        retrieved_at=AS_OF,
        effective_at=effective_at,
    )


def _observation(team_id: str, *, target_season: int = 2024, as_of: datetime = AS_OF, mean: float = 100.0):
    return TeamMetricForecastObservation(
        league_id="league-x",
        team_id=team_id,
        target_season=target_season,
        metric_id="max_pf",
        distribution=ForecastDistribution(mean=mean, stddev=10.0),
        as_of=as_of,
        source="test-model",
        model_version="v1",
        provenance=_provenance(as_of),
    )


def _rules(team_count: int = 4) -> LeagueRules:
    return LeagueRules(
        team_count=team_count,
        roster_size=20,
        rookie_draft_rounds=3,
        lineup=(),
        scoring=(),
    )


def test_selection_requires_explicit_target_season_and_does_not_carry_forward():
    observations = tuple(_observation(f"team-{index}", target_season=2023) for index in range(4))

    selected = select_team_metric_forecasts(
        observations,
        league_id="league-x",
        target_season=2024,
        metric_id="max_pf",
        as_of=AS_OF,
    )

    assert selected is None


def test_future_evidence_cannot_be_selected_before_it_was_known():
    future = datetime(2023, 5, 1, tzinfo=UTC)
    observations = tuple(_observation(f"team-{index}", as_of=future) for index in range(4))

    selected = select_team_metric_forecasts(
        observations,
        league_id="league-x",
        target_season=2024,
        metric_id="max_pf",
        as_of=AS_OF,
    )

    assert selected is None


def test_runtime_requires_complete_league_forecast_without_12_team_assumption():
    selected = select_team_metric_forecasts(
        tuple(_observation(f"team-{index}") for index in range(3)),
        league_id="league-x",
        target_season=2024,
        metric_id="max_pf",
        as_of=AS_OF,
    )
    assert selected is not None

    with pytest.raises(ValueError, match="every league team"):
        build_draft_metric_simulation_input(
            forecasts=selected,
            league_rules=_rules(team_count=4),
            draft_season=2025,
        )


def test_runtime_preserves_forecast_distribution_without_horizon_transform():
    selected = select_team_metric_forecasts(
        tuple(_observation(f"team-{index}", mean=100.0 + index) for index in range(4)),
        league_id="league-x",
        target_season=2024,
        metric_id="max_pf",
        as_of=AS_OF,
    )
    assert selected is not None

    request = build_draft_metric_simulation_input(
        forecasts=selected,
        league_rules=_rules(team_count=4),
        draft_season=2025,
        simulation_count=123,
        seed=7,
    )

    assert request.draft_season == 2025
    assert request.simulation_count == 123
    assert [item.mean_value for item in request.distributions] == [100.0, 101.0, 102.0, 103.0]
    assert all(item.stddev_value == 10.0 for item in request.distributions)

from datetime import UTC, datetime, timedelta

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.team_utility import (
    build_team_scoring_distribution,
    marginal_lineup_impact,
    optimize_team_lineup,
)


AS_OF = datetime(2026, 9, 5, 15, 0, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def player(player_id: str, position: Position) -> Player:
    return Player(player_id=player_id, full_name=player_id, position=position)


def forecast(player_id: str, position: Position, points: float) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=120),
        distribution=ForecastDistribution(mean=points, stddev=1.0),
        source="next2-test",
        model_version="forecast-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def league_state() -> LeagueState:
    players = (
        player("qb1", Position.QB),
        player("qb2", Position.QB),
        player("rb1", Position.RB),
        player("wr1", Position.WR),
        player("te1", Position.TE),
        player("wr2", Position.WR),
    )
    return LeagueState(
        league=League(
            league_id="league:1",
            name="Test League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=6,
                lineup=(
                    LineupRequirement(slot=RosterSlot.QB, count=1),
                    LineupRequirement(slot=RosterSlot.RB, count=1),
                    LineupRequirement(slot=RosterSlot.FLEX, count=1),
                    LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
                ),
                scoring=(),
            ),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="team:1", league_id="league:1", display_name="One"),
            Team(team_id="team:2", league_id="league:1", display_name="Two"),
        ),
        team_states=(
            TeamState(
                team_id="team:1",
                roster=tuple(RosterEntry(player_id=item.player_id, slot=RosterSlot.BENCH) for item in players),
            ),
            TeamState(team_id="team:2", roster=()),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=item.player_id,
                as_of=AS_OF,
                status=PlayerStatus.ACTIVE,
                provenance=PROVENANCE,
            )
            for item in players
        ),
    )


def forecasts() -> tuple[ForecastObservation, ...]:
    return (
        forecast("qb1", Position.QB, 30.0),
        forecast("qb2", Position.QB, 20.0),
        forecast("rb1", Position.RB, 25.0),
        forecast("wr1", Position.WR, 24.0),
        forecast("te1", Position.TE, 10.0),
        forecast("wr2", Position.WR, 15.0),
    )


def test_optimizer_handles_flex_and_superflex_jointly() -> None:
    result = optimize_team_lineup(
        league_state(), forecasts(), team_id="team:1", as_of=AS_OF, horizon=ForecastHorizon.SEASON
    )

    assert result.expected_points == 99.0
    by_slot = {(item.slot, item.slot_index): item.player_id for item in result.assignments}
    assert by_slot[(RosterSlot.QB, 1)] == "qb1"
    assert by_slot[(RosterSlot.RB, 1)] == "rb1"
    assert by_slot[(RosterSlot.FLEX, 1)] == "wr1"
    assert by_slot[(RosterSlot.SUPERFLEX, 1)] == "qb2"


def test_marginal_impact_uses_actual_roster_replacement() -> None:
    result = marginal_lineup_impact(
        league_state(),
        forecasts(),
        team_id="team:1",
        player_id="wr1",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
    )

    assert result.baseline_expected_points == 99.0
    assert result.without_player_expected_points == 90.0
    assert result.marginal_expected_points == 9.0
    assert result.replacement_player_ids == ("wr2",)


def test_missing_forecast_is_surfaced_not_imputed() -> None:
    result = optimize_team_lineup(
        league_state(),
        tuple(item for item in forecasts() if item.player_id != "te1"),
        team_id="team:1",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
    )

    assert result.missing_forecast_player_ids == ("te1",)


def test_team_scoring_distribution_combines_only_optimized_starters() -> None:
    result = build_team_scoring_distribution(
        league_state(),
        forecasts(),
        team_id="team:1",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
    )

    assert result.mean_points == 99.0
    assert result.stddev_points == 2.0
    assert "independent_player_variance" in result.model_version

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
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.value.intrinsic_runtime import build_current_intrinsic_values_v1
from fsffl.value.intrinsic_v1 import INTRINSIC_VALUE_V1_VERSION, IntrinsicV1Confidence


AS_OF = datetime(2026, 9, 13, 12, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _league_state() -> LeagueState:
    positions = (Position.QB, Position.QB, Position.RB, Position.RB, Position.WR, Position.WR, Position.TE, Position.TE)
    players = tuple(
        Player(player_id=f"p{index}", full_name=f"Player {index}", position=position)
        for index, position in enumerate(positions, start=1)
    )
    rules = LeagueRules(
        team_count=2,
        roster_size=4,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=1),
            LineupRequirement(slot=RosterSlot.WR, count=1),
            LineupRequirement(slot=RosterSlot.TE, count=1),
        ),
        scoring=(),
    )
    teams = (
        Team(team_id="t1", league_id="league", display_name="One"),
        Team(team_id="t2", league_id="league", display_name="Two"),
    )
    team_states = (
        TeamState(
            team_id="t1",
            roster=tuple(RosterEntry(player_id=f"p{i}", slot=RosterSlot.BENCH) for i in (1, 3, 5, 7)),
        ),
        TeamState(
            team_id="t2",
            roster=tuple(RosterEntry(player_id=f"p{i}", slot=RosterSlot.BENCH) for i in (2, 4, 6, 8)),
        ),
    )
    return LeagueState(
        league=League(league_id="league", name="League", season=2026, rules=rules),
        as_of=AS_OF,
        teams=teams,
        team_states=team_states,
        players=players,
        player_states=tuple(
            PlayerState(player_id=player.player_id, as_of=AS_OF, age_years=25, provenance=PROVENANCE)
            for player in players
        ),
        provenance=(PROVENANCE,),
    )


def _forecasts(state: LeagueState) -> tuple[ForecastObservation, ...]:
    means = {"p1": 300, "p2": 220, "p3": 200, "p4": 140, "p5": 210, "p6": 130, "p7": 160, "p8": 90}
    return tuple(
        ForecastObservation(
            player_id=player.player_id,
            position=player.position,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=AS_OF,
            period_end=AS_OF + timedelta(days=120),
            distribution=ForecastDistribution(mean=means[player.player_id], stddev=15),
            source="fsffl-test",
            model_version="forecast-test-v1",
            as_of=AS_OF,
            provenance=PROVENANCE,
        )
        for player in state.players
    )


def test_current_intrinsic_runtime_is_usable_with_authoritative_y1_and_carry_fallback():
    state = _league_state()
    result = build_current_intrinsic_values_v1(
        state,
        season_forecasts=_forecasts(state),
        base_forecast_model_version="forecast-test-v1",
    )
    assert result.model_version == INTRINSIC_VALUE_V1_VERSION
    assert result.coverage == 1.0
    assert len(result.estimates) == 8
    assert len(result.profiles) == 8
    assert all(estimate.confidence == IntrinsicV1Confidence.LOW for estimate in result.estimates)
    assert all(profile.intrinsic_value is not None for profile in result.profiles)
    assert all(profile.market_price is None for profile in result.profiles)

from datetime import UTC, datetime, timedelta

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
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
from fsffl.team_utility import optimize_team_lineup

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _forecast(player_id: str, position: Position, points: float) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=120),
        distribution=ForecastDistribution(mean=points, stddev=1.0),
        source="test",
        model_version="test-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def test_tiebreak_prefers_native_slots_even_when_rules_arrive_in_nonhuman_order() -> None:
    players = (
        Player(player_id="lamar", full_name="Lamar", position=Position.QB),
        Player(player_id="dak", full_name="Dak", position=Position.QB),
        Player(player_id="lamb", full_name="Lamb", position=Position.WR),
        Player(player_id="wr2", full_name="WR2", position=Position.WR),
        Player(player_id="wr3", full_name="WR3", position=Position.WR),
        Player(player_id="wr4", full_name="WR4", position=Position.WR),
    )
    # Deliberately put FLEX/SUPERFLEX first to ensure source ordering cannot drive
    # the points-neutral presentation tiebreak.
    lineup = (
        LineupRequirement(slot=RosterSlot.FLEX, count=1),
        LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        LineupRequirement(slot=RosterSlot.QB, count=1),
        LineupRequirement(slot=RosterSlot.WR, count=3),
    )
    state = LeagueState(
        league=League(
            league_id="league:1",
            name="Test",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=6, lineup=lineup, scoring=()),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="team:1", league_id="league:1", display_name="One"),
            Team(team_id="team:2", league_id="league:1", display_name="Two"),
        ),
        team_states=(
            TeamState(
                team_id="team:1",
                roster=tuple(RosterEntry(player_id=p.player_id, slot=RosterSlot.BENCH) for p in players),
            ),
            TeamState(team_id="team:2", roster=()),
        ),
        players=players,
        player_states=tuple(
            PlayerState(player_id=p.player_id, as_of=AS_OF, status=PlayerStatus.ACTIVE, provenance=PROVENANCE)
            for p in players
        ),
    )
    forecasts = (
        _forecast("lamar", Position.QB, 30.0),
        _forecast("dak", Position.QB, 20.0),
        _forecast("lamb", Position.WR, 28.0),
        _forecast("wr2", Position.WR, 26.0),
        _forecast("wr3", Position.WR, 24.0),
        _forecast("wr4", Position.WR, 22.0),
    )

    result = optimize_team_lineup(state, forecasts, team_id="team:1", as_of=AS_OF, horizon=ForecastHorizon.SEASON)
    by_slot = {(item.slot, item.slot_index): item.player_id for item in result.assignments}

    assert by_slot[(RosterSlot.QB, 1)] == "lamar"
    assert by_slot[(RosterSlot.WR, 1)] == "lamb"
    assert by_slot[(RosterSlot.WR, 2)] == "wr2"
    assert by_slot[(RosterSlot.WR, 3)] == "wr3"
    assert by_slot[(RosterSlot.FLEX, 1)] == "wr4"
    assert by_slot[(RosterSlot.SUPERFLEX, 1)] == "dak"
    assert result.expected_points == 150.0

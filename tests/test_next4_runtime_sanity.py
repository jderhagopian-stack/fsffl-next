from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.runtime import Next4LeagueSanityInput, run_next4_league_sanity
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
from fsffl.team_utility import CompetitiveStatePolicy, ScheduledMatchup


AS_OF = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)
PROVENANCE = Provenance(source="runtime-test", retrieved_at=AS_OF, effective_at=AS_OF)


def _player(player_id: str, position: Position) -> Player:
    return Player(player_id=player_id, full_name=player_id, position=position)


def _forecast(player_id: str, position: Position, points: float) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=120),
        distribution=ForecastDistribution(mean=points, stddev=2.0),
        source="next2-runtime-test",
        model_version="forecast-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def _league_state() -> LeagueState:
    team1_players = (
        _player("t1_qb1", Position.QB),
        _player("t1_qb2", Position.QB),
        _player("t1_wr1", Position.WR),
        _player("t1_wr2", Position.WR),
    )
    team2_players = (
        _player("t2_qb1", Position.QB),
        _player("t2_qb2", Position.QB),
        _player("t2_wr1", Position.WR),
        _player("t2_wr2", Position.WR),
    )
    all_players = team1_players + team2_players
    return LeagueState(
        league=League(
            league_id="league:runtime",
            name="Runtime League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=4,
                lineup=(
                    LineupRequirement(slot=RosterSlot.QB, count=1),
                    LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
                    LineupRequirement(slot=RosterSlot.WR, count=1),
                ),
                scoring=(),
            ),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="team:1", league_id="league:runtime", display_name="One"),
            Team(team_id="team:2", league_id="league:runtime", display_name="Two"),
        ),
        team_states=(
            TeamState(
                team_id="team:1",
                roster=tuple(RosterEntry(player_id=p.player_id, slot=RosterSlot.BENCH) for p in team1_players),
            ),
            TeamState(
                team_id="team:2",
                roster=tuple(RosterEntry(player_id=p.player_id, slot=RosterSlot.BENCH) for p in team2_players),
            ),
        ),
        players=all_players,
        player_states=tuple(
            PlayerState(
                player_id=p.player_id,
                as_of=AS_OF,
                status=PlayerStatus.ACTIVE,
                provenance=PROVENANCE,
            )
            for p in all_players
        ),
    )


def _forecasts() -> tuple[ForecastObservation, ...]:
    return (
        _forecast("t1_qb1", Position.QB, 26.0),
        _forecast("t1_qb2", Position.QB, 21.0),
        _forecast("t1_wr1", Position.WR, 18.0),
        _forecast("t1_wr2", Position.WR, 12.0),
        _forecast("t2_qb1", Position.QB, 22.0),
        _forecast("t2_qb2", Position.QB, 18.0),
        _forecast("t2_wr1", Position.WR, 15.0),
        _forecast("t2_wr2", Position.WR, 11.0),
    )


def _policy() -> CompetitiveStatePolicy:
    return CompetitiveStatePolicy(
        developing_playoff_min=0.20,
        competitive_playoff_min=0.45,
        contender_playoff_min=0.70,
        contender_first_place_min=0.45,
        model_version="runtime-test-policy-v1",
        evidence_through=AS_OF,
        provenance="test-only explicit policy",
    )


def test_runner_orchestrates_all_teams_without_inventing_inputs() -> None:
    result = run_next4_league_sanity(
        Next4LeagueSanityInput(
            league_state=_league_state(),
            forecasts=_forecasts(),
            schedule=(ScheduledMatchup(week=1, home_team_id="team:1", away_team_id="team:2"),),
            horizon=ForecastHorizon.SEASON,
            playoff_team_count=1,
            competitive_state_policy=_policy(),
            simulation_count=2_000,
            seed=7,
            as_of=AS_OF,
        )
    )

    assert result.league_id == "league:runtime"
    assert result.simulation_count == 2_000
    assert tuple(item.team_id for item in result.diagnostics) == ("team:1", "team:2")
    stronger, weaker = result.diagnostics
    assert stronger.scoring.mean_points > weaker.scoring.mean_points
    assert stronger.competitive_outcome.expected_wins > weaker.competitive_outcome.expected_wins
    assert stronger.utility.competitive_outcome == stronger.competitive_outcome
    assert stronger.utility.roster_resilience is not None


def test_runner_is_reproducible_for_identical_inputs() -> None:
    request = Next4LeagueSanityInput(
        league_state=_league_state(),
        forecasts=_forecasts(),
        schedule=(ScheduledMatchup(week=1, home_team_id="team:1", away_team_id="team:2"),),
        horizon=ForecastHorizon.SEASON,
        playoff_team_count=1,
        competitive_state_policy=_policy(),
        simulation_count=1_000,
        seed=99,
        as_of=AS_OF,
    )
    assert run_next4_league_sanity(request) == run_next4_league_sanity(request)


def test_runner_rejects_future_policy_evidence() -> None:
    future_policy = _policy().model_copy(update={"evidence_through": AS_OF + timedelta(days=1)})
    with pytest.raises(ValueError, match="future competitive-state policy evidence"):
        Next4LeagueSanityInput(
            league_state=_league_state(),
            forecasts=_forecasts(),
            schedule=(ScheduledMatchup(week=1, home_team_id="team:1", away_team_id="team:2"),),
            horizon=ForecastHorizon.SEASON,
            playoff_team_count=1,
            competitive_state_policy=future_policy,
            as_of=AS_OF,
        )

"""Repeatable synthetic benchmark for league-scale lineup preparation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
from statistics import median
from time import perf_counter

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
from fsffl.team_utility.lineup import optimize_team_lineup


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PROVENANCE = Provenance(source="benchmark", retrieved_at=AS_OF, effective_at=AS_OF)
POSITION_CYCLE = (
    Position.QB,
    Position.QB,
    Position.RB,
    Position.RB,
    Position.RB,
    Position.RB,
    Position.WR,
    Position.WR,
    Position.WR,
    Position.WR,
    Position.TE,
    Position.TE,
    Position.RB,
    Position.WR,
    Position.QB,
    Position.TE,
)


def workload() -> tuple[LeagueState, tuple[ForecastObservation, ...], tuple[tuple[str, frozenset[str]], ...]]:
    teams = tuple(
        Team(team_id=f"team:{index:02d}", league_id="league:benchmark", display_name=f"Team {index}")
        for index in range(12)
    )
    players = []
    team_states = []
    forecasts = []
    scenarios = []
    for team_index, team in enumerate(teams):
        roster = []
        ids = []
        for player_index, position in enumerate(POSITION_CYCLE):
            player_id = f"player:{team_index:02d}:{player_index:02d}"
            player = Player(
                player_id=player_id,
                full_name=player_id,
                position=position,
                nfl_team=f"NFL{(team_index * 3 + player_index) % 32:02d}",
            )
            players.append(player)
            ids.append(player_id)
            roster.append(RosterEntry(player_id=player_id, slot=RosterSlot.BENCH))
            forecasts.append(
                ForecastObservation(
                    player_id=player_id,
                    position=position,
                    horizon=ForecastHorizon.SEASON,
                    metric=ForecastMetric.FANTASY_POINTS,
                    period_start=AS_OF,
                    period_end=AS_OF + timedelta(days=120),
                    distribution=ForecastDistribution(
                        mean=float(8 + (player_index * 11 + team_index * 3) % 27),
                        stddev=4.0,
                    ),
                    source="benchmark",
                    model_version="benchmark-v1",
                    as_of=AS_OF,
                    provenance=PROVENANCE,
                )
            )
        team_states.append(TeamState(team_id=team.team_id, roster=tuple(roster)))
        scenarios.extend(
            (team.team_id, frozenset(ids[start : start + 1]))
            for start in (0, 2, 6, 10)
        )

    league = League(
        league_id="league:benchmark",
        name="Lineup Benchmark",
        season=2026,
        rules=LeagueRules(
            team_count=12,
            roster_size=len(POSITION_CYCLE),
            playoff_team_count=6,
            lineup=(
                LineupRequirement(slot=RosterSlot.QB, count=1),
                LineupRequirement(slot=RosterSlot.RB, count=2),
                LineupRequirement(slot=RosterSlot.WR, count=3),
                LineupRequirement(slot=RosterSlot.TE, count=1),
                LineupRequirement(slot=RosterSlot.FLEX, count=2),
                LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
            ),
            scoring=(),
        ),
    )
    state = LeagueState(
        league=league,
        as_of=AS_OF,
        teams=teams,
        team_states=tuple(team_states),
        players=tuple(players),
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=AS_OF,
                nfl_team=player.nfl_team,
                status=PlayerStatus.ACTIVE,
                provenance=PROVENANCE,
            )
            for player in players
        ),
    )
    return state, tuple(forecasts), tuple(scenarios)


def main() -> None:
    state, forecasts, scenarios = workload()

    def run() -> str:
        digest = hashlib.sha256()
        for team_id, excluded in scenarios:
            result = optimize_team_lineup(
                state,
                forecasts,
                team_id=team_id,
                as_of=AS_OF,
                horizon=ForecastHorizon.SEASON,
                excluded_player_ids=excluded,
                allow_unfilled_slots=True,
            )
            digest.update(result.model_dump_json().encode())
        return digest.hexdigest()

    expected = run()
    samples = []
    for _ in range(7):
        started = perf_counter()
        observed = run()
        samples.append(perf_counter() - started)
        assert observed == expected
    print(f"scenarios={len(scenarios)} median_seconds={median(samples):.6f} digest={expected}")


if __name__ == "__main__":
    main()

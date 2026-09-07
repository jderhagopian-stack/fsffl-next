from datetime import UTC, datetime

from fsffl.forecast.regular_season import fantasy_regular_season_weeks
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    Provenance,
    Team,
    TeamState,
)


def test_configured_regular_season_horizon_wins_over_partial_matchup_rows() -> None:
    as_of = datetime(2026, 9, 7, tzinfo=UTC)
    provenance = Provenance(source="test", retrieved_at=as_of, effective_at=as_of)
    league = League(
        league_id="l1",
        name="League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            fantasy_regular_season_end_week=14,
            lineup=(),
            scoring=(),
        ),
    )
    teams = (
        Team(team_id="a", league_id="l1", display_name="A"),
        Team(team_id="b", league_id="l1", display_name="B"),
    )
    state = LeagueState(
        league=league,
        as_of=as_of,
        teams=teams,
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(),
        player_states=(),
        matchups=(
            LeagueMatchup(
                week=1,
                team_a_id="a",
                team_b_id="b",
                provenance=provenance,
            ),
        ),
    )

    assert fantasy_regular_season_weeks(state) == tuple(range(1, 15))

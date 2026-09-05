from datetime import UTC, datetime

from fsffl.forecast.current_runtime import NamedCurrentProjectionFetcher, build_current_live_forecasts
from fsffl.forecast.models import ForecastMetric
from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.state.models import League, LeagueRules, LeagueState, Player, PlayerState, Position, Provenance, ScoringRule, Team, TeamState

NOW = datetime(2026, 9, 5, 20, tzinfo=UTC)


def state() -> LeagueState:
    provenance = Provenance(source="test", retrieved_at=NOW, effective_at=NOW)
    league = League(
        league_id="l1",
        name="League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            lineup=(),
            scoring=(
                ScoringRule(stat="pass_yd", points=0.04),
                ScoringRule(stat="pass_td", points=4.0),
                ScoringRule(stat="pass_int", points=-2.0),
                ScoringRule(stat="rush_yd", points=0.1),
                ScoringRule(stat="rush_td", points=6.0),
            ),
        ),
    )
    return LeagueState(
        league=league,
        as_of=NOW,
        teams=(Team(team_id="a", league_id="l1", display_name="A"), Team(team_id="b", league_id="l1", display_name="B")),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(Player(player_id="p1", full_name="Lamar Jackson", position=Position.QB, nfl_team="BAL"),),
        player_states=(PlayerState(player_id="p1", as_of=NOW, nfl_team="BAL", provenance=provenance),),
    )


def snapshot(provider: str, yards: float) -> CurrentProjectionSnapshot:
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=NOW,
        effective_at=datetime(2026, 9, 4, 12, tzinfo=UTC),
        rows=(CurrentProjectionRow(provider=provider, external_id=provider, player_name="Lamar Jackson", position=Position.QB, nfl_team="BAL", stats={"pass_yd": yards, "pass_td": 30.0, "pass_int": 10.0, "rush_yd": 800.0, "rush_td": 5.0}),),
        source_version=f"{provider}-v1",
        usage_class="beta-personal-research-requires-commercial-review",
    )


def test_current_runtime_ensembles_before_league_scoring() -> None:
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )
    result = build_current_live_forecasts(state(), fetchers=fetchers, clock=lambda: NOW)
    pass_yards = [item for item in result.raw_ensemble if item.metric == ForecastMetric.PASS_YARDS]
    assert len(pass_yards) == 1
    assert pass_yards[0].source == "fsffl:live_equal_weight"
    assert pass_yards[0].distribution.mean == 4100.0
    assert len(result.fantasy_point_forecasts) == 1
    assert result.fantasy_point_forecasts[0].source == "fsffl:live_league_scored"
    assert result.fantasy_point_forecasts[0].distribution.mean == 354.0

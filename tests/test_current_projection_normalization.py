from datetime import UTC, datetime

from fsffl.forecast.current_normalization import canonical_season_window, normalize_current_projection_snapshot
from fsffl.forecast.ensemble import equal_weight_ensemble
from fsffl.forecast.models import ForecastMetric
from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    Team,
    TeamState,
)


def _state() -> LeagueState:
    as_of = datetime(2026, 9, 5, 20, tzinfo=UTC)
    provenance = Provenance(source="test", retrieved_at=as_of, effective_at=as_of)
    league = League(
        league_id="l1",
        name="League",
        season=2026,
        rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
    )
    player = Player(player_id="p1", full_name="Lamar Jackson", position=Position.QB, nfl_team="BAL")
    return LeagueState(
        league=league,
        as_of=as_of,
        teams=(
            Team(team_id="a", league_id="l1", display_name="A"),
            Team(team_id="b", league_id="l1", display_name="B"),
        ),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(player,),
        player_states=(PlayerState(player_id="p1", as_of=as_of, nfl_team="BAL", provenance=provenance),),
    )


def _snapshot(provider: str, pass_yards: float, effective_day: int) -> CurrentProjectionSnapshot:
    captured = datetime(2026, 9, 5, 19, tzinfo=UTC)
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=captured,
        effective_at=datetime(2026, 9, effective_day, 12, tzinfo=UTC),
        rows=(
            CurrentProjectionRow(
                provider=provider,
                external_id=f"{provider}:lamar",
                player_name="Lamar Jackson",
                position=Position.QB,
                nfl_team="BAL",
                stats={"pass_yd": pass_yards, "pass_td": 30.0},
            ),
        ),
        source_version=f"{provider}-v1",
        usage_class="beta-personal-research-requires-commercial-review",
    )


def test_current_sources_share_common_season_identity_for_ensemble() -> None:
    state = _state()
    evaluation_as_of = datetime(2026, 9, 5, 20, tzinfo=UTC)
    first = normalize_current_projection_snapshot(
        _snapshot("fftoday", 4000.0, 3),
        league_state=state,
        season=2026,
        evaluation_as_of=evaluation_as_of,
    )
    second = normalize_current_projection_snapshot(
        _snapshot("cbs", 4200.0, 5),
        league_state=state,
        season=2026,
        evaluation_as_of=evaluation_as_of,
    )
    observations = first + second
    pass_yards = [item for item in observations if item.metric == ForecastMetric.PASS_YARDS]
    assert len(pass_yards) == 2
    assert {item.as_of for item in pass_yards} == {evaluation_as_of}
    assert {item.provenance.effective_at.day for item in pass_yards} == {3, 5}
    assert {(item.period_start, item.period_end) for item in pass_yards} == {canonical_season_window(2026)}

    ensemble = equal_weight_ensemble(tuple(pass_yards))
    assert len(ensemble) == 1
    assert ensemble[0].distribution.mean == 4100.0
    assert ensemble[0].distribution.stddev > 0


def test_ambiguous_or_unmatched_identity_is_not_guessed() -> None:
    state = _state()
    snapshot = CurrentProjectionSnapshot(
        provider="cbs",
        captured_at=datetime(2026, 9, 5, 19, tzinfo=UTC),
        effective_at=datetime(2026, 9, 5, 18, tzinfo=UTC),
        rows=(
            CurrentProjectionRow(
                provider="cbs",
                external_id="unknown",
                player_name="Not A Player",
                position=Position.QB,
                nfl_team="BAL",
                stats={"pass_yd": 1000.0},
            ),
        ),
        source_version="cbs-v1",
        usage_class="beta-personal-research-requires-commercial-review",
    )
    observations = normalize_current_projection_snapshot(
        snapshot,
        league_state=state,
        season=2026,
        evaluation_as_of=datetime(2026, 9, 5, 20, tzinfo=UTC),
    )
    assert observations == ()

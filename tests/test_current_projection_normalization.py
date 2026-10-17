from datetime import UTC, datetime
from dataclasses import replace

import pytest

from fsffl.forecast.current_normalization import (
    canonical_season_window,
    map_projection_rows,
    normalize_current_projection_snapshot,
)
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
    ProviderRef,
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


def test_common_name_suffix_difference_resolves_same_canonical_player() -> None:
    state = _state()
    snapshot = CurrentProjectionSnapshot(
        provider="cbs",
        captured_at=datetime(2026, 9, 5, 19, tzinfo=UTC),
        effective_at=datetime(2026, 9, 5, 18, tzinfo=UTC),
        rows=(
            CurrentProjectionRow(
                provider="cbs",
                external_id="cbs:lamar-jr",
                player_name="Lamar Jackson Jr.",
                position=Position.QB,
                nfl_team="BAL",
                stats={"pass_yd": 4100.0},
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
    assert len(observations) == 1
    assert observations[0].player_id == "p1"
    assert observations[0].metric == ForecastMetric.PASS_YARDS


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


def test_asserted_provider_identity_resolves_changed_name_and_team() -> None:
    state = _state().model_copy(update={
        "players": (
            Player(
                player_id="p1",
                full_name="Lamar Jackson",
                position=Position.QB,
                nfl_team="BAL",
                provider_refs=(ProviderRef(provider="cbs", external_id="cbs:canonical-1"),),
            ),
        ),
    })
    snapshot = CurrentProjectionSnapshot(
        provider="CBS",
        captured_at=datetime(2026, 9, 5, 19, tzinfo=UTC),
        effective_at=datetime(2026, 9, 5, 18, tzinfo=UTC),
        rows=(CurrentProjectionRow(
            provider="CBS",
            external_id="cbs:canonical-1",
            player_name="Provider Alias",
            position=Position.QB,
            nfl_team="NYJ",
            stats={"pass_yd": 4100.0},
        ),),
        source_version="cbs-v1",
        usage_class="beta-personal-research-requires-commercial-review",
    )
    observations = normalize_current_projection_snapshot(
        snapshot,
        league_state=state,
        season=2026,
        evaluation_as_of=datetime(2026, 9, 5, 20, tzinfo=UTC),
    )
    assert len(observations) == 1
    assert observations[0].player_id == "p1"
    assert observations[0].provenance.provider_ref.external_id == "cbs:canonical-1"


def test_shared_mapper_resolves_rostered_player_outside_frozen_reference_universe() -> None:
    state = _state().model_copy(update={
        "players": _state().players + tuple(
            Player(
                player_id=f"reference-{index}",
                full_name=f"Reference Player {index}",
                position=Position.WR,
                nfl_team="BUF",
            )
            for index in range(335)
        ) + (
            Player(
                player_id="sleeper:player:new-roster",
                full_name="New Roster Player",
                position=Position.WR,
                nfl_team="SEA",
                provider_refs=(ProviderRef(provider="cbs", external_id="cbs:new-roster"),),
            ),
        ),
    })
    snapshot = CurrentProjectionSnapshot(
        provider="CBS",
        captured_at=datetime(2026, 9, 5, 19, tzinfo=UTC),
        effective_at=datetime(2026, 9, 5, 18, tzinfo=UTC),
        rows=(CurrentProjectionRow(
            provider="CBS",
            external_id="cbs:new-roster",
            player_name="Provider Alias",
            position=Position.WR,
            nfl_team="NYJ",
            stats={"rec_yd": 900.0},
        ),),
        source_version="cbs-ros-v1",
        usage_class="test",
    )

    mapped = map_projection_rows(snapshot, players=state.players)
    observations = normalize_current_projection_snapshot(
        snapshot,
        league_state=state,
        season=2026,
        evaluation_as_of=datetime(2026, 9, 5, 20, tzinfo=UTC),
    )
    assert [(row.external_id, player.player_id) for row, player in mapped] == [
        ("cbs:new-roster", "sleeper:player:new-roster")
    ]
    assert [item.player_id for item in observations] == ["sleeper:player:new-roster"]


@pytest.mark.parametrize("provider", ["cbs", "razzball"])
def test_verified_okonkwo_alias_maps_without_changing_source_rows(provider) -> None:
    player = Player(player_id="sleeper:player:8210", full_name="Chig Okonkwo",
                    position=Position.TE, nfl_team="WAS")
    row = CurrentProjectionRow(provider=provider, external_id="TE:WAS:chigoziemokonkwo",
        player_name="Chigoziem Okonkwo", position=Position.TE, nfl_team="WAS",
        stats={"rec": 41.4, "rec_yd": 420., "rec_td": 1.9})
    snapshot = replace(_snapshot(provider, 0., 3), rows=(row,))
    assert map_projection_rows(snapshot, players=(player,)) == ((row, player),)
    # A verified alias belongs to one canonical identity, not arbitrary Chigs.
    other = player.model_copy(update={"player_id": "another-player"})
    assert map_projection_rows(snapshot, players=(other,)) == ()
    # The existing ambiguity and position safeguards still apply.
    duplicate = player.model_copy(update={"player_id": "duplicate", "full_name": row.player_name})
    assert map_projection_rows(snapshot, players=(player, duplicate)) == ()
    wrong_position = player.model_copy(update={"position": Position.WR})
    assert map_projection_rows(snapshot, players=(wrong_position,)) == ()

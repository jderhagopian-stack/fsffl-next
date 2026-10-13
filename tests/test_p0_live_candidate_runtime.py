from datetime import UTC, datetime

from fsffl.product.p0_forecast_runtime import frozen_p0_source_rows
from fsffl.product.p0_live_candidate_runtime import exact_state_rostered_p0_subject_ids
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    Position,
    PlayerState,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)


def test_dynamic_p0_selection_uses_exact_state_roster_and_excludes_frozen_reference():
    now = datetime(2026, 10, 8, tzinfo=UTC)
    reference_id = frozen_p0_source_rows()[0].player_id
    dynamic_id = "sleeper:player:11638"
    players = (
        Player(player_id=dynamic_id, full_name="Dynamic Player", position=Position.WR),
        Player(player_id=reference_id, full_name="Reference Player", position=Position.QB),
    )
    provenance = Provenance(source="fixture", retrieved_at=now, effective_at=now)
    state = LeagueState(
        league=League(
            league_id="fixture-league",
            name="Fixture",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=2, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(
            Team(team_id="team-a", league_id="fixture-league", display_name="A"),
            Team(team_id="team-b", league_id="fixture-league", display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="team-a",
                roster=(
                    RosterEntry(player_id=dynamic_id, slot=RosterSlot.BENCH),
                    RosterEntry(player_id=reference_id, slot=RosterSlot.BENCH),
                ),
            ),
            TeamState(team_id="team-b", roster=()),
        ),
        players=players,
        player_states=tuple(
            PlayerState(player_id=player.player_id, as_of=now, provenance=provenance)
            for player in players
        ),
    )

    assert exact_state_rostered_p0_subject_ids(state) == (dynamic_id,)

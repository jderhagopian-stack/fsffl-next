from datetime import UTC, datetime

from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
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
from fsffl.trade_decision import RosterLegalityStatus, resolve_mandatory_roster_cuts

AS_OF = datetime(2026, 9, 7, 10, 30, tzinfo=UTC)
PROVENANCE = Provenance(source="roster-cut-test", retrieved_at=AS_OF, effective_at=AS_OF)


def _state() -> LeagueState:
    return LeagueState(
        league=League(
            league_id="league:cuts",
            name="Cuts",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=2, taxi_size=1, lineup=(), scoring=()),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="A", league_id="league:cuts", display_name="A"),
            Team(team_id="B", league_id="league:cuts", display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="A",
                roster=(
                    RosterEntry(player_id="p1", slot=RosterSlot.BENCH),
                    RosterEntry(player_id="p2", slot=RosterSlot.BENCH),
                    RosterEntry(player_id="p3", slot=RosterSlot.BENCH),
                    RosterEntry(player_id="p4", slot=RosterSlot.TAXI),
                ),
            ),
            TeamState(
                team_id="B",
                roster=(
                    RosterEntry(player_id="p5", slot=RosterSlot.BENCH),
                    RosterEntry(player_id="p6", slot=RosterSlot.BENCH),
                ),
            ),
        ),
        players=tuple(
            Player(player_id=f"p{i}", full_name=f"P{i}", position=Position.WR)
            for i in range(1, 7)
        ),
        player_states=tuple(
            PlayerState(
                player_id=f"p{i}",
                as_of=AS_OF,
                status=PlayerStatus.ACTIVE,
                provenance=PROVENANCE,
            )
            for i in range(1, 7)
        ),
    )


def test_overflow_cuts_lowest_known_market_value_and_preserves_taxi() -> None:
    result = resolve_mandatory_roster_cuts(
        _state(),
        market_values={"p1": 100.0, "p2": 50.0, "p3": 10.0, "p4": 1.0},
    )
    resolution = next(item for item in result.resolutions if item.team_id == "A")
    assert resolution.required_cut_count == 1
    assert resolution.status == RosterLegalityStatus.RESOLVED
    assert resolution.cut_market_value_total == 10.0
    assert tuple(cut.player_id for cut in resolution.cuts) == ("p3",)

    state = next(item for item in result.league_state.team_states if item.team_id == "A")
    assert {entry.player_id for entry in state.roster} == {"p1", "p2", "p4"}
    assert next(entry for entry in state.roster if entry.player_id == "p4").slot == RosterSlot.TAXI


def test_missing_cut_value_keeps_roster_legal_but_marks_cost_incomplete() -> None:
    result = resolve_mandatory_roster_cuts(
        _state(),
        market_values={"p1": 100.0, "p2": 50.0},
    )
    resolution = next(item for item in result.resolutions if item.team_id == "A")
    # Known-value bench players are preserved behind lower known values, so p2 is
    # the cheapest fully evidenced cut candidate before unknown p3.
    assert tuple(cut.player_id for cut in resolution.cuts) == ("p2",)
    assert resolution.cut_market_value_total == 50.0
    assert resolution.status == RosterLegalityStatus.RESOLVED


def test_no_overflow_requires_no_cut() -> None:
    result = resolve_mandatory_roster_cuts(_state(), market_values={})
    resolution = next(item for item in result.resolutions if item.team_id == "B")
    assert resolution.required_cut_count == 0
    assert resolution.cuts == ()
    assert resolution.status == RosterLegalityStatus.NOT_REQUIRED

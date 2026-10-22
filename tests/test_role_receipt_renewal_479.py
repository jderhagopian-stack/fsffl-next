"""Regression checks for producer-owned role corroboration (Issue #479)."""
from datetime import UTC, datetime, timedelta

from fsffl.providers.nfl_status_evidence import (
    NFL_ROLE_RECEIPTS, corroborated_current_role_receipts,
)
from fsffl.product.p0_live_candidate_runtime import recorded_ytd_only_year_one_evidence
from fsffl.state.models import League, LeagueRules, LeagueState, Player, PlayerState, Position, Provenance, RosterEntry, Team, TeamState


def state_for_receipts():
    ids = ("sleeper:player:3321", "sleeper:player:6803", "sleeper:player:13268")
    return LeagueState(
        league=League(league_id="fixture", name="Fixture", season=2026,
                      rules=LeagueRules(team_count=2, roster_size=3, lineup=(), scoring=())),
        as_of=datetime(2026, 10, 21, tzinfo=UTC),
        teams=(Team(team_id="a", league_id="fixture", display_name="A"),
               Team(team_id="b", league_id="fixture", display_name="B")),
        team_states=(TeamState(team_id="a", roster=tuple(RosterEntry(player_id=i, slot="BENCH") for i in ids)),
                     TeamState(team_id="b", roster=())),
        players=tuple(Player(player_id=i, full_name=i, position=Position.WR) for i in ids),
        player_states=tuple(PlayerState(
            player_id=i, as_of=datetime(2026, 10, 21, tzinfo=UTC),
            provenance=Provenance(source="fixture", retrieved_at=datetime(2026, 10, 21, tzinfo=UTC),
                                  effective_at=datetime(2026, 10, 21, tzinfo=UTC)),
        ) for i in ids),
    )


def test_expired_static_roles_require_fresh_corroboration():
    state = state_for_receipts()
    captured = datetime(2026, 10, 21, 12, tzinfo=UTC)
    catalog = {
        "3321": {"team": None, "status": "Inactive"},
        "6803": {"team": "SF", "status": "RLS"},
        "13268": {"team": "BAL", "status": "Active", "depth_chart_order": 3},
    }
    from fsffl.providers.nfl_status_evidence import recorded_nfl_role_receipts
    assert recorded_nfl_role_receipts(state, as_of=captured) == {}
    result = corroborated_current_role_receipts(state, as_of=captured, captured_at=captured, catalog=catalog)
    assert set(result) == set(row.player_id for row in state.players)
    assert all(row.captured_at == captured for row in result.values())
    admitted = recorded_ytd_only_year_one_evidence(state, as_of=captured, verified_roles=result)
    assert set(admitted) == set(result)
    assert all("career-ytd-only-v1" in row.source_version for row in admitted.values())


def test_stale_or_contradictory_catalog_never_renews_role():
    state = state_for_receipts()
    captured = datetime(2026, 10, 21, 12, tzinfo=UTC)
    changed = {
        "3321": {"team": "MIA", "status": "Active"},
        "6803": {"team": "SF", "status": "Active"},
        "13268": {"team": "BAL", "status": "Active", "depth_chart_order": 1},
    }
    assert not corroborated_current_role_receipts(state, as_of=captured, captured_at=captured, catalog=changed)
    correct = {
        "3321": {"team": None, "status": "Inactive"},
        "6803": {"team": "SF", "status": "RLS"},
        "13268": {"team": "BAL", "status": "Active", "depth_chart_order": 3},
    }
    assert not corroborated_current_role_receipts(
        state, as_of=captured + timedelta(hours=7), captured_at=captured, catalog=correct,
    )
    assert not corroborated_current_role_receipts(
        state, as_of=captured - timedelta(seconds=1), captured_at=captured, catalog=correct,
    )
    assert not corroborated_current_role_receipts(
        state.model_copy(update={"league": state.league.model_copy(update={"season": 2027})}),
        as_of=captured, captured_at=captured, catalog=correct,
    )

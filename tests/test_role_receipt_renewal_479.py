"""Regression checks for producer-owned role corroboration (Issue #479)."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fsffl.providers.nfl_status_evidence import (
    NFL_ROLE_RECEIPTS, corroborated_current_role_receipts, current_catalog_role_receipts,
    acquire_official_reserve_role_receipts,
)
from fsffl.product.p0_live_candidate_runtime import (
    recorded_ir_no_projection_year_one_evidence, recorded_ytd_only_year_one_evidence,
)
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
        players=tuple(Player(player_id=i, full_name={"sleeper:player:3321":"Tyreek Hill", "sleeper:player:6803":"Brandon Aiyuk", "sleeper:player:13268":"Elijah Sarratt"}[i], position=Position.WR) for i in ids),
        player_states=tuple(PlayerState(
            player_id=i, as_of=datetime(2026, 10, 21, tzinfo=UTC),
            provenance=Provenance(source="fixture", retrieved_at=datetime(2026, 10, 21, tzinfo=UTC),
                                  effective_at=datetime(2026, 10, 21, tzinfo=UTC)),
        ) for i in ids),
    )


def test_catalog_team_field_governs_unsigned_for_every_rostered_player():
    state = state_for_receipts()
    captured = datetime(2026, 10, 24, 12, tzinfo=UTC)
    roles = current_catalog_role_receipts(
        state, as_of=captured, captured_at=captured,
        catalog={"3321": {"team": None}, "13268": {}},
    )
    assert roles["sleeper:player:3321"].status == "unsigned"
    assert "sleeper:player:13268" not in roles
    accepted = recorded_ytd_only_year_one_evidence(
        state, as_of=captured, verified_roles=roles,
    )
    assert accepted["sleeper:player:3321"].source_version.startswith("career-ytd-only")
    signed = current_catalog_role_receipts(
        state, as_of=captured, captured_at=captured,
        catalog={"3321": {"team": "MIA"}, "6803": {"team": "SF"}},
    )
    assert signed["sleeper:player:3321"].status == "signed"
    assert "sleeper:player:6803" not in signed


def test_ir_without_projection_gets_provenanced_zero_ros_assumption():
    state = state_for_receipts()
    teams = list(state.team_states)
    first = teams[0]
    teams[0] = first.model_copy(update={"roster": (
        first.roster[0].model_copy(update={"slot": "IR"}), *first.roster[1:]
    )})
    state = state.model_copy(update={"team_states": tuple(teams)})
    evidence = recorded_ir_no_projection_year_one_evidence(
        state, player_id="sleeper:player:3321", as_of=state.as_of,
        available_projection_rows=(),
    )
    assert evidence is not None
    assert evidence.source == "fsffl:exact-state-ir-no-projection"
    assert evidence.status == "low_confidence_ytd_only_no_additional_production_assumed"
    assert recorded_ir_no_projection_year_one_evidence(
        state, player_id="sleeper:player:3321", as_of=state.as_of,
        available_projection_rows=(SimpleNamespace(player_id="sleeper:player:3321"),),
    ) is None


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


def test_official_roster_rls_exact_row_required():
    state = state_for_receipts()
    cutoff = datetime(2026, 10, 21, 12, tzinfo=UTC)
    html = "<table><tr><th>Player</th><th>No</th><th>Pos</th><th>Status</th></tr>" \
           "<tr><td>Brandon Aiyuk</td><td>11</td><td>WR</td><td>RLS</td></tr>" \
           "<tr><td>Other Player</td><td>20</td><td>WR</td><td>ACT</td></tr></table>"
    fresh = acquire_official_reserve_role_receipts(
        state, evaluation_cutoff=cutoff, fetcher=lambda url: (html, cutoff),
    )
    assert set(fresh) == {"sleeper:player:6803"}
    assert fresh["sleeper:player:6803"].source_url == "https://www.nfl.com/teams/san-francisco-49ers/roster"
    changed = html.replace("<td>RLS</td>", "<td>ACT</td>")
    assert not acquire_official_reserve_role_receipts(
        state, evaluation_cutoff=cutoff, fetcher=lambda url: (changed, cutoff),
    )
    assert not acquire_official_reserve_role_receipts(
        state, evaluation_cutoff=cutoff, fetcher=lambda url: (html, cutoff + timedelta(minutes=1)),
    )
    assert acquire_official_reserve_role_receipts(
        state, evaluation_cutoff=cutoff, allow_current_capture=True,
        fetcher=lambda url: (html, cutoff + timedelta(minutes=1)),
    )

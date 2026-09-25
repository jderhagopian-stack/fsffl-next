from datetime import UTC, datetime

from fsffl.providers.sleeper import SleeperNormalizer, SleeperPayloadBundle
from fsffl.providers.sleeper_snapshot import canonical_players_from_sleeper_player_universe
from fsffl.state.models import Position, RosterSlot


AS_OF = datetime(2026, 9, 4, 14, 0, tzinfo=UTC)


def bundle() -> SleeperPayloadBundle:
    return SleeperPayloadBundle(
        league={
            "league_id": "123",
            "name": "Fixture League",
            "season": "2026",
            "settings": {
                "num_teams": 2,
                "roster_size": 4,
                "taxi_slots": 1,
                "reserve_slots": 1,
                "draft_rounds": 2,
                "waiver_budget": 100,
            },
            "roster_positions": ["QB", "RB", "FLEX", "BN"],
            "scoring_settings": {"rec": 0.5, "pass_yd": 0.04},
        },
        users=[
            {"user_id": "u1", "display_name": "Alpha"},
            {"user_id": "u2", "display_name": "Beta"},
        ],
        rosters=[
            {
                "roster_id": 1,
                "owner_id": "u1",
                "players": ["p1", "p2"],
                "starters": ["p1", "p2"],
                "settings": {"waiver_budget_used": 25},
            },
            {
                "roster_id": 2,
                "owner_id": "u2",
                "players": ["p3", "p4"],
                "starters": ["p3"],
                "taxi": ["p4"],
                "settings": {"waiver_budget_used": 10},
            },
        ],
        players={
            "p1": {"full_name": "Quarterback One", "position": "QB", "team": "AAA", "status": "active", "age": 27},
            "p2": {"full_name": "Runner Two", "position": "RB", "team": "BBB", "status": "active", "age": "24.5"},
            "p3": {"full_name": "Quarterback Three", "position": "QB", "team": "CCC", "status": "active", "age": "unknown"},
            "p4": {"full_name": "Receiver Four", "position": "WR", "team": "DDD", "status": "active"},
        },
        traded_picks=[{"season": "2027", "round": 1, "roster_id": 1, "owner_id": 2}],
        retrieved_at=AS_OF,
    )


def test_normalizer_returns_provider_neutral_state() -> None:
    state = SleeperNormalizer().normalize(bundle(), as_of=AS_OF)

    assert state.league.league_id == "sleeper:123"
    assert state.league.rules.team_count == 2
    assert len(state.teams) == 2
    assert len(state.players) == 4
    assert state.as_of == AS_OF

    alpha = next(item for item in state.team_states if item.team_id.endswith(":team:1"))
    assert alpha.faab_balance == 75
    slots = {entry.player_id: entry.slot for entry in alpha.roster}
    assert slots["sleeper:player:p1"] == RosterSlot.QB
    assert slots["sleeper:player:p2"] == RosterSlot.RB


def test_explicit_player_age_is_preserved_without_guessing() -> None:
    state = SleeperNormalizer().normalize(bundle(), as_of=AS_OF)
    ages = {item.player_id: item.age_years for item in state.player_states}
    assert ages["sleeper:player:p1"] == 27.0
    assert ages["sleeper:player:p2"] == 24.5
    assert ages["sleeper:player:p3"] is None
    assert ages["sleeper:player:p4"] is None


def test_traded_pick_ownership_is_normalized() -> None:
    state = SleeperNormalizer().normalize(bundle(), as_of=AS_OF)
    pick = next(
        entry
        for entry in state.pick_ownership
        if entry.pick_id == "sleeper:123:pick:2027:1:1"
    )
    assert pick.owner_team_id == "sleeper:123:team:2"


def test_taxi_assignment_is_preserved() -> None:
    state = SleeperNormalizer().normalize(bundle(), as_of=AS_OF)
    beta = next(item for item in state.team_states if item.team_id.endswith(":team:2"))
    p4 = next(entry for entry in beta.roster if entry.player_id == "sleeper:player:p4")
    assert p4.slot == RosterSlot.TAXI

def test_matchup_completion_uses_sleeper_leg_and_future_zero_rows_fail_closed() -> None:
    base = bundle()
    settings = {**dict(base.league["settings"]), "leg": 3}
    league = {**dict(base.league), "settings": settings}
    with_matchups = SleeperPayloadBundle(
        league=league,
        users=base.users,
        rosters=base.rosters,
        players=base.players,
        traded_picks=base.traded_picks,
        matchups={
            "1": (
                {"matchup_id": 1, "roster_id": 1, "points": 121.5},
                {"matchup_id": 1, "roster_id": 2, "points": 99.0},
            ),
            "2": (
                {"matchup_id": 1, "roster_id": 1, "points": 0.0},
                {"matchup_id": 1, "roster_id": 2, "points": 0.0},
            ),
            "3": (
                {"matchup_id": 1, "roster_id": 1, "points": 0.0},
                {"matchup_id": 1, "roster_id": 2, "points": 0.0},
            ),
            "14": (
                {"matchup_id": 1, "roster_id": 1, "points": 0.0},
                {"matchup_id": 1, "roster_id": 2, "points": 0.0},
            ),
        },
        retrieved_at=AS_OF,
    )

    state = SleeperNormalizer().normalize(with_matchups, as_of=AS_OF)

    assert state.completed_through_week == 2
    by_week = {matchup.week: matchup for matchup in state.matchups}
    assert by_week[1].team_a_points == 121.5
    assert by_week[2].team_a_points == 0.0
    assert by_week[2].team_b_points == 0.0
    assert by_week[3].team_a_points is None
    assert by_week[3].team_b_points is None
    assert by_week[14].team_a_points is None
    assert by_week[14].team_b_points is None

def test_nfl_state_is_stronger_than_lagging_league_leg_for_matchup_completion() -> None:
    base = bundle()
    settings = {**dict(base.league["settings"]), "leg": 2}
    league = {**dict(base.league), "settings": settings}
    with_matchups = SleeperPayloadBundle(
        league=league,
        users=base.users,
        rosters=base.rosters,
        players=base.players,
        traded_picks=base.traded_picks,
        matchups={
            "1": (
                {"matchup_id": 1, "roster_id": 1, "points": 121.5},
                {"matchup_id": 1, "roster_id": 2, "points": 99.0},
            ),
            "2": (
                {"matchup_id": 1, "roster_id": 1, "points": 110.0},
                {"matchup_id": 1, "roster_id": 2, "points": 108.0},
            ),
            "3": (
                {"matchup_id": 1, "roster_id": 1, "points": 0.0},
                {"matchup_id": 1, "roster_id": 2, "points": 0.0},
            ),
        },
        nfl_state={
            "season": "2026",
            "week": 2,
            "display_week": 3,
            "season_type": "regular",
        },
        retrieved_at=AS_OF,
    )

    state = SleeperNormalizer().normalize(with_matchups, as_of=AS_OF)

    assert state.completed_through_week == 2
    by_week = {matchup.week: matchup for matchup in state.matchups}
    assert by_week[2].team_a_points == 110.0
    assert by_week[3].team_a_points is None
    assert by_week[3].team_b_points is None



def test_live_nfl_week_and_leg_beat_lagging_display_week_and_league_leg() -> None:
    base = bundle()
    settings = {**dict(base.league["settings"]), "leg": 2}
    league = {**dict(base.league), "settings": settings}
    with_matchups = SleeperPayloadBundle(
        league=league,
        users=base.users,
        rosters=base.rosters,
        players=base.players,
        traded_picks=base.traded_picks,
        matchups={
            "1": (
                {"matchup_id": 1, "roster_id": 1, "points": 121.5},
                {"matchup_id": 1, "roster_id": 2, "points": 99.0},
            ),
            "2": (
                {"matchup_id": 1, "roster_id": 1, "points": 110.0},
                {"matchup_id": 1, "roster_id": 2, "points": 108.0},
            ),
            "3": (
                {"matchup_id": 1, "roster_id": 1, "points": 0.0},
                {"matchup_id": 1, "roster_id": 2, "points": 0.0},
            ),
        },
        nfl_state={
            "season": "2026",
            "week": 3,
            "leg": 3,
            "display_week": 2,
            "season_type": "regular",
        },
        retrieved_at=AS_OF,
    )

    state = SleeperNormalizer().normalize(with_matchups, as_of=AS_OF)

    assert state.completed_through_week == 2
    by_week = {matchup.week: matchup for matchup in state.matchups}
    assert by_week[2].team_a_points == 110.0
    assert by_week[3].team_a_points is None


def test_sleeper_ppts_is_normalized_as_canonical_max_pf_with_provenance() -> None:
    base = bundle()
    rosters = []
    for roster in base.rosters:
        settings = dict(roster.get("settings") or {})
        if roster["roster_id"] == 1:
            settings.update({"ppts": 321, "ppts_decimal": 10})
        rosters.append({**dict(roster), "settings": settings})
    with_ppts = SleeperPayloadBundle(
        league=base.league,
        users=base.users,
        rosters=tuple(rosters),
        players=base.players,
        traded_picks=base.traded_picks,
        retrieved_at=AS_OF,
    )

    state = SleeperNormalizer().normalize(with_ppts, as_of=AS_OF)
    alpha = next(item for item in state.team_states if item.team_id.endswith(":team:1"))

    assert alpha.max_points_for == 321.10
    assert alpha.max_points_for_provenance is not None
    assert alpha.max_points_for_provenance.source == "sleeper:roster_settings:ppts"
    assert alpha.max_points_for_provenance.source_version == "ppts+ppts_decimal"

    beta = next(item for item in state.team_states if item.team_id.endswith(":team:2"))
    assert beta.max_points_for is None
    assert beta.max_points_for_provenance is None


def test_rostered_sleeper_dst_retains_canonical_team_identity_without_forecast_player_semantics() -> None:
    base = bundle()
    league = {
        **dict(base.league),
        "roster_positions": ["QB", "DEF", "BN", "BN"],
    }
    rosters = (
        {
            "roster_id": 1,
            "owner_id": "u1",
            "players": ["p1", "JAC"],
            "starters": ["p1", "JAC"],
            "settings": {"waiver_budget_used": 25},
        },
        base.rosters[1],
    )
    players = {
        **dict(base.players),
        "JAC": {"full_name": "Jacksonville Jaguars", "position": "DEF", "team": None, "status": "active"},
    }
    state = SleeperNormalizer().normalize(
        SleeperPayloadBundle(
            league=league,
            users=base.users,
            rosters=rosters,
            players=players,
            traded_picks=base.traded_picks,
            retrieved_at=AS_OF,
        ),
        as_of=AS_OF,
    )

    dst = next(item for item in state.players if item.player_id == "sleeper:player:JAC")
    assert dst.position == Position.DST
    assert dst.nfl_team == "JAX"
    alpha = next(item for item in state.team_states if item.team_id.endswith(":team:1"))
    dst_entry = next(item for item in alpha.roster if item.player_id == "sleeper:player:JAC")
    assert dst_entry.slot == RosterSlot.DST


def test_current_player_universe_includes_kickers_but_not_dst_pseudo_players() -> None:
    players = canonical_players_from_sleeper_player_universe(
        {
            "k1": {"full_name": "Kicker One", "position": "K", "team": "BUF"},
            "DEN": {"full_name": "Denver Broncos", "position": "DEF", "team": "DEN"},
        }
    )

    assert [(item.player_id, item.position, item.nfl_team) for item in players] == [
        ("sleeper:player:k1", Position.K, "BUF"),
    ]

from datetime import UTC, datetime

from fsffl.product.p0_forecast_runtime import frozen_p0_source_rows
from fsffl.product.p0_live_candidate_runtime import exact_state_rostered_p0_subject_ids
from fsffl.product.p0_live_candidate_runtime import (
    StatusBasedZeroRosEvidence,
    _active_bench_player_ids,
    _status_based_zero_ros,
)
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


def test_status_based_ros_zero_requires_recorded_no_participation_evidence():
    now = datetime(2026, 10, 8, tzinfo=UTC)
    player_id = "sleeper:player:11638"
    player = Player(player_id=player_id, full_name="Dynamic Player", position=Position.WR)
    provenance = Provenance(source="fixture", retrieved_at=now, effective_at=now)
    state = LeagueState(
        league=League(
            league_id="fixture-league",
            name="Fixture",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(Team(team_id="team-a", league_id="fixture-league", display_name="A"),),
        team_states=(TeamState(team_id="team-a", roster=()),),
        players=(player,),
        player_states=(PlayerState(player_id=player_id, as_of=now, provenance=provenance),),
    )
    evidence = StatusBasedZeroRosEvidence(
        player_id=player_id,
        status="out_for_season",
        source="governed-status-record",
        source_version="v1",
        observed_at=now,
        no_expected_2026_participation=True,
    )

    ros = _status_based_zero_ros(league_state=state, evidence=evidence, as_of=now)

    assert ros
    assert all(item.distribution.mean == 0 for item in ros)
    assert all(item.model_version == "status-based-zero-ros-v1:v1" for item in ros)
    assert all(item.provenance.source == "governed-status-record" for item in ros)


def test_status_based_ros_rejects_unconfirmed_injury_status():
    now = datetime(2026, 10, 8, tzinfo=UTC)
    evidence = StatusBasedZeroRosEvidence(
        player_id="sleeper:player:11638",
        status="injured",
        source="fixture",
        source_version="v1",
        observed_at=now,
        no_expected_2026_participation=False,
    )

    try:
        evidence.validate()
    except ValueError as exc:
        assert "season-long nonparticipation" in str(exc)
    else:
        raise AssertionError("temporary injury status must not authorize zero ROS")


def test_active_bench_eligibility_is_exact_state_bound():
    now = datetime(2026, 10, 8, tzinfo=UTC)
    active_id = "sleeper:player:11638"
    starter_id = "sleeper:player:12484"
    inactive_id = "sleeper:player:12510"
    players = tuple(
        Player(player_id=player_id, full_name=player_id, position=Position.WR)
        for player_id in (active_id, starter_id, inactive_id)
    )
    provenance = Provenance(source="fixture", retrieved_at=now, effective_at=now)
    state = LeagueState(
        league=League(
            league_id="fixture-league",
            name="Fixture",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=3, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(Team(team_id="team-a", league_id="fixture-league", display_name="A"),),
        team_states=(
            TeamState(
                team_id="team-a",
                roster=(
                    RosterEntry(player_id=active_id, slot=RosterSlot.BENCH),
                    RosterEntry(player_id=starter_id, slot=RosterSlot.WR),
                    RosterEntry(player_id=inactive_id, slot=RosterSlot.BENCH),
                ),
            ),
        ),
        players=players,
        player_states=(
            PlayerState(player_id=active_id, as_of=now, status="active", nfl_team="SEA", provenance=provenance),
            PlayerState(player_id=starter_id, as_of=now, status="active", nfl_team="BUF", provenance=provenance),
            PlayerState(player_id=inactive_id, as_of=now, status="inactive", nfl_team="CHI", provenance=provenance),
        ),
    )

    assert _active_bench_player_ids(state) == {active_id}

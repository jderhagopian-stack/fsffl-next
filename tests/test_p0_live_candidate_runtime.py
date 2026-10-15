from datetime import UTC, datetime, timedelta
from dataclasses import fields

from fsffl.product.p0_forecast_runtime import frozen_p0_source_rows
from fsffl.product.p0_live_candidate_runtime import exact_state_rostered_p0_subject_ids
from fsffl.product.p0_live_candidate_runtime import (
    StatusBasedZeroRosEvidence,
    _active_backup_player_ids,
    _all_ros_source_observations,
    _score_complete_single_source_year_one,
    _single_source_fumbles_gap_player_ids,
    _status_based_zero_ros,
    _catalog_evidence_cutoff,
    _source_evidence_cutoff,
)
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.product.i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
from fsffl.state.models import ScoringRule
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


def test_live_catalog_is_included_in_cutoff_and_replay_rejects_later_capture():
    import pytest

    cutoff = datetime(2026, 10, 13, 19, 0, tzinfo=UTC)
    catalog_capture = cutoff + timedelta(minutes=3)
    assert _catalog_evidence_cutoff(
        cutoff, catalog_capture, explicit_cutoff=False
    ) == catalog_capture
    with pytest.raises(ValueError, match="catalog snapshot postdates"):
        _catalog_evidence_cutoff(cutoff, catalog_capture, explicit_cutoff=True)


def test_explicit_replay_cutoff_rejects_later_ros_weekly_and_prior_inputs():
    import pytest

    cutoff = datetime(2026, 10, 13, 19, 0, tzinfo=UTC)
    later = cutoff + timedelta(minutes=3)
    captures = (
        ("REST-of-season projections", later),
        ("Sleeper weekly stats week 7", later),
        ("Sleeper prior-season stats", later),
    )
    for source, captured_at in captures:
        with pytest.raises(ValueError, match=f"{source} postdates"):
            _source_evidence_cutoff(
                cutoff, ((source, captured_at),), explicit_cutoff=True
            )
    assert _source_evidence_cutoff(
        cutoff, captures, explicit_cutoff=False
    ) == later


def test_dynamic_p0_source_row_retains_candidate_evidence_identity():
    from fsffl.product.p0_candidate_evidence import (
        P0CandidateFacts, accepted_p0_source_state_authority,
        build_p0_candidate_source_rows,
    )

    now = datetime(2026, 10, 13, tzinfo=UTC)
    reference = next(row for row in frozen_p0_source_rows() if row.position == 'QB')
    player_id = 'sleeper:player:dynamic-source-contract'
    player = Player(player_id=player_id, full_name='Dynamic QB', position=Position.QB)
    state = LeagueState(
        league=League(league_id='fixture', name='Fixture', season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=())),
        as_of=now,
        teams=(Team(team_id='a', league_id='fixture', display_name='A'),
               Team(team_id='b', league_id='fixture', display_name='B')),
        team_states=(TeamState(team_id='a', roster=()), TeamState(team_id='b', roster=())),
        players=(player,), player_states=(PlayerState(player_id=player_id, as_of=now,
            provenance=Provenance(source='fixture', retrieved_at=now, effective_at=now)),),
    )
    values = {field.name: getattr(reference, field.name)
        for field in fields(P0CandidateFacts) if hasattr(reference, field.name)}
    facts = P0CandidateFacts(**{**values,
        'player_id': player_id, 'current_player_id': player_id,
        'player_name': player.full_name, 'facts_as_of': now,
        'facts_source_version': 'accepted-live-y1-v1', 'facts_digest': 'a' * 64})
    rows = build_p0_candidate_source_rows(league_state=state,
        candidate_facts={player_id: facts},
        source_state_authority=accepted_p0_source_state_authority(), evaluation_as_of=now)
    assert rows[player_id].evidence_as_of == now.isoformat()
    assert rows[player_id].evidence_source_version == facts.facts_source_version
    assert len(rows[player_id].evidence_sha256) == 64
    assert rows[player_id].standard_y1_points == reference.standard_y1_points
    assert reference.evidence_as_of is None


def test_p0_future_contract_rejects_evidence_after_explicit_cutoff():
    import pytest
    from fsffl.product.p0_future_forecast_provider import build_p0_future_forecast_contract

    now = datetime(2026, 10, 13, tzinfo=UTC)
    row = ForecastObservation(player_id='sleeper:player:dynamic', position=Position.QB,
        horizon=ForecastHorizon.SEASON, metric=ForecastMetric.FANTASY_POINTS,
        period_start=now, period_end=datetime(2027, 1, 15, tzinfo=UTC),
        distribution=ForecastDistribution(mean=10, stddev=0),
        source='fixture', model_version='fixture', as_of=now,
        provenance=Provenance(source='fixture', retrieved_at=now, effective_at=now))
    with pytest.raises(ValueError, match='postdates evaluation cutoff'):
        build_p0_future_forecast_contract(league_state=None, raw_forecasts=(row,),
            league_year_one=(row,), evaluation_as_of=datetime(2026, 10, 12, tzinfo=UTC))
    with pytest.raises(ValueError, match='timezone-aware'):
        build_p0_future_forecast_contract(league_state=None, raw_forecasts=(),
            league_year_one=(), evaluation_as_of=datetime(2026, 10, 13))


def test_actuals_plus_ros_scores_one_complete_coordinate_across_capture_times():
    from fsffl.product.p0_live_candidate_runtime import _year_one_raw_forecasts, _score_season_points

    now = datetime(2026, 10, 13, tzinfo=UTC)
    player_id = 'sleeper:player:dynamic-qb'
    provenance = Provenance(source='fixture', retrieved_at=now, effective_at=now)
    state = LeagueState(league=League(league_id='fixture', name='Fixture', season=2026,
        rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=FROZEN_I1_STANDARD_SCORING)),
        as_of=now, teams=(), team_states=(),
        players=(Player(player_id=player_id, full_name='Dynamic QB', position=Position.QB),),
        player_states=(PlayerState(player_id=player_id, as_of=now, provenance=provenance),))
    ros = tuple(ForecastObservation(player_id=player_id, position=Position.QB,
        horizon=ForecastHorizon.REST_OF_SEASON, metric=metric,
        period_start=now, period_end=datetime(2027, 1, 15, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=0),
        source='fixture', model_version='fixture', as_of=now + timedelta(seconds=index),
        provenance=provenance)
        for index, (metric, mean) in enumerate(((ForecastMetric.PASS_YARDS,100),
            (ForecastMetric.PASS_TD,1), (ForecastMetric.INTERCEPTIONS,0),
            (ForecastMetric.RUSH_YARDS,10), (ForecastMetric.RUSH_TD,0),
            (ForecastMetric.FUMBLES_LOST,1))))
    actual = ros[0].model_copy(update={'horizon': ForecastHorizon.SEASON,
        'as_of': now + timedelta(seconds=10),
        'distribution': ForecastDistribution(mean=25, stddev=0)})
    raw = _year_one_raw_forecasts(league_state=state, completed_actuals=(actual,), ros_forecasts=ros)
    assert {item.as_of for item in raw} == {actual.as_of}
    complete, partial = _score_season_points(raw, league_state=state, standard=True)
    assert not partial
    assert complete[player_id].distribution.mean == 8.0
    from fsffl.product.p0_live_candidate_runtime import _ensemble_ros_with_fumbles
    fumbles = ros[-1]
    assert _ensemble_ros_with_fumbles((), (fumbles,)) == ()
    assert _ensemble_ros_with_fumbles(ros[:-1], (fumbles,)) == ros


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
        teams=(
            Team(team_id="team-a", league_id="fixture-league", display_name="A"),
            Team(team_id="team-b", league_id="fixture-league", display_name="B"),
        ),
        team_states=(TeamState(team_id="team-a", roster=()), TeamState(team_id="team-b", roster=())),
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


def test_active_backup_eligibility_requires_exact_state_and_depth_chart_evidence():
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
        teams=(
            Team(team_id="team-a", league_id="fixture-league", display_name="A"),
            Team(team_id="team-b", league_id="fixture-league", display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="team-a",
                roster=(
                    RosterEntry(player_id=active_id, slot=RosterSlot.BENCH),
                    RosterEntry(player_id=starter_id, slot=RosterSlot.WR),
                    RosterEntry(player_id=inactive_id, slot=RosterSlot.BENCH),
                ),
            ),
            TeamState(team_id="team-b", roster=()),
        ),
        players=players,
        player_states=(
            PlayerState(player_id=active_id, as_of=now, status="active", nfl_team="SEA", provenance=provenance),
            PlayerState(player_id=starter_id, as_of=now, status="active", nfl_team="BUF", provenance=provenance),
            PlayerState(player_id=inactive_id, as_of=now, status="inactive", nfl_team="CHI", provenance=provenance),
        ),
    )

    assert _active_backup_player_ids(
        state,
        {
            "11638": {"team": "SEA", "depth_chart_order": "2"},
            "12484": {"team": "BUF", "depth_chart_order": "1"},
            "12510": {"team": "CHI", "depth_chart_order": "2"},
        },
    ) == {active_id}
    assert _active_backup_player_ids(state, {"11638": {"team": "SEA"}}) == set()


def test_complete_single_source_year_one_is_labeled_eligible_and_missing_metrics_fail():
    now = datetime(2026, 10, 8, tzinfo=UTC)
    player_id = "sleeper:player:11638"
    player = Player(player_id=player_id, full_name="Dynamic Player", position=Position.WR)
    provenance = Provenance(source="razzball", retrieved_at=now, effective_at=now)
    state = LeagueState(
        league=League(
            league_id="fixture-league",
            name="Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(*FROZEN_I1_STANDARD_SCORING, ScoringRule(stat="rec", points=1.0)),
            ),
        ),
        as_of=now,
        teams=(
            Team(team_id="team-a", league_id="fixture-league", display_name="A"),
            Team(team_id="team-b", league_id="fixture-league", display_name="B"),
        ),
        team_states=(TeamState(team_id="team-a", roster=()), TeamState(team_id="team-b", roster=())),
        players=(player,),
        player_states=(PlayerState(player_id=player_id, as_of=now, provenance=provenance),),
    )
    stat_metrics = {
        "pass_yd": ForecastMetric.PASS_YARDS,
        "pass_td": ForecastMetric.PASS_TD,
        "pass_int": ForecastMetric.INTERCEPTIONS,
        "rush_yd": ForecastMetric.RUSH_YARDS,
        "rush_td": ForecastMetric.RUSH_TD,
        "rec_yd": ForecastMetric.REC_YARDS,
        "rec_td": ForecastMetric.REC_TD,
        "fum_lost": ForecastMetric.FUMBLES_LOST,
        "rec": ForecastMetric.RECEPTIONS,
    }

    def source_rows(*, include_fumbles: bool) -> tuple[ForecastObservation, ...]:
        return tuple(
            ForecastObservation(
                player_id=player_id,
                position=Position.WR,
                horizon=ForecastHorizon.REST_OF_SEASON,
                metric=metric,
                period_start=datetime(2026, 10, 8, tzinfo=UTC),
                period_end=datetime(2027, 1, 15, tzinfo=UTC),
                distribution=ForecastDistribution(mean=1.0, stddev=0.0, p10=1.0, p50=1.0, p90=1.0),
                source="razzball",
                model_version="captured-v1",
                as_of=now,
                provenance=provenance,
            )
            for stat, metric in stat_metrics.items()
            if include_fumbles or stat != "fum_lost"
        )

    complete = _score_complete_single_source_year_one(
        player_id=player_id,
        source_rows=source_rows(include_fumbles=True),
        completed_actuals=(),
        league_state=state,
    )
    incomplete = _score_complete_single_source_year_one(
        player_id=player_id,
        source_rows=source_rows(include_fumbles=False),
        completed_actuals=(),
        league_state=state,
    )

    assert complete is not None
    assert complete[1] is not None and complete[2] is not None
    assert {item.source for item in complete[0]} == {"fsffl:sleeper-actuals-plus-governed-ros"}
    assert incomplete is None


def test_retained_roster_ros_rows_enter_fumbles_gap_eligibility():
    now = datetime(2026, 10, 8, tzinfo=UTC)
    player_id = "sleeper:player:7567"
    provenance = Provenance(source="razzball", retrieved_at=now, effective_at=now)
    state = LeagueState(
        league=League(
            league_id="fixture-league",
            name="Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(*FROZEN_I1_STANDARD_SCORING, ScoringRule(stat="fum_lost", points=-2.0)),
            ),
        ),
        as_of=now,
        teams=(
            Team(team_id="team-a", league_id="fixture-league", display_name="A"),
            Team(team_id="team-b", league_id="fixture-league", display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="team-a",
                roster=(RosterEntry(player_id=player_id, slot=RosterSlot.BENCH),),
            ),
            TeamState(team_id="team-b", roster=()),
        ),
        players=(Player(player_id=player_id, full_name="Kenny Gainwell", position=Position.RB),),
        player_states=(PlayerState(player_id=player_id, as_of=now, provenance=provenance),),
    )
    fallback = tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.RB,
            horizon=ForecastHorizon.REST_OF_SEASON,
            metric=metric,
            period_start=now,
            period_end=datetime(2027, 1, 10, tzinfo=UTC),
            distribution=ForecastDistribution(mean=1.0, stddev=0.0),
            source="razzball",
            model_version="retained-roster-capture-v1",
            as_of=now,
            provenance=provenance,
        )
        for metric in (
            ForecastMetric.RUSH_YARDS,
            ForecastMetric.RUSH_TD,
            ForecastMetric.RECEPTIONS,
            ForecastMetric.REC_YARDS,
            ForecastMetric.REC_TD,
        )
    )
    saved_runtime = type("SavedRuntime", (), {"source_observations": ()})()

    runtime_rows = _all_ros_source_observations(saved_runtime, fallback)
    assert runtime_rows == fallback
    assert _single_source_fumbles_gap_player_ids(
        league_state=state,
        candidate_ids={player_id},
        source_observations=runtime_rows,
    ) == {player_id}


def test_single_source_fumbles_fallback_requires_primary_scoring_domain():
    now = datetime(2026, 10, 8, tzinfo=UTC)
    player_id = "sleeper:player:7567"
    provenance = Provenance(source="razzball", retrieved_at=now, effective_at=now)
    state = LeagueState(
        league=League(
            league_id="fixture-league",
            name="Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(*FROZEN_I1_STANDARD_SCORING, ScoringRule(stat="fum_lost", points=-2.0)),
            ),
        ),
        as_of=now,
        teams=(
            Team(team_id="team-a", league_id="fixture-league", display_name="A"),
            Team(team_id="team-b", league_id="fixture-league", display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="team-a",
                roster=(RosterEntry(player_id=player_id, slot=RosterSlot.BENCH),),
            ),
            TeamState(team_id="team-b", roster=()),
        ),
        players=(Player(player_id=player_id, full_name="Receiver", position=Position.WR),),
        player_states=(PlayerState(player_id=player_id, as_of=now, provenance=provenance),),
    )
    rushing_only = tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.WR,
            horizon=ForecastHorizon.REST_OF_SEASON,
            metric=metric,
            period_start=now,
            period_end=datetime(2027, 1, 10, tzinfo=UTC),
            distribution=ForecastDistribution(mean=1.0, stddev=0.0),
            source="razzball",
            model_version="retained-roster-capture-v1",
            as_of=now,
            provenance=provenance,
        )
        for metric in (ForecastMetric.RUSH_YARDS, ForecastMetric.RUSH_TD)
    )

    assert _single_source_fumbles_gap_player_ids(
        league_state=state,
        candidate_ids={player_id},
        source_observations=rushing_only,
    ) == set()

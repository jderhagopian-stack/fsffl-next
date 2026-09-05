from datetime import UTC, datetime, timedelta

from fsffl.analytics.models import AnalyticsContext, ModelLineageEntry
from fsffl.analytics.team import build_team_analytics_view
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    PickOwnership,
    Player,
    PlayerState,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.team_utility.models import LineupAssignment, OptimizedTeamLineup

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PROV = Provenance(
    source="test",
    retrieved_at=AS_OF,
    effective_at=AS_OF,
    provider_ref=ProviderRef(provider="test", external_id="x"),
)


def _state() -> LeagueState:
    league = League(
        league_id="l1",
        name="League",
        season=2026,
        rules=LeagueRules(team_count=2, roster_size=2, taxi_size=1, lineup=(), scoring=()),
    )
    teams = (
        Team(team_id="a", league_id="l1", display_name="Alpha"),
        Team(team_id="b", league_id="l1", display_name="Beta"),
    )
    players = (
        Player(player_id="p1", full_name="Starter", position=Position.QB),
        Player(player_id="p2", full_name="Bench", position=Position.WR),
        Player(player_id="p3", full_name="Taxi", position=Position.RB),
        Player(player_id="p4", full_name="Other", position=Position.TE),
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=teams,
        team_states=(
            TeamState(
                team_id="a",
                roster=(
                    RosterEntry(player_id="p2", slot=RosterSlot.BENCH),
                    RosterEntry(player_id="p1", slot=RosterSlot.BENCH),
                    RosterEntry(player_id="p3", slot=RosterSlot.TAXI),
                ),
            ),
            TeamState(team_id="b", roster=(RosterEntry(player_id="p4", slot=RosterSlot.BENCH),)),
        ),
        players=players,
        player_states=(
            PlayerState(player_id="p1", as_of=AS_OF, age_years=28.0, provenance=PROV),
            PlayerState(player_id="p2", as_of=AS_OF, age_years=25.0, provenance=PROV),
            PlayerState(player_id="p3", as_of=AS_OF, age_years=22.0, provenance=PROV),
            PlayerState(player_id="p4", as_of=AS_OF, age_years=30.0, provenance=PROV),
        ),
        draft_picks=(
            DraftPick(pick_id="pick-a", league_id="l1", season=2027, round=1, original_team_id="a"),
            DraftPick(pick_id="pick-b", league_id="l1", season=2027, round=2, original_team_id="b"),
        ),
        pick_ownership=(
            PickOwnership(pick_id="pick-a", owner_team_id="a"),
            PickOwnership(pick_id="pick-b", owner_team_id="b"),
        ),
    )


def _context(state: LeagueState) -> AnalyticsContext:
    return AnalyticsContext(
        schema_version="1",
        league_id="l1",
        league_state_id=state.state_id,
        as_of=state.as_of,
        generated_at=state.as_of + timedelta(seconds=1),
        lineage=(ModelLineageEntry(component="forecast", model_version="test"),),
    )


def _forecast(player_id: str, *, as_of=AS_OF) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=Position.QB if player_id == "p1" else Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=100),
        distribution=ForecastDistribution(mean=100.0, stddev=10.0),
        source="test",
        model_version="forecast-test",
        as_of=as_of,
        provenance=PROV,
    )


def test_team_view_preserves_roster_age_starter_and_pick_identity() -> None:
    state = _state()
    lineup = OptimizedTeamLineup(
        team_id="a",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
        assignments=(
            LineupAssignment(
                slot=RosterSlot.QB,
                slot_index=1,
                player_id="p1",
                position=Position.QB,
                expected_points=100.0,
            ),
        ),
        expected_points=100.0,
        bench_player_ids=("p2",),
        unavailable_player_ids=("p3",),
        model_version="lineup-test",
    )
    view = build_team_analytics_view(
        state,
        context=_context(state),
        team_id="a",
        forecasts=(_forecast("p1"), _forecast("p2")),
        optimized_lineup=lineup,
    )

    assert [row.player_id for row in view.players] == ["p1", "p2", "p3"]
    starter = view.players[0]
    assert starter.projected_starter
    assert starter.projected_lineup_slot == RosterSlot.QB
    assert starter.age_years == 28.0
    assert next(row for row in view.players if row.player_id == "p3").roster_slot == RosterSlot.TAXI
    assert [row.pick.pick_id for row in view.draft_picks] == ["pick-a"]


def test_team_view_filters_future_forecast_observations() -> None:
    state = _state()
    view = build_team_analytics_view(
        state,
        context=_context(state),
        team_id="a",
        forecasts=(
            _forecast("p2"),
            _forecast("p2", as_of=AS_OF + timedelta(days=1)),
        ),
    )

    row = next(row for row in view.players if row.player_id == "p2")
    assert len(row.forecasts) == 1
    assert row.forecasts[0].as_of == AS_OF


def test_team_view_requires_exact_canonical_state_identity() -> None:
    state = _state()
    bad_context = AnalyticsContext(
        schema_version="1",
        league_id="l1",
        league_state_id="wrong-state",
        as_of=state.as_of,
        generated_at=state.as_of + timedelta(seconds=1),
        lineage=(),
    )
    try:
        build_team_analytics_view(state, context=bad_context, team_id="a")
    except ValueError as exc:
        assert "state id" in str(exc)
    else:
        raise AssertionError("expected state identity rejection")

from datetime import UTC, datetime, timedelta

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
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
from fsffl.team_utility import (
    CalculatedCompetitiveState,
    CompetitiveStatePolicy,
    TeamCompetitiveOutcome,
    assemble_team_utility_vector,
)


AS_OF = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)
PROV = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _state_and_forecasts() -> tuple[LeagueState, tuple[ForecastObservation, ...]]:
    players = (
        Player(player_id="qb1", full_name="QB1", position=Position.QB),
        Player(player_id="qb2", full_name="QB2", position=Position.QB),
    )
    state = LeagueState(
        league=League(
            league_id="league:1",
            name="Test",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=2,
                lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
                scoring=(),
            ),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="team:1", league_id="league:1", display_name="One"),
            Team(team_id="team:2", league_id="league:1", display_name="Two"),
        ),
        team_states=(
            TeamState(
                team_id="team:1",
                roster=(
                    RosterEntry(player_id="qb1", slot=RosterSlot.BENCH),
                    RosterEntry(player_id="qb2", slot=RosterSlot.BENCH),
                ),
            ),
            TeamState(team_id="team:2", roster=()),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=item.player_id,
                as_of=AS_OF,
                status=PlayerStatus.ACTIVE,
                provenance=PROV,
            )
            for item in players
        ),
    )
    forecasts = tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.QB,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=AS_OF,
            period_end=AS_OF + timedelta(days=120),
            distribution=ForecastDistribution(mean=points, stddev=2.0),
            source="next2-test",
            model_version="forecast-v1",
            as_of=AS_OF,
            provenance=PROV,
        )
        for player_id, points in (("qb1", 300.0), ("qb2", 200.0))
    )
    return state, forecasts


def _outcome() -> TeamCompetitiveOutcome:
    return TeamCompetitiveOutcome(
        team_id="team:1",
        expected_wins=9.0,
        wins_stddev=1.5,
        playoff_probability=0.72,
        first_place_probability=0.22,
        simulation_count=50_000,
        simulation_model_version="sim-v1",
    )


def test_assembly_derives_resilience_and_classifies_supplied_simulation() -> None:
    state, forecasts = _state_and_forecasts()
    outcome = _outcome()
    policy = CompetitiveStatePolicy(
        developing_playoff_min=0.20,
        competitive_playoff_min=0.45,
        contender_playoff_min=0.65,
        contender_first_place_min=0.15,
        model_version="state-policy-v1",
        evidence_through=AS_OF,
        provenance="test policy",
    )

    result = assemble_team_utility_vector(
        state,
        forecasts,
        team_id="team:1",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
        competitive_outcome=outcome,
        competitive_state_policy=policy,
    )

    assert result.calculated_competitive_state == CalculatedCompetitiveState.CONTENDER
    assert result.roster_resilience is not None
    assert result.roster_resilience.largest_single_player_lineup_drop == 100.0
    assert result.competitive_outcome is outcome


def test_assembly_allows_simulation_without_inventing_state_classification() -> None:
    state, forecasts = _state_and_forecasts()
    outcome = _outcome()

    result = assemble_team_utility_vector(
        state,
        forecasts,
        team_id="team:1",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
        competitive_outcome=outcome,
    )

    assert result.competitive_outcome is outcome
    assert result.calculated_competitive_state == CalculatedCompetitiveState.UNKNOWN


def test_assembly_rejects_policy_without_simulation_outcome() -> None:
    state, forecasts = _state_and_forecasts()
    policy = CompetitiveStatePolicy(
        developing_playoff_min=0.20,
        competitive_playoff_min=0.45,
        contender_playoff_min=0.65,
        contender_first_place_min=0.15,
        model_version="state-policy-v1",
        evidence_through=AS_OF,
        provenance="test policy",
    )
    try:
        assemble_team_utility_vector(
            state,
            forecasts,
            team_id="team:1",
            as_of=AS_OF,
            horizon=ForecastHorizon.SEASON,
            competitive_state_policy=policy,
        )
    except ValueError as exc:
        assert "requires a supplied competitive outcome" in str(exc)
    else:
        raise AssertionError("expected policy without simulation outcome to fail closed")

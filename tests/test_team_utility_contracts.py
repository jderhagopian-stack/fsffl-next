from datetime import UTC, datetime

import pytest

from fsffl.team_utility import (
    CalculatedCompetitiveState,
    OwnerStrategicPosture,
    StrategicTeamView,
    TeamCompetitiveOutcome,
    TeamUtilityVector,
)


AS_OF = datetime(2026, 9, 5, 15, 15, tzinfo=UTC)


def outcome(team_id: str) -> TeamCompetitiveOutcome:
    return TeamCompetitiveOutcome(
        team_id=team_id,
        expected_wins=9.0,
        wins_stddev=2.0,
        playoff_probability=0.7,
        first_place_probability=0.2,
        simulation_count=50_000,
        simulation_model_version="sim-v1",
    )


def test_owner_posture_does_not_rewrite_calculated_state() -> None:
    calculated = TeamUtilityVector(
        team_id="team:1",
        as_of=AS_OF,
        competitive_outcome=outcome("team:1"),
        calculated_competitive_state=CalculatedCompetitiveState.CONTENDER,
        model_version="utility-vector-v1",
    )
    view = StrategicTeamView(calculated=calculated, owner_posture=OwnerStrategicPosture.REBUILD)

    assert view.calculated.calculated_competitive_state == CalculatedCompetitiveState.CONTENDER
    assert view.owner_posture == OwnerStrategicPosture.REBUILD


def test_team_utility_vector_rejects_cross_team_components() -> None:
    with pytest.raises(ValueError, match="same team"):
        TeamUtilityVector(
            team_id="team:1",
            as_of=AS_OF,
            competitive_outcome=outcome("team:2"),
            model_version="utility-vector-v1",
        )

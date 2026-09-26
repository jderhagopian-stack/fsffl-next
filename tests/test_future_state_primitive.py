from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.future_state_primitive import (
    FUTURE_STATE_PRIMITIVE_VERSION,
    build_future_state_probability_materialization,
    frozen_future_state_source_rows,
)
from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.p0_forecast_runtime import (
    build_p0_standard_future_materialization,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    ProviderRef,
    Provenance,
)


def _fixture(player_index: int = 0):
    source = frozen_future_state_source_rows()[player_index]
    now = datetime(2026, 9, 1, tzinfo=UTC)
    provenance = Provenance(
        source="future-state-primitive-fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    player = Player(
        player_id="canonical-player",
        full_name=source.player_name,
        position=Position(source.position),
        provider_refs=(
            ProviderRef(
                provider="sleeper",
                external_id=source.sleeper_external_id,
            ),
        ),
    )
    state = LeagueState(
        league=League(
            league_id="future-state-primitive-fixture",
            name="Future state primitive fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=now,
        teams=(),
        team_states=(),
        players=(player,),
        player_states=(
            PlayerState(
                player_id=player.player_id,
                as_of=now,
                provenance=provenance,
            ),
        ),
    )
    year_one = (
        ForecastObservation(
            player_id=player.player_id,
            position=player.position,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=now,
            period_end=now + timedelta(days=180),
            distribution=ForecastDistribution(
                mean=float(source.standard_y1_points),
                stddev=0.0,
            ),
            source="future-state-primitive-fixture",
            model_version="fixture-v1",
            as_of=now,
            provenance=provenance,
        ),
    )
    return state, year_one


@pytest.mark.parametrize("player_index", (0, 17, 101, 220, 334))
def test_future_state_probability_primitive_matches_legacy_p0_probability_layer_exactly(
    player_index: int,
) -> None:
    state, year_one = _fixture(player_index)
    primitive = build_future_state_probability_materialization(
        league_state=state,
        standard_year_one=year_one,
    )
    legacy = build_p0_standard_future_materialization(
        league_state=state,
        standard_year_one=year_one,
    )

    assert primitive.primitive_version == FUTURE_STATE_PRIMITIVE_VERSION
    assert set(primitive.players) == set(legacy.players) == {"canonical-player"}
    for horizon in (2, 3):
        actual = primitive.players["canonical-player"].probabilities_for(horizon)
        expected = legacy.players["canonical-player"].result_for(horizon).probabilities
        assert set(actual) == set(expected) == set(STATE_NAMES)
        for state_name in STATE_NAMES:
            assert actual[state_name] == pytest.approx(
                expected[state_name],
                abs=1e-15,
            )


def test_future_state_primitive_exposes_probability_only_not_p0_routes_or_point_results() -> None:
    state, year_one = _fixture()
    primitive = build_future_state_probability_materialization(
        league_state=state,
        standard_year_one=year_one,
    )
    player = primitive.players["canonical-player"]

    assert hasattr(player, "probabilities_for")
    assert not hasattr(player, "result_for")
    assert not hasattr(player, "route_for")
    assert not hasattr(player, "routes")
    assert not hasattr(player, "results")

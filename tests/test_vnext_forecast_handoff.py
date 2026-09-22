from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
from fsffl.product.p0_forecast_runtime import frozen_p0_source_rows
from fsffl.product.vnext_future_forecast_provider import (
    VNEXT_ARCHIVE_SHA256,
    VNEXT_CURRENT_SOURCE_PLAYER_COUNT,
    VNEXT_CURRENT_SOURCE_REFRESH_AUTHORITY,
    VNEXT_FORECAST_VERSION,
    VNEXT_MANIFEST_FILE_COUNT,
    VNEXT_NEW_PLAYER_POLICY,
    VNEXT_PROBABILITY_CANONICAL_SHA256_11DP,
    VNEXT_RESEARCH_COMMIT,
    VNEXT_STAGE_D_FORECAST_CANONICAL_SHA256_10DP,
    VNEXT_STAGE_D_PLAYER_COUNT,
    VNEXT_STAGE_D_ROW_COUNT,
    VNEXT_STAGE_D_STATE_MEAN_SHARDS_SHA256,
    _state_mean_shard_digest,
    build_vnext_future_forecast_contract,
    frozen_vnext_stage_d_state_means,
    vnext_shadow_identity,
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
    source = frozen_p0_source_rows()[player_index]
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    player = Player(
        player_id="canonical-player",
        full_name=source.player_name,
        position=Position(source.position),
        provider_refs=(
            ProviderRef(provider="sleeper", external_id=source.sleeper_external_id),
        ),
    )
    state = LeagueState(
        league=League(
            league_id="league",
            name="Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=FROZEN_I1_STANDARD_SCORING,
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
    raw = tuple(
        ForecastObservation(
            player_id=player.player_id,
            position=player.position,
            horizon=ForecastHorizon.SEASON,
            metric=metric,
            period_start=now,
            period_end=now + timedelta(days=180),
            distribution=ForecastDistribution(mean=mean, stddev=1.0),
            source="fixture-raw",
            model_version="fixture-raw-v1",
            as_of=now,
            provenance=provenance,
        )
        for metric, mean in (
            (ForecastMetric.RUSH_YARDS, float(source.standard_y1_points) * 10.0),
            (ForecastMetric.RUSH_TD, 0.0),
        )
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
                stddev=1.0,
            ),
            source="fixture-league",
            model_version="fixture-league-v1",
            as_of=now,
            provenance=provenance,
        ),
    )
    return source, state, raw, year_one


def test_frozen_vnext_identity_and_current_coordinate_are_explicit() -> None:
    assert VNEXT_ARCHIVE_SHA256 == "76b2842349093bb0f5c2bdc60995f78256d7cf6e2e4d64be84768a082450ceb1"
    assert VNEXT_RESEARCH_COMMIT == "122e802f327baf2fc7989ab635a68dfdc481d63f"
    assert VNEXT_MANIFEST_FILE_COUNT == 40
    assert VNEXT_STAGE_D_PLAYER_COUNT == 335
    assert VNEXT_STAGE_D_ROW_COUNT == 670
    assert VNEXT_CURRENT_SOURCE_PLAYER_COUNT == 335
    assert VNEXT_CURRENT_SOURCE_REFRESH_AUTHORITY == "governed_annual_preseason_source_snapshot"
    assert VNEXT_NEW_PLAYER_POLICY == "fail_closed_until_governed_source_refresh"


def test_frozen_stage_d_state_mean_shards_are_byte_identity_guarded() -> None:
    assert {
        f"{position}:{horizon}": _state_mean_shard_digest(position, horizon)
        for position in ("QB", "RB", "TE", "WR")
        for horizon in (2, 3)
    } == VNEXT_STAGE_D_STATE_MEAN_SHARDS_SHA256


def test_shadow_replay_matches_frozen_stage_d_probability_and_forecast_coordinates() -> None:
    identity = vnext_shadow_identity()
    assert identity["players"] == 335
    assert identity["rows"] == 670
    assert (
        identity["probability_canonical_sha256_11dp"]
        == VNEXT_PROBABILITY_CANONICAL_SHA256_11DP
    )
    assert (
        identity["forecast_canonical_sha256_10dp"]
        == VNEXT_STAGE_D_FORECAST_CANONICAL_SHA256_10DP
    )
    assert float(identity["max_probability_mass_error"]) <= 1e-12
    assert float(identity["max_expected_identity_error"]) <= 1e-12


def test_vnext_contract_preserves_central_probability_mean_identity_and_schema() -> None:
    source, state, raw, year_one = _fixture()
    materialized = build_vnext_future_forecast_contract(
        league_state=state,
        raw_forecasts=raw,
        league_year_one=year_one,
    )
    contract = materialized.contract
    assert contract.forecast_model_version == VNEXT_FORECAST_VERSION
    assert len(contract.forecasts) == 2
    assert contract.provenance["current_source_refresh_authority"] == (
        "governed_annual_preseason_source_snapshot"
    )
    assert contract.provenance["new_player_policy"] == (
        "fail_closed_until_governed_source_refresh"
    )
    assert contract.provenance["runtime_generalizes_beyond_frozen_source_coordinate"] is False

    for row in contract.forecasts:
        probabilities = {
            scenario.scenario_id: float(scenario.probability)
            for scenario in row.scenarios
        }
        means = {
            scenario.scenario_id: float(scenario.fantasy_points)
            for scenario in row.scenarios
        }
        assert set(probabilities) == set(STATE_NAMES)
        assert sum(probabilities.values()) == pytest.approx(1.0, abs=1e-12)
        assert row.central_expectation == pytest.approx(
            sum(probabilities[state_name] * means[state_name] for state_name in STATE_NAMES),
            abs=1e-10,
        )
        expected_standard = frozen_vnext_stage_d_state_means(
            source.position,
            row.year_index,
            source.sleeper_external_id,
        )
        for state_name in STATE_NAMES[1:]:
            assert means[state_name] == pytest.approx(
                float(expected_standard[state_name]),
                abs=1e-10,
            )
        assert row.p10 is not None
        assert row.p25 is not None
        assert row.p50 is not None
        assert row.p75 is not None
        assert row.p90 is not None
        assert row.p10 <= row.p25 <= row.p50 <= row.p75 <= row.p90


def test_vnext_current_coordinate_fails_closed_for_player_outside_governed_refresh() -> None:
    _, state, raw, year_one = _fixture()
    unknown = state.players[0].model_copy(
        update={
            "player_id": "unmapped-player",
            "full_name": "Unmapped Player",
            "provider_refs": (),
        }
    )
    unknown_state = state.model_copy(
        update={
            "players": (unknown,),
            "player_states": (
                state.player_states[0].model_copy(
                    update={"player_id": "unmapped-player"}
                ),
            ),
        }
    )
    unknown_raw = tuple(
        item.model_copy(update={"player_id": "unmapped-player"})
        for item in raw
    )
    unknown_year_one = tuple(
        item.model_copy(update={"player_id": "unmapped-player"})
        for item in year_one
    )
    with pytest.raises(ValueError, match="current source"):
        build_vnext_future_forecast_contract(
            league_state=unknown_state,
            raw_forecasts=unknown_raw,
            league_year_one=unknown_year_one,
        )

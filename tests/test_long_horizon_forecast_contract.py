from __future__ import annotations

import pytest
from pydantic import ValidationError

from fsffl.forecast.long_horizon_contract import (
    LONG_HORIZON_AUTHORITY_MAP_SHA256,
    LONG_HORIZON_AUTHORITY_MAP_VERSION,
    LONG_HORIZON_POLICIES,
    LongHorizonForecastAuthorityContract,
    LongHorizonPolicyForecast,
    supported_long_horizon_policies,
)
from fsffl.state.models import Position


def _row(
    *,
    player_id: str = "p1",
    position: Position = Position.WR,
    year_index: int = 4,
    policy_id: str = "baseline",
    central: float = 120.0,
) -> LongHorizonPolicyForecast:
    return LongHorizonPolicyForecast(
        player_id=player_id,
        position=position,
        evaluation_season=2026,
        year_index=year_index,
        target_season=2026 + year_index - 1,
        policy_id=policy_id,
        central_expectation=central,
        absolute_error_80=20.0,
        absolute_error_90=35.0,
        model_version=f"{policy_id}-fixture-v1",
        source="fixture",
        evidence_path="frozen-research-authority",
    )


def _complete_player(
    *,
    player_id: str = "p1",
    position: Position = Position.WR,
) -> tuple[LongHorizonPolicyForecast, ...]:
    return tuple(
        _row(
            player_id=player_id,
            position=position,
            year_index=year_index,
            policy_id=policy,
            central=100.0 + year_index + index,
        )
        for year_index in (4, 5, 6, 7)
        for index, policy in enumerate(LONG_HORIZON_POLICIES)
    )


def test_frozen_y4_y7_authority_map_preserves_exact_and_set_valued_cells() -> None:
    assert len(LONG_HORIZON_AUTHORITY_MAP_SHA256) == 64
    assert LONG_HORIZON_AUTHORITY_MAP_VERSION == "y4-y7-symmetric-authority-20260927-v1"

    assert supported_long_horizon_policies(Position.QB, 5) == ("blanket_75_25",)
    assert supported_long_horizon_policies(Position.WR, 5) == ("hard_router",)
    assert set(supported_long_horizon_policies(Position.RB, 4)) == set(
        LONG_HORIZON_POLICIES
    )
    assert set(supported_long_horizon_policies(Position.TE, 7)) == {
        "baseline",
        "blanket_75_25",
        "soft_stack",
    }


def test_long_horizon_contract_requires_all_four_policy_boards_for_y4_y7() -> None:
    rows = _complete_player()
    contract = LongHorizonForecastAuthorityContract(
        evaluation_season=2026,
        forecast_model_version="long-horizon-fixture-v1",
        forecast_source="fixture",
        forecasts=rows,
    )

    assert contract.player_ids == ("p1",)
    assert len(contract.forecasts) == 16
    assert [
        row.policy_id
        for row in contract.rows_for(player_id="p1", year_index=5)
    ] == sorted(LONG_HORIZON_POLICIES)


def test_transport_rejects_missing_global_policy_even_when_player_cell_is_set_valued() -> None:
    rows = tuple(
        row
        for row in _complete_player(position=Position.RB)
        if not (row.year_index == 4 and row.policy_id == "baseline")
    )
    with pytest.raises(ValidationError, match="carry all four frozen policies"):
        LongHorizonForecastAuthorityContract(
            evaluation_season=2026,
            forecast_model_version="long-horizon-fixture-v1",
            forecast_source="fixture",
            forecasts=rows,
        )


def test_y8_cardinal_transport_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _row(year_index=8)


def test_90_band_cannot_be_narrower_than_80_band() -> None:
    with pytest.raises(ValidationError, match="cannot be narrower"):
        LongHorizonPolicyForecast(
            player_id="p1",
            position=Position.WR,
            evaluation_season=2026,
            year_index=4,
            target_season=2029,
            policy_id="soft_stack",
            central_expectation=120.0,
            absolute_error_80=30.0,
            absolute_error_90=20.0,
            model_version="fixture-v1",
            source="fixture",
            evidence_path="fixture",
        )


def test_authority_map_identity_fails_closed_if_mutated() -> None:
    with pytest.raises(ValidationError, match="authority-map hash"):
        LongHorizonForecastAuthorityContract(
            evaluation_season=2026,
            authority_map_sha256="0" * 64,
            forecast_model_version="long-horizon-fixture-v1",
            forecast_source="fixture",
            forecasts=_complete_player(),
        )

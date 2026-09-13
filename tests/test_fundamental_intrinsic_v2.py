from __future__ import annotations

from datetime import UTC, datetime

from fsffl.forecast.intrinsic_v1 import (
    ForecastEvidenceStrength,
    IntrinsicV1ForecastHorizon,
    IntrinsicV1ForecastMethod,
    IntrinsicV1PlayerForecastPath,
)
from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import PlayerState, PlayerStatus, Position, Provenance
from fsffl.value.intrinsic_v2 import (
    INTRINSIC_DISPLAY_SCALE_VERSION,
    INTRINSIC_TERMINAL_MODEL_VERSION,
    INTRINSIC_VALUE_V2_VERSION,
    estimate_intrinsic_value_v2,
    intrinsic_display_value,
)


AS_OF = datetime(2026, 9, 13, tzinfo=UTC)


def _path(position: Position, means=(100.0, 90.0, 80.0), sds=(15.0, 18.0, 20.0)):
    methods = (
        IntrinsicV1ForecastMethod.AUTHORITATIVE_CURRENT,
        IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION,
        IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION,
    )
    return IntrinsicV1PlayerForecastPath(
        player_id="player:test",
        position=position,
        evaluation_as_of=AS_OF,
        base_forecast_model_version="forecast:test",
        horizons=tuple(
            IntrinsicV1ForecastHorizon(
                horizon_year=index + 1,
                distribution=ForecastDistribution(mean=mean, stddev=sd),
                method=methods[index],
                evidence_strength=(
                    ForecastEvidenceStrength.HIGH if index == 0 else ForecastEvidenceStrength.MODERATE
                ),
                provenance_note="test",
            )
            for index, (mean, sd) in enumerate(zip(means, sds, strict=True))
        ),
    )


def _state(*, draft_number: int | None = None, draft_round: int | None = None):
    return PlayerState(
        player_id="player:test",
        as_of=AS_OF,
        age_years=24.0,
        experience_years=2,
        draft_year=2024,
        draft_round=draft_round,
        draft_number=draft_number,
        status=PlayerStatus.ACTIVE,
        provenance=Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF),
    )


def test_fundamental_value_includes_post_y3_continuation():
    estimate = estimate_intrinsic_value_v2(player_path=_path(Position.WR), player_state=_state(draft_number=12))
    assert estimate.raw_terminal_value > 0
    assert estimate.raw_fundamental_career_value > estimate.raw_discounted_y1_y3
    assert estimate.terminal.model_version == INTRINSIC_TERMINAL_MODEL_VERSION


def test_pedigree_is_residual_terminal_information_not_forecast_replacement():
    path = _path(Position.RB)
    early = estimate_intrinsic_value_v2(player_path=path, player_state=_state(draft_number=20))
    late = estimate_intrinsic_value_v2(player_path=path, player_state=_state(draft_number=220))
    assert early.raw_discounted_y1_y3 == late.raw_discounted_y1_y3
    assert early.raw_terminal_value > late.raw_terminal_value
    assert early.fundamental_value > late.fundamental_value


def test_missing_pedigree_uses_governed_position_baseline_not_zero():
    estimate = estimate_intrinsic_value_v2(player_path=_path(Position.TE), player_state=_state())
    assert estimate.raw_terminal_value > 0
    assert estimate.terminal.pedigree_band is None
    assert estimate.terminal.pedigree_residual_value == 0


def test_positive_developmental_forecast_has_nonzero_asset_value():
    estimate = estimate_intrinsic_value_v2(
        player_path=_path(Position.WR, means=(22.0, 35.0, 48.0), sds=(12.0, 18.0, 25.0)),
        player_state=_state(draft_number=50),
    )
    assert estimate.raw_fundamental_career_value > 0
    assert estimate.display_value > 0


def test_display_scale_is_strictly_monotone_and_bounded():
    inputs = (0.0, 1.0, 10.0, 25.0, 50.0, 100.0, 170.0, 300.0)
    values = [intrinsic_display_value(value) for value in inputs]
    assert values[0] == 0
    assert values == sorted(values)
    assert len(set(values)) == len(values)
    assert all(0 <= value <= 10_000 for value in values)


def test_versioning_and_determinism_are_explicit():
    path = _path(Position.QB, means=(280.0, 240.0, 210.0), sds=(35.0, 45.0, 55.0))
    state = _state(draft_number=7)
    first = estimate_intrinsic_value_v2(player_path=path, player_state=state)
    second = estimate_intrinsic_value_v2(player_path=path, player_state=state)
    assert first == second
    assert first.model_version == INTRINSIC_VALUE_V2_VERSION
    assert first.display_scale_version == INTRINSIC_DISPLAY_SCALE_VERSION


def test_player_state_preserves_optional_pit_career_and_pedigree_evidence():
    state = _state(draft_number=42, draft_round=2)
    assert state.experience_years == 2
    assert state.draft_year == 2024
    assert state.draft_round == 2
    assert state.draft_number == 42

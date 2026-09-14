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
    INTRINSIC_CALIBRATION_VERSION,
    INTRINSIC_DISPLAY_SCALE_VERSION,
    INTRINSIC_VALUE_V2_VERSION,
    IntrinsicV2EvidenceState,
    estimate_intrinsic_value_v2,
    intrinsic_display_value,
)


AS_OF = datetime(2026, 9, 12, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _path(
    position: Position,
    *,
    means: tuple[float, float, float],
    sds: tuple[float, float, float],
) -> IntrinsicV1PlayerForecastPath:
    horizons = tuple(
        IntrinsicV1ForecastHorizon(
            horizon_year=year,
            distribution=ForecastDistribution(mean=mean, stddev=sd),
            method=(
                IntrinsicV1ForecastMethod.AUTHORITATIVE_CURRENT
                if year == 1
                else IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION
            ),
            evidence_strength=(ForecastEvidenceStrength.HIGH if year == 1 else ForecastEvidenceStrength.MODERATE),
            cumulative_survival_probability=1.0,
            evidence_model_version="test-forecast",
            provenance_note="test",
        )
        for year, mean, sd in zip((1, 2, 3), means, sds, strict=True)
    )
    return IntrinsicV1PlayerForecastPath(
        player_id="player:test",
        position=position,
        evaluation_as_of=AS_OF,
        base_forecast_model_version="test-forecast",
        horizons=horizons,
    )


def _state(*, draft_number: int | None = 10, draft_round: int | None = 1) -> PlayerState:
    return PlayerState(
        player_id="player:test",
        as_of=AS_OF,
        age_years=26.0,
        experience_years=2,
        draft_year=2024,
        draft_round=draft_round,
        draft_number=draft_number,
        status=PlayerStatus.ACTIVE,
        provenance=PROVENANCE,
    )


def test_shared_raw_coordinate_is_not_position_normalized():
    values = {}
    for position in (Position.QB, Position.RB, Position.WR, Position.TE):
        estimate = estimate_intrinsic_value_v2(
            player_path=_path(position, means=(100.0, 90.0, 80.0), sds=(10.0, 10.0, 10.0)),
            player_state=_state(draft_number=None),
        )
        values[position] = estimate.raw_discounted_y1_y3
    assert len(set(values.values())) == 1


def test_state_conditioned_aging_reduces_late_rb_continuation():
    path = _path(Position.RB, means=(250.0, 180.0, 120.0), sds=(40.0, 45.0, 50.0))
    prime_state = _state()
    prime_state = prime_state.model_copy(update={"age_years": 25.0})
    late_state = prime_state.model_copy(update={"age_years": 32.0})
    prime = estimate_intrinsic_value_v2(player_path=path, player_state=prime_state)
    late = estimate_intrinsic_value_v2(player_path=path, player_state=late_state)
    assert late.raw_terminal_value < prime.raw_terminal_value


def test_structural_factor_converts_football_value_into_economic_value():
    path = _path(Position.QB, means=(300.0, 260.0, 230.0), sds=(30.0, 35.0, 40.0))
    neutral = estimate_intrinsic_value_v2(player_path=path, player_state=_state(), structural_factor=1.0)
    pressured = estimate_intrinsic_value_v2(
        player_path=path,
        player_state=_state(),
        structural_factor=1.8,
        structural_starter_demand=24,
        structural_effective_supply=37.0,
    )
    assert pressured.pre_structural_fundamental_value == neutral.pre_structural_fundamental_value
    assert pressured.fundamental_value == neutral.pre_structural_fundamental_value * 1.8
    assert pressured.fundamental_stddev == neutral.raw_fundamental_stddev * 1.8
    assert pressured.structural_starter_demand == 24
    assert pressured.structural_effective_supply == 37.0


def test_missing_pedigree_is_neutral_not_undrafted():
    estimate = estimate_intrinsic_value_v2(
        player_path=_path(Position.RB, means=(160.0, 125.0, 95.0), sds=(35.0, 40.0, 45.0)),
        player_state=_state(draft_number=None),
    )
    assert estimate.residual_fundamental_value == 0
    assert estimate.evidence_state == IntrinsicV2EvidenceState.PARTIAL
    assert "no residual pedigree adjustment is fabricated" in estimate.evidence_note


def test_positive_developmental_forecast_has_nonzero_asset_value():
    estimate = estimate_intrinsic_value_v2(
        player_path=_path(Position.WR, means=(22.0, 35.0, 48.0), sds=(12.0, 18.0, 25.0)),
        player_state=_state(draft_number=50),
    )
    assert estimate.raw_fundamental_career_value > 0
    assert estimate.display_value > 0


def test_display_scale_is_strictly_monotone_across_economic_reference_tiers_and_bounded():
    inputs = (0.0, 121.45, 153.53, 241.64, 398.47, 860.30, 1431.17, 1783.30, 2200.0, 3000.0)
    values = [intrinsic_display_value(value) for value in inputs]
    assert values[0] == 0
    assert values == sorted(values)
    assert len(set(values)) == len(values)
    assert all(0 <= value <= 10_000 for value in values)
    assert 1950 <= intrinsic_display_value(121.44812067567622) <= 2050
    assert 6450 <= intrinsic_display_value(241.62841665403283) <= 6550
    assert 7950 <= intrinsic_display_value(398.4623347230747) <= 8050
    assert 8950 <= intrinsic_display_value(860.2953473881821) <= 9050
    assert 9650 <= intrinsic_display_value(1783.2893275391143) <= 9750
    assert intrinsic_display_value(3000.0) < 10_000


def test_versioning_and_determinism_are_explicit():
    path = _path(Position.QB, means=(280.0, 240.0, 210.0), sds=(35.0, 45.0, 55.0))
    state = _state(draft_number=7)
    first = estimate_intrinsic_value_v2(player_path=path, player_state=state)
    second = estimate_intrinsic_value_v2(player_path=path, player_state=state)
    assert first == second
    assert first.model_version == INTRINSIC_VALUE_V2_VERSION
    assert first.calibration_version == INTRINSIC_CALIBRATION_VERSION
    assert first.display_scale_version == INTRINSIC_DISPLAY_SCALE_VERSION


def test_player_state_preserves_optional_pit_career_and_pedigree_evidence():
    state = _state(draft_number=42, draft_round=2)
    assert state.experience_years == 2
    assert state.draft_year == 2024
    assert state.draft_round == 2
    assert state.draft_number == 42


def test_uncertainty_changes_uncertainty_not_base_career_mean():
    low = estimate_intrinsic_value_v2(
        player_path=_path(Position.WR, means=(100, 90, 80), sds=(5, 5, 5)),
        player_state=_state(),
    )
    high = estimate_intrinsic_value_v2(
        player_path=_path(Position.WR, means=(100, 90, 80), sds=(50, 50, 50)),
        player_state=_state(),
    )
    assert low.raw_fundamental_career_value == high.raw_fundamental_career_value
    assert low.fundamental_stddev < high.fundamental_stddev


def test_no_market_team_or_replacement_input_is_required():
    estimate = estimate_intrinsic_value_v2(
        player_path=_path(Position.QB, means=(250, 230, 205), sds=(30, 40, 50)),
        player_state=_state(),
    )
    assert estimate.fundamental_value >= 0
    assert estimate.display_value >= 0

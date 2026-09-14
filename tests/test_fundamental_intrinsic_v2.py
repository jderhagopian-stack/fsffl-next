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
    INTRINSIC_TERMINAL_MODEL_VERSION,
    INTRINSIC_VALUE_V2_VERSION,
    IntrinsicV2EvidenceState,
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
                evidence_strength=ForecastEvidenceStrength.HIGH if index == 0 else ForecastEvidenceStrength.MODERATE,
                provenance_note="test",
            )
            for index, (mean, sd) in enumerate(zip(means, sds, strict=True))
        ),
    )


def _state(*, age: float = 24.0, experience: int = 2, draft_number: int | None = None, draft_round: int | None = None):
    return PlayerState(
        player_id="player:test",
        as_of=AS_OF,
        age_years=age,
        experience_years=experience,
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
    assert estimate.terminal.calibration_version == INTRINSIC_CALIBRATION_VERSION


def test_aging_non_qb_continuation_tapers_without_youth_bonus():
    path = _path(Position.RB, means=(200.0, 150.0, 100.0))
    prime = estimate_intrinsic_value_v2(player_path=path, player_state=_state(age=25, experience=3, draft_number=40))
    veteran = estimate_intrinsic_value_v2(player_path=path, player_state=_state(age=28, experience=6, draft_number=40))
    late = estimate_intrinsic_value_v2(player_path=path, player_state=_state(age=32, experience=10, draft_number=40))
    assert prime.terminal.applied_factor == prime.terminal.position_baseline_factor
    assert veteran.terminal.applied_factor < prime.terminal.applied_factor
    assert late.terminal.applied_factor < veteran.terminal.applied_factor
    assert late.raw_terminal_value < veteran.raw_terminal_value < prime.raw_terminal_value


def test_qb_continuation_keeps_validated_parent_factor():
    path = _path(Position.QB, means=(300.0, 270.0, 240.0))
    young = estimate_intrinsic_value_v2(player_path=path, player_state=_state(age=24, experience=2, draft_number=7))
    old = estimate_intrinsic_value_v2(player_path=path, player_state=_state(age=35, experience=13, draft_number=7))
    assert young.terminal.applied_factor == young.terminal.position_baseline_factor
    assert old.terminal.applied_factor == old.terminal.position_baseline_factor


def test_final_raw_coordinate_is_shared_football_magnitude_not_position_normalized():
    means = (300.0, 270.0, 240.0)
    qb = estimate_intrinsic_value_v2(player_path=_path(Position.QB, means=means), player_state=_state(draft_number=None))
    te = estimate_intrinsic_value_v2(player_path=_path(Position.TE, means=means), player_state=_state(draft_number=None))
    # With missing pedigree and prime-age parent continuation, differences come
    # from football-career continuation only; no per-position divide-to-100 exists.
    assert qb.fundamental_value == qb.raw_fundamental_career_value
    assert te.fundamental_value == te.raw_fundamental_career_value
    assert qb.fundamental_value > 500
    assert te.fundamental_value > 500


def test_pedigree_is_residual_value_after_forecast_not_terminal_replacement():
    path = _path(Position.RB)
    early = estimate_intrinsic_value_v2(player_path=path, player_state=_state(draft_number=20))
    late = estimate_intrinsic_value_v2(player_path=path, player_state=_state(draft_number=220))
    assert early.raw_discounted_y1_y3 == late.raw_discounted_y1_y3
    assert early.raw_terminal_value == late.raw_terminal_value
    assert early.terminal.pedigree_forecast_explained == late.terminal.pedigree_forecast_explained
    assert early.terminal.pedigree_residual_value > late.terminal.pedigree_residual_value
    assert early.fundamental_value > late.fundamental_value


def test_missing_pedigree_is_neutral_and_explicitly_partial_not_known_undrafted():
    estimate = estimate_intrinsic_value_v2(player_path=_path(Position.TE), player_state=_state())
    assert estimate.raw_terminal_value > 0
    assert estimate.terminal.pedigree_score is None
    assert estimate.terminal.pedigree_residual_value == 0
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


def test_display_scale_is_strictly_monotone_across_reference_tiers_and_bounded():
    inputs = (0.0, 10.53, 46.18, 107.34, 148.60, 200.22, 276.92, 404.19, 529.13, 640.20, 789.63, 1200.0, 2000.0)
    values = [intrinsic_display_value(value) for value in inputs]
    assert values[0] == 0
    assert values == sorted(values)
    assert len(set(values)) == len(values)
    assert all(0 <= value <= 10_000 for value in values)
    assert 7900 <= intrinsic_display_value(404.18990857971215) <= 8100
    assert 8950 <= intrinsic_display_value(789.6239953076092) <= 9050
    assert intrinsic_display_value(2000.0) < 10_000


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
        player_state=_state(draft_number=10),
    )
    assert estimate.fundamental_value > 0
    assert estimate.display_value > 0

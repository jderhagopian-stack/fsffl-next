"""Focused research gates for model-era and weekly participation evidence."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from fsffl.analytics.forecast_strength_readiness import (
    CompletedForecastReceipt,
    ExplicitWeekAvailability,
    OptimizedStarterStatus,
    audit_forecast_readiness,
)


T0 = datetime(2026, 11, 20, 15, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 11, 12, 23, tzinfo=timezone.utc)
FINISHED = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


def _receipt(**changes):
    base = CompletedForecastReceipt(
        "artifact-1", 10, "v18-season", "season",
        KICKOFF - timedelta(hours=3), KICKOFF, FINISHED, 103.0, 113.0,
    )
    return replace(base, **changes)


def _audit(receipts=(), starters=(), facts=()):
    return audit_forecast_readiness(
        target_week=11, as_of=T0,
        current_model_regime="v19-native-ros",
        current_lineup_horizon="rest_of_season",
        receipts=receipts, optimized_starters=starters,
        week_availability=facts,
    )


def test_old_season_model_does_not_calibrate_new_ros_model():
    result = _audit((_receipt(),))
    assert not result.validation_eligible
    assert not result.publication_ready
    assert result.compatible_mean_projection_error is None
    assert result.incompatible_model_artifact_ids == ("artifact-1",)
    assert "historical_model_regime_mismatch" in result.reasons


def test_compatible_completed_model_is_validation_eligible_not_publication_ready():
    a = _receipt(model_regime="v19-native-ros", lineup_horizon="rest_of_season")
    result = _audit((a,))
    assert result.validation_eligible
    assert result.compatible_completed_weeks == (10,)
    assert result.compatible_mean_projection_error == pytest.approx(10.0)
    assert not result.publication_ready


def test_no_completed_history_is_explicit_not_zero_projection_error():
    result = _audit()
    assert result.compatible_mean_projection_error is None
    assert "no_compatible_completed_forecast_regime" in result.reasons


def test_future_week_outcomes_are_rejected():
    with pytest.raises(ValueError, match="future"):
        _audit((_receipt(week=11),))


def test_post_asof_results_are_rejected():
    with pytest.raises(ValueError, match="future"):
        _audit((_receipt(week_completed_at=T0 + timedelta(days=1)),))


def test_postkickoff_forecast_is_never_treated_as_pregame():
    with pytest.raises(ValueError, match="predate"):
        _receipt(forecast_computed_at=KICKOFF + timedelta(seconds=1))


def test_injured_optimized_starter_without_week_fact_is_flagged_not_zeroed():
    result = _audit(starters=(OptimizedStarterStatus("team", "puka", "injured"),))
    assert result.unverified_starter_player_ids == ("puka",)
    assert result.confirmed_unavailable_starter_player_ids == ()
    assert "injury_or_status_without_exact_week_participation" in result.reasons


def test_exact_available_fact_clears_ambiguity_but_does_not_claim_started():
    result = _audit(
        starters=(OptimizedStarterStatus("team", "puka", "injured"),),
        facts=(ExplicitWeekAvailability(11, "puka", "available"),)
    )
    assert result.unverified_starter_player_ids == ()
    assert result.confirmed_available_starter_player_ids == ("puka",)


def test_exact_unavailable_fact_requires_week_specific_lineup_exclusion():
    result = _audit(
        starters=(OptimizedStarterStatus("team", "puka", "active"),),
        facts=(ExplicitWeekAvailability(11, "puka", "unavailable"),)
    )
    assert result.confirmed_unavailable_starter_player_ids == ("puka",)
    assert "baseline_optimized_starter_explicitly_unavailable" in result.reasons


def test_healthy_status_without_week_fact_does_not_fabricate_injury():
    result = _audit(starters=(OptimizedStarterStatus("team", "qb", "active"),))
    assert not result.unverified_starter_player_ids
    assert not result.confirmed_unavailable_starter_player_ids


def test_different_model_versions_are_not_automatically_assumed_equivalent():
    a = _receipt(model_regime="v19-native-ros", lineup_horizon="season")
    result = _audit((a,))
    assert not result.validation_eligible


def test_duplicate_receipts_and_week_facts_rejected():
    row = _receipt()
    with pytest.raises(ValueError, match="duplicate archived"):
        _audit((row, row))
    fact = ExplicitWeekAvailability(11, "puka", "available")
    with pytest.raises(ValueError, match="duplicate weekly"):
        _audit(facts=(fact, fact))


def test_duplicate_player_identity_rejected():
    s = OptimizedStarterStatus("team", "player", "injured")
    with pytest.raises(ValueError, match="duplicate optimized"):
        _audit(starters=(s, s))


def test_invalid_scoring_values_and_missing_timezones_fail_closed():
    with pytest.raises(ValueError, match="nonnegative finite"):
        _receipt(league_actual_mean=float("nan"))
    with pytest.raises(ValueError, match="timezone-aware"):
        audit_forecast_readiness(
            target_week=11, as_of=datetime(2026, 11, 20),
            current_model_regime="v19", current_lineup_horizon="rest_of_season",
            receipts=(), optimized_starters=(), week_availability=()
        )


def test_week_availability_requires_explicit_binary_evidence():
    with pytest.raises(ValueError, match="explicit"):
        ExplicitWeekAvailability(11, "player", "unknown")

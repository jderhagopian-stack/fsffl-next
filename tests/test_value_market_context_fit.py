from datetime import UTC, datetime

import pytest

from fsffl.value import (
    CalibrationEvidenceKind,
    CalibrationObservation,
    CalibrationPanel,
    DataRightsClass,
    MarketContextFitPolicy,
    fit_market_context_calibration,
)

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def _row(value: float, *, format_id: str | None, league_id: str | None) -> CalibrationObservation:
    return CalibrationObservation(
        source_id="test-source",
        evidence_kind=CalibrationEvidenceKind.COMPLETED_TRANSACTION,
        observed_at=NOW,
        asset_id="player:1",
        league_context_id=league_id,
        format_context_id=format_id,
        metric="market_residual",
        value=value,
        rights_class=DataRightsClass.PRIVATE_RETAINED,
    )


def test_fit_market_context_uses_explicit_partial_pooling() -> None:
    panel = CalibrationPanel(
        observations=(
            _row(10.0, format_id="sf", league_id="league-a"),
            _row(14.0, format_id="sf", league_id="league-a"),
            _row(6.0, format_id="sf", league_id="league-b"),
            _row(2.0, format_id="1qb", league_id="league-c"),
        ),
        as_of=NOW,
        panel_version="panel-v1",
    )
    policy = MarketContextFitPolicy(
        residual_metric="market_residual",
        format_prior_strength=3.0,
        league_prior_strength=2.0,
        model_version="market-context-fit-v1",
    )

    calibration = fit_market_context_calibration(
        panel,
        global_context_id="global",
        format_context_id="sf",
        league_context_id="league-a",
        policy=policy,
        fitted_at=NOW,
    )

    # SF mean is 10, based on three rows. Weight = 3/(3+3)=0.5.
    assert calibration.format_offset == pytest.approx(10.0)
    assert calibration.format_shrinkage_weight == pytest.approx(0.5)
    # League A mean is 12, therefore its residual vs SF is +2. Two rows with
    # prior strength two gives weight 2/(2+2)=0.5.
    assert calibration.league_offset == pytest.approx(2.0)
    assert calibration.league_shrinkage_weight == pytest.approx(0.5)
    assert calibration.format_sample_size == 3
    assert calibration.league_sample_size == 2


def test_fit_market_context_with_no_league_history_stays_at_broader_prior() -> None:
    panel = CalibrationPanel(
        observations=(
            _row(8.0, format_id="sf", league_id="league-a"),
            _row(12.0, format_id="sf", league_id="league-b"),
        ),
        as_of=NOW,
        panel_version="panel-v1",
    )
    policy = MarketContextFitPolicy(
        residual_metric="market_residual",
        format_prior_strength=2.0,
        league_prior_strength=2.0,
        model_version="market-context-fit-v1",
    )

    calibration = fit_market_context_calibration(
        panel,
        global_context_id="global",
        format_context_id="sf",
        league_context_id="new-league",
        policy=policy,
        fitted_at=NOW,
    )

    assert calibration.league_sample_size == 0
    assert calibration.league_offset == 0.0
    assert calibration.league_shrinkage_weight == 0.0
    assert calibration.format_shrinkage_weight > 0


def test_fit_market_context_rejects_future_panel() -> None:
    later = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
    panel = CalibrationPanel(
        observations=(_row(8.0, format_id="sf", league_id="league-a"),),
        as_of=later,
        panel_version="panel-v1",
    )
    policy = MarketContextFitPolicy(
        residual_metric="market_residual",
        format_prior_strength=2.0,
        league_prior_strength=2.0,
        model_version="market-context-fit-v1",
    )

    with pytest.raises(ValueError, match="before panel as_of"):
        fit_market_context_calibration(
            panel,
            global_context_id="global",
            format_context_id="sf",
            league_context_id="league-a",
            policy=policy,
            fitted_at=NOW,
        )

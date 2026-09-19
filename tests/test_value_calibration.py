from datetime import UTC, datetime, timedelta

import pytest

from fsffl.value.calibration import (
    CalibrationEvidenceKind,
    CalibrationFitMetadata,
    CalibrationObservation,
    CalibrationPanel,
    DataRightsClass,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def observation(**overrides):
    values = dict(
        source_id="source-a",
        evidence_kind=CalibrationEvidenceKind.COMPLETED_TRANSACTION,
        observed_at=NOW - timedelta(days=1),
        asset_id="player:1",
        league_context_id="league:1",
        format_context_id="12-team-sf-half-ppr",
        metric="implied_value",
        value=100.0,
        rights_class=DataRightsClass.RUNTIME_ONLY,
        source_version="2026-09-04",
        provenance_uri="runtime://source-a/2026-09-04",
    )
    values.update(overrides)
    return CalibrationObservation(**values)


def test_panel_rejects_future_information() -> None:
    with pytest.raises(ValueError, match="observed after as_of"):
        CalibrationPanel(
            observations=(observation(observed_at=NOW + timedelta(seconds=1)),),
            as_of=NOW,
            panel_version="next3-panel-v1",
        )


def test_panel_can_be_reused_by_evidence_kind_and_league() -> None:
    league_one = observation(source_id="source-b")
    league_two = observation(
        source_id="source-a",
        evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
        league_context_id="league:2",
        metric="market_value",
    )
    panel = CalibrationPanel(
        observations=(league_one, league_two),
        as_of=NOW,
        panel_version="next3-panel-v1",
    )

    assert panel.sources() == ("source-a", "source-b")
    assert panel.by_league("league:1") == (league_one,)
    assert panel.by_kind(CalibrationEvidenceKind.MARKET_VALUE) == (league_two,)


def test_rights_class_is_explicit_and_does_not_imply_git_storage() -> None:
    row = observation(rights_class=DataRightsClass.RESEARCH_ONLY)
    assert row.rights_class == DataRightsClass.RESEARCH_ONLY
    assert row.provenance_uri == "runtime://source-a/2026-09-04"


def test_fit_metadata_requires_temporal_and_source_provenance() -> None:
    metadata = CalibrationFitMetadata(
        model_version="market-context-v1",
        fitted_at=NOW,
        evidence_through=NOW - timedelta(days=1),
        sample_size=500,
        panel_version="next3-panel-v1",
        source_ids=("source-a", "source-b"),
        training_window_start=datetime(2023, 1, 1, tzinfo=UTC),
        holdout_window_start=datetime(2025, 1, 1, tzinfo=UTC),
    )
    assert metadata.sample_size == 500

    with pytest.raises(ValueError, match="evidence_through"):
        CalibrationFitMetadata(
            model_version="market-context-v1",
            fitted_at=NOW,
            evidence_through=NOW + timedelta(days=1),
            sample_size=1,
            panel_version="next3-panel-v1",
            source_ids=("source-a",),
        )

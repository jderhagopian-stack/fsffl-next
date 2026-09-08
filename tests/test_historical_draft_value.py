from datetime import UTC, datetime

from fsffl.value.calibration import (
    CalibrationEvidenceKind,
    CalibrationObservation,
    CalibrationPanel,
    DataRightsClass,
)
from fsffl.value.historical_draft_value import (
    HistoricalDraftSelection,
    HistoricalDraftValuePolicy,
    freeze_historical_draft_values,
)
from fsffl.value.models import ValueScale


SCALE = ValueScale(scale_id="market-index", version="v1", unit_label="index points")


def observation(*, source: str, player: str, at: datetime, value: float, metric: str = "market_value"):
    return CalibrationObservation(
        source_id=source,
        evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
        observed_at=at,
        asset_id=player,
        metric=metric,
        value=value,
        rights_class=DataRightsClass.RESEARCH_ONLY,
        source_version="snapshot-v1",
        provenance_uri=f"source:{source}:{at.date().isoformat()}",
    )


def policy(*, max_age: int = 14):
    return HistoricalDraftValuePolicy(
        source_ids=("source-a", "source-b"),
        metric="market_value",
        scale=SCALE,
        max_observation_age_days=max_age,
        model_version="historical-draft-freeze-v1",
        provenance="approved PIT market evidence",
    )


def test_freezes_latest_pre_selection_value_without_future_leakage() -> None:
    selected_at = datetime(2025, 5, 1, 18, tzinfo=UTC)
    panel = CalibrationPanel(
        observations=(
            observation(source="source-a", player="rookie-1", at=datetime(2025, 4, 25, tzinfo=UTC), value=90),
            observation(source="source-a", player="rookie-1", at=datetime(2025, 5, 2, tzinfo=UTC), value=150),
        ),
        as_of=datetime(2025, 5, 2, tzinfo=UTC),
        panel_version="panel-v1",
    )
    selection = HistoricalDraftSelection(
        draft_season=2025,
        round=1,
        slot_in_round=1,
        player_id="rookie-1",
        selected_at=selected_at,
        provenance="league draft log",
    )

    result = freeze_historical_draft_values(
        selections=(selection,), panel=panel, policy=policy(), as_of=datetime(2025, 5, 3, tzinfo=UTC)
    )

    assert result.missing_player_ids == ()
    assert result.stale_player_ids == ()
    assert len(result.values) == 1
    assert result.values[0].value.mean == 90
    assert result.values[0].available_at == datetime(2025, 4, 25, tzinfo=UTC)


def test_same_latest_timestamp_sources_form_uncertainty_not_hidden_weighting() -> None:
    at = datetime(2025, 4, 30, tzinfo=UTC)
    panel = CalibrationPanel(
        observations=(
            observation(source="source-a", player="rookie-1", at=at, value=80),
            observation(source="source-b", player="rookie-1", at=at, value=100),
        ),
        as_of=at,
        panel_version="panel-v1",
    )
    selection = HistoricalDraftSelection(
        draft_season=2025,
        round=1,
        slot_in_round=2,
        player_id="rookie-1",
        selected_at=datetime(2025, 5, 1, tzinfo=UTC),
        provenance="league draft log",
    )

    result = freeze_historical_draft_values(
        selections=(selection,), panel=panel, policy=policy(), as_of=datetime(2025, 5, 1, tzinfo=UTC)
    )

    assert result.values[0].value.mean == 90
    assert result.values[0].value.stddev == 10


def test_stale_and_missing_values_fail_closed() -> None:
    panel = CalibrationPanel(
        observations=(
            observation(
                source="source-a",
                player="stale-rookie",
                at=datetime(2025, 3, 1, tzinfo=UTC),
                value=75,
            ),
        ),
        as_of=datetime(2025, 5, 1, tzinfo=UTC),
        panel_version="panel-v1",
    )
    selections = (
        HistoricalDraftSelection(
            draft_season=2025,
            round=2,
            slot_in_round=1,
            player_id="stale-rookie",
            selected_at=datetime(2025, 5, 1, tzinfo=UTC),
            provenance="league draft log",
        ),
        HistoricalDraftSelection(
            draft_season=2025,
            round=2,
            slot_in_round=2,
            player_id="missing-rookie",
            selected_at=datetime(2025, 5, 1, tzinfo=UTC),
            provenance="league draft log",
        ),
    )

    result = freeze_historical_draft_values(
        selections=selections, panel=panel, policy=policy(max_age=14), as_of=datetime(2025, 5, 1, tzinfo=UTC)
    )

    assert result.values == ()
    assert result.stale_player_ids == ("stale-rookie",)
    assert result.missing_player_ids == ("missing-rookie",)


def test_wrong_metric_or_unapproved_source_is_not_silently_used() -> None:
    at = datetime(2025, 4, 30, tzinfo=UTC)
    panel = CalibrationPanel(
        observations=(
            observation(source="unapproved", player="rookie-1", at=at, value=500),
            observation(source="source-a", player="rookie-1", at=at, value=500, metric="other_metric"),
        ),
        as_of=at,
        panel_version="panel-v1",
    )
    selection = HistoricalDraftSelection(
        draft_season=2025,
        round=1,
        slot_in_round=3,
        player_id="rookie-1",
        selected_at=datetime(2025, 5, 1, tzinfo=UTC),
        provenance="league draft log",
    )

    result = freeze_historical_draft_values(
        selections=(selection,), panel=panel, policy=policy(), as_of=datetime(2025, 5, 1, tzinfo=UTC)
    )

    assert result.values == ()
    assert result.missing_player_ids == ("rookie-1",)

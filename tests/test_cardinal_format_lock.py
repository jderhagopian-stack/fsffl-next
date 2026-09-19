from datetime import UTC, datetime

import pytest

from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.cardinal_authority import build_authoritative_player_cardinal_scores


NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
CONTEXT = "dynasty:12t:sf:0.5ppr"


def _row(asset_id: str, *, context: str = CONTEXT, source_version: str | None = "sf_dynasty") -> NativeMarketMagnitudeObservation:
    return NativeMarketMagnitudeObservation(
        asset_id=asset_id,
        source_id="statsguy_market_values",
        native_scale_id="statsguy-dynasty-value",
        value=7000,
        observed_at=NOW,
        market_context_id=context,
        rights_class=DataRightsClass.RUNTIME_ONLY,
        source_version=source_version,
    )


def test_sf_cardinal_promotion_requires_exact_reference_format() -> None:
    scores = build_authoritative_player_cardinal_scores(
        (_row("qb1"),),
        expected_market_context_id=CONTEXT,
        expected_reference_format="sf_dynasty",
    )
    assert scores[0].score == 7000


@pytest.mark.parametrize("source_version", ["non_sf_dynasty", None])
def test_sf_cardinal_promotion_fails_closed_on_wrong_or_unlabeled_format(source_version: str | None) -> None:
    with pytest.raises(ValueError, match="requested reference format"):
        build_authoritative_player_cardinal_scores(
            (_row("qb1", source_version=source_version),),
            expected_market_context_id=CONTEXT,
            expected_reference_format="sf_dynasty",
        )


def test_cardinal_promotion_fails_closed_on_mixed_market_contexts() -> None:
    with pytest.raises(ValueError, match="one market context"):
        build_authoritative_player_cardinal_scores(
            (_row("qb1"), _row("qb2", context="dynasty:12t:1qb:0.5ppr")),
        )


def test_cardinal_promotion_fails_closed_on_duplicate_asset_reference_rows() -> None:
    with pytest.raises(ValueError, match="one reference row per asset"):
        build_authoritative_player_cardinal_scores((_row("qb1"), _row("qb1")))

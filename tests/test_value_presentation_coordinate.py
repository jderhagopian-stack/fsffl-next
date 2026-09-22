from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.product.value_presentation import (
    VALUE_PRESENTATION_COORDINATE_VERSION,
    build_value_presentation_coordinate,
)
from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation


NOW = datetime(2026, 9, 21, tzinfo=UTC)


def _rows(source: str, values: list[float]) -> tuple[NativeMarketMagnitudeObservation, ...]:
    return tuple(
        NativeMarketMagnitudeObservation(
            asset_id=f"{source}:{index}",
            source_id=source,
            native_scale_id=f"{source}-native",
            value=value,
            observed_at=NOW,
            market_context_id="dynasty:12t:sf:0.5ppr",
            rights_class=DataRightsClass.RUNTIME_ONLY,
            source_version="fixture-v1",
        )
        for index, value in enumerate(values)
    )


def test_shared_coordinate_is_empirical_nonlinear_and_provider_neutral() -> None:
    evidence = (
        *_rows("source-a", [float(index**2) for index in range(30)]),
        *_rows("source-b", [float(index**3 + 1) for index in range(30)]),
        *_rows("source-c", [float((index + 1) ** 4) for index in range(30)]),
    )
    coordinate = build_value_presentation_coordinate(
        evidence,
        minimum_source_sample=25,
    )

    assert coordinate.contract_version == VALUE_PRESENTATION_COORDINATE_VERSION
    assert coordinate.source_ids == ("source-a", "source-b", "source-c")
    assert coordinate.index_for_percentile(0.0) == pytest.approx(0.0)
    assert coordinate.index_for_percentile(1.0) == pytest.approx(10_000.0)

    middle = coordinate.index_for_percentile(0.50)
    elite = coordinate.index_for_percentile(0.99)
    assert middle is not None and elite is not None
    assert elite - middle > middle
    assert coordinate.index_for_percentile(0.95) < elite
    assert coordinate.raw_market_and_intrinsic_comparable is False
    assert coordinate.display_gap_subtraction_allowed is True


def test_shared_coordinate_preserves_percentile_order_for_both_lenses() -> None:
    evidence = (
        *_rows("source-a", [float(i * i) for i in range(30)]),
        *_rows("source-b", [float(i**3 + 1) for i in range(30)]),
    )
    coordinate = build_value_presentation_coordinate(evidence)

    market_percentiles = [0.05, 0.25, 0.50, 0.75, 0.95]
    intrinsic_percentiles = [0.10, 0.30, 0.60, 0.80, 0.99]
    market = [coordinate.index_for_percentile(value) for value in market_percentiles]
    intrinsic = [coordinate.index_for_percentile(value) for value in intrinsic_percentiles]

    assert market == sorted(market)
    assert intrinsic == sorted(intrinsic)
    assert coordinate.index_for_percentile(0.55) != pytest.approx(5500.0)


def test_shared_coordinate_fails_closed_without_enough_governed_sources() -> None:
    with pytest.raises(ValueError, match="cannot support"):
        build_value_presentation_coordinate(
            _rows("only-source", [float(i) for i in range(30)])
        )


def test_shared_coordinate_does_not_depend_on_cardinal_scores_or_named_players() -> None:
    evidence = (
        *_rows("alpha", [float(i * 7) for i in range(30)]),
        *_rows("beta", [float(i * i + 3) for i in range(30)]),
    )
    coordinate = build_value_presentation_coordinate(evidence)
    payload = coordinate.summary_payload()

    assert "cardinal" not in str(payload).lower()
    assert "player" not in str(payload).lower()
    assert payload["presentation_only"] is True
    assert payload["raw_market_and_intrinsic_comparable"] is False

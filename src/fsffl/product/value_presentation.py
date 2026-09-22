from __future__ import annotations

from math import floor
from statistics import median

from pydantic import Field

from fsffl.state.models import FrozenModel
from fsffl.value.cardinal import NativeMarketMagnitudeObservation


VALUE_PRESENTATION_COORDINATE_VERSION = (
    "value-presentation-coordinate-v1:empirical-native-quantile-median"
)
VALUE_PRESENTATION_MIN_SOURCES = 2
VALUE_PRESENTATION_MIN_SOURCE_SAMPLE = 25
VALUE_PRESENTATION_MAX_INDEX = 10_000.0
VALUE_PRESENTATION_KNOT_COUNT = 101


class ValuePresentationKnot(FrozenModel):
    percentile: float = Field(ge=0.0, le=1.0)
    value_index: float = Field(ge=0.0, le=VALUE_PRESENTATION_MAX_INDEX)


class ValuePresentationCoordinate(FrozenModel):
    """Presentation-only shared ruler for distinct Value lenses.

    The coordinate never changes Broad Market or Intrinsic authority. It maps a
    cross-player percentile to a common human-readable display magnitude using
    the empirical shape of currently governed provider-native market evidence.

    Each provider distribution is independently min-max normalized to [0, 10k].
    At each percentile knot, the source empirical quantiles are combined by
    median. This preserves nonlinear market-tail shape without privileging one
    provider, fitting an exponent, or calibrating to named players.
    """

    contract_version: str = VALUE_PRESENTATION_COORDINATE_VERSION
    method: str = "within_source_minmax_then_empirical_quantile_median"
    source_ids: tuple[str, ...]
    source_sample_sizes: dict[str, int]
    knots: tuple[ValuePresentationKnot, ...]
    presentation_only: bool = True
    raw_market_and_intrinsic_comparable: bool = False
    display_gap_subtraction_allowed: bool = True
    maximum_index: float = VALUE_PRESENTATION_MAX_INDEX

    def index_for_percentile(self, percentile: float | None) -> float | None:
        if percentile is None:
            return None
        p = max(0.0, min(1.0, float(percentile)))
        if not self.knots:
            return None
        scaled = p * (len(self.knots) - 1)
        left = int(floor(scaled))
        right = min(left + 1, len(self.knots) - 1)
        if left == right:
            return float(self.knots[left].value_index)
        fraction = scaled - left
        low = float(self.knots[left].value_index)
        high = float(self.knots[right].value_index)
        return low + fraction * (high - low)

    def summary_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "method": self.method,
            "source_ids": list(self.source_ids),
            "source_sample_sizes": dict(self.source_sample_sizes),
            "presentation_only": self.presentation_only,
            "raw_market_and_intrinsic_comparable": self.raw_market_and_intrinsic_comparable,
            "display_gap_subtraction_allowed": self.display_gap_subtraction_allowed,
            "maximum_index": self.maximum_index,
            "reference_knots": [
                knot.model_dump(mode="json")
                for knot in self.knots
                if round(knot.percentile * 100) in {0, 25, 50, 75, 90, 95, 99, 100}
            ],
        }


def _empirical_quantile(values: tuple[float, ...], percentile: float) -> float:
    if not values:
        raise ValueError("empirical quantile requires observations")
    if len(values) == 1:
        return float(values[0])
    p = max(0.0, min(1.0, float(percentile)))
    position = p * (len(values) - 1)
    lower = int(floor(position))
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return float(values[lower] + fraction * (values[upper] - values[lower]))


def build_value_presentation_coordinate(
    observations: tuple[NativeMarketMagnitudeObservation, ...],
    *,
    minimum_sources: int = VALUE_PRESENTATION_MIN_SOURCES,
    minimum_source_sample: int = VALUE_PRESENTATION_MIN_SOURCE_SAMPLE,
) -> ValuePresentationCoordinate:
    """Build a provider-neutral empirical 0-10,000 presentation ruler.

    The input is already-governed retained native Market evidence. The transform
    does not alter source ordering and does not consume Cardinal scores. A
    provider with insufficient coverage is excluded rather than being padded.
    """

    grouped: dict[str, list[float]] = {}
    for row in observations:
        value = float(row.value)
        if value < 0.0:
            raise ValueError("market presentation evidence cannot contain negative magnitudes")
        grouped.setdefault(row.source_id, []).append(value)

    normalized: dict[str, tuple[float, ...]] = {}
    for source_id, values in sorted(grouped.items()):
        if len(values) < minimum_source_sample:
            continue
        ordered = sorted(values)
        minimum = float(ordered[0])
        maximum = float(ordered[-1])
        if maximum <= minimum:
            continue
        normalized[source_id] = tuple(
            sorted(
                VALUE_PRESENTATION_MAX_INDEX * (float(value) - minimum) / (maximum - minimum)
                for value in ordered
            )
        )

    if len(normalized) < minimum_sources:
        raise ValueError(
            "governed Broad Market native magnitude evidence cannot support the "
            "shared presentation coordinate; "
            f"eligible_sources={sorted(normalized)} required={minimum_sources}"
        )

    knots: list[ValuePresentationKnot] = []
    for index in range(VALUE_PRESENTATION_KNOT_COUNT):
        percentile = index / (VALUE_PRESENTATION_KNOT_COUNT - 1)
        source_values = [
            _empirical_quantile(values, percentile)
            for values in normalized.values()
        ]
        knots.append(
            ValuePresentationKnot(
                percentile=percentile,
                value_index=max(
                    0.0,
                    min(VALUE_PRESENTATION_MAX_INDEX, float(median(source_values))),
                ),
            )
        )

    # Median of monotone source quantile functions should be monotone; keep a
    # fail-closed assertion so later refactors cannot silently violate the ruler.
    if any(
        knots[index].value_index > knots[index + 1].value_index
        for index in range(len(knots) - 1)
    ):
        raise ValueError("shared Value presentation coordinate must be monotone")

    return ValuePresentationCoordinate(
        source_ids=tuple(sorted(normalized)),
        source_sample_sizes={
            source_id: len(values)
            for source_id, values in sorted(normalized.items())
        },
        knots=tuple(knots),
    )

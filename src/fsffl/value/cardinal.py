from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import median

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel

from .calibration import CalibrationObservation, DataRightsClass


_NATIVE_SCALE_BY_SOURCE = {
    "dynastydealer_market_values": "dynastydealer-current-value",
    "fantasycalc_market_values": "fantasycalc-dynasty-value",
    "statsguy_market_values": "statsguy-dynasty-value",
}

# Shadow-product reference only. This does NOT promote Dynasty Dealer to Value
# authority or define the final FSFFL scale. It gives Presentation a stable
# cardinal-shaped number while empirical calibration continues.
_PROVISIONAL_REFERENCE_SOURCE_ID = "dynastydealer_market_values"
_PROVISIONAL_REFERENCE_SCALE_ID = "dynastydealer-current-value"


class NativeMarketMagnitudeObservation(FrozenModel):
    """Provider-native market magnitude retained for cardinal-scale research.

    This evidence is deliberately not an FSFFL Value Score. It preserves the
    provider's own magnitude before the authoritative live market runtime maps
    observations to the common percentile scale.
    """

    asset_id: str
    source_id: str
    native_scale_id: str
    value: float
    observed_at: datetime
    market_context_id: str
    rights_class: DataRightsClass
    source_version: str | None = None
    provenance_uri: str | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_identifiers(self) -> "NativeMarketMagnitudeObservation":
        required = (
            self.asset_id,
            self.source_id,
            self.native_scale_id,
            self.market_context_id,
        )
        if any(not value.strip() for value in required):
            raise ValueError("native market magnitude identifiers cannot be blank")
        return self


class NativeMagnitudeSourceSummary(FrozenModel):
    """Descriptive, non-authoritative characterization of one provider scale."""

    source_id: str
    native_scale_id: str
    sample_size: int
    minimum: float
    median: float
    maximum: float
    top_to_median_ratio: float | None


class ProvisionalFSFFLValueScore(FrozenModel):
    """Non-authoritative shadow score for UI/product-contract testing only.

    The score currently mirrors one explicit provider-native cardinal reference
    scale. It MUST NOT be consumed by Decision or Search and MUST NOT be treated
    as the final 0-10,000 FSFFL scale. Its purpose is to let Presentation exercise
    the future cardinal-value contract while empirical mapping research continues.
    """

    asset_id: str
    score: float
    status: str = "challenger"
    model_version: str = "next3-provisional-shadow-value-v1"
    reference_source_id: str = _PROVISIONAL_REFERENCE_SOURCE_ID
    reference_scale_id: str = _PROVISIONAL_REFERENCE_SCALE_ID
    observed_at: datetime
    market_context_id: str

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("provisional FSFFL Value timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_shadow_contract(self) -> "ProvisionalFSFFLValueScore":
        if self.status != "challenger":
            raise ValueError("provisional FSFFL Value must remain challenger")
        if not self.asset_id.strip() or not self.market_context_id.strip():
            raise ValueError("provisional FSFFL Value identifiers cannot be blank")
        return self


def preserve_native_market_magnitudes(
    observations: tuple[CalibrationObservation, ...],
) -> tuple[NativeMarketMagnitudeObservation, ...]:
    """Retain the latest provider-native magnitude for each source/asset pair."""

    latest: dict[tuple[str, str], CalibrationObservation] = {}
    for row in observations:
        if row.asset_id is None or row.metric != "market_value":
            continue
        native_scale_id = _NATIVE_SCALE_BY_SOURCE.get(row.source_id)
        if native_scale_id is None:
            continue
        key = (row.source_id, row.asset_id)
        prior = latest.get(key)
        if prior is None or row.observed_at > prior.observed_at:
            latest[key] = row

    retained: list[NativeMarketMagnitudeObservation] = []
    for (source_id, asset_id), row in sorted(latest.items()):
        if row.format_context_id is None:
            raise ValueError("native market magnitude evidence requires format context")
        retained.append(
            NativeMarketMagnitudeObservation(
                asset_id=asset_id,
                source_id=source_id,
                native_scale_id=_NATIVE_SCALE_BY_SOURCE[source_id],
                value=row.value,
                observed_at=row.observed_at,
                market_context_id=row.format_context_id,
                rights_class=row.rights_class,
                source_version=row.source_version,
                provenance_uri=row.provenance_uri,
            )
        )
    return tuple(retained)


def build_provisional_fsffl_values(
    observations: tuple[NativeMarketMagnitudeObservation, ...],
) -> tuple[ProvisionalFSFFLValueScore, ...]:
    """Expose a clearly labeled shadow cardinal contract for UI testing.

    No cross-provider arithmetic occurs here. Until the empirical common-scale
    mapping is validated, only the designated reference source is surfaced.
    This deliberately favors honest incompleteness over inventing a composite.
    """

    reference_rows = [
        row
        for row in observations
        if row.source_id == _PROVISIONAL_REFERENCE_SOURCE_ID
        and row.native_scale_id == _PROVISIONAL_REFERENCE_SCALE_ID
    ]
    return tuple(
        ProvisionalFSFFLValueScore(
            asset_id=row.asset_id,
            score=row.value,
            observed_at=row.observed_at,
            market_context_id=row.market_context_id,
        )
        for row in sorted(reference_rows, key=lambda item: item.asset_id)
    )


def characterize_native_magnitudes(
    observations: tuple[NativeMarketMagnitudeObservation, ...],
) -> tuple[NativeMagnitudeSourceSummary, ...]:
    """Describe scale shape without converting or promoting provider magnitudes."""

    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in observations:
        grouped[(row.source_id, row.native_scale_id)].append(row.value)

    summaries: list[NativeMagnitudeSourceSummary] = []
    for (source_id, scale_id), values in sorted(grouped.items()):
        ordered = sorted(values)
        center = float(median(ordered))
        top_to_median = None if center == 0 else ordered[-1] / center
        summaries.append(
            NativeMagnitudeSourceSummary(
                source_id=source_id,
                native_scale_id=scale_id,
                sample_size=len(ordered),
                minimum=ordered[0],
                median=center,
                maximum=ordered[-1],
                top_to_median_ratio=top_to_median,
            )
        )
    return tuple(summaries)

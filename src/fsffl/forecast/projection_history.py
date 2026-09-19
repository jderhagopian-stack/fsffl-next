from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .models import ForecastHorizon, ForecastMetric, ForecastObservation


class ProjectionBasis(StrEnum):
    """Explicit evidence family requested from durable Forecast history."""

    PROVIDER = "provider"
    PRESEASON_BASELINE = "preseason_baseline"


class ProjectionSelector(FrozenModel):
    """Horizon-aware lookup contract for point-in-time Forecast evidence.

    Callers must state the requested horizon. `as_of` means "latest evidence that
    was knowable no later than this instant"; omitting it means current/latest.
    The immutable preseason baseline is explicit rather than inferred from the
    oldest or latest season-shaped projection.
    """

    season: int = Field(ge=2000)
    horizon: ForecastHorizon
    week: int | None = Field(default=None, ge=1, le=18)
    as_of: datetime | None = None
    basis: ProjectionBasis = ProjectionBasis.PROVIDER
    provider: str | None = None

    @field_validator("as_of")
    @classmethod
    def require_aware_as_of(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("projection selector as_of must be timezone-aware")
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def validate_horizon_contract(self) -> "ProjectionSelector":
        if self.horizon == ForecastHorizon.WEEK and self.week is None:
            raise ValueError("week-specific projection lookup requires week")
        if self.horizon != ForecastHorizon.WEEK and self.week is not None:
            raise ValueError("week may be supplied only for WEEK projection horizon")
        if self.basis == ProjectionBasis.PRESEASON_BASELINE:
            if self.horizon != ForecastHorizon.SEASON:
                raise ValueError("preseason baseline lookup requires SEASON horizon")
            if self.provider is not None:
                raise ValueError("preseason baseline is an FSFFL ensemble, not one provider")
        return self


class ProjectionSnapshotRecord(FrozenModel):
    """One immutable provider publication/revision retained for reconstruction."""

    provider: str
    season: int = Field(ge=2000)
    horizon: ForecastHorizon
    week: int | None = Field(default=None, ge=1, le=18)
    period_start: datetime
    period_end: datetime
    effective_at: datetime
    retrieved_at: datetime
    source_version: str
    usage_class: str | None = None
    content_fingerprint: str
    raw_payload: dict[str, object] | None = None
    snapshot_id: int | None = None

    @field_validator("period_start", "period_end", "effective_at", "retrieved_at")
    @classmethod
    def require_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("projection snapshot timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_snapshot(self) -> "ProjectionSnapshotRecord":
        if not self.provider.strip():
            raise ValueError("projection provider cannot be blank")
        if self.period_end <= self.period_start:
            raise ValueError("projection period_end must be after period_start")
        if self.effective_at > self.retrieved_at:
            raise ValueError("projection effective_at cannot postdate retrieval")
        if self.horizon == ForecastHorizon.WEEK and self.week is None:
            raise ValueError("WEEK projection snapshot requires week")
        if self.horizon != ForecastHorizon.WEEK and self.week is not None:
            raise ValueError("week may be supplied only for WEEK projection snapshots")
        if not self.content_fingerprint.strip():
            raise ValueError("projection content_fingerprint cannot be blank")
        return self


class ProjectionObservationRecord(FrozenModel):
    """Normalized source observation belonging to one immutable snapshot."""

    player_id: str
    external_id: str
    position: Position
    metric: ForecastMetric
    mean: float
    stddev: float = Field(default=0.0, ge=0)
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None

    @model_validator(mode="after")
    def validate_quantiles(self) -> "ProjectionObservationRecord":
        supplied = [self.p10, self.p50, self.p90]
        concrete = [value for value in supplied if value is not None]
        if concrete != sorted(concrete):
            raise ValueError("projection quantiles must satisfy p10 <= p50 <= p90")
        return self


class ProjectionRevision(FrozenModel):
    snapshot: ProjectionSnapshotRecord
    observations: tuple[ProjectionObservationRecord, ...]

    @model_validator(mode="after")
    def require_unique_observations(self) -> "ProjectionRevision":
        keys = [(item.player_id, item.metric) for item in self.observations]
        if len(keys) != len(set(keys)):
            raise ValueError("projection revision contains duplicate player/metric observations")
        return self


def normalized_projection_fingerprint(
    observations: tuple[ProjectionObservationRecord, ...],
) -> str:
    """Fingerprint semantic source content while ignoring duplicate retrievals."""

    payload = [
        item.model_dump(mode="json")
        for item in sorted(
            observations,
            key=lambda item: (item.player_id, item.metric.value, item.external_id),
        )
    ]
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def revision_from_forecast_observations(
    observations: tuple[ForecastObservation, ...],
    *,
    provider: str,
    season: int,
    horizon: ForecastHorizon,
    week: int | None = None,
    usage_class: str | None = None,
    raw_payload: dict[str, object] | None = None,
) -> ProjectionRevision:
    """Build a durable source revision without changing Forecast calculation truth.

    This helper only packages already-normalized provider observations. It does not
    score, ensemble, impute, trim horizons, or otherwise create Forecast values.
    """

    selected = tuple(
        item for item in observations if item.source == provider and item.horizon == horizon
    )
    if not selected:
        raise ValueError("projection revision requires provider observations for requested horizon")
    if len({(item.period_start, item.period_end) for item in selected}) != 1:
        raise ValueError("projection revision requires one canonical forecast period")
    if len({item.provenance.effective_at for item in selected}) != 1:
        raise ValueError("projection revision requires one provider effective timestamp")
    if len({item.provenance.retrieved_at for item in selected}) != 1:
        raise ValueError("projection revision requires one retrieval timestamp")
    if len({item.model_version for item in selected}) != 1:
        raise ValueError("projection revision requires one provider source version")

    normalized: list[ProjectionObservationRecord] = []
    for item in selected:
        provider_ref = item.provenance.provider_ref
        normalized.append(
            ProjectionObservationRecord(
                player_id=item.player_id,
                external_id=provider_ref.external_id if provider_ref is not None else item.player_id,
                position=item.position,
                metric=item.metric,
                mean=item.distribution.mean,
                stddev=item.distribution.stddev,
                p10=item.distribution.p10,
                p50=item.distribution.p50,
                p90=item.distribution.p90,
            )
        )
    normalized_tuple = tuple(normalized)
    period_start, period_end = next(iter({(item.period_start, item.period_end) for item in selected}))
    effective_at = selected[0].provenance.effective_at
    retrieved_at = selected[0].provenance.retrieved_at
    source_version = selected[0].model_version
    snapshot = ProjectionSnapshotRecord(
        provider=provider,
        season=season,
        horizon=horizon,
        week=week,
        period_start=period_start,
        period_end=period_end,
        effective_at=effective_at,
        retrieved_at=retrieved_at,
        source_version=source_version,
        usage_class=usage_class,
        content_fingerprint=normalized_projection_fingerprint(normalized_tuple),
        raw_payload=raw_payload,
    )
    return ProjectionRevision(snapshot=snapshot, observations=normalized_tuple)

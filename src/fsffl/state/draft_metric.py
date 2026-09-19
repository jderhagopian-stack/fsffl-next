from __future__ import annotations

from datetime import datetime

from pydantic import field_validator, model_validator

from .models import FrozenModel, Provenance


class HistoricalTeamDraftMetric(FrozenModel):
    """Observed league-defined draft metric that became knowable at a point in time."""

    league_id: str
    draft_season: int
    team_id: str
    metric_id: str
    value: float
    effective_at: datetime
    available_at: datetime
    model_version: str
    provenance: Provenance

    @field_validator("effective_at", "available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical draft metric timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "HistoricalTeamDraftMetric":
        if any(not value.strip() for value in (self.league_id, self.team_id, self.metric_id, self.model_version)):
            raise ValueError("historical draft metric identifiers cannot be blank")
        return self


def resolve_historical_draft_metrics(
    observations: tuple[HistoricalTeamDraftMetric, ...],
    *,
    league_id: str,
    draft_season: int,
    metric_id: str,
    as_of: datetime,
) -> tuple[HistoricalTeamDraftMetric, ...]:
    """Resolve the latest knowable observation per team without future leakage."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    latest: dict[str, HistoricalTeamDraftMetric] = {}
    for item in observations:
        if (
            item.league_id != league_id
            or item.draft_season != draft_season
            or item.metric_id != metric_id
            or item.effective_at > as_of
            or item.available_at > as_of
        ):
            continue
        current = latest.get(item.team_id)
        if current is None or (item.effective_at, item.available_at, item.model_version) > (
            current.effective_at,
            current.available_at,
            current.model_version,
        ):
            latest[item.team_id] = item
    return tuple(latest[team_id] for team_id in sorted(latest))

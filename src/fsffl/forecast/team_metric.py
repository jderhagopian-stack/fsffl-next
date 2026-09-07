from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Provenance

from .models import ForecastDistribution


class TeamMetricForecastObservation(FrozenModel):
    """Point-in-time forecast for one team's future league-defined metric.

    This is a Forecast-layer artifact. It may describe Max PF, points for, or
    another explicit metric for a future competitive season, but it does not
    decide how that metric maps to rookie-draft order. No horizon decay or
    current-season proxy is implied by this contract; the supplied distribution
    must already represent the target competitive season using evidence that was
    available by ``as_of``.
    """

    league_id: str
    team_id: str
    target_season: Annotated[int, Field(ge=1900)]
    metric_id: str
    distribution: ForecastDistribution
    as_of: datetime
    source: str
    model_version: str
    provenance: Provenance

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("team metric forecast as_of must be timezone-aware")
        return value

    @field_validator("league_id", "team_id", "metric_id", "source", "model_version")
    @classmethod
    def require_nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("team metric forecast identifiers cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_point_in_time_semantics(self) -> "TeamMetricForecastObservation":
        if self.provenance.effective_at > self.as_of:
            raise ValueError("team metric forecast evidence cannot postdate observation as_of")
        return self


class TeamMetricForecastSet(FrozenModel):
    """Complete PIT team forecast set for one target season and metric."""

    league_id: str
    target_season: Annotated[int, Field(ge=1900)]
    metric_id: str
    as_of: datetime
    observations: tuple[TeamMetricForecastObservation, ...]
    model_version: str
    provenance: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("team metric forecast set as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_set(self) -> "TeamMetricForecastSet":
        if any(not value.strip() for value in (self.league_id, self.metric_id, self.model_version, self.provenance)):
            raise ValueError("team metric forecast set identifiers/provenance cannot be blank")
        if not self.observations:
            raise ValueError("team metric forecast set requires observations")
        team_ids = [item.team_id for item in self.observations]
        if len(team_ids) != len(set(team_ids)):
            raise ValueError("team metric forecast set requires unique team ids")
        for item in self.observations:
            if item.league_id != self.league_id:
                raise ValueError("team metric forecast observation league mismatch")
            if item.target_season != self.target_season:
                raise ValueError("team metric forecast observation target season mismatch")
            if item.metric_id != self.metric_id:
                raise ValueError("team metric forecast observation metric mismatch")
            if item.as_of != self.as_of:
                raise ValueError("team metric forecast observation as_of mismatch")
        return self


def select_team_metric_forecasts(
    observations: tuple[TeamMetricForecastObservation, ...],
    *,
    league_id: str,
    target_season: int,
    metric_id: str,
    as_of: datetime,
) -> TeamMetricForecastSet | None:
    """Select latest knowable forecasts for every represented team.

    This function never carries a current-season forecast forward to a later
    season and never applies an implicit horizon transform. A target-season
    forecast must exist explicitly for that target season.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    eligible = [
        item
        for item in observations
        if item.league_id == league_id
        and item.target_season == target_season
        and item.metric_id == metric_id
        and item.as_of <= as_of
        and item.provenance.effective_at <= as_of
    ]
    if not eligible:
        return None

    latest_by_team: dict[str, TeamMetricForecastObservation] = {}
    for item in eligible:
        current = latest_by_team.get(item.team_id)
        if current is None or (item.as_of, item.model_version) > (current.as_of, current.model_version):
            latest_by_team[item.team_id] = item

    selected = tuple(sorted(latest_by_team.values(), key=lambda item: item.team_id))
    selected_as_of = max(item.as_of for item in selected)
    # A scenario set must represent one common information boundary. Reject
    # mixed-time snapshots rather than quietly blending forecasts from different
    # historical knowledge states.
    if any(item.as_of != selected_as_of for item in selected):
        raise ValueError("team metric forecast set cannot mix different as_of boundaries")

    return TeamMetricForecastSet(
        league_id=league_id,
        target_season=target_season,
        metric_id=metric_id,
        as_of=selected_as_of,
        observations=selected,
        model_version="+".join(sorted({item.model_version for item in selected})),
        provenance="; ".join(sorted({item.provenance.source for item in selected})),
    )

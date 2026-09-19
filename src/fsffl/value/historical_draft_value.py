from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .calibration import CalibrationEvidenceKind, CalibrationPanel
from .historical_pick_evidence import FrozenDraftedAssetValue
from .models import ValueDistribution, ValueScale


class HistoricalDraftSelection(FrozenModel):
    """Historically observed rookie-draft selection identity.

    This is selection identity only. It does not contain the selected player's
    later production or later market value.
    """

    draft_season: Annotated[int, Field(ge=1900)]
    round: Annotated[int, Field(ge=1)]
    slot_in_round: Annotated[int, Field(ge=1)]
    player_id: str
    selected_at: datetime
    provenance: str

    @field_validator("selected_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical draft selection timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "HistoricalDraftSelection":
        if not self.player_id.strip() or not self.provenance.strip():
            raise ValueError("historical draft selection identity/provenance cannot be blank")
        return self


class HistoricalDraftValuePolicy(FrozenModel):
    """Explicit policy for freezing PIT market evidence at a draft boundary.

    No source, metric, scale conversion, or staleness limit is implicit. The
    caller must select a market metric already expressed on the supplied scale.
    """

    source_ids: tuple[str, ...]
    metric: str
    scale: ValueScale
    max_observation_age_days: Annotated[int, Field(ge=0)]
    model_version: str
    provenance: str

    @model_validator(mode="after")
    def validate_policy(self) -> "HistoricalDraftValuePolicy":
        if not self.source_ids or any(not value.strip() for value in self.source_ids):
            raise ValueError("historical draft value policy requires source ids")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("historical draft value policy source ids must be unique")
        if any(not value.strip() for value in (self.metric, self.model_version, self.provenance)):
            raise ValueError("historical draft value policy identifiers/provenance cannot be blank")
        return self


class HistoricalDraftValueFreezeResult(FrozenModel):
    values: tuple[FrozenDraftedAssetValue, ...]
    missing_player_ids: tuple[str, ...] = ()
    stale_player_ids: tuple[str, ...] = ()


def freeze_historical_draft_values(
    *,
    selections: tuple[HistoricalDraftSelection, ...],
    panel: CalibrationPanel,
    policy: HistoricalDraftValuePolicy,
    as_of: datetime,
) -> HistoricalDraftValueFreezeResult:
    """Freeze the latest eligible pre-selection market observation per drafted player.

    Evidence after the selection or after ``as_of`` is never eligible. Missing or
    stale evidence is surfaced rather than name-matched, interpolated, backfilled,
    or replaced by a current value. Multiple approved sources observed at the same
    latest timestamp are combined only by an equal-weight mixture of their point
    estimates; no source weighting is invented here.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if panel.as_of > as_of:
        # A later-built panel is acceptable only because individual observations
        # are filtered by timestamp. Its panel boundary must not be mistaken for
        # evidence availability, so keep the per-row cutoffs authoritative.
        pass

    approved_sources = set(policy.source_ids)
    values: list[FrozenDraftedAssetValue] = []
    missing: list[str] = []
    stale: list[str] = []

    for selection in selections:
        if selection.selected_at > as_of:
            raise ValueError("historical draft selection cannot postdate requested as_of")
        eligible = [
            row
            for row in panel.observations
            if row.evidence_kind == CalibrationEvidenceKind.MARKET_VALUE
            and row.asset_id == selection.player_id
            and row.source_id in approved_sources
            and row.metric == policy.metric
            and row.observed_at <= selection.selected_at
            and row.observed_at <= as_of
        ]
        if not eligible:
            missing.append(selection.player_id)
            continue

        latest_at = max(row.observed_at for row in eligible)
        if selection.selected_at - latest_at > timedelta(days=policy.max_observation_age_days):
            stale.append(selection.player_id)
            continue
        latest = [row for row in eligible if row.observed_at == latest_at]
        source_ids = [row.source_id for row in latest]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate historical market observations for source/player/timestamp")

        mean = sum(row.value for row in latest) / len(latest)
        if len(latest) == 1:
            stddev = 0.0
        else:
            second = sum(row.value**2 for row in latest) / len(latest)
            stddev = max(0.0, second - mean**2) ** 0.5

        source_versions = sorted({row.source_version or "unversioned" for row in latest})
        row_provenance = sorted({row.provenance_uri or row.source_id for row in latest})
        values.append(
            FrozenDraftedAssetValue(
                draft_season=selection.draft_season,
                round=selection.round,
                slot_in_round=selection.slot_in_round,
                value=ValueDistribution(mean=mean, stddev=stddev),
                scale=policy.scale,
                available_at=latest_at,
                model_version=f"{policy.model_version}+{'+' .join(source_versions)}",
                provenance=(
                    f"{policy.provenance}; selection={selection.provenance}; "
                    f"market={' ; '.join(row_provenance)}"
                ),
            )
        )

    values.sort(key=lambda item: (item.draft_season, item.round, item.slot_in_round))
    return HistoricalDraftValueFreezeResult(
        values=tuple(values),
        missing_player_ids=tuple(sorted(set(missing))),
        stale_player_ids=tuple(sorted(set(stale))),
    )

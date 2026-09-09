from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Mapping

from pydantic import Field, field_validator, model_validator

from fsffl.state.history import StateSnapshotStore
from fsffl.state.models import FrozenModel

from .action_context import BehavioralActionContext, reconstruct_behavioral_action_context
from .models import BehavioralAssetKind, OwnerBehaviorEvent


class BehavioralContextCalibrationRow(FrozenModel):
    """One observed owner action paired with strictly pre-action context.

    The row is calibration evidence, not a preference estimate. Outcomes are the
    positions actually acquired/disposed in the observed action; features come only
    from the reconstructed pre-action canonical LeagueState.
    """

    event_id: str
    owner_id: str
    season: int
    occurred_at: datetime
    event_kind: str
    acquired_position_counts: dict[str, int] = Field(default_factory=dict)
    disposed_position_counts: dict[str, int] = Field(default_factory=dict)
    acquired_pick_count: int = 0
    disposed_pick_count: int = 0
    acquired_faab: int = 0
    disposed_faab: int = 0
    context: BehavioralActionContext
    model_version: str = "behavioral-context-calibration-row-v1"

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("behavioral calibration row timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_row(self) -> "BehavioralContextCalibrationRow":
        if not self.event_id.strip() or not self.owner_id.strip() or not self.model_version.strip():
            raise ValueError("behavioral calibration row identifiers cannot be blank")
        if self.context.event_id != self.event_id or self.context.owner_id != self.owner_id:
            raise ValueError("behavioral calibration row context identity must match event")
        if self.context.occurred_at != self.occurred_at:
            raise ValueError("behavioral calibration row context timestamp must match event")
        if any(value < 0 for value in self.acquired_position_counts.values()):
            raise ValueError("acquired position counts cannot be negative")
        if any(value < 0 for value in self.disposed_position_counts.values()):
            raise ValueError("disposed position counts cannot be negative")
        if min(self.acquired_pick_count, self.disposed_pick_count, self.acquired_faab, self.disposed_faab) < 0:
            raise ValueError("behavioral calibration asset counts cannot be negative")
        return self


class BehavioralContextCoverageIssue(FrozenModel):
    event_id: str
    reason: str

    @model_validator(mode="after")
    def require_metadata(self) -> "BehavioralContextCoverageIssue":
        if not self.event_id.strip() or not self.reason.strip():
            raise ValueError("behavioral context coverage issue metadata cannot be blank")
        return self


class BehavioralContextCalibrationDataset(FrozenModel):
    rows: tuple[BehavioralContextCalibrationRow, ...]
    unavailable: tuple[BehavioralContextCoverageIssue, ...]
    total_event_count: int
    usable_event_count: int
    coverage_rate: float
    model_version: str = "behavioral-context-calibration-dataset-v1"

    @model_validator(mode="after")
    def validate_dataset(self) -> "BehavioralContextCalibrationDataset":
        if self.total_event_count < 0 or self.usable_event_count < 0:
            raise ValueError("behavioral calibration dataset counts cannot be negative")
        if self.usable_event_count != len(self.rows):
            raise ValueError("usable event count must equal calibration row count")
        if self.total_event_count != len(self.rows) + len(self.unavailable):
            raise ValueError("behavioral calibration dataset coverage counts must reconcile")
        expected = self.usable_event_count / self.total_event_count if self.total_event_count else 0.0
        if abs(self.coverage_rate - expected) > 1e-12:
            raise ValueError("behavioral calibration dataset coverage rate must reconcile")
        return self


def _asset_outcomes(event: OwnerBehaviorEvent) -> tuple[dict[str, int], dict[str, int], int, int, int, int]:
    acquired_positions: Counter[str] = Counter()
    disposed_positions: Counter[str] = Counter()
    acquired_picks = disposed_picks = acquired_faab = disposed_faab = 0

    for asset in event.acquired:
        if asset.kind == BehavioralAssetKind.PLAYER and asset.position:
            acquired_positions[asset.position] += 1
        elif asset.kind == BehavioralAssetKind.PICK:
            acquired_picks += 1
        elif asset.kind == BehavioralAssetKind.FAAB:
            acquired_faab += asset.faab_amount or 0
    for asset in event.disposed:
        if asset.kind == BehavioralAssetKind.PLAYER and asset.position:
            disposed_positions[asset.position] += 1
        elif asset.kind == BehavioralAssetKind.PICK:
            disposed_picks += 1
        elif asset.kind == BehavioralAssetKind.FAAB:
            disposed_faab += asset.faab_amount or 0

    return (
        dict(sorted(acquired_positions.items())),
        dict(sorted(disposed_positions.items())),
        acquired_picks,
        disposed_picks,
        acquired_faab,
        disposed_faab,
    )


def build_behavioral_context_calibration_dataset(
    events: tuple[OwnerBehaviorEvent, ...] | list[OwnerBehaviorEvent],
    *,
    snapshots: StateSnapshotStore,
    league_id_by_event: Mapping[str, str],
    team_id_by_event: Mapping[str, str],
) -> BehavioralContextCalibrationDataset:
    """Pair observed actions with PIT context and report historical coverage.

    Events lacking identity mappings or a defensible strictly pre-action snapshot
    are retained as explicit coverage issues instead of being silently dropped.
    This makes the eventual residual model's evidence completeness measurable.
    """

    rows: list[BehavioralContextCalibrationRow] = []
    unavailable: list[BehavioralContextCoverageIssue] = []

    ordered = sorted(events, key=lambda item: (item.occurred_at, item.event_id))
    seen_ids: set[str] = set()
    for event in ordered:
        if event.event_id in seen_ids:
            raise ValueError("behavioral calibration dataset requires unique event ids")
        seen_ids.add(event.event_id)

        league_id = league_id_by_event.get(event.event_id)
        team_id = team_id_by_event.get(event.event_id)
        if not league_id or not team_id:
            unavailable.append(
                BehavioralContextCoverageIssue(
                    event_id=event.event_id,
                    reason="missing canonical league/team identity mapping",
                )
            )
            continue

        result = reconstruct_behavioral_action_context(
            event,
            league_id=league_id,
            team_id=team_id,
            snapshots=snapshots,
        )
        if result.context is None:
            unavailable.append(
                BehavioralContextCoverageIssue(
                    event_id=event.event_id,
                    reason=result.unavailable_reason or "historical context unavailable",
                )
            )
            continue

        acquired_positions, disposed_positions, acquired_picks, disposed_picks, acquired_faab, disposed_faab = _asset_outcomes(event)
        rows.append(
            BehavioralContextCalibrationRow(
                event_id=event.event_id,
                owner_id=event.owner_id,
                season=event.season,
                occurred_at=event.occurred_at,
                event_kind=event.kind.value,
                acquired_position_counts=acquired_positions,
                disposed_position_counts=disposed_positions,
                acquired_pick_count=acquired_picks,
                disposed_pick_count=disposed_picks,
                acquired_faab=acquired_faab,
                disposed_faab=disposed_faab,
                context=result.context,
            )
        )

    total = len(ordered)
    usable = len(rows)
    return BehavioralContextCalibrationDataset(
        rows=tuple(rows),
        unavailable=tuple(unavailable),
        total_event_count=total,
        usable_event_count=usable,
        coverage_rate=usable / total if total else 0.0,
    )

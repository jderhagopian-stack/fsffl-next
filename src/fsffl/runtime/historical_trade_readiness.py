from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.state.historical_trade import HistoricalTradeRecord
from fsffl.state.models import FaabAsset, FrozenModel, PickAsset, PlayerAsset


class HistoricalAssetEvidenceStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    EXCLUDED = "excluded"


class HistoricalEvidenceMode(StrEnum):
    """How strongly one historical asset is evidenced at the PIT boundary."""

    EXACT = "exact"
    PROBABILISTIC = "probabilistic"
    BOUNDED_NUISANCE = "bounded_nuisance"
    SENSITIVITY_ONLY = "sensitivity_only"


class HistoricalAssetEvidence(FrozenModel):
    """Runtime evidence status for one material historical trade asset.

    The value itself remains owned by Value. Runtime records only whether an
    authoritative point-in-time coordinate exists, the evidence mode, and why
    evidence is unavailable when missing/excluded.

    ``PROBABILISTIC`` is first-class usable evidence. A future pick does not need
    its eventual slot to be eligible for analysis when Value has an authoritative
    PIT distribution. ``BOUNDED_NUISANCE`` is intended for small ancillary terms
    (for example incidental FAAB) whose effect is represented by an explicit
    governed range rather than an invented exact exchange rate.

    ``SENSITIVITY_ONLY`` preserves evidence that is too weak for a single precise
    estimate but still supports an explicit plausible range. It may advance to
    Decision robustness analysis; a final grade is allowed only if the conclusion
    is stable across the governed range. Runtime does not choose that conclusion.
    """

    asset_key: str
    status: HistoricalAssetEvidenceStatus
    reason: str
    model_version: str | None = None
    mode: HistoricalEvidenceMode | None = None

    @field_validator("asset_key", "reason")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("historical asset evidence fields cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_model_lineage(self) -> "HistoricalAssetEvidence":
        if self.status == HistoricalAssetEvidenceStatus.AVAILABLE:
            if not (self.model_version and self.model_version.strip()):
                raise ValueError("available historical asset evidence requires model_version")
            if self.mode is None:
                raise ValueError("available historical asset evidence requires an evidence mode")
        elif self.mode is not None:
            raise ValueError("missing/excluded historical evidence cannot declare an evidence mode")
        return self


class HistoricalTradeAssetReadiness(FrozenModel):
    team_id: str
    asset_key: str
    asset_kind: str
    status: HistoricalAssetEvidenceStatus
    reason: str
    model_version: str | None = None
    mode: HistoricalEvidenceMode | None = None


class HistoricalTradeValuationReadiness(FrozenModel):
    """Inventory PIT evidence without equating uncertainty with unusability.

    ``complete`` means every material asset has some authoritative PIT evidence.
    It does NOT mean every asset is known exactly. ``grade_eligible`` means the
    trade may advance to Value/Decision uncertainty analysis. Decision remains
    responsible for deciding whether probabilistic, nuisance, or sensitivity-only
    uncertainty is too wide to support a final grade.
    """

    transaction_id: str
    assets: tuple[HistoricalTradeAssetReadiness, ...]
    complete: bool
    grade_eligible: bool
    missing_asset_keys: tuple[str, ...] = ()
    excluded_asset_keys: tuple[str, ...] = ()
    probabilistic_asset_keys: tuple[str, ...] = ()
    bounded_nuisance_asset_keys: tuple[str, ...] = ()
    sensitivity_only_asset_keys: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_summary(self) -> "HistoricalTradeValuationReadiness":
        expected_missing = tuple(
            sorted(item.asset_key for item in self.assets if item.status == HistoricalAssetEvidenceStatus.MISSING)
        )
        expected_excluded = tuple(
            sorted(item.asset_key for item in self.assets if item.status == HistoricalAssetEvidenceStatus.EXCLUDED)
        )
        expected_probabilistic = tuple(
            sorted(item.asset_key for item in self.assets if item.mode == HistoricalEvidenceMode.PROBABILISTIC)
        )
        expected_nuisance = tuple(
            sorted(item.asset_key for item in self.assets if item.mode == HistoricalEvidenceMode.BOUNDED_NUISANCE)
        )
        expected_sensitivity = tuple(
            sorted(item.asset_key for item in self.assets if item.mode == HistoricalEvidenceMode.SENSITIVITY_ONLY)
        )
        if self.missing_asset_keys != expected_missing:
            raise ValueError("missing_asset_keys must match asset readiness rows")
        if self.excluded_asset_keys != expected_excluded:
            raise ValueError("excluded_asset_keys must match asset readiness rows")
        if self.probabilistic_asset_keys != expected_probabilistic:
            raise ValueError("probabilistic_asset_keys must match asset readiness rows")
        if self.bounded_nuisance_asset_keys != expected_nuisance:
            raise ValueError("bounded_nuisance_asset_keys must match asset readiness rows")
        if self.sensitivity_only_asset_keys != expected_sensitivity:
            raise ValueError("sensitivity_only_asset_keys must match asset readiness rows")
        expected_complete = not expected_missing and not expected_excluded
        if self.complete != expected_complete:
            raise ValueError("historical trade readiness complete flag is inconsistent")
        if self.grade_eligible != expected_complete:
            raise ValueError("historical trade grade eligibility is inconsistent")
        return self


class HistoricalTradeReadinessSummary(FrozenModel):
    """Batch-level reconstructability matrix summary for historical calibration."""

    trade_count: int
    complete_trade_count: int
    blocked_trade_count: int
    probabilistic_trade_count: int = 0
    bounded_nuisance_trade_count: int = 0
    sensitivity_only_trade_count: int = 0
    missing_asset_count_by_kind: tuple[tuple[str, int], ...] = ()
    excluded_asset_count_by_kind: tuple[tuple[str, int], ...] = ()
    blocked_transaction_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_counts(self) -> "HistoricalTradeReadinessSummary":
        values = (
            self.trade_count,
            self.complete_trade_count,
            self.blocked_trade_count,
            self.probabilistic_trade_count,
            self.bounded_nuisance_trade_count,
            self.sensitivity_only_trade_count,
        )
        if any(value < 0 for value in values):
            raise ValueError("historical trade readiness counts cannot be negative")
        if self.complete_trade_count + self.blocked_trade_count != self.trade_count:
            raise ValueError("complete and blocked trade counts must equal trade_count")
        if len(self.blocked_transaction_ids) != self.blocked_trade_count:
            raise ValueError("blocked transaction ids must match blocked trade count")
        return self


def historical_trade_asset_key(*, team_id: str, ordinal: int, asset: PlayerAsset | PickAsset | FaabAsset) -> str:
    """Return a stable trade-local identity for one outgoing asset."""

    if isinstance(asset, PlayerAsset):
        identity = asset.player_id
    elif isinstance(asset, PickAsset):
        identity = asset.pick_id
    else:
        identity = str(asset.amount)
    return f"{team_id}:{ordinal}:{asset.kind}:{identity}"


def assess_historical_trade_valuation_readiness(
    record: HistoricalTradeRecord,
    *,
    evidence: Sequence[HistoricalAssetEvidence],
) -> HistoricalTradeValuationReadiness:
    """Inventory every asset while allowing governed uncertainty to remain usable.

    Missing evidence is never interpreted as zero value, and an excluded asset is
    never silently dropped. But a probabilistic pick coordinate is authoritative
    evidence, not a failure merely because the eventual slot was unknown.
    Likewise, bounded nuisance and sensitivity-only representations can preserve
    uncertain assets for downstream robustness analysis without claiming false
    empirical precision.
    """

    evidence_by_key: Mapping[str, HistoricalAssetEvidence] = {item.asset_key: item for item in evidence}
    if len(evidence_by_key) != len(evidence):
        raise ValueError("historical asset evidence must contain unique asset keys")

    rows: list[HistoricalTradeAssetReadiness] = []
    expected_keys: set[str] = set()
    for leg in record.legs:
        for ordinal, asset in enumerate(leg.sends):
            key = historical_trade_asset_key(team_id=leg.team_id, ordinal=ordinal, asset=asset)
            expected_keys.add(key)
            item = evidence_by_key.get(key)
            if item is None:
                rows.append(
                    HistoricalTradeAssetReadiness(
                        team_id=leg.team_id,
                        asset_key=key,
                        asset_kind=asset.kind,
                        status=HistoricalAssetEvidenceStatus.MISSING,
                        reason="no authoritative point-in-time value evidence supplied",
                    )
                )
            else:
                rows.append(
                    HistoricalTradeAssetReadiness(
                        team_id=leg.team_id,
                        asset_key=key,
                        asset_kind=asset.kind,
                        status=item.status,
                        reason=item.reason,
                        model_version=item.model_version,
                        mode=item.mode,
                    )
                )

    unexpected = set(evidence_by_key) - expected_keys
    if unexpected:
        raise ValueError(f"historical asset evidence contains assets outside the trade: {sorted(unexpected)}")

    rows.sort(key=lambda item: (item.team_id, item.asset_key))
    missing = tuple(sorted(item.asset_key for item in rows if item.status == HistoricalAssetEvidenceStatus.MISSING))
    excluded = tuple(sorted(item.asset_key for item in rows if item.status == HistoricalAssetEvidenceStatus.EXCLUDED))
    probabilistic = tuple(sorted(item.asset_key for item in rows if item.mode == HistoricalEvidenceMode.PROBABILISTIC))
    nuisance = tuple(sorted(item.asset_key for item in rows if item.mode == HistoricalEvidenceMode.BOUNDED_NUISANCE))
    sensitivity = tuple(sorted(item.asset_key for item in rows if item.mode == HistoricalEvidenceMode.SENSITIVITY_ONLY))
    complete = not missing and not excluded
    return HistoricalTradeValuationReadiness(
        transaction_id=record.transaction_id,
        assets=tuple(rows),
        complete=complete,
        grade_eligible=complete,
        missing_asset_keys=missing,
        excluded_asset_keys=excluded,
        probabilistic_asset_keys=probabilistic,
        bounded_nuisance_asset_keys=nuisance,
        sensitivity_only_asset_keys=sensitivity,
    )


def summarize_historical_trade_readiness(
    rows: Sequence[HistoricalTradeValuationReadiness],
) -> HistoricalTradeReadinessSummary:
    """Aggregate a league history without hiding uncertainty or blocker causes."""

    transaction_ids = [row.transaction_id for row in rows]
    if len(transaction_ids) != len(set(transaction_ids)):
        raise ValueError("historical readiness summary requires unique transaction ids")

    missing_by_kind: Counter[str] = Counter()
    excluded_by_kind: Counter[str] = Counter()
    blocked: list[str] = []
    for row in rows:
        if not row.grade_eligible:
            blocked.append(row.transaction_id)
        for asset in row.assets:
            if asset.status == HistoricalAssetEvidenceStatus.MISSING:
                missing_by_kind[asset.asset_kind] += 1
            elif asset.status == HistoricalAssetEvidenceStatus.EXCLUDED:
                excluded_by_kind[asset.asset_kind] += 1

    blocked.sort()
    complete_count = sum(row.grade_eligible for row in rows)
    probabilistic_count = sum(bool(row.probabilistic_asset_keys) for row in rows)
    nuisance_count = sum(bool(row.bounded_nuisance_asset_keys) for row in rows)
    sensitivity_count = sum(bool(row.sensitivity_only_asset_keys) for row in rows)
    return HistoricalTradeReadinessSummary(
        trade_count=len(rows),
        complete_trade_count=complete_count,
        blocked_trade_count=len(rows) - complete_count,
        probabilistic_trade_count=probabilistic_count,
        bounded_nuisance_trade_count=nuisance_count,
        sensitivity_only_trade_count=sensitivity_count,
        missing_asset_count_by_kind=tuple(sorted(missing_by_kind.items())),
        excluded_asset_count_by_kind=tuple(sorted(excluded_by_kind.items())),
        blocked_transaction_ids=tuple(blocked),
    )

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


class HistoricalAssetEvidence(FrozenModel):
    """Runtime evidence status for one material historical trade asset.

    The value itself remains owned by Value. Runtime records only whether an
    authoritative point-in-time coordinate exists and why it does not when
    missing/excluded.
    """

    asset_key: str
    status: HistoricalAssetEvidenceStatus
    reason: str
    model_version: str | None = None

    @field_validator("asset_key", "reason")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("historical asset evidence fields cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_model_lineage(self) -> "HistoricalAssetEvidence":
        if self.status == HistoricalAssetEvidenceStatus.AVAILABLE and not (
            self.model_version and self.model_version.strip()
        ):
            raise ValueError("available historical asset evidence requires model_version")
        return self


class HistoricalTradeAssetReadiness(FrozenModel):
    team_id: str
    asset_key: str
    asset_kind: str
    status: HistoricalAssetEvidenceStatus
    reason: str
    model_version: str | None = None


class HistoricalTradeValuationReadiness(FrozenModel):
    """Fail-closed inventory of PIT value evidence for a complete trade."""

    transaction_id: str
    assets: tuple[HistoricalTradeAssetReadiness, ...]
    complete: bool
    missing_asset_keys: tuple[str, ...] = ()
    excluded_asset_keys: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_summary(self) -> "HistoricalTradeValuationReadiness":
        expected_missing = tuple(
            sorted(item.asset_key for item in self.assets if item.status == HistoricalAssetEvidenceStatus.MISSING)
        )
        expected_excluded = tuple(
            sorted(item.asset_key for item in self.assets if item.status == HistoricalAssetEvidenceStatus.EXCLUDED)
        )
        if self.missing_asset_keys != expected_missing:
            raise ValueError("missing_asset_keys must match asset readiness rows")
        if self.excluded_asset_keys != expected_excluded:
            raise ValueError("excluded_asset_keys must match asset readiness rows")
        if self.complete != (not expected_missing and not expected_excluded):
            raise ValueError("historical trade readiness complete flag is inconsistent")
        return self


class HistoricalTradeReadinessSummary(FrozenModel):
    """Batch-level reconstructability matrix summary for historical calibration."""

    trade_count: int
    complete_trade_count: int
    blocked_trade_count: int
    missing_asset_count_by_kind: tuple[tuple[str, int], ...] = ()
    excluded_asset_count_by_kind: tuple[tuple[str, int], ...] = ()
    blocked_transaction_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_counts(self) -> "HistoricalTradeReadinessSummary":
        if self.trade_count < 0 or self.complete_trade_count < 0 or self.blocked_trade_count < 0:
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
    """Require an explicit PIT value-evidence decision for every trade asset.

    Missing evidence is never interpreted as zero value, and an excluded asset is
    never silently dropped from the package. This gate is intentionally agnostic
    about how Player, Pick, or FAAB value is produced; those remain authoritative
    in their owning layers.
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
                    )
                )

    unexpected = set(evidence_by_key) - expected_keys
    if unexpected:
        raise ValueError(f"historical asset evidence contains assets outside the trade: {sorted(unexpected)}")

    rows.sort(key=lambda item: (item.team_id, item.asset_key))
    missing = tuple(sorted(item.asset_key for item in rows if item.status == HistoricalAssetEvidenceStatus.MISSING))
    excluded = tuple(sorted(item.asset_key for item in rows if item.status == HistoricalAssetEvidenceStatus.EXCLUDED))
    return HistoricalTradeValuationReadiness(
        transaction_id=record.transaction_id,
        assets=tuple(rows),
        complete=not missing and not excluded,
        missing_asset_keys=missing,
        excluded_asset_keys=excluded,
    )


def summarize_historical_trade_readiness(
    rows: Sequence[HistoricalTradeValuationReadiness],
) -> HistoricalTradeReadinessSummary:
    """Aggregate a league history without hiding why transactions are blocked."""

    transaction_ids = [row.transaction_id for row in rows]
    if len(transaction_ids) != len(set(transaction_ids)):
        raise ValueError("historical readiness summary requires unique transaction ids")

    missing_by_kind: Counter[str] = Counter()
    excluded_by_kind: Counter[str] = Counter()
    blocked: list[str] = []
    for row in rows:
        if not row.complete:
            blocked.append(row.transaction_id)
        for asset in row.assets:
            if asset.status == HistoricalAssetEvidenceStatus.MISSING:
                missing_by_kind[asset.asset_kind] += 1
            elif asset.status == HistoricalAssetEvidenceStatus.EXCLUDED:
                excluded_by_kind[asset.asset_kind] += 1

    blocked.sort()
    complete_count = sum(row.complete for row in rows)
    return HistoricalTradeReadinessSummary(
        trade_count=len(rows),
        complete_trade_count=complete_count,
        blocked_trade_count=len(rows) - complete_count,
        missing_asset_count_by_kind=tuple(sorted(missing_by_kind.items())),
        excluded_asset_count_by_kind=tuple(sorted(excluded_by_kind.items())),
        blocked_transaction_ids=tuple(blocked),
    )

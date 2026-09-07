from __future__ import annotations

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

from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import DraftPick, FrozenModel

from .cardinal import NativeMarketMagnitudeObservation
from .models import ValueAssetKind, ValueScale


FSFFL_CARDINAL_SCALE = ValueScale(
    scale_id="fsffl-market-cardinal",
    version="next3-v1",
    unit_label="FSFFL Value points",
)
FSFFL_CARDINAL_MODEL_VERSION = "next3-fsffl-market-cardinal-v1"
FSFFL_CARDINAL_REFERENCE_SOURCE_ID = "statsguy_market_values"
FSFFL_CARDINAL_REFERENCE_SCALE_ID = "statsguy-dynasty-value"
FSFFL_CARDINAL_VALIDATION_MAE = 237.23160063271538
FSFFL_CARDINAL_VALIDATION_RMSE = 553.5983180097163
FSFFL_CARDINAL_VALIDATION_HOLDOUT_SIZE = 4503


class FSFFLCardinalValueScore(FrozenModel):
    """Authoritative NEXT-3 market-cardinal score on one explicit common scale.

    This is an exchange-market representation, not intrinsic dynasty value or a
    team-specific recommendation. Downstream Decision may consume it as one typed
    input but must preserve its own package and bilateral economics.
    """

    asset_id: str
    asset_kind: ValueAssetKind
    score: float = Field(ge=0.0, le=10000.0)
    scale: ValueScale = FSFFL_CARDINAL_SCALE
    as_of: datetime
    market_context_id: str
    model_version: str = FSFFL_CARDINAL_MODEL_VERSION
    authority_status: Literal["authoritative_market_cardinal"] = "authoritative_market_cardinal"
    evidence_source_id: str = FSFFL_CARDINAL_REFERENCE_SOURCE_ID
    evidence_source_scale_id: str = FSFFL_CARDINAL_REFERENCE_SCALE_ID
    source_asset_id: str | None = None
    cross_source_validation_mae: float = FSFFL_CARDINAL_VALIDATION_MAE
    cross_source_validation_rmse: float = FSFFL_CARDINAL_VALIDATION_RMSE
    cross_source_validation_holdout_size: int = FSFFL_CARDINAL_VALIDATION_HOLDOUT_SIZE
    slot_certainty: Literal["not_applicable", "generic_unknown_slot", "slot_specific"] = "not_applicable"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("FSFFL cardinal score timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_score(self) -> "FSFFLCardinalValueScore":
        required = (
            self.asset_id,
            self.market_context_id,
            self.model_version,
            self.evidence_source_id,
            self.evidence_source_scale_id,
        )
        if any(not value.strip() for value in required):
            raise ValueError("FSFFL cardinal score identifiers cannot be blank")
        if self.scale != FSFFL_CARDINAL_SCALE:
            raise ValueError("FSFFL cardinal score must use the governed NEXT-3 v1 scale")
        if self.asset_kind == ValueAssetKind.PICK and self.slot_certainty == "not_applicable":
            raise ValueError("pick cardinal scores must identify slot certainty")
        if self.asset_kind != ValueAssetKind.PICK and self.slot_certainty != "not_applicable":
            raise ValueError("player cardinal scores cannot claim pick slot certainty")
        return self


def build_authoritative_player_cardinal_scores(
    observations: tuple[NativeMarketMagnitudeObservation, ...],
) -> tuple[FSFFLCardinalValueScore, ...]:
    """Promote direct Stats Guy player evidence onto the governed FSFFL axis.

    The reference source already uses the selected 0-10,000 trade-derived axis,
    so no percentile rescaling, clipping, or cross-provider arithmetic occurs.
    Out-of-scale evidence fails validation rather than being silently transformed.
    """

    rows = [
        row
        for row in observations
        if row.source_id == FSFFL_CARDINAL_REFERENCE_SOURCE_ID
        and row.native_scale_id == FSFFL_CARDINAL_REFERENCE_SCALE_ID
    ]
    return tuple(
        FSFFLCardinalValueScore(
            asset_id=row.asset_id,
            asset_kind=ValueAssetKind.PLAYER,
            score=row.value,
            as_of=row.observed_at,
            market_context_id=row.market_context_id,
            source_asset_id=row.asset_id,
        )
        for row in sorted(rows, key=lambda item: item.asset_id)
    )


def build_authoritative_pick_cardinal_scores(
    json_text: str,
    *,
    draft_picks: tuple[DraftPick, ...],
    format_key: str,
    market_context_id: str,
    retrieved_at: datetime,
) -> tuple[FSFFLCardinalValueScore, ...]:
    """Attach generic unknown-slot rookie-pick values on the player score axis.

    Canonical NEXT future picks know season/round but not their eventual slot.
    Therefore v1 intentionally selects the provider's bare round-only pick id.
    Early/mid/late and slot-specific values are not guessed from owner strength.
    """

    if retrieved_at.tzinfo is None:
        raise ValueError("pick cardinal retrieval timestamp must be timezone-aware")
    if not format_key.strip() or not market_context_id.strip():
        raise ValueError("pick cardinal context identifiers cannot be blank")

    payload = json.loads(json_text)
    if not isinstance(payload, dict) or not isinstance(payload.get("picks"), list):
        raise ValueError("Stats Guy picks payload must contain a picks list")
    values_as_of = payload.get("valuesAsOf") or {}
    as_of_raw = values_as_of.get(format_key) if isinstance(values_as_of, dict) else None
    as_of = retrieved_at
    if as_of_raw:
        as_of = datetime.fromisoformat(str(as_of_raw).replace("Z", "+00:00"))
        if as_of.tzinfo is None:
            raise ValueError("Stats Guy pick valuesAsOf must be timezone-aware")

    generic_by_id: dict[str, float] = {}
    for row in payload["picks"]:
        if not isinstance(row, dict):
            continue
        provider_id = str(row.get("id") or "").strip()
        if not provider_id or row.get("slot") is not None or row.get("variant") is not None:
            continue
        value_map = row.get("value") or {}
        if not isinstance(value_map, dict) or format_key not in value_map:
            continue
        generic_by_id[provider_id] = float(value_map[format_key])

    result: list[FSFFLCardinalValueScore] = []
    for pick in sorted(draft_picks, key=lambda item: (item.season, item.round, item.pick_id)):
        provider_id = f"pick:{pick.season}:{pick.round}"
        value = generic_by_id.get(provider_id)
        if value is None:
            continue
        result.append(
            FSFFLCardinalValueScore(
                asset_id=pick.pick_id,
                asset_kind=ValueAssetKind.PICK,
                score=value,
                as_of=as_of,
                market_context_id=market_context_id,
                source_asset_id=provider_id,
                slot_certainty="generic_unknown_slot",
            )
        )
    return tuple(result)

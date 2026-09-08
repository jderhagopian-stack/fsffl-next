from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .cardinal_authority import FSFFL_CARDINAL_SCALE
from .models import ValueScale


class PickVariant(StrEnum):
    EARLY = "early"
    MID = "mid"
    LATE = "late"


class PickVariantMarketValue(FrozenModel):
    """Provider-backed early/mid/late future-pick magnitude on the Cardinal axis."""

    season: int = Field(ge=2020)
    round: int = Field(ge=1)
    variant: PickVariant
    score: float = Field(ge=0.0, le=10000.0)
    as_of: datetime
    market_context_id: str
    source_asset_id: str
    scale: ValueScale = FSFFL_CARDINAL_SCALE
    evidence_source_id: str = "statsguy_pick_values"
    model_version: str = "next3-pick-variant-market-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("pick variant timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_reference(self) -> "PickVariantMarketValue":
        if not self.market_context_id.strip() or not self.source_asset_id.strip():
            raise ValueError("pick variant identifiers cannot be blank")
        if self.scale != FSFFL_CARDINAL_SCALE:
            raise ValueError("pick variant values must use the governed Cardinal scale")
        return self


def normalize_pick_variant_market_values(
    json_text: str,
    *,
    format_key: str,
    market_context_id: str,
    retrieved_at: datetime,
) -> tuple[PickVariantMarketValue, ...]:
    """Normalize Stats Guy GET /picks early/mid/late rows without reinterpretation."""

    if retrieved_at.tzinfo is None:
        raise ValueError("pick variant retrieval timestamp must be timezone-aware")
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

    output: list[PickVariantMarketValue] = []
    for row in payload["picks"]:
        if not isinstance(row, dict):
            continue
        raw_variant = row.get("variant")
        if raw_variant not in {item.value for item in PickVariant}:
            continue
        value_map = row.get("value") or {}
        if not isinstance(value_map, dict) or format_key not in value_map:
            continue
        season = int(row["year"])
        round_number = int(row["round"])
        provider_id = str(row.get("id") or "").strip()
        expected_id = f"pick:{season}:{round_number}:{raw_variant}"
        if provider_id != expected_id:
            raise ValueError(f"pick variant id mismatch: expected {expected_id}, got {provider_id}")
        output.append(
            PickVariantMarketValue(
                season=season,
                round=round_number,
                variant=PickVariant(raw_variant),
                score=float(value_map[format_key]),
                as_of=as_of,
                market_context_id=market_context_id,
                source_asset_id=provider_id,
            )
        )
    return tuple(sorted(output, key=lambda item: (item.season, item.round, item.variant.value)))

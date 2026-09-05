from __future__ import annotations

import json
from datetime import datetime
from typing import Mapping

from pydantic import Field

from fsffl.state.models import FrozenModel

from ..calibration import (
    CalibrationEvidenceKind,
    CalibrationObservation,
    DataRightsClass,
)


class DynastyDealerImportResult(FrozenModel):
    observations: tuple[CalibrationObservation, ...]
    rows_seen: int = Field(ge=0)
    rows_imported: int = Field(ge=0)
    rows_unmapped: int = Field(ge=0)


def normalize_dynastydealer_values(
    json_text: str,
    *,
    asset_id_by_sleeper_id: Mapping[str, str],
    format_context_id: str,
    source_version: str | None = None,
    rights_class: DataRightsClass = DataRightsClass.RUNTIME_ONLY,
    provenance_uri: str | None = None,
) -> DynastyDealerImportResult:
    """Normalize Dynasty Dealer public player values into NEXT-3 evidence.

    Dynasty Dealer exposes Sleeper identifiers and transaction-derived current
    values. NEXT still requires an explicit canonical identity crosswalk so
    provider identifiers never become authoritative asset ids. The caller must
    also supply the applicable format context rather than letting this adapter
    guess league/scoring semantics from a provider default.

    The default rights class is runtime-only even though the public API permits
    broad use with attribution; promotion to a more permissive retention class
    belongs in the governed source registry rather than inside parsing code.
    """

    if not format_context_id.strip():
        raise ValueError("format_context_id cannot be blank")

    payload = json.loads(json_text)
    if not isinstance(payload, dict) or not isinstance(payload.get("players"), list):
        raise ValueError("Dynasty Dealer payload must contain a players list")

    observations: list[CalibrationObservation] = []
    rows_seen = 0
    rows_imported = 0
    rows_unmapped = 0

    for row in payload["players"]:
        rows_seen += 1
        if not isinstance(row, dict):
            raise ValueError("Dynasty Dealer player rows must be objects")

        sleeper_id = str(row.get("sleeper_id") or "").strip()
        current_value = row.get("current_value")
        updated_at = row.get("updated_at")
        if not sleeper_id or current_value is None or not updated_at:
            raise ValueError(
                "Dynasty Dealer player row missing sleeper_id, current_value, or updated_at"
            )

        asset_id = asset_id_by_sleeper_id.get(sleeper_id)
        if asset_id is None:
            rows_unmapped += 1
            continue

        observed_at = _parse_timestamp(str(updated_at))
        observations.append(
            CalibrationObservation(
                source_id="dynastydealer_market_values",
                evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
                observed_at=observed_at,
                asset_id=asset_id,
                format_context_id=format_context_id,
                metric="market_value",
                value=float(current_value),
                rights_class=rights_class,
                source_version=source_version,
                provenance_uri=provenance_uri,
            )
        )
        rows_imported += 1

    return DynastyDealerImportResult(
        observations=tuple(observations),
        rows_seen=rows_seen,
        rows_imported=rows_imported,
        rows_unmapped=rows_unmapped,
    )


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("Dynasty Dealer updated_at must be ISO-8601") from exc
    if timestamp.tzinfo is None:
        raise ValueError("Dynasty Dealer updated_at must be timezone-aware")
    return timestamp

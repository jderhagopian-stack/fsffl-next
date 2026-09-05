from __future__ import annotations

import json
from datetime import datetime
from typing import Mapping

from pydantic import Field

from fsffl.state.models import FrozenModel

from ..calibration import CalibrationEvidenceKind, CalibrationObservation, DataRightsClass


class StatsGuyImportResult(FrozenModel):
    observations: tuple[CalibrationObservation, ...]
    rows_seen: int = Field(ge=0)
    rows_imported: int = Field(ge=0)
    rows_unmapped: int = Field(ge=0)


def normalize_statsguy_rankings(
    json_text: str,
    *,
    asset_id_by_sleeper_id: Mapping[str, str],
    format_context_id: str,
    source_version: str | None = None,
    rights_class: DataRightsClass = DataRightsClass.RUNTIME_ONLY,
    provenance_uri: str | None = None,
) -> StatsGuyImportResult:
    """Normalize Stats Guy Fantasy rankings into NEXT-3 market evidence.

    The documented API is Sleeper-ID keyed and returns an ``asOf`` timestamp for
    the calculation snapshot. NEXT still requires an explicit research/canonical
    crosswalk rather than promoting a provider identifier into core identity.
    """
    if not format_context_id.strip():
        raise ValueError("format_context_id cannot be blank")

    payload = json.loads(json_text)
    if not isinstance(payload, dict) or not isinstance(payload.get("rankings"), list):
        raise ValueError("Stats Guy payload must contain a rankings list")
    as_of = payload.get("asOf")
    if not as_of:
        raise ValueError("Stats Guy payload is missing asOf")
    observed_at = _parse_timestamp(str(as_of))

    observations: list[CalibrationObservation] = []
    rows_seen = 0
    rows_imported = 0
    rows_unmapped = 0

    for row in payload["rankings"]:
        rows_seen += 1
        if not isinstance(row, dict):
            raise ValueError("Stats Guy ranking rows must be objects")
        sleeper_id = str(row.get("id") or "").strip()
        value = row.get("value")
        if not sleeper_id or value is None:
            raise ValueError("Stats Guy ranking row missing id or value")
        asset_id = asset_id_by_sleeper_id.get(sleeper_id)
        if asset_id is None:
            rows_unmapped += 1
            continue
        observations.append(
            CalibrationObservation(
                source_id="statsguy_market_values",
                evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
                observed_at=observed_at,
                asset_id=asset_id,
                format_context_id=format_context_id,
                metric="market_value",
                value=float(value),
                rights_class=rights_class,
                source_version=source_version,
                provenance_uri=provenance_uri,
            )
        )
        rows_imported += 1

    return StatsGuyImportResult(
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
        raise ValueError("Stats Guy asOf must be ISO-8601") from exc
    if timestamp.tzinfo is None:
        raise ValueError("Stats Guy asOf must be timezone-aware")
    return timestamp

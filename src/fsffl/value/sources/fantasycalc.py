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


class FantasyCalcImportResult(FrozenModel):
    observations: tuple[CalibrationObservation, ...]
    rows_seen: int = Field(ge=0)
    rows_imported: int = Field(ge=0)
    rows_unmapped: int = Field(ge=0)


def normalize_fantasycalc_values(
    json_text: str,
    *,
    observed_at: datetime,
    asset_id_by_sleeper_id: Mapping[str, str],
    format_context_id: str,
    source_version: str | None = None,
    rights_class: DataRightsClass = DataRightsClass.RUNTIME_ONLY,
    provenance_uri: str | None = None,
) -> FantasyCalcImportResult:
    """Normalize FantasyCalc current dynasty rankings into NEXT-3 evidence.

    FantasyCalc current-value responses expose Sleeper ids and a transaction-derived
    market value. Current snapshots do not carry a guaranteed historical effective
    timestamp, so the caller must supply the acquisition timestamp explicitly.
    Historical benchmarking must use historical FantasyCalc evidence rather than
    backfilling a current snapshot into earlier dates.
    """
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    if not format_context_id.strip():
        raise ValueError("format_context_id cannot be blank")

    payload = json.loads(json_text)
    if not isinstance(payload, list):
        raise ValueError("FantasyCalc payload must be a list")

    observations: list[CalibrationObservation] = []
    rows_seen = 0
    rows_imported = 0
    rows_unmapped = 0

    for row in payload:
        rows_seen += 1
        if not isinstance(row, dict):
            raise ValueError("FantasyCalc rows must be objects")

        player = row.get("player") if isinstance(row.get("player"), dict) else row
        sleeper_id = str(
            player.get("sleeperId")
            or player.get("sleeper_id")
            or row.get("sleeperId")
            or row.get("sleeper_id")
            or ""
        ).strip()
        value = row.get("value")
        if value is None and isinstance(player, dict):
            value = player.get("value")
        if not sleeper_id or value is None:
            raise ValueError("FantasyCalc row missing Sleeper id or value")

        asset_id = asset_id_by_sleeper_id.get(sleeper_id)
        if asset_id is None:
            rows_unmapped += 1
            continue

        observations.append(
            CalibrationObservation(
                source_id="fantasycalc_market_values",
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

    return FantasyCalcImportResult(
        observations=tuple(observations),
        rows_seen=rows_seen,
        rows_imported=rows_imported,
        rows_unmapped=rows_unmapped,
    )

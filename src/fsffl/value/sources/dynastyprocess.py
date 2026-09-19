from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from typing import Mapping

from pydantic import Field

from fsffl.state.models import FrozenModel

from ..calibration import (
    CalibrationEvidenceKind,
    CalibrationObservation,
    DataRightsClass,
)


class DynastyProcessImportResult(FrozenModel):
    observations: tuple[CalibrationObservation, ...]
    rows_seen: int = Field(ge=0)
    rows_imported: int = Field(ge=0)
    rows_unmapped: int = Field(ge=0)


def normalize_dynastyprocess_values(
    csv_text: str,
    *,
    asset_id_by_fp_id: Mapping[str, str],
    source_version: str | None = None,
    rights_class: DataRightsClass = DataRightsClass.RESEARCH_ONLY,
    provenance_uri: str | None = None,
) -> DynastyProcessImportResult:
    """Normalize DynastyProcess market-value snapshots into NEXT-3 evidence.

    DynastyProcess exposes source-specific FantasyPros identifiers. NEXT never
    promotes those identifiers into canonical asset identity: callers must supply
    an explicit point-in-time crosswalk. Unmapped rows are counted and skipped so
    coverage loss is visible instead of silently inventing identity matches.

    The default rights class is deliberately conservative because the repository
    is open-data while some upstream market inputs are derived from third-party
    consensus rankings. A future rights review may explicitly promote a source.
    """

    reader = csv.DictReader(StringIO(csv_text))
    required = {"fp_id", "scrape_date", "value_1qb", "value_2qb"}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        missing = sorted(required - set(reader.fieldnames or ()))
        raise ValueError(f"DynastyProcess values schema missing required columns: {missing}")

    observations: list[CalibrationObservation] = []
    rows_seen = 0
    rows_imported = 0
    rows_unmapped = 0

    for row in reader:
        rows_seen += 1
        fp_id = (row.get("fp_id") or "").strip()
        asset_id = asset_id_by_fp_id.get(fp_id)
        if asset_id is None:
            rows_unmapped += 1
            continue

        scrape_date = _parse_snapshot_date(row.get("scrape_date"))
        imported_any = False
        for column, context in (
            ("value_1qb", "dynasty:1qb"),
            ("value_2qb", "dynasty:2qb"),
        ):
            raw_value = (row.get(column) or "").strip()
            if not raw_value:
                continue
            observations.append(
                CalibrationObservation(
                    source_id="dynastyprocess_market_values",
                    evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
                    observed_at=scrape_date,
                    asset_id=asset_id,
                    format_context_id=context,
                    metric="market_value",
                    value=float(raw_value),
                    rights_class=rights_class,
                    source_version=source_version,
                    provenance_uri=provenance_uri,
                )
            )
            imported_any = True

        if imported_any:
            rows_imported += 1

    return DynastyProcessImportResult(
        observations=tuple(observations),
        rows_seen=rows_seen,
        rows_imported=rows_imported,
        rows_unmapped=rows_unmapped,
    )


def _parse_snapshot_date(value: str | None) -> datetime:
    if value is None or not value.strip():
        raise ValueError("DynastyProcess row is missing scrape_date")
    try:
        day = datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("DynastyProcess scrape_date must be YYYY-MM-DD") from exc
    return day.replace(tzinfo=UTC)

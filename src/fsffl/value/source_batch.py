from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Iterable

from pydantic import Field

from fsffl.state.models import FrozenModel

from .calibration import CalibrationObservation, CalibrationPanel


class MarketSourceBatchResult(FrozenModel):
    panel: CalibrationPanel
    completed_source_ids: tuple[str, ...]
    failed_source_ids: tuple[str, ...]
    errors_by_source_id: dict[str, str]
    observation_count_by_source_id: dict[str, int]


SourceLoader = Callable[[], tuple[CalibrationObservation, ...]]


def build_market_calibration_panel_batch(
    loaders: dict[str, SourceLoader],
    *,
    as_of: datetime,
    panel_version: str,
    max_workers: int | None = None,
    fail_on_source_error: bool = False,
) -> MarketSourceBatchResult:
    """Run independent market evidence loaders concurrently into one panel.

    Loaders own provider-specific acquisition/normalization. This orchestration
    layer only coordinates independent sources, records source-level failures,
    and constructs one immutable point-in-time panel. A provider failure therefore
    cannot silently masquerade as an empty successful source.
    """
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not panel_version.strip():
        raise ValueError("panel_version cannot be blank")
    if not loaders:
        raise ValueError("at least one market source loader is required")
    if any(not source_id.strip() for source_id in loaders):
        raise ValueError("source loader identifiers cannot be blank")

    observations: list[CalibrationObservation] = []
    completed: list[str] = []
    failed: list[str] = []
    errors: dict[str, str] = {}
    counts: dict[str, int] = {}

    workers = max_workers or min(8, len(loaders))
    if workers < 1:
        raise ValueError("max_workers must be positive")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(loader): source_id for source_id, loader in loaders.items()}
        for future in as_completed(futures):
            source_id = futures[future]
            try:
                rows = tuple(future.result())
                mismatched = sorted({row.source_id for row in rows if row.source_id != source_id})
                if mismatched:
                    raise ValueError(
                        f"loader {source_id!r} emitted observations for other sources: {mismatched}"
                    )
                future_rows = [row for row in rows if row.observed_at > as_of]
                if future_rows:
                    raise ValueError(
                        f"loader {source_id!r} emitted evidence observed after panel as_of"
                    )
                observations.extend(rows)
                completed.append(source_id)
                counts[source_id] = len(rows)
            except Exception as exc:  # source boundary: preserve provider failure explicitly
                failed.append(source_id)
                errors[source_id] = f"{type(exc).__name__}: {exc}"
                counts[source_id] = 0
                if fail_on_source_error:
                    raise RuntimeError(f"market source loader failed: {source_id}") from exc

    ordered = tuple(sorted(observations, key=lambda row: (row.observed_at, row.source_id, row.asset_id or "", row.metric)))
    panel = CalibrationPanel(observations=ordered, as_of=as_of, panel_version=panel_version)
    return MarketSourceBatchResult(
        panel=panel,
        completed_source_ids=tuple(sorted(completed)),
        failed_source_ids=tuple(sorted(failed)),
        errors_by_source_id=errors,
        observation_count_by_source_id=counts,
    )

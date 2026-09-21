from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any, Mapping, Sequence

from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.state.models import FrozenModel, LeagueRules, Player, Position

from .current_normalization import canonical_season_window, normalize_projection_snapshot
from .current_runtime import NamedCurrentProjectionFetcher, default_current_projection_fetchers
from .league_scoring import derive_league_fantasy_point_forecasts
from .live_ensemble import LiveEnsembleCoverage, LiveForecastSourceBatch, build_authoritative_live_ensemble
from .models import ForecastHorizon, ForecastObservation
from .source_health import validate_current_projection_snapshot_health


ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION = "next2-annual-preseason-raw-stat-snapshot-v1"
ANNUAL_PRESEASON_NORMALIZATION_VERSION = "next2-current-projection-normalization-v1"
ANNUAL_PRESEASON_REPLAY_VERSION = "next2-annual-preseason-league-scoring-replay-v1"
TARGET_DAYS_BEFORE_OPENER = 14


class AnnualProviderProjectionRow(FrozenModel):
    provider: str
    external_id: str
    player_name: str
    position: Position
    nfl_team: str
    stats: tuple[tuple[str, float], ...]


class AnnualProviderProjectionEvidence(FrozenModel):
    provider: str
    source_version: str
    source_identifier: str
    captured_at: datetime
    effective_at: datetime
    usage_class: str
    provider_payload_sha256: str
    source_health_disposition: str
    raw_rows: tuple[AnnualProviderProjectionRow, ...]
    normalized_observations: tuple[ForecastObservation, ...] = ()
    normalized_observations_sha256: str | None = None
    normalization_provenance: str


class AnnualPreseasonProjectionSnapshot(FrozenModel):
    season: int
    opener_date: date
    opener_coordinate_source: str
    opener_coordinate_precision: str = "date"
    target_capture_date: date
    captured_at: datetime
    capture_offset_days_before_opener: int
    provider_evidence: tuple[AnnualProviderProjectionEvidence, ...]
    provider_failures: tuple[str, ...]
    governed_raw_ensemble: tuple[ForecastObservation, ...]
    governed_raw_ensemble_sha256: str
    coverage: LiveEnsembleCoverage
    successful_source_ids: tuple[str, ...]
    source_runtime_model_version: str = "next2-live-equal-weight-v1"
    normalization_model_version: str = ANNUAL_PRESEASON_NORMALIZATION_VERSION
    model_version: str = ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _row_payload(row: CurrentProjectionRow) -> dict[str, object]:
    return {
        "provider": row.provider,
        "external_id": row.external_id,
        "player_name": row.player_name,
        "position": row.position.value,
        "nfl_team": row.nfl_team,
        "stats": [[key, float(value)] for key, value in sorted(row.stats.items())],
    }


def provider_projection_payload_sha256(snapshot: CurrentProjectionSnapshot) -> str:
    """Hash immutable provider content without volatile transport timestamps or row order."""

    rows = sorted(
        (_row_payload(row) for row in snapshot.rows),
        key=lambda item: (
            str(item["external_id"]),
            str(item["player_name"]),
            str(item["position"]),
            str(item["nfl_team"]),
            json.dumps(item["stats"], separators=(",", ":")),
        ),
    )
    return _canonical_json_sha256(
        {
            "provider": snapshot.provider,
            "source_version": snapshot.source_version,
            "usage_class": snapshot.usage_class,
            "rows": rows,
        }
    )


def _frozen_rows(snapshot: CurrentProjectionSnapshot) -> tuple[AnnualProviderProjectionRow, ...]:
    return tuple(
        AnnualProviderProjectionRow(
            provider=row.provider,
            external_id=row.external_id,
            player_name=row.player_name,
            position=row.position,
            nfl_team=row.nfl_team,
            stats=tuple(sorted((key, float(value)) for key, value in row.stats.items())),
        )
        for row in snapshot.rows
    )


def _observation_sha256(observations: tuple[ForecastObservation, ...]) -> str:
    return _canonical_json_sha256(
        [item.model_dump(mode="json") for item in observations]
    )


def nfl_regular_season_opener_date(
    schedule_rows: Sequence[Mapping[str, Any]],
    *,
    season: int,
) -> date:
    """Resolve the earliest Week-1 regular-season date from governed schedule evidence."""

    candidates: list[date] = []
    for raw in schedule_rows:
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            continue
        if week != 1:
            continue
        raw_date = raw.get("date")
        if raw_date in (None, ""):
            continue
        try:
            value = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            continue
        if value.year != season:
            continue
        candidates.append(value)
    if not candidates:
        raise ValueError(
            "trustworthy NFL season-opener date is unavailable from governed regular-season schedule"
        )
    return min(candidates)


def annual_preseason_capture_window(
    schedule_rows: Sequence[Mapping[str, Any]],
    *,
    season: int,
) -> tuple[date, date]:
    opener = nfl_regular_season_opener_date(schedule_rows, season=season)
    return opener - timedelta(days=TARGET_DAYS_BEFORE_OPENER), opener


def _source_identifier(snapshot: CurrentProjectionSnapshot) -> str:
    return f"{snapshot.provider}:{snapshot.source_version}"


def _provider_evidence(
    snapshot: CurrentProjectionSnapshot,
    *,
    health_disposition: str,
    observations: tuple[ForecastObservation, ...] = (),
    normalization_provenance: str,
) -> AnnualProviderProjectionEvidence:
    return AnnualProviderProjectionEvidence(
        provider=snapshot.provider,
        source_version=snapshot.source_version,
        source_identifier=_source_identifier(snapshot),
        captured_at=snapshot.captured_at.astimezone(UTC),
        effective_at=snapshot.effective_at.astimezone(UTC),
        usage_class=snapshot.usage_class,
        provider_payload_sha256=provider_projection_payload_sha256(snapshot),
        source_health_disposition=health_disposition,
        raw_rows=_frozen_rows(snapshot),
        normalized_observations=observations,
        normalized_observations_sha256=(
            _observation_sha256(observations) if observations else None
        ),
        normalization_provenance=normalization_provenance,
    )


def capture_annual_preseason_projection_snapshot(
    *,
    season: int,
    canonical_players: tuple[Player, ...],
    schedule_rows: Sequence[Mapping[str, Any]],
    fetchers: tuple[NamedCurrentProjectionFetcher, ...] | None = None,
    clock: callable | None = None,
    minimum_independent_sources: int = 2,
) -> AnnualPreseasonProjectionSnapshot:
    """Capture one league-agnostic, point-in-time preseason raw-stat baseline.

    The function is intentionally safe to invoke once per day. Before T-14 it refuses
    capture. From T-14 through the day before the opener it attempts the normal governed
    live source path. Any attempt that cannot satisfy the existing independent-source
    rule raises without manufacturing a baseline, so an external scheduler may retry on
    the next day. The first successfully persisted artifact is made immutable by the
    persistence service, not by rewriting this pure capture function.
    """

    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        raise ValueError("annual preseason capture clock must be timezone-aware")
    now = now.astimezone(UTC)

    target_date, opener_date = annual_preseason_capture_window(
        schedule_rows,
        season=season,
    )
    if now.date() < target_date:
        raise ValueError(
            f"annual preseason capture window has not opened; target={target_date.isoformat()}"
        )
    if now.date() >= opener_date:
        raise ValueError(
            f"annual preseason capture window is closed; opener_date={opener_date.isoformat()}"
        )
    if not canonical_players:
        raise ValueError("canonical NFL player universe is required for preseason capture")

    active_fetchers = fetchers or default_current_projection_fetchers()
    if len({item.source_id for item in active_fetchers}) != len(active_fetchers):
        raise ValueError("annual preseason provider ids must be unique")

    fetched: list[tuple[str, CurrentProjectionSnapshot]] = []
    failures: list[str] = []
    rejected_health: dict[str, str] = {}
    for fetcher in active_fetchers:
        try:
            snapshot = fetcher.fetch(season)
            if snapshot.provider != fetcher.source_id:
                raise ValueError("current projection fetcher returned wrong provider id")
            fetched.append((fetcher.source_id, snapshot))
            try:
                validate_current_projection_snapshot_health(snapshot)
            except Exception as exc:
                rejected_health[fetcher.source_id] = (
                    f"{type(exc).__name__}: {exc}"
                )
                failures.append(
                    f"{fetcher.source_id}: source_health_rejected: {type(exc).__name__}: {exc}"
                )
        except Exception as exc:
            failures.append(f"{fetcher.source_id}: {type(exc).__name__}: {exc}")

    healthy = [
        (source_id, snapshot)
        for source_id, snapshot in fetched
        if source_id not in rejected_health
    ]
    if len(healthy) < minimum_independent_sources:
        raise ValueError(
            "valid governed annual preseason baseline unavailable; retry before kickoff; "
            f"healthy_sources={sorted(source_id for source_id, _ in healthy)}; "
            f"failures={'; '.join(sorted(failures))}"
        )

    evaluation_as_of = max(
        now,
        *(snapshot.captured_at.astimezone(UTC) for _, snapshot in healthy),
        *(snapshot.effective_at.astimezone(UTC) for _, snapshot in healthy),
    )
    period_start, period_end = canonical_season_window(season)

    batches: list[LiveForecastSourceBatch] = []
    observations_by_source: dict[str, tuple[ForecastObservation, ...]] = {}
    for source_id, snapshot in healthy:
        try:
            observations = normalize_projection_snapshot(
                snapshot,
                players=canonical_players,
                horizon=ForecastHorizon.SEASON,
                period_start=period_start,
                period_end=period_end,
                evaluation_as_of=evaluation_as_of,
            )
            if not observations:
                raise ValueError("provider produced no canonical player observations")
        except Exception as exc:
            failures.append(
                f"{source_id}: normalization_failed: {type(exc).__name__}: {exc}"
            )
            continue
        observations_by_source[source_id] = observations
        batches.append(
            LiveForecastSourceBatch(
                source_id=source_id,
                observations=observations,
            )
        )

    if len(batches) < minimum_independent_sources:
        raise ValueError(
            "valid governed annual preseason baseline unavailable; retry before kickoff; "
            f"normalized_sources={sorted(observations_by_source)}; "
            f"failures={'; '.join(sorted(failures))}"
        )

    raw_ensemble, coverage = build_authoritative_live_ensemble(
        tuple(batches),
        minimum_independent_sources=minimum_independent_sources,
    )
    if not raw_ensemble:
        raise ValueError(
            "valid governed annual preseason baseline unavailable; no sufficiently covered "
            "player/metric observations; retry before kickoff"
        )

    provider_evidence: list[AnnualProviderProjectionEvidence] = []
    for source_id, snapshot in sorted(fetched, key=lambda item: item[0]):
        if source_id in rejected_health:
            provider_evidence.append(
                _provider_evidence(
                    snapshot,
                    health_disposition=f"rejected:{rejected_health[source_id]}",
                    normalization_provenance="not-run:source-health-rejected",
                )
            )
            continue
        observations = observations_by_source.get(source_id, ())
        provider_evidence.append(
            _provider_evidence(
                snapshot,
                health_disposition="accepted",
                observations=observations,
                normalization_provenance=(
                    ANNUAL_PRESEASON_NORMALIZATION_VERSION
                    if observations
                    else "failed:no-canonical-observations"
                ),
            )
        )

    successful = tuple(sorted(batch.source_id for batch in batches))
    return AnnualPreseasonProjectionSnapshot(
        season=season,
        opener_date=opener_date,
        opener_coordinate_source="sleeper:nfl_regular_season_schedule",
        opener_coordinate_precision="date",
        target_capture_date=target_date,
        captured_at=now,
        capture_offset_days_before_opener=(opener_date - now.date()).days,
        provider_evidence=tuple(provider_evidence),
        provider_failures=tuple(sorted(failures)),
        governed_raw_ensemble=raw_ensemble,
        governed_raw_ensemble_sha256=_observation_sha256(raw_ensemble),
        coverage=coverage,
        successful_source_ids=successful,
    )


def replay_annual_preseason_snapshot_for_league_rules(
    snapshot: AnnualPreseasonProjectionSnapshot,
    *,
    rules: LeagueRules,
) -> tuple[ForecastObservation, ...]:
    """Derive fantasy points later from frozen league-agnostic raw-stat evidence."""

    if snapshot.model_version != ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION:
        raise ValueError("annual preseason projection snapshot model version is stale")
    return derive_league_fantasy_point_forecasts(
        snapshot.governed_raw_ensemble,
        rules=rules,
        source="fsffl:annual_preseason_snapshot_league_scored",
        model_version=ANNUAL_PRESEASON_REPLAY_VERSION,
    )

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.forecast.projection_history import (
    ProjectionBasis,
    ProjectionObservationRecord,
    ProjectionRevision,
    ProjectionSelector,
    ProjectionSnapshotRecord,
)
from fsffl.state.models import Position


ConnectFactory = Callable[[], Any]


class PostgresProjectionHistoryStore:
    """Append-only PostgreSQL evidence store for source projection revisions.

    This adapter never scores, ensembles, trims, imputes, or chooses a forecast
    horizon. Forecast callers must provide an explicit ``ProjectionSelector``.
    """

    def __init__(self, database_url: str, *, connect_factory: ConnectFactory | None = None) -> None:
        if not database_url.strip():
            raise ValueError("database_url cannot be blank")
        self._database_url = database_url
        self._connect_factory = connect_factory

    def _connect(self):
        if self._connect_factory is not None:
            return self._connect_factory()
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - deployment dependency guard
            raise RuntimeError("PostgreSQL projection history requires psycopg") from exc
        return psycopg.connect(self._database_url, row_factory=dict_row)

    @staticmethod
    def _provider_selector(selector: ProjectionSelector) -> None:
        if selector.basis != ProjectionBasis.PROVIDER:
            raise ValueError(
                "preseason baseline is retained by the immutable baseline artifact store; "
                "provider projection history only serves provider evidence"
            )

    def save_revision(self, revision: ProjectionRevision) -> int:
        snapshot = revision.snapshot
        with self._connect() as connection, connection.cursor() as cursor:
            # Suppress only a consecutive unchanged poll. A provider may legitimately
            # publish A, change to B, and later revert to A; that reversion is a new
            # point-in-time revision and must be retained. Historical backfills whose
            # effective time predates the latest retained row are also never discarded.
            cursor.execute(
                """select id, effective_at, content_fingerprint
                   from fsffl.projection_snapshot
                   where provider=%s and season=%s and horizon=%s
                     and coalesce(week, 0)=coalesce(%s, 0)
                     and period_start=%s and period_end=%s and source_version=%s
                   order by effective_at desc, id desc
                   limit 1""",
                (
                    snapshot.provider,
                    snapshot.season,
                    snapshot.horizon.value,
                    snapshot.week,
                    snapshot.period_start,
                    snapshot.period_end,
                    snapshot.source_version,
                ),
            )
            latest = cursor.fetchone()
            if (
                latest is not None
                and snapshot.effective_at >= latest["effective_at"]
                and latest["content_fingerprint"] == snapshot.content_fingerprint
            ):
                return int(latest["id"])

            cursor.execute(
                """insert into fsffl.projection_snapshot
                   (provider, season, horizon, week, period_start, period_end,
                    effective_at, retrieved_at, source_version, usage_class,
                    content_fingerprint, raw_payload)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                   on conflict do nothing""",
                (
                    snapshot.provider,
                    snapshot.season,
                    snapshot.horizon.value,
                    snapshot.week,
                    snapshot.period_start,
                    snapshot.period_end,
                    snapshot.effective_at,
                    snapshot.retrieved_at,
                    snapshot.source_version,
                    snapshot.usage_class,
                    snapshot.content_fingerprint,
                    json.dumps(snapshot.raw_payload) if snapshot.raw_payload is not None else None,
                ),
            )
            cursor.execute(
                """select id from fsffl.projection_snapshot
                   where provider=%s and season=%s and horizon=%s
                     and coalesce(week, 0)=coalesce(%s, 0)
                     and period_start=%s and period_end=%s and effective_at=%s
                     and content_fingerprint=%s and source_version=%s""",
                (
                    snapshot.provider,
                    snapshot.season,
                    snapshot.horizon.value,
                    snapshot.week,
                    snapshot.period_start,
                    snapshot.period_end,
                    snapshot.effective_at,
                    snapshot.content_fingerprint,
                    snapshot.source_version,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("projection snapshot write did not persist")
            snapshot_id = int(row["id"])
            for observation in revision.observations:
                cursor.execute(
                    """insert into fsffl.projection_observation
                       (snapshot_id, player_id, external_id, position, metric, mean,
                        stddev, p10, p50, p90)
                       values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       on conflict (snapshot_id, player_id, metric) do nothing""",
                    (
                        snapshot_id,
                        observation.player_id,
                        observation.external_id,
                        observation.position.value,
                        observation.metric.value,
                        observation.mean,
                        observation.stddev,
                        observation.p10,
                        observation.p50,
                        observation.p90,
                    ),
                )
        return snapshot_id

    @staticmethod
    def _selector_where(
        selector: ProjectionSelector,
        *,
        alias: str | None = None,
    ) -> tuple[str, list[object]]:
        prefix = f"{alias}." if alias else ""
        clauses = [
            f"{prefix}season=%s",
            f"{prefix}horizon=%s",
            f"coalesce({prefix}week, 0)=coalesce(%s, 0)",
        ]
        params: list[object] = [selector.season, selector.horizon.value, selector.week]
        if selector.provider is not None:
            clauses.append(f"{prefix}provider=%s")
            params.append(selector.provider)
        if selector.as_of is not None:
            clauses.append(f"{prefix}effective_at <= %s")
            params.append(selector.as_of)
        return " and ".join(clauses), params

    def latest_revisions(self, selector: ProjectionSelector) -> tuple[ProjectionRevision, ...]:
        """Return the latest revision per provider for an explicit horizon/cutoff."""

        self._provider_selector(selector)
        where, params = self._selector_where(selector)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""select distinct on (provider)
                           id, provider, season, horizon, week, period_start, period_end,
                           effective_at, retrieved_at, source_version, usage_class,
                           content_fingerprint, raw_payload
                    from fsffl.projection_snapshot
                    where {where}
                    order by provider, effective_at desc, id desc""",  # nosec B608 - fixed clauses only
                params,
            )
            snapshots = cursor.fetchall()
            return tuple(self._revision_from_row(cursor, row) for row in snapshots)

    def player_revisions(
        self,
        player_id: str,
        selector: ProjectionSelector,
    ) -> tuple[ProjectionRevision, ...]:
        """Return all knowable revisions for one player, newest first."""

        if not player_id.strip():
            raise ValueError("player_id cannot be blank")
        self._provider_selector(selector)
        where, params = self._selector_where(selector, alias="s")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""select distinct s.id, s.provider, s.season, s.horizon, s.week,
                           s.period_start, s.period_end, s.effective_at, s.retrieved_at,
                           s.source_version, s.usage_class, s.content_fingerprint,
                           s.raw_payload
                    from fsffl.projection_snapshot s
                    join fsffl.projection_observation o on o.snapshot_id=s.id
                    where {where} and o.player_id=%s
                    order by s.effective_at desc, s.id desc""",  # nosec B608 - fixed clauses only
                [*params, player_id],
            )
            snapshots = cursor.fetchall()
            return tuple(
                self._revision_from_row(cursor, row, player_id=player_id)
                for row in snapshots
            )

    @staticmethod
    def _revision_from_row(cursor, row, *, player_id: str | None = None) -> ProjectionRevision:
        sql = """select player_id, external_id, position, metric, mean, stddev,
                        p10, p50, p90
                 from fsffl.projection_observation where snapshot_id=%s"""
        params: list[object] = [row["id"]]
        if player_id is not None:
            sql += " and player_id=%s"
            params.append(player_id)
        sql += " order by player_id, metric"
        cursor.execute(sql, params)
        observations = tuple(
            ProjectionObservationRecord(
                player_id=item["player_id"],
                external_id=item["external_id"],
                position=Position(item["position"]),
                metric=ForecastMetric(item["metric"]),
                mean=float(item["mean"]),
                stddev=float(item["stddev"]),
                p10=float(item["p10"]) if item["p10"] is not None else None,
                p50=float(item["p50"]) if item["p50"] is not None else None,
                p90=float(item["p90"]) if item["p90"] is not None else None,
            )
            for item in cursor.fetchall()
        )
        snapshot = ProjectionSnapshotRecord(
            snapshot_id=int(row["id"]),
            provider=row["provider"],
            season=int(row["season"]),
            horizon=ForecastHorizon(row["horizon"]),
            week=row["week"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            effective_at=row["effective_at"],
            retrieved_at=row["retrieved_at"],
            source_version=row["source_version"],
            usage_class=row["usage_class"],
            content_fingerprint=row["content_fingerprint"],
            raw_payload=row["raw_payload"],
        )
        return ProjectionRevision(snapshot=snapshot, observations=observations)


def projection_history_store_from_env() -> PostgresProjectionHistoryStore | None:
    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        return None
    return PostgresProjectionHistoryStore(database_url)

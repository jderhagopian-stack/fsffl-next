from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from typing import Any, Annotated, Literal, Mapping, Sequence

from pydantic import Field, field_validator, model_validator

from fsffl.providers.ros_projection_rows import (
    ProjectionRightsStatus,
    RosProjectionRow,
    RosProjectionSnapshot,
)
from fsffl.state.models import FrozenModel, Position, canonical_nfl_team

from .models import ForecastHorizon, ForecastMetric


LATE_START_EXCEPTION_SEASON = 2026
LATE_START_EXCEPTION_VERSION = "2026-late-start-v1"
LATE_START_BASELINE_CLASS = "late_start_current_ros_exception"
LATE_START_SNAPSHOT_MODEL_VERSION = "late-start-current-projection-snapshot-v1"
PRESEASON_COMPARISON_UNAVAILABLE = (
    "unavailable_no_qualifying_pre_week1_k_dst_evidence"
)


class RowHealthDisposition(StrEnum):
    ACCEPTED = "accepted"
    QUARANTINED = "quarantined"


class LateStartSourceHealthEvent(FrozenModel):
    source_id: str
    subject_key: str
    nfl_team: str
    position: Position
    disposition: RowHealthDisposition
    reason: str
    canonical_remaining_games: Annotated[int, Field(ge=0, le=18)] | None = None
    provider_projected_games: Annotated[int, Field(ge=0, le=18)] | None = None

    @field_validator("source_id", "subject_key", "reason")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("late-start health text cannot be blank")
        return value

    @field_validator("nfl_team")
    @classmethod
    def normalize_team(cls, value: str) -> str:
        return canonical_nfl_team(value)


class LateStartMetricCoverage(FrozenModel):
    subject_key: str
    metric: ForecastMetric
    source_ids: tuple[str, ...]

    @model_validator(mode="after")
    def unique_sources(self) -> "LateStartMetricCoverage":
        if not self.source_ids or len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("metric coverage requires unique non-empty source ids")
        return self


class LateStartIndependentCoverage(FrozenModel):
    subject_key: str
    metric: ForecastMetric
    independence_groups: tuple[str, ...]
    production_rights_independence_groups: tuple[str, ...] = ()
    minimum_required: Annotated[int, Field(ge=1)] = 2
    meets_minimum: bool
    production_authority_meets_minimum: bool = False

    @model_validator(mode="after")
    def validate_count(self) -> "LateStartIndependentCoverage":
        if len(self.independence_groups) != len(set(self.independence_groups)):
            raise ValueError("independence groups must be unique")
        if len(self.production_rights_independence_groups) != len(
            set(self.production_rights_independence_groups)
        ):
            raise ValueError("production-rights independence groups must be unique")
        if not set(self.production_rights_independence_groups).issubset(
            set(self.independence_groups)
        ):
            raise ValueError("production-rights groups must be a subset of evidence groups")
        if self.meets_minimum != (
            len(self.independence_groups) >= self.minimum_required
        ):
            raise ValueError("meets_minimum must match independence group count")
        if self.production_authority_meets_minimum != (
            len(self.production_rights_independence_groups) >= self.minimum_required
        ):
            raise ValueError(
                "production_authority_meets_minimum must match rights-cleared group count"
            )
        return self


class LateStartProviderEvidence(FrozenModel):
    provider: str
    source_id: str
    independence_group: str
    endpoint: str
    captured_at: datetime
    provider_effective_at: datetime | None
    source_version: str
    usage_class: str
    rights_status: ProjectionRightsStatus
    content_sha256: str
    raw_rows: tuple[RosProjectionRow, ...]
    source_health_events: tuple[LateStartSourceHealthEvent, ...]
    accepted_subject_keys: tuple[str, ...]
    quarantined_subject_keys: tuple[str, ...]

    @field_validator("captured_at", "provider_effective_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("late-start provider timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_subject_dispositions(self) -> "LateStartProviderEvidence":
        accepted = set(self.accepted_subject_keys)
        quarantined = set(self.quarantined_subject_keys)
        if accepted & quarantined:
            raise ValueError("subject cannot be both accepted and quarantined")
        event_accepted = {
            item.subject_key
            for item in self.source_health_events
            if item.disposition == RowHealthDisposition.ACCEPTED
        }
        event_quarantined = {
            item.subject_key
            for item in self.source_health_events
            if item.disposition == RowHealthDisposition.QUARANTINED
        }
        if accepted != event_accepted or quarantined != event_quarantined:
            raise ValueError("provider subject lists must match source-health events")
        return self

    @property
    def production_rights_eligible(self) -> bool:
        return self.rights_status in {
            ProjectionRightsStatus.LICENSED_BETA,
            ProjectionRightsStatus.PRODUCTION_CLEARED,
        }


class LateStartCurrentProjectionSnapshot(FrozenModel):
    """2026-only current-date ROS evidence artifact.

    This class is intentionally incompatible with AnnualPreseasonProjectionSnapshot.
    It can never answer a pre-Week-1 question.
    """

    season: Literal[2026] = 2026
    exception_version: Literal["2026-late-start-v1"] = LATE_START_EXCEPTION_VERSION
    baseline_class: Literal[
        "late_start_current_ros_exception"
    ] = LATE_START_BASELINE_CLASS
    model_version: Literal[
        "late-start-current-projection-snapshot-v1"
    ] = LATE_START_SNAPSHOT_MODEL_VERSION
    captured_at: datetime
    evaluation_as_of: datetime
    horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    period_start: datetime
    period_end: datetime
    provider_evidence: tuple[LateStartProviderEvidence, ...]
    metric_coverage: tuple[LateStartMetricCoverage, ...]
    independent_source_coverage: tuple[LateStartIndependentCoverage, ...]
    minimum_independent_sources: Annotated[int, Field(ge=2)] = 2
    preseason_eligible: Literal[False] = False
    preseason_comparison_status: Literal[
        "unavailable_no_qualifying_pre_week1_k_dst_evidence"
    ] = PRESEASON_COMPARISON_UNAVAILABLE

    @field_validator("captured_at", "evaluation_as_of", "period_start", "period_end")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("late-start artifact timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_exception_boundary(self) -> "LateStartCurrentProjectionSnapshot":
        if not self.provider_evidence:
            raise ValueError("late-start artifact requires provider evidence")
        if self.period_start != self.evaluation_as_of:
            raise ValueError("late-start ROS period_start must equal evaluation_as_of")
        if self.period_end <= self.period_start:
            raise ValueError("late-start period_end must follow period_start")
        latest_source_capture = max(
            item.captured_at for item in self.provider_evidence
        )
        if self.captured_at < latest_source_capture:
            raise ValueError("artifact capture cannot predate source acquisition")
        if self.evaluation_as_of < self.captured_at:
            raise ValueError("evaluation_as_of cannot predate artifact capture")
        if any(
            item.minimum_required != self.minimum_independent_sources
            for item in self.independent_source_coverage
        ):
            raise ValueError("coverage minimum must match artifact governance")
        return self


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return "".join(re.findall(r"[a-z0-9]+", ascii_text.lower()))


def ros_subject_key(row: RosProjectionRow) -> str:
    if row.position == Position.DST:
        return f"DST:{canonical_nfl_team(row.nfl_team)}"
    if row.position == Position.K:
        return f"K:{_normalize_name(row.subject_name)}:{canonical_nfl_team(row.nfl_team)}"
    raise ValueError("late-start subject key supports K/DST only")


def _schedule_teams(raw: Mapping[str, Any]) -> tuple[str, str] | None:
    home = (
        raw.get("home_team")
        or raw.get("home")
        or raw.get("team_home")
        or raw.get("homeTeam")
    )
    away = (
        raw.get("away_team")
        or raw.get("away")
        or raw.get("team_away")
        or raw.get("awayTeam")
    )
    if home in (None, "") or away in (None, ""):
        return None
    return canonical_nfl_team(str(home)), canonical_nfl_team(str(away))


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return None
        return value.astimezone(UTC)
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000.0
        try:
            return datetime.fromtimestamp(raw, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _schedule_coordinate(raw: Mapping[str, Any]) -> tuple[datetime | None, date]:
    for key in (
        "start_time",
        "kickoff",
        "kickoff_at",
        "scheduled_at",
        "datetime",
        "game_time",
    ):
        parsed = _parse_datetime(raw.get(key))
        if parsed is not None:
            return parsed, parsed.date()

    raw_date = raw.get("date") or raw.get("game_date") or raw.get("gameday")
    if raw_date in (None, ""):
        raise ValueError("NFL schedule row lacks a trustworthy game date")
    try:
        game_date = date.fromisoformat(str(raw_date)[:10])
    except ValueError as exc:
        raise ValueError("NFL schedule row has malformed game date") from exc

    raw_clock = raw.get("time") or raw.get("gametime")
    if raw_clock not in (None, ""):
        try:
            clock_value = time.fromisoformat(str(raw_clock))
        except ValueError:
            clock_value = None
        if clock_value is not None and clock_value.tzinfo is not None:
            combined = datetime.combine(game_date, clock_value).astimezone(UTC)
            return combined, combined.date()
    return None, game_date


def _is_regular_season_row(raw: Mapping[str, Any], *, season: int) -> bool:
    raw_season = raw.get("season")
    if raw_season not in (None, ""):
        try:
            if int(raw_season) != season:
                return False
        except (TypeError, ValueError):
            return False
    season_type = str(
        raw.get("season_type") or raw.get("seasonType") or "regular"
    ).lower()
    return season_type in {"regular", "reg"}


def remaining_regular_season_games_by_team(
    schedule_rows: Sequence[Mapping[str, Any]],
    *,
    season: int,
    as_of: datetime,
) -> dict[str, int]:
    """Return games not yet started at the acquisition instant.

    When only a game date is available, same-day games are conservatively retained.
    A prior-date game is no longer part of a current ROS horizon.
    """

    if as_of.tzinfo is None:
        raise ValueError("schedule health as_of must be timezone-aware")
    as_of = as_of.astimezone(UTC)
    counts: dict[str, int] = {}
    seen_games: set[tuple[str, str, str]] = set()

    for raw in schedule_rows:
        if not _is_regular_season_row(raw, season=season):
            continue
        teams = _schedule_teams(raw)
        if teams is None:
            continue
        game_dt, game_date = _schedule_coordinate(raw)
        home, away = teams
        game_id = str(
            raw.get("game_id")
            or raw.get("gameId")
            or f"{game_date.isoformat()}:{away}:{home}"
        )
        key = (game_id, away, home)
        if key in seen_games:
            continue
        seen_games.add(key)

        for team in (home, away):
            counts.setdefault(team, 0)

        if game_dt is not None:
            remaining = game_dt > as_of
        else:
            remaining = game_date >= as_of.date()
        if remaining:
            counts[home] += 1
            counts[away] += 1

    if not counts:
        raise ValueError("canonical NFL regular-season schedule is unavailable")
    return counts


def regular_season_period_end(
    schedule_rows: Sequence[Mapping[str, Any]],
    *,
    season: int,
) -> datetime:
    candidates: list[datetime] = []
    for raw in schedule_rows:
        if not _is_regular_season_row(raw, season=season):
            continue
        if _schedule_teams(raw) is None:
            continue
        game_dt, game_date = _schedule_coordinate(raw)
        if game_dt is not None:
            candidates.append(game_dt + timedelta(hours=8))
        else:
            candidates.append(datetime.combine(game_date + timedelta(days=1), time.min, tzinfo=UTC))
    if not candidates:
        raise ValueError("NFL regular-season end is unavailable from schedule")
    return max(candidates)


def evaluate_ros_snapshot_row_health(
    snapshot: RosProjectionSnapshot,
    *,
    schedule_rows: Sequence[Mapping[str, Any]],
) -> tuple[LateStartSourceHealthEvent, ...]:
    if snapshot.season != LATE_START_EXCEPTION_SEASON:
        raise ValueError("late-start row health is authorized only for 2026")
    remaining = remaining_regular_season_games_by_team(
        schedule_rows,
        season=snapshot.season,
        as_of=snapshot.captured_at,
    )
    source_id = f"{snapshot.provider}:{snapshot.source_version}"
    events: list[LateStartSourceHealthEvent] = []

    for row in snapshot.rows:
        subject_key = ros_subject_key(row)
        expected = remaining.get(row.nfl_team)
        if expected is None:
            disposition = RowHealthDisposition.QUARANTINED
            reason = "canonical remaining-game coordinate unavailable for subject team"
        elif row.projected_games is None:
            disposition = RowHealthDisposition.QUARANTINED
            reason = (
                "provider row lacks projected-games evidence required for "
                "schedule-aware late-start health"
            )
        elif row.projected_games > expected:
            disposition = RowHealthDisposition.QUARANTINED
            reason = (
                "provider row includes more games than remain at capture time; "
                "completed/started game must not be backdated or subtracted heuristically"
            )
        elif row.position == Position.DST and row.projected_games != expected:
            disposition = RowHealthDisposition.QUARANTINED
            reason = (
                "D/ST team-unit ROS row must cover the canonical remaining team schedule"
            )
        else:
            disposition = RowHealthDisposition.ACCEPTED
            reason = (
                "provider row is schedule-consistent at the actual acquisition instant"
            )

        events.append(
            LateStartSourceHealthEvent(
                source_id=source_id,
                subject_key=subject_key,
                nfl_team=row.nfl_team,
                position=row.position,
                disposition=disposition,
                reason=reason,
                canonical_remaining_games=expected,
                provider_projected_games=row.projected_games,
            )
        )
    return tuple(sorted(events, key=lambda item: (item.subject_key, item.source_id)))


def _row_metrics(row: RosProjectionRow) -> tuple[ForecastMetric, ...]:
    metrics: list[ForecastMetric] = []
    for stat, _value in row.stats:
        try:
            metric = ForecastMetric(stat)
        except ValueError:
            continue
        if row.position == Position.K and metric.value.startswith(("fg_", "xp_")):
            metrics.append(metric)
        elif row.position == Position.DST and metric.value.startswith("dst_"):
            metrics.append(metric)
    return tuple(sorted(set(metrics), key=lambda item: item.value))


def capture_late_start_current_projection_snapshot(
    *,
    season: int,
    snapshots: tuple[RosProjectionSnapshot, ...],
    schedule_rows: Sequence[Mapping[str, Any]],
    evaluation_as_of: datetime | None = None,
    clock: callable | None = None,
    minimum_independent_sources: int = 2,
) -> LateStartCurrentProjectionSnapshot:
    """Capture an evidence artifact for the one-season-only 2026 ROS exception.

    The artifact preserves partial evidence. It does not promote fantasy points,
    provider rights, or uncertainty; those remain separate governed gates.
    """

    if season != LATE_START_EXCEPTION_SEASON:
        raise ValueError("late-start K/DST exception is authorized only for season 2026")
    if minimum_independent_sources < 2:
        raise ValueError("late-start exception may not weaken the two-source rule")
    if not snapshots:
        raise ValueError("late-start capture requires at least one ROS provider snapshot")
    if len({item.provider for item in snapshots}) != len(snapshots):
        raise ValueError("late-start capture requires unique provider snapshots")
    if any(item.season != season for item in snapshots):
        raise ValueError("provider snapshot season must match late-start season")

    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        raise ValueError("late-start capture clock must be timezone-aware")
    now = now.astimezone(UTC)
    if any(item.captured_at > now for item in snapshots):
        raise ValueError("source acquisition cannot be backdated from a future timestamp")

    evaluation = (evaluation_as_of or now)
    if evaluation.tzinfo is None:
        raise ValueError("late-start evaluation_as_of must be timezone-aware")
    evaluation = evaluation.astimezone(UTC)
    if evaluation < now:
        raise ValueError("evaluation_as_of cannot predate artifact capture")

    provider_evidence: list[LateStartProviderEvidence] = []
    accepted_rows: list[tuple[RosProjectionSnapshot, RosProjectionRow]] = []
    for snapshot in snapshots:
        events = evaluate_ros_snapshot_row_health(
            snapshot,
            schedule_rows=schedule_rows,
        )
        accepted_keys = tuple(
            sorted(
                item.subject_key
                for item in events
                if item.disposition == RowHealthDisposition.ACCEPTED
            )
        )
        quarantined_keys = tuple(
            sorted(
                item.subject_key
                for item in events
                if item.disposition == RowHealthDisposition.QUARANTINED
            )
        )
        accepted_set = set(accepted_keys)
        for row in snapshot.rows:
            if ros_subject_key(row) in accepted_set:
                accepted_rows.append((snapshot, row))
        provider_evidence.append(
            LateStartProviderEvidence(
                provider=snapshot.provider,
                source_id=f"{snapshot.provider}:{snapshot.source_version}",
                independence_group=snapshot.independence_group,
                endpoint=snapshot.endpoint,
                captured_at=snapshot.captured_at,
                provider_effective_at=snapshot.provider_effective_at,
                source_version=snapshot.source_version,
                usage_class=snapshot.usage_class,
                rights_status=snapshot.rights_status,
                content_sha256=snapshot.content_sha256,
                raw_rows=snapshot.rows,
                source_health_events=events,
                accepted_subject_keys=accepted_keys,
                quarantined_subject_keys=quarantined_keys,
            )
        )

    source_ids_by_metric: dict[
        tuple[str, ForecastMetric], set[str]
    ] = {}
    groups_by_metric: dict[
        tuple[str, ForecastMetric], set[str]
    ] = {}
    rights_groups_by_metric: dict[
        tuple[str, ForecastMetric], set[str]
    ] = {}
    for snapshot, row in accepted_rows:
        key_subject = ros_subject_key(row)
        source_id = f"{snapshot.provider}:{snapshot.source_version}"
        for metric in _row_metrics(row):
            key = (key_subject, metric)
            source_ids_by_metric.setdefault(key, set()).add(source_id)
            groups_by_metric.setdefault(key, set()).add(snapshot.independence_group)
            if snapshot.rights_status in {
                ProjectionRightsStatus.LICENSED_BETA,
                ProjectionRightsStatus.PRODUCTION_CLEARED,
            }:
                rights_groups_by_metric.setdefault(key, set()).add(
                    snapshot.independence_group
                )

    metric_coverage = tuple(
        LateStartMetricCoverage(
            subject_key=subject_key,
            metric=metric,
            source_ids=tuple(sorted(source_ids)),
        )
        for (subject_key, metric), source_ids in sorted(
            source_ids_by_metric.items(),
            key=lambda item: (item[0][0], item[0][1].value),
        )
    )
    independent_coverage = tuple(
        LateStartIndependentCoverage(
            subject_key=subject_key,
            metric=metric,
            independence_groups=tuple(sorted(groups)),
            production_rights_independence_groups=tuple(
                sorted(rights_groups_by_metric.get((subject_key, metric), set()))
            ),
            minimum_required=minimum_independent_sources,
            meets_minimum=len(groups) >= minimum_independent_sources,
            production_authority_meets_minimum=(
                len(rights_groups_by_metric.get((subject_key, metric), set()))
                >= minimum_independent_sources
            ),
        )
        for (subject_key, metric), groups in sorted(
            groups_by_metric.items(),
            key=lambda item: (item[0][0], item[0][1].value),
        )
    )

    return LateStartCurrentProjectionSnapshot(
        captured_at=now,
        evaluation_as_of=evaluation,
        period_start=evaluation,
        period_end=regular_season_period_end(schedule_rows, season=season),
        provider_evidence=tuple(
            sorted(provider_evidence, key=lambda item: item.source_id)
        ),
        metric_coverage=metric_coverage,
        independent_source_coverage=independent_coverage,
        minimum_independent_sources=minimum_independent_sources,
    )


def source_rule_evidence_for_subject(
    snapshot: LateStartCurrentProjectionSnapshot,
    *,
    subject_key: str,
    require_production_rights: bool = True,
):
    """Build rule-level evidence inputs only from healthy accepted subject rows.

    By default research-only sources are excluded so a source-rights failure can
    never become production scoring authority merely because raw evidence exists.
    """

    from .k_dst_scoring import SourceRuleEvidence

    output: list[SourceRuleEvidence] = []
    for provider in snapshot.provider_evidence:
        if subject_key not in set(provider.accepted_subject_keys):
            continue
        if require_production_rights and not provider.production_rights_eligible:
            continue
        metrics: set[ForecastMetric] = set()
        for row in provider.raw_rows:
            if ros_subject_key(row) != subject_key:
                continue
            metrics.update(_row_metrics(row))
        if not metrics:
            continue
        output.append(
            SourceRuleEvidence(
                source_id=provider.source_id,
                independence_group=provider.independence_group,
                metrics=frozenset(metrics),
                provenance_ref=f"sha256:{provider.content_sha256}",
            )
        )
    return tuple(sorted(output, key=lambda item: item.source_id))

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.k_dst_ros_normalization import normalize_late_start_provider_evidence
from fsffl.forecast.late_start_snapshot import (
    PRESEASON_COMPARISON_UNAVAILABLE,
    RowHealthDisposition,
    capture_late_start_current_projection_snapshot,
    evaluate_ros_snapshot_row_health,
)
from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.persistence.late_start_projection_snapshot import (
    LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
    decode_late_start_current_projection_snapshot,
    late_start_current_projection_snapshot_artifact,
)
from fsffl.providers.ros_projection_rows import (
    ProjectionRightsStatus,
    RosProjectionRow,
    RosProjectionSnapshot,
)
from fsffl.state.models import Player, Position


CAPTURED = datetime(2026, 9, 25, 12, 30, tzinfo=UTC)


def _schedule() -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = [
        {
            "season": 2026,
            "season_type": "regular",
            "game_id": "ATL_GB_W3",
            "date": "2026-09-24",
            "home_team": "ATL",
            "away_team": "GB",
        }
    ]
    # At the Friday capture instant ATL has 14 future games. BUF has 15.
    for offset in range(14):
        rows.append(
            {
                "season": 2026,
                "season_type": "regular",
                "game_id": f"ATL_FUTURE_{offset}",
                "date": (CAPTURED.date() + timedelta(days=2 + 7 * offset)).isoformat(),
                "home_team": "ATL",
                "away_team": f"X{offset:02d}",
            }
        )
    for offset in range(15):
        rows.append(
            {
                "season": 2026,
                "season_type": "regular",
                "game_id": f"BUF_FUTURE_{offset}",
                "date": (CAPTURED.date() + timedelta(days=3 + 7 * offset)).isoformat(),
                "home_team": "BUF",
                "away_team": f"Y{offset:02d}",
            }
        )
    return tuple(rows)


def _snapshot(
    *,
    provider: str = "cbs",
    independence_group: str = "cbs",
    captured_at: datetime = CAPTURED,
    rows: tuple[RosProjectionRow, ...] | None = None,
    rights_status: ProjectionRightsStatus = ProjectionRightsStatus.RESEARCH_ONLY,
) -> RosProjectionSnapshot:
    return RosProjectionSnapshot(
        provider=provider,
        independence_group=independence_group,
        endpoint=f"https://example.invalid/{provider}/ros",
        season=2026,
        captured_at=captured_at,
        rows=rows
        or (
            RosProjectionRow(
                provider=provider,
                external_id=f"DST:BUF:{provider}",
                subject_name="Buffalo Bills",
                position=Position.DST,
                nfl_team="BUF",
                projected_games=15,
                stats=((ForecastMetric.DST_SACK.value, 40.0),),
            ),
        ),
        source_version=f"{provider}-ros-v1",
        usage_class="research-only",
        rights_status=rights_status,
        content_sha256=("a" if provider == "cbs" else "b") * 64,
    )


def test_2026_exception_is_ros_only_and_never_preseason_eligible() -> None:
    artifact = capture_late_start_current_projection_snapshot(
        season=2026,
        snapshots=(_snapshot(),),
        schedule_rows=_schedule(),
        clock=lambda: CAPTURED,
    )

    assert artifact.season == 2026
    assert artifact.horizon == ForecastHorizon.REST_OF_SEASON.value
    assert artifact.baseline_class == "late_start_current_ros_exception"
    assert artifact.preseason_eligible is False
    assert artifact.preseason_comparison_status == PRESEASON_COMPARISON_UNAVAILABLE
    assert artifact.period_start == CAPTURED


@pytest.mark.parametrize("season", [2025, 2027])
def test_exception_rejects_every_non_2026_season(season: int) -> None:
    with pytest.raises(ValueError, match="only for season 2026"):
        capture_late_start_current_projection_snapshot(
            season=season,
            snapshots=(_snapshot(),),
            schedule_rows=_schedule(),
            clock=lambda: CAPTURED,
        )


def test_source_acquisition_cannot_be_backdated() -> None:
    future = CAPTURED + timedelta(hours=1)
    with pytest.raises(ValueError, match="cannot be backdated"):
        capture_late_start_current_projection_snapshot(
            season=2026,
            snapshots=(_snapshot(captured_at=future),),
            schedule_rows=_schedule(),
            clock=lambda: CAPTURED,
        )


def test_thursday_completed_team_row_is_quarantined_but_sunday_team_is_healthy() -> None:
    snapshot = _snapshot(
        rows=(
            RosProjectionRow(
                provider="cbs",
                external_id="DST:ATL",
                subject_name="Atlanta Falcons",
                position=Position.DST,
                nfl_team="ATL",
                projected_games=15,
                stats=((ForecastMetric.DST_SACK.value, 35.0),),
            ),
            RosProjectionRow(
                provider="cbs",
                external_id="DST:BUF",
                subject_name="Buffalo Bills",
                position=Position.DST,
                nfl_team="BUF",
                projected_games=15,
                stats=((ForecastMetric.DST_SACK.value, 40.0),),
            ),
        )
    )

    events = evaluate_ros_snapshot_row_health(snapshot, schedule_rows=_schedule())
    by_team = {item.nfl_team: item for item in events}

    assert by_team["ATL"].canonical_remaining_games == 14
    assert by_team["ATL"].disposition == RowHealthDisposition.QUARANTINED
    assert by_team["BUF"].canonical_remaining_games == 15
    assert by_team["BUF"].disposition == RowHealthDisposition.ACCEPTED


def test_partial_evidence_is_persisted_without_fabricating_two_source_authority() -> None:
    first = _snapshot(provider="cbs", independence_group="shared")
    second = _snapshot(provider="aggregate", independence_group="shared")
    artifact = capture_late_start_current_projection_snapshot(
        season=2026,
        snapshots=(first, second),
        schedule_rows=_schedule(),
        clock=lambda: CAPTURED,
    )

    metric = next(
        item
        for item in artifact.metric_coverage
        if item.subject_key == "DST:BUF" and item.metric == ForecastMetric.DST_SACK
    )
    independent = next(
        item
        for item in artifact.independent_source_coverage
        if item.subject_key == "DST:BUF" and item.metric == ForecastMetric.DST_SACK
    )
    assert len(metric.source_ids) == 2
    assert independent.independence_groups == ("shared",)
    assert independent.meets_minimum is False


def test_research_only_source_can_be_retained_but_is_not_production_rights_eligible() -> None:
    artifact = capture_late_start_current_projection_snapshot(
        season=2026,
        snapshots=(_snapshot(rights_status=ProjectionRightsStatus.RESEARCH_ONLY),),
        schedule_rows=_schedule(),
        clock=lambda: CAPTURED,
    )
    assert artifact.provider_evidence[0].production_rights_eligible is False


def test_late_start_persistence_is_a_distinct_non_preseason_artifact_kind() -> None:
    snapshot = capture_late_start_current_projection_snapshot(
        season=2026,
        snapshots=(_snapshot(),),
        schedule_rows=_schedule(),
        clock=lambda: CAPTURED,
    )
    record = late_start_current_projection_snapshot_artifact(snapshot=snapshot)

    assert record.key.artifact_kind == LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND
    assert record.key.artifact_kind != "annual_preseason_projection_snapshot"
    decoded = decode_late_start_current_projection_snapshot(dict(record.payload))
    assert decoded == snapshot
    assert decoded.preseason_eligible is False


def test_ros_normalization_keeps_k_as_player_and_dst_as_team_unit() -> None:
    rows = (
        RosProjectionRow(
            provider="cbs",
            external_id="K:BUF:Tyler Bass",
            subject_name="Tyler Bass",
            position=Position.K,
            nfl_team="BUF",
            projected_games=15,
            stats=(
                (ForecastMetric.FG_MADE.value, 20.0),
                (ForecastMetric.FG_ATTEMPT.value, 24.0),
            ),
        ),
        RosProjectionRow(
            provider="cbs",
            external_id="DST:BUF",
            subject_name="Buffalo Bills",
            position=Position.DST,
            nfl_team="BUF",
            projected_games=15,
            stats=(
                (ForecastMetric.DST_SACK.value, 40.0),
                ("diagnostic_points_allowed", 300.0),
            ),
        ),
    )
    artifact = capture_late_start_current_projection_snapshot(
        season=2026,
        snapshots=(_snapshot(rows=rows),),
        schedule_rows=_schedule(),
        clock=lambda: CAPTURED,
    )

    normalized = normalize_late_start_provider_evidence(
        artifact.provider_evidence[0],
        players=(
            Player(
                player_id="sleeper:player:7042",
                full_name="Tyler Bass",
                position=Position.K,
                nfl_team="BUF",
            ),
        ),
        season=2026,
        period_start=artifact.period_start,
        period_end=artifact.period_end,
        evaluation_as_of=artifact.evaluation_as_of,
    )

    assert {item.metric for item in normalized.kicker_observations} == {
        ForecastMetric.FG_MADE,
        ForecastMetric.FG_ATTEMPT,
    }
    assert all(
        item.horizon == ForecastHorizon.REST_OF_SEASON
        for item in normalized.kicker_observations
    )
    assert len(normalized.dst_observations) == 1
    assert normalized.dst_observations[0].subject.nfl_team == "BUF"
    assert normalized.dst_observations[0].metric == ForecastMetric.DST_SACK


def test_wrong_horizon_cannot_be_coerced_into_ros_snapshot() -> None:
    with pytest.raises(Exception):
        RosProjectionSnapshot.model_validate(
            {
                "provider": "fftoday",
                "independence_group": "fftoday",
                "endpoint": "https://example.invalid/full-season",
                "season": 2026,
                "horizon": "season",
                "captured_at": CAPTURED,
                "rows": [
                    {
                        "provider": "fftoday",
                        "external_id": "K:BUF",
                        "subject_name": "Kicker",
                        "position": "K",
                        "nfl_team": "BUF",
                        "projected_games": 15,
                        "stats": [[ForecastMetric.FG_MADE.value, 20.0]],
                    }
                ],
                "source_version": "full-season",
                "usage_class": "research-only",
                "rights_status": "research_only",
                "content_sha256": "c" * 64,
            }
        )

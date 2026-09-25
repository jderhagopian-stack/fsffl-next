from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from fsffl.forecast.k_dst_calibration import K_REDUCED_2024_FINGERPRINT
from fsffl.forecast.k_dst_provisional import (
    ProvisionalKDstConsumer,
    assess_provisional_k_dst_consumer,
    build_provisional_k_dst_forecast,
    provisional_k_dst_readiness,
)
from fsffl.forecast.k_dst_scoring import RuleEvidenceStatus
from fsffl.forecast.late_start_snapshot import (
    PRESEASON_COMPARISON_UNAVAILABLE,
    capture_late_start_current_projection_snapshot,
)
from fsffl.forecast.models import ForecastMetric
from fsffl.persistence.provisional_k_dst_forecast import (
    PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND,
    decode_provisional_k_dst_forecast,
    provisional_k_dst_forecast_artifact,
)
from fsffl.product.provisional_k_dst_presentation import (
    build_provisional_k_dst_presentation,
)
from fsffl.product.provisional_k_dst_routes import (
    ProvisionalKDstLookupError,
    load_provisional_k_dst_presentation,
)
from fsffl.product.provisional_k_dst_runtime import (
    materialize_provisional_k_dst_for_state,
)
from fsffl.providers.ros_projection_rows import (
    ProjectionRightsStatus,
    RosProjectionRow,
    RosProjectionSnapshot,
)
from fsffl.state.models import (
    LeagueRules,
    LineupRequirement,
    Position,
    RosterSlot,
    ScoringRule,
)


CAPTURED = datetime(2026, 9, 25, 12, 30, tzinfo=UTC)


def _schedule() -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for offset in range(15):
        rows.append(
            {
                "season": 2026,
                "season_type": "regular",
                "game_id": f"BUF_FUTURE_{offset}",
                "date": (CAPTURED.date() + timedelta(days=2 + 7 * offset)).isoformat(),
                "home_team": "BUF",
                "away_team": f"Y{offset:02d}",
            }
        )
    return tuple(rows)


def _snapshot(
    provider: str,
    *,
    position: Position,
    stats: tuple[tuple[str, float], ...],
    independence_group: str | None = None,
    rights_status: ProjectionRightsStatus = ProjectionRightsStatus.LICENSED_BETA,
    hash_char: str = "a",
) -> RosProjectionSnapshot:
    if position == Position.K:
        row = RosProjectionRow(
            provider=provider,
            external_id=f"K:BUF:{provider}",
            subject_name="Tyler Bass",
            position=Position.K,
            nfl_team="BUF",
            projected_games=15,
            stats=stats,
        )
    else:
        row = RosProjectionRow(
            provider=provider,
            external_id=f"DST:BUF:{provider}",
            subject_name="Buffalo Bills",
            position=Position.DST,
            nfl_team="BUF",
            projected_games=15,
            stats=stats,
        )
    return RosProjectionSnapshot(
        provider=provider,
        independence_group=independence_group or provider,
        endpoint=f"https://example.invalid/{provider}/ros",
        season=2026,
        captured_at=CAPTURED,
        rows=(row,),
        source_version=f"{provider}-ros-v1",
        usage_class="private-beta-licensed",
        rights_status=rights_status,
        content_sha256=hash_char * 64,
    )


def _artifact(*snapshots: RosProjectionSnapshot):
    return capture_late_start_current_projection_snapshot(
        season=2026,
        snapshots=snapshots,
        schedule_rows=_schedule(),
        clock=lambda: CAPTURED,
    )


def _k_rules(*scoring: ScoringRule) -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.K, count=1),),
        scoring=scoring,
    )


def _dst_rules(*scoring: ScoringRule) -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.DST, count=1),),
        scoring=scoring,
    )


def test_k_50_plus_supports_only_five_point_base_and_omits_60_plus_increment() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=((ForecastMetric.FG_MADE_50_PLUS.value, 10.0),),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=((ForecastMetric.FG_MADE_50_PLUS.value, 12.0),),
            hash_char="b",
        ),
    )
    forecast = build_provisional_k_dst_forecast(
        artifact,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="K:tylerbass:BUF",
        rules=_k_rules(
            ScoringRule(stat="fgm_50_59", points=5),
            ScoringRule(stat="fgm_60p", points=6),
        ),
    )

    assert forecast.available is True
    assert forecast.fantasy_points_mean == pytest.approx(55.0)
    assert forecast.full_rule_authority is False
    assert forecast.preseason_eligible is False
    assert forecast.preseason_comparison_status == PRESEASON_COMPARISON_UNAVAILABLE
    assert forecast.partially_supported_rule_stats == ("fgm_60p",)
    assert len(forecast.included_coordinates) == 1
    base = forecast.included_coordinates[0]
    assert base.coordinate == "fgm_50_plus_five_point_base"
    assert base.status == RuleEvidenceStatus.PROVISIONAL_GOVERNED
    assert base.projected_events == pytest.approx(11.0)
    assert base.points_per_event == 5.0
    assert [item.coordinate for item in forecast.omitted_coordinates] == [
        "fgm_60_plus_increment"
    ]
    assert forecast.uncertainty.empirical_reference_applied_to_provisional_total is False
    assert forecast.uncertainty.omitted_coordinate_uncertainty == "unquantified_not_imputed"
    assert forecast.uncertainty.simulation_grade is False


def test_governed_60_plus_adds_only_increment_without_reallocating_50_plus() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=(
                (ForecastMetric.FG_MADE_50_PLUS.value, 10.0),
                (ForecastMetric.FG_MADE_60_PLUS.value, 2.0),
            ),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=(
                (ForecastMetric.FG_MADE_50_PLUS.value, 12.0),
                (ForecastMetric.FG_MADE_60_PLUS.value, 4.0),
            ),
            hash_char="b",
        ),
    )
    forecast = build_provisional_k_dst_forecast(
        artifact,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="K:tylerbass:BUF",
        rules=_k_rules(
            ScoringRule(stat="fgm_50_59", points=5),
            ScoringRule(stat="fgm_60p", points=6),
        ),
    )

    by_name = {item.coordinate: item for item in forecast.included_coordinates}
    assert forecast.fantasy_points_mean == pytest.approx(58.0)
    assert by_name["fgm_50_plus_five_point_base"].fantasy_points == pytest.approx(55.0)
    assert by_name["fgm_60_plus_increment"].projected_events == pytest.approx(3.0)
    assert by_name["fgm_60_plus_increment"].points_per_event == 1.0
    assert forecast.omitted_coordinates == ()
    assert forecast.full_rule_authority is False


def test_research_only_or_non_independent_evidence_cannot_activate_private_beta_provisional() -> None:
    research = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 20.0),),
            rights_status=ProjectionRightsStatus.RESEARCH_ONLY,
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 22.0),),
            rights_status=ProjectionRightsStatus.RESEARCH_ONLY,
            hash_char="b",
        ),
    )
    research_forecast = build_provisional_k_dst_forecast(
        research,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="K:tylerbass:BUF",
        rules=_k_rules(ScoringRule(stat="xpm", points=1)),
    )
    assert research_forecast.available is False
    assert research_forecast.fantasy_points_mean is None

    shared = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 20.0),),
            independence_group="shared",
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 22.0),),
            independence_group="shared",
            hash_char="b",
        ),
    )
    shared_forecast = build_provisional_k_dst_forecast(
        shared,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="K:tylerbass:BUF",
        rules=_k_rules(ScoringRule(stat="xpm", points=1)),
    )
    assert shared_forecast.available is False


def test_dst_scores_only_two_source_linear_coordinates_and_omits_pa_and_rare_events() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.DST,
            stats=(
                (ForecastMetric.DST_SACK.value, 40.0),
                (ForecastMetric.DST_INTERCEPTION.value, 12.0),
                (ForecastMetric.DST_BLOCKED_KICK.value, 2.0),
                ("diagnostic_points_allowed", 300.0),
            ),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.DST,
            stats=(
                (ForecastMetric.DST_SACK.value, 42.0),
                (ForecastMetric.DST_INTERCEPTION.value, 14.0),
                ("diagnostic_points_allowed", 280.0),
            ),
            hash_char="b",
        ),
    )
    forecast = build_provisional_k_dst_forecast(
        artifact,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="DST:BUF",
        rules=_dst_rules(
            ScoringRule(stat="sack", points=1),
            ScoringRule(stat="int", points=2),
            ScoringRule(stat="blk_kick", points=2),
            ScoringRule(stat="pts_allow_0", points=10),
            ScoringRule(stat="pts_allow_1_6", points=7),
        ),
    )

    assert forecast.fantasy_points_mean == pytest.approx(67.0)
    assert {item.coordinate for item in forecast.included_coordinates} == {"sack", "int"}
    omissions = {item.coordinate: item.reason for item in forecast.omitted_coordinates}
    assert "blk_kick" in omissions
    assert "pts_allow_0" in omissions
    assert "pts_allow_1_6" in omissions
    assert "distributional" in omissions["pts_allow_0"]
    assert all(
        "diagnostic_points_allowed" not in str(item.model_dump(mode="json"))
        for item in forecast.included_coordinates
    )


def test_provisional_downstream_gate_allows_exposure_but_blocks_model_consumers() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 20.0),),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 22.0),),
            hash_char="b",
        ),
    )
    forecast = build_provisional_k_dst_forecast(
        artifact,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="K:tylerbass:BUF",
        rules=_k_rules(
            ScoringRule(stat="xpm", points=1),
            ScoringRule(stat="fgm_60p", points=6),
        ),
    )

    for consumer in (
        ProvisionalKDstConsumer.PRESENTATION,
        ProvisionalKDstConsumer.READINESS,
        ProvisionalKDstConsumer.ANALYTICS_API,
    ):
        decision = assess_provisional_k_dst_consumer(forecast, consumer)
        assert decision.allowed is True
        assert decision.requires_provisional_metadata is True

    for consumer in (
        ProvisionalKDstConsumer.VALUE,
        ProvisionalKDstConsumer.SIMULATION,
        ProvisionalKDstConsumer.TEAM_UTILITY,
        ProvisionalKDstConsumer.DECISION,
        ProvisionalKDstConsumer.SEARCH_OPTIMIZATION,
    ):
        assert assess_provisional_k_dst_consumer(forecast, consumer).allowed is False

    readiness = provisional_k_dst_readiness(forecast)
    assert readiness.status == "provisional"
    assert readiness.current_forward_usable is True
    assert readiness.full_forecast_authority_ready is False
    assert readiness.simulation_grade_uncertainty_ready is False


def test_provisional_persistence_and_presentation_cannot_masquerade_as_canonical_forecast() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.DST,
            stats=((ForecastMetric.DST_SACK.value, 40.0),),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.DST,
            stats=((ForecastMetric.DST_SACK.value, 42.0),),
            hash_char="b",
        ),
    )
    forecast = build_provisional_k_dst_forecast(
        artifact,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="DST:BUF",
        rules=_dst_rules(
            ScoringRule(stat="sack", points=1),
            ScoringRule(stat="pts_allow_0", points=10),
        ),
    )

    record = provisional_k_dst_forecast_artifact(forecast=forecast)
    assert record.key.artifact_kind == PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND
    assert record.key.scope_id == "state-1:DST:BUF"
    assert record.key.artifact_kind != "forecast_runtime"
    assert record.key.artifact_kind != "annual_preseason_projection_snapshot"
    assert decode_provisional_k_dst_forecast(dict(record.payload)) == forecast

    presentation = build_provisional_k_dst_presentation(forecast)
    assert presentation["label"] == "Provisional 2026 ROS K/DST"
    assert presentation["authority_tier"] == "provisional_partial_rule_coverage"
    assert presentation["league_id"] == "league-1"
    assert presentation["league_state_id"] == "state-1"
    assert presentation["full_forecast_authority"] is False
    assert presentation["simulation_grade"] is False
    assert presentation["preseason_comparison"]["available"] is False
    assert presentation["coverage"]["omitted_rule_stats"] == ["pts_allow_0"]


def test_builder_hard_rejects_non_2026_even_if_model_is_unsafely_copied() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 20.0),),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 22.0),),
            hash_char="b",
        ),
    )
    unsafe = artifact.model_copy(update={"season": 2027})
    with pytest.raises(ValueError, match="only for 2026"):
        build_provisional_k_dst_forecast(
            unsafe,
            league_id="league-1",
            league_state_id="state-1",
            subject_key="K:tylerbass:BUF",
            rules=_k_rules(ScoringRule(stat="xpm", points=1)),
        )


def test_provisional_path_uses_exact_difference_transform_without_inventing_misses() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=(
                (ForecastMetric.FG_ATTEMPT.value, 24.0),
                (ForecastMetric.FG_MADE.value, 20.0),
            ),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=(
                (ForecastMetric.FG_ATTEMPT.value, 26.0),
                (ForecastMetric.FG_MADE.value, 21.0),
            ),
            hash_char="b",
        ),
    )
    forecast = build_provisional_k_dst_forecast(
        artifact,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="K:tylerbass:BUF",
        rules=_k_rules(ScoringRule(stat="fgmiss", points=-1)),
    )

    assert forecast.fantasy_points_mean == pytest.approx(-4.5)
    assert forecast.included_coordinates[0].status == RuleEvidenceStatus.EXACT_DERIVED
    assert set(forecast.included_coordinates[0].metrics) == {
        ForecastMetric.FG_ATTEMPT,
        ForecastMetric.FG_MADE,
    }


def test_full_authority_supersedes_provisional_when_existing_full_gates_clear() -> None:
    stats_one = (
        (ForecastMetric.FG_MADE.value, 20.0),
        (ForecastMetric.FG_ATTEMPT.value, 24.0),
        (ForecastMetric.XP_MADE.value, 30.0),
    )
    stats_two = (
        (ForecastMetric.FG_MADE.value, 22.0),
        (ForecastMetric.FG_ATTEMPT.value, 27.0),
        (ForecastMetric.XP_MADE.value, 32.0),
    )
    artifact = _artifact(
        _snapshot("one", position=Position.K, stats=stats_one, hash_char="a"),
        _snapshot("two", position=Position.K, stats=stats_two, hash_char="b"),
    )
    rules = _k_rules(
        ScoringRule(stat="fgm", points=3),
        ScoringRule(stat="fgmiss", points=-1),
        ScoringRule(stat="xpm", points=1),
    )

    with pytest.raises(ValueError, match="full K/DST Forecast authority is available"):
        build_provisional_k_dst_forecast(
            artifact,
            league_id="league-1",
            league_state_id="state-1",
            subject_key="K:tylerbass:BUF",
            rules=rules,
            promoted_uncertainty_fingerprint_ids=frozenset(
                {K_REDUCED_2024_FINGERPRINT.fingerprint_id}
            ),
        )


class _ArtifactStore:
    def __init__(self, record, *, ignore_scope: bool = False) -> None:
        self.record = record
        self.ignore_scope = ignore_scope

    def get_latest_reusable_artifact(
        self,
        *,
        artifact_kind: str,
        scope_kind: str,
        scope_id: str,
        model_version: str,
    ):
        if self.ignore_scope:
            return self.record
        return self.record if scope_id == self.record.key.scope_id else None


def _runtime_stub(*, league_id: str = "league-1", state_id: str = "state-1", season: int = 2026):
    return SimpleNamespace(
        league_state=SimpleNamespace(
            league=SimpleNamespace(league_id=league_id, season=season),
            state_id=state_id,
        )
    )


def test_product_lookup_is_scoped_to_exact_league_state_and_revalidates_payload_identity() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.DST,
            stats=((ForecastMetric.DST_SACK.value, 40.0),),
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.DST,
            stats=((ForecastMetric.DST_SACK.value, 42.0),),
            hash_char="b",
        ),
    )
    forecast = build_provisional_k_dst_forecast(
        artifact,
        league_id="league-1",
        league_state_id="state-1",
        subject_key="DST:BUF",
        rules=_dst_rules(ScoringRule(stat="sack", points=1)),
    )
    record = provisional_k_dst_forecast_artifact(forecast=forecast)
    store = _ArtifactStore(record)

    payload = load_provisional_k_dst_presentation(
        _runtime_stub(),
        persistence_store=store,
        subject_key="DST:BUF",
    )
    assert payload["league_state_id"] == "state-1"
    assert payload["fantasy_points"] == pytest.approx(41.0)

    with pytest.raises(ProvisionalKDstLookupError) as missing:
        load_provisional_k_dst_presentation(
            _runtime_stub(state_id="state-2"),
            persistence_store=store,
            subject_key="DST:BUF",
        )
    assert missing.value.status_code == 404

    with pytest.raises(ProvisionalKDstLookupError) as mismatch:
        load_provisional_k_dst_presentation(
            _runtime_stub(state_id="state-2"),
            persistence_store=_ArtifactStore(record, ignore_scope=True),
            subject_key="DST:BUF",
        )
    assert mismatch.value.status_code == 409


def test_product_lookup_hard_fails_outside_2026() -> None:
    with pytest.raises(ProvisionalKDstLookupError) as exc:
        load_provisional_k_dst_presentation(
            _runtime_stub(season=2027),
            persistence_store=None,
            subject_key="DST:BUF",
        )
    assert exc.value.status_code == 404



class _CaptureArtifactStore:
    def __init__(self) -> None:
        self.rows = []

    def put_artifact(self, record) -> None:
        self.rows.append(record)


def _materialization_state(rules: LeagueRules):
    return SimpleNamespace(
        league=SimpleNamespace(
            season=2026,
            league_id="league-materialize",
            rules=rules,
        ),
        state_id="state-materialize",
        as_of=CAPTURED,
    )


def test_provisional_materializer_persists_only_rights_cleared_supported_subjects() -> None:
    artifact = _artifact(
        _snapshot(
            "one",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 20.0),),
            independence_group="one",
            rights_status=ProjectionRightsStatus.LICENSED_BETA,
            hash_char="a",
        ),
        _snapshot(
            "two",
            position=Position.K,
            stats=((ForecastMetric.XP_MADE.value, 22.0),),
            independence_group="two",
            rights_status=ProjectionRightsStatus.PRODUCTION_CLEARED,
            hash_char="b",
        ),
    )
    store = _CaptureArtifactStore()
    summary = materialize_provisional_k_dst_for_state(
        _materialization_state(
            _k_rules(ScoringRule(stat="xpm", points=1.0))
        ),
        snapshot=artifact,
        persistence_store=store,  # type: ignore[arg-type]
    )

    assert summary.rights_cleared_provider_ids == ("one", "two")
    assert summary.eligible_subject_keys == ("K:tylerbass:BUF",)
    assert summary.persisted_subject_keys == ("K:tylerbass:BUF",)
    assert summary.blockers == ()
    assert len(store.rows) == 1
    decoded = decode_provisional_k_dst_forecast(dict(store.rows[0].payload))
    assert decoded.league_id == "league-materialize"
    assert decoded.league_state_id == "state-materialize"
    assert decoded.fantasy_points_mean == pytest.approx(21.0)


def test_provisional_materializer_keeps_research_only_snapshot_non_promoting() -> None:
    artifact = _artifact(
        _snapshot(
            "cbs",
            position=Position.DST,
            stats=((ForecastMetric.DST_SACK.value, 40.0),),
            independence_group="cbs",
            rights_status=ProjectionRightsStatus.RESEARCH_ONLY,
            hash_char="c",
        ),
    )
    store = _CaptureArtifactStore()
    summary = materialize_provisional_k_dst_for_state(
        _materialization_state(
            _dst_rules(ScoringRule(stat="sack", points=1.0))
        ),
        snapshot=artifact,
        persistence_store=store,  # type: ignore[arg-type]
    )

    assert summary.persisted_subject_keys == ()
    assert summary.rights_cleared_provider_ids == ()
    assert summary.research_only_provider_ids == ("cbs",)
    assert "no_rights_cleared_accepted_ros_subjects" in summary.blockers
    assert (
        "research_only_ros_sources_cannot_promote_private_beta_forecast"
        in summary.blockers
    )
    assert store.rows == []

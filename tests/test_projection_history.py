from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.projection_history import (
    ProjectionBasis,
    ProjectionObservationRecord,
    ProjectionSelector,
    normalized_projection_fingerprint,
    revision_from_forecast_observations,
    career_ros_projection_selector,
)
from fsffl.persistence.projection_history import PostgresProjectionHistoryStore
from fsffl.state.models import Position, Provenance, ProviderRef


NOW = datetime(2026, 9, 11, 16, 0, tzinfo=UTC)


def _observation(
    *,
    player_id: str = "p1",
    metric: ForecastMetric = ForecastMetric.RUSH_YARDS,
    mean: float = 800.0,
    horizon: ForecastHorizon = ForecastHorizon.REST_OF_SEASON,
    source: str = "provider-a",
) -> ForecastObservation:
    effective = NOW - timedelta(hours=3)
    retrieved = NOW - timedelta(hours=2)
    return ForecastObservation(
        player_id=player_id,
        position=Position.RB,
        horizon=horizon,
        metric=metric,
        period_start=NOW + timedelta(days=1),
        period_end=NOW + timedelta(days=100),
        distribution=ForecastDistribution(mean=mean, stddev=12.0),
        source=source,
        model_version="provider-a-ros-v1",
        as_of=NOW,
        provenance=Provenance(
            source=source,
            retrieved_at=retrieved,
            effective_at=effective,
            provider_ref=ProviderRef(provider=source, external_id=f"ext:{player_id}"),
            source_version="provider-a-ros-v1",
        ),
    )


def test_projection_selector_requires_explicit_week_for_week_horizon():
    with pytest.raises(ValueError, match="requires week"):
        ProjectionSelector(season=2026, horizon=ForecastHorizon.WEEK)

    selector = ProjectionSelector(season=2026, horizon=ForecastHorizon.WEEK, week=4)
    assert selector.week == 4


def test_projection_selector_does_not_allow_week_on_ros():
    with pytest.raises(ValueError, match="only for WEEK"):
        ProjectionSelector(
            season=2026,
            horizon=ForecastHorizon.REST_OF_SEASON,
            week=4,
        )


def test_preseason_baseline_is_explicit_and_cannot_be_confused_with_provider_ros():
    selector = ProjectionSelector(
        season=2026,
        horizon=ForecastHorizon.SEASON,
        basis=ProjectionBasis.PRESEASON_BASELINE,
    )
    assert selector.basis == ProjectionBasis.PRESEASON_BASELINE

    with pytest.raises(ValueError, match="requires SEASON"):
        ProjectionSelector(
            season=2026,
            horizon=ForecastHorizon.REST_OF_SEASON,
            basis=ProjectionBasis.PRESEASON_BASELINE,
        )


def test_projection_fingerprint_is_semantic_and_order_independent():
    first = ProjectionObservationRecord(
        player_id="p1",
        external_id="ext:p1",
        position=Position.RB,
        metric=ForecastMetric.RUSH_YARDS,
        mean=800.0,
    )
    second = ProjectionObservationRecord(
        player_id="p2",
        external_id="ext:p2",
        position=Position.WR,
        metric=ForecastMetric.REC_YARDS,
        mean=900.0,
    )
    assert normalized_projection_fingerprint((first, second)) == normalized_projection_fingerprint(
        (second, first)
    )
    changed = second.model_copy(update={"mean": 901.0})
    assert normalized_projection_fingerprint((first, second)) != normalized_projection_fingerprint(
        (first, changed)
    )


def test_revision_packages_existing_forecast_evidence_without_recalculating_it():
    observations = (
        _observation(metric=ForecastMetric.RUSH_YARDS, mean=800.0),
        _observation(metric=ForecastMetric.RUSH_TD, mean=7.0),
    )
    revision = revision_from_forecast_observations(
        observations,
        provider="provider-a",
        season=2026,
        horizon=ForecastHorizon.REST_OF_SEASON,
        usage_class="test",
    )

    assert revision.snapshot.horizon == ForecastHorizon.REST_OF_SEASON
    assert revision.snapshot.effective_at == observations[0].provenance.effective_at
    assert revision.snapshot.retrieved_at == observations[0].provenance.retrieved_at
    assert revision.snapshot.content_fingerprint
    assert {item.metric for item in revision.observations} == {
        ForecastMetric.RUSH_YARDS,
        ForecastMetric.RUSH_TD,
    }
    assert next(item for item in revision.observations if item.metric == ForecastMetric.RUSH_YARDS).mean == 800.0


def test_revision_rejects_wrong_horizon_instead_of_relabeling_it():
    with pytest.raises(ValueError, match="requested horizon"):
        revision_from_forecast_observations(
            (_observation(horizon=ForecastHorizon.WEEK),),
            provider="provider-a",
            season=2026,
            horizon=ForecastHorizon.REST_OF_SEASON,
        )


def test_store_query_contract_is_horizon_and_cutoff_aware():
    cutoff = NOW - timedelta(days=2)
    selector = ProjectionSelector(
        season=2026,
        horizon=ForecastHorizon.REST_OF_SEASON,
        as_of=cutoff,
        provider="provider-a",
    )
    where, params = PostgresProjectionHistoryStore._selector_where(selector)

    assert "season=%s" in where
    assert "horizon=%s" in where
    assert "provider=%s" in where
    assert "effective_at <= %s" in where
    assert "retrieved_at <= %s" in where
    assert params == [2026, "rest_of_season", None, "provider-a", cutoff, cutoff]


@pytest.mark.parametrize("changes", [
    {"period_start": NOW},
    {"period_end": NOW},
    {"period_start": NOW, "period_end": NOW},
    {"period_start": NOW.replace(tzinfo=None), "period_end": NOW + timedelta(days=1)},
])
def test_projection_selector_rejects_ambiguous_period(changes):
    with pytest.raises(ValueError):
        ProjectionSelector(season=2026, horizon=ForecastHorizon.REST_OF_SEASON, **changes)


def test_career_reads_and_fingerprints_select_correct_window_before_decoding():
    """A newer raw research capture must not shadow canonical ROS evidence.

    Mirror the hosted failure: research has fum_lost/standard_points and a
    capture-to-Jan15 window; admitted Forecast has fumbles_lost and Week6-18.
    Also exclude a same-window row retrieved after the pinned cutoff.
    """
    from contextlib import nullcontext

    cutoff = datetime(2026, 10, 17, 4, 46, tzinfo=UTC)
    selector = career_ros_projection_selector(season=2026, completed_through_week=5, as_of=cutoff)
    assert selector.period_start == datetime(2026, 10, 6, tzinfo=UTC)
    assert selector.period_end == datetime(2027, 1, 5, tzinfo=UTC)
    base = dict(
        id=1, provider="cbs", season=2026, horizon="rest_of_season", week=None,
        period_start=selector.period_start, period_end=selector.period_end,
        effective_at=cutoff-timedelta(hours=6), retrieved_at=cutoff-timedelta(hours=5),
        source_version="accepted-source-v1", usage_class="test",
        content_fingerprint="unchanged-source-fingerprint", raw_payload={"receipt": "original"},
    )
    research = dict(base, id=2, period_start=cutoff-timedelta(hours=3),
                    period_end=datetime(2027, 1, 15, tzinfo=UTC),
                    effective_at=cutoff-timedelta(hours=2), retrieved_at=cutoff-timedelta(hours=1))
    future = dict(base, id=3, effective_at=cutoff, retrieved_at=cutoff+timedelta(seconds=1))
    queries = []

    class Cursor:
        def execute(self, sql, params):
            queries.append((sql, params))
            self.sql = sql
            if "from fsffl.projection_snapshot" in sql:
                # The shared SQL predicate executes before DISTINCT ON(provider).
                assert "period_start=%s" in sql and "period_end=%s" in sql
                assert "effective_at <= %s" in sql and "retrieved_at <= %s" in sql
                assert params == [2026, "rest_of_season", None, selector.period_start,
                                  selector.period_end, cutoff, cutoff]
                eligible = [r for r in (base, research, future)
                            if r["period_start"] == params[3] and r["period_end"] == params[4]
                            and r["effective_at"] <= params[5] and r["retrieved_at"] <= params[6]]
                self.rows = [max(eligible, key=lambda r: r["effective_at"])]
            else:
                assert params == [1], "never decode the wrong-window research observations"
                self.rows = [dict(player_id="p1", external_id="ext:p1", position="RB",
                                  metric="fumbles_lost", mean=1.25, stddev=0.5,
                                  p10=None, p50=None, p90=None)]

        def fetchall(self):
            return self.rows

    cursor = Cursor()
    connection = type("Connection", (), {"cursor": lambda self: nullcontext(cursor)})()
    store = PostgresProjectionHistoryStore("test", connect_factory=lambda: nullcontext(connection))
    revision, = store.latest_revisions(selector)
    assert revision.snapshot.content_fingerprint == base["content_fingerprint"]
    for field in ("effective_at", "retrieved_at", "period_start", "period_end", "source_version", "raw_payload"):
        assert getattr(revision.snapshot, field) == base[field]
    assert revision.observations[0].metric == ForecastMetric.FUMBLES_LOST
    assert revision.observations[0].mean == 1.25
    fingerprints = store.latest_revision_fingerprints(selector)
    assert fingerprints[0]["content_fingerprint"] == base["content_fingerprint"]
    assert fingerprints[0]["period_start"] == selector.period_start.isoformat()
    assert len(queries) == 3  # bounded snapshot + observations + metadata reads

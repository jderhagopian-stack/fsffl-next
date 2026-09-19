from __future__ import annotations

from datetime import UTC, datetime

from fsffl.behavioral.action_context import BehavioralActionContext, BehavioralPositionContext
from fsffl.behavioral.context_dataset import (
    BehavioralContextCalibrationDataset,
    BehavioralContextCalibrationRow,
)
from fsffl.behavioral.context_expectation import (
    BehavioralContextExpectationPolicy,
    estimate_context_acquisition_distribution,
    fit_behavioral_context_expectation_model,
)
from fsffl.state.models import Position


def dt(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def context(
    event_id: str,
    owner_id: str,
    day: int,
    *,
    rb_active: int,
    rb_league: float = 4.0,
    wr_active: int = 5,
    wr_league: float = 5.0,
) -> BehavioralActionContext:
    positions = (
        BehavioralPositionContext(
            position=Position.QB,
            rostered_count=3,
            active_rostered_count=3,
            direct_starter_requirement=1,
            league_average_rostered_count=3.0,
            league_average_active_rostered_count=3.0,
        ),
        BehavioralPositionContext(
            position=Position.RB,
            rostered_count=rb_active,
            active_rostered_count=rb_active,
            direct_starter_requirement=2,
            league_average_rostered_count=rb_league,
            league_average_active_rostered_count=rb_league,
        ),
        BehavioralPositionContext(
            position=Position.WR,
            rostered_count=wr_active,
            active_rostered_count=wr_active,
            direct_starter_requirement=3,
            league_average_rostered_count=wr_league,
            league_average_active_rostered_count=wr_league,
        ),
        BehavioralPositionContext(
            position=Position.TE,
            rostered_count=2,
            active_rostered_count=2,
            direct_starter_requirement=1,
            league_average_rostered_count=2.0,
            league_average_active_rostered_count=2.0,
        ),
    )
    return BehavioralActionContext(
        event_id=event_id,
        owner_id=owner_id,
        team_id=f"team-{owner_id}",
        league_id="league",
        occurred_at=dt(day),
        snapshot_as_of=datetime(2026, 1, day, 11, tzinfo=UTC),
        snapshot_state_id=f"state-{event_id}",
        snapshot_age_seconds=3600.0,
        roster_size=18,
        active_roster_size=18,
        faab_balance=100,
        owned_pick_count=6,
        flex_slot_count=1,
        superflex_slot_count=1,
        positions=positions,
        source_state_schema_version="1",
    )


def row(
    event_id: str,
    owner_id: str,
    day: int,
    acquired: dict[str, int],
    *,
    rb_active: int,
    wr_active: int = 5,
) -> BehavioralContextCalibrationRow:
    ctx = context(event_id, owner_id, day, rb_active=rb_active, wr_active=wr_active)
    return BehavioralContextCalibrationRow(
        event_id=event_id,
        owner_id=owner_id,
        season=2026,
        occurred_at=dt(day),
        event_kind="trade",
        acquired_position_counts=acquired,
        context=ctx,
    )


def dataset(rows: list[BehavioralContextCalibrationRow]) -> BehavioralContextCalibrationDataset:
    return BehavioralContextCalibrationDataset(
        rows=tuple(rows),
        unavailable=(),
        total_event_count=len(rows),
        usable_event_count=len(rows),
        coverage_rate=1.0 if rows else 0.0,
    )


def policy(*, neighbors: int = 4, owners: int = 2, prior_strength: float = 0.0) -> BehavioralContextExpectationPolicy:
    return BehavioralContextExpectationPolicy(
        parameter_id="behavioral:context-knn-test-v1",
        neighbor_count=neighbors,
        prior_strength=prior_strength,
        min_distinct_owners=owners,
        provenance="test fixture",
    )


def test_context_expectation_excludes_focal_owner_history() -> None:
    training = dataset(
        [
            # Focal owner buys RB repeatedly, but this history must not teach the
            # context-only baseline used to evaluate that same owner.
            row("focal-1", "focal", 2, {"RB": 1}, rb_active=1),
            row("focal-2", "focal", 3, {"RB": 1}, rb_active=1),
            # Other owners in comparable contexts chose WR.
            row("other-a", "a", 4, {"WR": 1}, rb_active=1),
            row("other-b", "b", 5, {"WR": 1}, rb_active=1),
        ]
    )
    model = fit_behavioral_context_expectation_model(training)
    target = context("target", "focal", 10, rb_active=1)

    result = estimate_context_acquisition_distribution(
        model,
        target,
        owner_id="focal",
        policy=policy(neighbors=2),
    )

    assert result.unavailable_reason is None
    assert result.training_owner_count == 2
    assert result.share_for("WR") > result.share_for("RB")


def test_context_expectation_prefers_similar_shortage_contexts() -> None:
    training = dataset(
        [
            # Similar RB-short contexts acquire RB.
            row("short-a", "a", 2, {"RB": 1}, rb_active=1),
            row("short-b", "b", 3, {"RB": 1}, rb_active=1),
            # Distant RB-surplus contexts acquire WR.
            row("deep-c", "c", 4, {"WR": 1}, rb_active=7),
            row("deep-d", "d", 5, {"WR": 1}, rb_active=7),
        ]
    )
    model = fit_behavioral_context_expectation_model(training)
    target = context("target", "target-owner", 10, rb_active=1)

    result = estimate_context_acquisition_distribution(
        model,
        target,
        owner_id="target-owner",
        policy=policy(neighbors=2),
    )

    assert result.unavailable_reason is None
    assert result.share_for("RB") > result.share_for("WR")
    assert abs(sum(item.expected_acquisition_share for item in result.expectations) - 1.0) < 1e-12


def test_context_expectation_filters_future_actions() -> None:
    training = dataset(
        [
            row("past-a", "a", 2, {"RB": 1}, rb_active=1),
            row("past-b", "b", 3, {"RB": 1}, rb_active=1),
            # These future WR actions must not affect a day-10 prediction.
            row("future-c", "c", 20, {"WR": 1}, rb_active=1),
            row("future-d", "d", 21, {"WR": 1}, rb_active=1),
        ]
    )
    model = fit_behavioral_context_expectation_model(training)
    target = context("target", "target-owner", 10, rb_active=1)

    result = estimate_context_acquisition_distribution(
        model,
        target,
        owner_id="target-owner",
        policy=policy(neighbors=2),
    )

    assert result.unavailable_reason is None
    assert result.training_owner_count == 2
    assert result.training_through == dt(3)
    assert result.share_for("RB") > result.share_for("WR")


def test_context_expectation_fails_closed_on_too_few_other_owners() -> None:
    training = dataset(
        [
            row("a1", "a", 2, {"RB": 1}, rb_active=1),
            row("a2", "a", 3, {"RB": 1}, rb_active=1),
        ]
    )
    model = fit_behavioral_context_expectation_model(training)
    target = context("target", "target-owner", 10, rb_active=1)

    result = estimate_context_acquisition_distribution(
        model,
        target,
        owner_id="target-owner",
        policy=policy(neighbors=2, owners=2),
    )

    assert result.expectations == ()
    assert "insufficient distinct" in (result.unavailable_reason or "")


def test_context_expectation_shrinkage_is_explicit_and_empirical() -> None:
    training = dataset(
        [
            row("short-a", "a", 2, {"RB": 1}, rb_active=1),
            row("short-b", "b", 3, {"RB": 1}, rb_active=1),
            row("deep-c", "c", 4, {"WR": 1}, rb_active=7),
            row("deep-d", "d", 5, {"WR": 1}, rb_active=7),
        ]
    )
    model = fit_behavioral_context_expectation_model(training)
    target = context("target", "target-owner", 10, rb_active=1)

    no_shrink = estimate_context_acquisition_distribution(
        model,
        target,
        owner_id="target-owner",
        policy=policy(neighbors=2, prior_strength=0.0),
    )
    shrunk = estimate_context_acquisition_distribution(
        model,
        target,
        owner_id="target-owner",
        policy=policy(neighbors=2, prior_strength=20.0),
    )

    rb_no_shrink = next(item for item in no_shrink.expectations if item.position == Position.RB)
    rb_shrunk = next(item for item in shrunk.expectations if item.position == Position.RB)
    assert rb_no_shrink.evidence_weight == 1.0
    assert rb_shrunk.evidence_weight < 1.0
    assert rb_shrunk.expected_acquisition_share < rb_no_shrink.expected_acquisition_share

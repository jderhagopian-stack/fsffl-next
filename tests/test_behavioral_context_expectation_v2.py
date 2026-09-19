from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.behavioral.action_context import BehavioralActionContext, BehavioralPositionContext
from fsffl.behavioral.context_dataset import BehavioralContextCalibrationDataset, BehavioralContextCalibrationRow
from fsffl.behavioral.context_expectation import BehavioralContextExpectationPolicy
from fsffl.behavioral.context_expectation_v2 import (
    estimate_multiclass_context_acquisition_distribution,
    fit_behavioral_multiclass_context_expectation_model,
)
from fsffl.state.models import Position


def dt(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def context(event_id: str, owner_id: str, day: int, *, rb_active: int, wr_active: int = 5) -> BehavioralActionContext:
    counts = {Position.QB: 3, Position.RB: rb_active, Position.WR: wr_active, Position.TE: 2}
    league = {Position.QB: 3.0, Position.RB: 4.0, Position.WR: 5.0, Position.TE: 2.0}
    starters = {Position.QB: 1, Position.RB: 2, Position.WR: 3, Position.TE: 1}
    positions = tuple(
        BehavioralPositionContext(
            position=position,
            rostered_count=counts[position],
            active_rostered_count=counts[position],
            direct_starter_requirement=starters[position],
            league_average_rostered_count=league[position],
            league_average_active_rostered_count=league[position],
        )
        for position in (Position.QB, Position.RB, Position.WR, Position.TE)
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


def row(event_id: str, owner_id: str, day: int, acquired: dict[str, int], *, rb_active: int) -> BehavioralContextCalibrationRow:
    ctx = context(event_id, owner_id, day, rb_active=rb_active)
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
        rows=tuple(rows), unavailable=(), total_event_count=len(rows), usable_event_count=len(rows), coverage_rate=1.0
    )


def policy(*, neighbors: int = 2, owners: int = 2, prior_strength: float = 0.0) -> BehavioralContextExpectationPolicy:
    return BehavioralContextExpectationPolicy(
        parameter_id="behavioral:multiclass-context-test-v2",
        neighbor_count=neighbors,
        prior_strength=prior_strength,
        min_distinct_owners=owners,
        provenance="test fixture",
    )


def test_multiclass_model_learns_cross_position_substitution_from_full_roster() -> None:
    training = dataset([
        row("short-a", "a", 2, {"RB": 1}, rb_active=1),
        row("short-b", "b", 3, {"RB": 1}, rb_active=1),
        row("deep-c", "c", 4, {"WR": 1}, rb_active=7),
        row("deep-d", "d", 5, {"WR": 1}, rb_active=7),
    ])
    model = fit_behavioral_multiclass_context_expectation_model(training)

    short = estimate_multiclass_context_acquisition_distribution(
        model, context("short-target", "target", 10, rb_active=1), owner_id="target", policy=policy()
    )
    deep = estimate_multiclass_context_acquisition_distribution(
        model, context("deep-target", "target", 10, rb_active=7), owner_id="target", policy=policy()
    )

    assert short.share_for("RB") > short.share_for("WR")
    assert deep.share_for("WR") > deep.share_for("RB")
    assert all(item.neighbor_count == 2 for item in short.expectations)
    assert all(item.distinct_owner_count == 2 for item in short.expectations)


def test_multiclass_model_excludes_focal_owner_and_future_actions() -> None:
    training = dataset([
        row("focal", "target", 2, {"RB": 1}, rb_active=1),
        row("past-a", "a", 3, {"WR": 1}, rb_active=1),
        row("past-b", "b", 4, {"WR": 1}, rb_active=1),
        row("future-c", "c", 20, {"RB": 1}, rb_active=1),
        row("future-d", "d", 21, {"RB": 1}, rb_active=1),
    ])
    model = fit_behavioral_multiclass_context_expectation_model(training)
    result = estimate_multiclass_context_acquisition_distribution(
        model, context("target-event", "target", 10, rb_active=1), owner_id="target", policy=policy()
    )

    assert result.unavailable_reason is None
    assert result.training_owner_count == 2
    assert result.training_through == dt(4)
    assert result.share_for("WR") > result.share_for("RB")


def test_multiclass_shrinkage_moves_neighbor_distribution_toward_pooled_prior() -> None:
    training = dataset([
        row("short-a", "a", 2, {"RB": 1}, rb_active=1),
        row("short-b", "b", 3, {"RB": 1}, rb_active=1),
        row("deep-c", "c", 4, {"WR": 1}, rb_active=7),
        row("deep-d", "d", 5, {"WR": 1}, rb_active=7),
    ])
    model = fit_behavioral_multiclass_context_expectation_model(training)
    result = estimate_multiclass_context_acquisition_distribution(
        model,
        context("target", "target", 10, rb_active=1),
        owner_id="target",
        policy=policy(prior_strength=2.0),
    )

    rb = next(item for item in result.expectations if item.position == Position.RB)
    assert rb.raw_neighbor_share == 1.0
    assert rb.pooled_prior_share == 0.5
    assert rb.evidence_weight == pytest.approx(0.5)
    assert rb.expected_acquisition_share == pytest.approx(0.75)
    assert sum(item.expected_acquisition_share for item in result.expectations) == pytest.approx(1.0)


def test_multiclass_model_fails_closed_with_too_few_other_owners() -> None:
    training = dataset([row("a1", "a", 2, {"RB": 1}, rb_active=1), row("a2", "a", 3, {"RB": 1}, rb_active=1)])
    model = fit_behavioral_multiclass_context_expectation_model(training)
    result = estimate_multiclass_context_acquisition_distribution(
        model, context("target", "target", 10, rb_active=1), owner_id="target", policy=policy(owners=2)
    )
    assert result.unavailable_reason is not None
    assert result.expectations == ()


def test_multiclass_observation_contains_context_not_owner_indicator() -> None:
    model = fit_behavioral_multiclass_context_expectation_model(
        dataset([row("a", "owner-a", 2, {"RB": 1}, rb_active=1)])
    )
    observation = model.observations[0]
    assert observation.owner_id == "owner-a"
    assert len(observation.features) == 21
    assert all(not isinstance(value, str) for value in observation.features)

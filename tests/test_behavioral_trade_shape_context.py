from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.behavioral.action_context import BehavioralActionContext, BehavioralPositionContext
from fsffl.behavioral.context_dataset import BehavioralContextCalibrationDataset, BehavioralContextCalibrationRow
from fsffl.behavioral.context_expectation import BehavioralContextExpectationPolicy
from fsffl.behavioral.models import BehavioralAsset, BehavioralAssetKind, BehavioralEventKind, OwnerBehaviorEvent
from fsffl.behavioral.residual_preference import BehavioralResidualPolicy
from fsffl.behavioral.trade_shape_context import (
    BehavioralTradeShape,
    build_owner_trade_shape_preference_profile,
    classify_behavioral_trade_shape,
    estimate_trade_shape_context_distribution,
    fit_behavioral_trade_shape_context_model,
)
from fsffl.state.models import Position


def dt(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def asset(ref: str) -> BehavioralAsset:
    return BehavioralAsset(kind=BehavioralAssetKind.PLAYER, asset_ref=ref, position="WR")


def event(event_id: str, owner: str, day: int, *, sent: int, received: int) -> OwnerBehaviorEvent:
    return OwnerBehaviorEvent(
        event_id=event_id,
        league_family_id="family",
        league_external_id="league",
        season=2026,
        owner_id=owner,
        roster_id=1,
        occurred_at=dt(day),
        kind=BehavioralEventKind.TRADE,
        acquired=tuple(asset(f"{event_id}-a-{index}") for index in range(received)),
        disposed=tuple(asset(f"{event_id}-d-{index}") for index in range(sent)),
    )


def context(event_id: str, owner: str, day: int, *, rb_active: int) -> BehavioralActionContext:
    counts = {Position.QB: 3, Position.RB: rb_active, Position.WR: 5, Position.TE: 2}
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
        owner_id=owner,
        team_id=f"team-{owner}",
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


def row(ev: OwnerBehaviorEvent, *, rb_active: int) -> BehavioralContextCalibrationRow:
    return BehavioralContextCalibrationRow(
        event_id=ev.event_id,
        owner_id=ev.owner_id,
        season=ev.season,
        occurred_at=ev.occurred_at,
        event_kind="trade",
        acquired_position_counts={"WR": 1},
        context=context(ev.event_id, ev.owner_id, ev.occurred_at.day, rb_active=rb_active),
    )


def dataset(rows: list[BehavioralContextCalibrationRow]) -> BehavioralContextCalibrationDataset:
    return BehavioralContextCalibrationDataset(
        rows=tuple(rows), unavailable=(), total_event_count=len(rows), usable_event_count=len(rows), coverage_rate=1.0
    )


def context_policy() -> BehavioralContextExpectationPolicy:
    return BehavioralContextExpectationPolicy(
        parameter_id="shape-context-test", neighbor_count=2, prior_strength=0.0, min_distinct_owners=2, provenance="test"
    )


def residual_policy() -> BehavioralResidualPolicy:
    return BehavioralResidualPolicy(
        parameter_id="shape-residual-test", prior_strength=2.0, evidence_through=dt(1), provenance="test"
    )


def test_trade_shape_classifier_preserves_existing_structural_definition() -> None:
    assert classify_behavioral_trade_shape(event("c", "o", 2, sent=2, received=1)) == BehavioralTradeShape.CONSOLIDATION
    assert classify_behavioral_trade_shape(event("d", "o", 2, sent=1, received=2)) == BehavioralTradeShape.DIVERSIFICATION
    assert classify_behavioral_trade_shape(event("b", "o", 2, sent=1, received=1)) == BehavioralTradeShape.BALANCED


def test_trade_shape_context_learns_roster_conditioned_shape() -> None:
    events = [
        event("short-a", "a", 2, sent=2, received=1),
        event("short-b", "b", 3, sent=2, received=1),
        event("deep-c", "c", 4, sent=1, received=2),
        event("deep-d", "d", 5, sent=1, received=2),
    ]
    data = dataset([row(events[0], rb_active=1), row(events[1], rb_active=1), row(events[2], rb_active=7), row(events[3], rb_active=7)])
    model = fit_behavioral_trade_shape_context_model(data, events)

    short = estimate_trade_shape_context_distribution(model, context("target-short", "target", 10, rb_active=1), owner_id="target", policy=context_policy())
    deep = estimate_trade_shape_context_distribution(model, context("target-deep", "target", 10, rb_active=7), owner_id="target", policy=context_policy())

    assert short.share_for("consolidation") > short.share_for("diversification")
    assert deep.share_for("diversification") > deep.share_for("consolidation")
    assert sum(item.expected_share for item in short.expectations) == pytest.approx(1.0)


def test_owner_trade_shape_profile_residualizes_each_trade_against_its_context() -> None:
    training = [
        event("short-a", "a", 2, sent=2, received=1),
        event("short-b", "b", 3, sent=2, received=1),
        event("deep-c", "c", 4, sent=1, received=2),
        event("deep-d", "d", 5, sent=1, received=2),
    ]
    focal = [
        event("focal-short", "focal", 10, sent=2, received=1),
        event("focal-deep", "focal", 11, sent=2, received=1),
    ]
    events = training + focal
    rows = [
        row(training[0], rb_active=1), row(training[1], rb_active=1), row(training[2], rb_active=7), row(training[3], rb_active=7),
        row(focal[0], rb_active=1), row(focal[1], rb_active=7),
    ]
    data = dataset(rows)
    model = fit_behavioral_trade_shape_context_model(data, events)
    profile = build_owner_trade_shape_preference_profile(
        data,
        events,
        model,
        owner_id="focal",
        league_family_id="family",
        context_policy=context_policy(),
        residual_policy=residual_policy(),
        as_of=dt(12),
    )

    consolidation = profile.shape("consolidation")
    diversification = profile.shape("diversification")
    assert profile.estimated_trade_count == 2
    assert profile.coverage_rate == 1.0
    assert consolidation.observed_share == 1.0
    assert consolidation.context_expected_share == pytest.approx(0.5)
    assert diversification.context_expected_share == pytest.approx(0.5)
    assert consolidation.raw_residual_share == pytest.approx(0.5)
    assert consolidation.shrunk_residual_share == pytest.approx(0.25)
    assert sum(item.raw_residual_share or 0.0 for item in profile.shapes) == pytest.approx(0.0)

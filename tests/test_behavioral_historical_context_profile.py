from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.behavioral.action_context import BehavioralActionContext, BehavioralPositionContext
from fsffl.behavioral.context_dataset import BehavioralContextCalibrationDataset, BehavioralContextCalibrationRow
from fsffl.behavioral.context_expectation import BehavioralContextExpectationPolicy
from fsffl.behavioral.context_expectation_v2 import fit_behavioral_multiclass_context_expectation_model
from fsffl.behavioral.historical_context_profile import build_owner_historical_context_controlled_preference_profile
from fsffl.behavioral.residual_preference import BehavioralResidualPolicy
from fsffl.state.models import Position


def dt(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def context(event_id: str, owner_id: str, day: int, *, rb_active: int) -> BehavioralActionContext:
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


def row(event_id: str, owner: str, day: int, acquired: dict[str, int], *, rb_active: int) -> BehavioralContextCalibrationRow:
    return BehavioralContextCalibrationRow(
        event_id=event_id,
        owner_id=owner,
        season=2026,
        occurred_at=dt(day),
        event_kind="trade",
        acquired_position_counts=acquired,
        context=context(event_id, owner, day, rb_active=rb_active),
    )


def dataset(rows: list[BehavioralContextCalibrationRow]) -> BehavioralContextCalibrationDataset:
    return BehavioralContextCalibrationDataset(
        rows=tuple(rows), unavailable=(), total_event_count=len(rows), usable_event_count=len(rows), coverage_rate=1.0
    )


def context_policy() -> BehavioralContextExpectationPolicy:
    return BehavioralContextExpectationPolicy(
        parameter_id="context-v2-test", neighbor_count=2, prior_strength=0.0, min_distinct_owners=2, provenance="test"
    )


def residual_policy() -> BehavioralResidualPolicy:
    return BehavioralResidualPolicy(
        parameter_id="residual-test", prior_strength=2.0, evidence_through=dt(1), provenance="test"
    )


def training_rows() -> list[BehavioralContextCalibrationRow]:
    return [
        row("short-a", "a", 2, {"RB": 1}, rb_active=1),
        row("short-b", "b", 3, {"RB": 1}, rb_active=1),
        row("deep-c", "c", 4, {"WR": 1}, rb_active=7),
        row("deep-d", "d", 5, {"WR": 1}, rb_active=7),
    ]


def test_eventwise_profile_compares_each_action_to_its_own_historical_context() -> None:
    rows = training_rows() + [
        row("focal-short", "focal", 10, {"RB": 1}, rb_active=1),
        row("focal-deep", "focal", 11, {"RB": 1}, rb_active=7),
    ]
    data = dataset(rows)
    model = fit_behavioral_multiclass_context_expectation_model(data)
    result = build_owner_historical_context_controlled_preference_profile(
        data,
        model,
        owner_id="focal",
        league_family_id="family",
        context_policy=context_policy(),
        residual_policy=residual_policy(),
        as_of=dt(12),
    )

    profile = result.profile
    rb = profile.position("RB")
    wr = profile.position("WR")
    assert result.coverage.estimated_event_count == 2
    assert result.coverage.event_coverage_rate == 1.0
    assert rb.observed_acquisition_share == 1.0
    # Short context expects RB; deep context expects WR, so aggregate expected RB is 50%.
    assert rb.context_expected_acquisition_share == pytest.approx(0.5)
    assert wr.context_expected_acquisition_share == pytest.approx(0.5)
    assert rb.raw_residual_share == pytest.approx(0.5)
    assert rb.shrunk_residual_share == pytest.approx(0.25)
    assert sum(row.raw_residual_share or 0.0 for row in profile.positions) == pytest.approx(0.0)
    assert sum(row.shrunk_residual_share or 0.0 for row in profile.positions) == pytest.approx(0.0)


def test_uncovered_early_focal_event_is_excluded_from_observed_and_expected() -> None:
    rows = [
        # No other-owner history exists before this focal action, so it must be uncovered.
        row("early-focal", "focal", 1, {"WR": 1}, rb_active=7),
        *training_rows(),
        row("covered-focal", "focal", 10, {"RB": 1}, rb_active=1),
    ]
    data = dataset(rows)
    model = fit_behavioral_multiclass_context_expectation_model(data)
    result = build_owner_historical_context_controlled_preference_profile(
        data,
        model,
        owner_id="focal",
        league_family_id="family",
        context_policy=context_policy(),
        residual_policy=residual_policy(),
        as_of=dt(12),
    )

    assert result.coverage.eligible_event_count == 2
    assert result.coverage.estimated_event_count == 1
    assert result.coverage.eligible_positioned_acquisitions == 2
    assert result.coverage.estimated_positioned_acquisitions == 1
    assert result.coverage.unavailable[0].event_id == "early-focal"
    # If the uncovered WR action leaked into observed counts, this would be 50%, not 100%.
    assert result.profile.position("RB").observed_acquisition_share == 1.0
    assert result.profile.observed_positioned_acquisitions == 1


def test_eventwise_profile_uses_only_actions_at_or_before_as_of() -> None:
    rows = training_rows() + [
        row("past-focal", "focal", 10, {"RB": 1}, rb_active=1),
        row("future-focal", "focal", 20, {"WR": 1}, rb_active=7),
    ]
    data = dataset(rows)
    model = fit_behavioral_multiclass_context_expectation_model(data)
    result = build_owner_historical_context_controlled_preference_profile(
        data, model, owner_id="focal", league_family_id="family", context_policy=context_policy(), residual_policy=residual_policy(), as_of=dt(12)
    )
    assert result.coverage.eligible_event_count == 1
    assert result.profile.position("RB").observed_acquisition_share == 1.0

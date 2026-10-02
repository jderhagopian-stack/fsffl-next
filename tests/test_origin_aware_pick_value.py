from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from fsffl.product.origin_aware_pick_value_runtime import (
    build_origin_aware_pick_values_from_simulation,
)
from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    PickOwnership,
    Provenance,
    Team,
    TeamState,
)
from fsffl.team_utility.future_pick import (
    PickSlotProbability,
    TeamOriginFuturePickDistribution,
)
from fsffl.team_utility.simulation import RegularSeasonSimulationResult
from fsffl.value.historical_pick import HistoricalDraftSlotObservation
from fsffl.value.models import ValueDistribution, ValueScale
from fsffl.value.origin_aware_pick import (
    GenericPickValuePrior,
    OriginAwarePickValueStatus,
)


AS_OF = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
SCALE = ValueScale(
    scale_id="fsffl-pick-economic",
    version="1",
    unit_label="pick economic units",
)
PROV = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _state(
    *,
    owner_a: str = "a",
    owner_b: str = "b",
    include_2028: bool = False,
) -> LeagueState:
    picks = [
        DraftPick(
            pick_id="pick-2027-r1-a",
            league_id="league",
            season=2027,
            round=1,
            original_team_id="a",
        ),
        DraftPick(
            pick_id="pick-2027-r1-b",
            league_id="league",
            season=2027,
            round=1,
            original_team_id="b",
        ),
    ]
    ownership = [
        PickOwnership(pick_id="pick-2027-r1-a", owner_team_id=owner_a),
        PickOwnership(pick_id="pick-2027-r1-b", owner_team_id=owner_b),
    ]
    if include_2028:
        picks.append(
            DraftPick(
                pick_id="pick-2028-r1-a",
                league_id="league",
                season=2028,
                round=1,
                original_team_id="a",
            )
        )
        ownership.append(
            PickOwnership(pick_id="pick-2028-r1-a", owner_team_id=owner_a)
        )
    return LeagueState(
        league=League(
            league_id="league",
            name="Test",
            season=2026,
            rules=LeagueRules(
                team_count=3,
                roster_size=1,
                rookie_draft_rounds=1,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=AS_OF,
        teams=tuple(
            Team(team_id=team_id, league_id="league", display_name=team_id.upper())
            for team_id in ("a", "b", "c")
        ),
        team_states=tuple(
            TeamState(team_id=team_id, roster=())
            for team_id in ("a", "b", "c")
        ),
        players=(),
        player_states=(),
        draft_picks=tuple(picks),
        pick_ownership=tuple(ownership),
        provenance=(PROV,),
    )


def _distribution(
    team_id: str,
    probabilities: tuple[float, float, float],
    *,
    count: int = 50_000,
) -> TeamOriginFuturePickDistribution:
    rows = tuple(
        PickSlotProbability(slot_in_round=slot, probability=probability)
        for slot, probability in enumerate(probabilities, start=1)
        if probability > 0
    )
    expected = sum(row.slot_in_round * row.probability for row in rows)
    cumulative = 0.0
    median = rows[-1].slot_in_round
    for row in rows:
        cumulative += row.probability
        if cumulative >= 0.5:
            median = row.slot_in_round
            break
    return TeamOriginFuturePickDistribution(
        draft_season=2027,
        original_team_id=team_id,
        slot_probabilities=rows,
        expected_slot=expected,
        median_slot=median,
        expected_slot_percentile_from_earliest=(expected - 1.0) / 2.0,
        early_probability=sum(
            row.probability for row in rows if row.slot_in_round == 1
        ),
        mid_probability=sum(
            row.probability for row in rows if row.slot_in_round == 2
        ),
        late_probability=sum(
            row.probability for row in rows if row.slot_in_round == 3
        ),
        simulation_count=count,
        simulation_model_version="sim-v1",
        draft_order_policy_id="draft-order",
        draft_order_policy_version="v1",
        draft_order_policy_authority="derived_standard_fallback",
        draft_order_projection_model_version="pick-slot-v1",
        provenance="Simulation-owned exact team-of-origin slot distribution",
    )


def _simulation(
    *,
    a: tuple[float, float, float] = (0.5, 0.0, 0.5),
    b: tuple[float, float, float] = (0.0, 1.0, 0.0),
    count: int = 50_000,
) -> RegularSeasonSimulationResult:
    return RegularSeasonSimulationResult(
        outcomes=(),
        future_pick_distributions=(
            _distribution("a", a, count=count),
            _distribution("b", b, count=count),
        ),
        simulation_count=count,
        seed=77,
        model_version="sim-result-v1",
        simulation_input_fingerprint="sim-input-fingerprint",
    )


def _obs(
    slot: int,
    mean: float,
    *,
    season: int = 2025,
    stddev: float = 0.0,
    available_at: datetime | None = None,
) -> HistoricalDraftSlotObservation:
    return HistoricalDraftSlotObservation(
        draft_season=season,
        round=1,
        slot_in_round=slot,
        value=ValueDistribution(mean=mean, stddev=stddev),
        scale=SCALE,
        available_at=available_at or datetime(season, 6, 1, tzinfo=UTC),
        model_version=f"slot-economics-{season}",
        provenance=f"PIT slot economics {season}",
    )


def _curve() -> tuple[HistoricalDraftSlotObservation, ...]:
    return (
        _obs(1, 100.0, season=2024, stddev=5.0),
        _obs(1, 100.0, season=2025, stddev=5.0),
        _obs(2, 50.0, season=2024, stddev=5.0),
        _obs(2, 50.0, season=2025, stddev=5.0),
        _obs(3, 20.0, season=2024, stddev=5.0),
        _obs(3, 20.0, season=2025, stddev=5.0),
    )


def _by_pick(results):
    return {row.pick_id: row for row in results}


def test_origin_aware_value_uses_full_nonlinear_probability_mixture() -> None:
    results = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )
    a = results["pick-2027-r1-a"]

    assert a.status == OriginAwarePickValueStatus.ORIGIN_AWARE_AUTHORITATIVE
    assert a.authoritative is True
    assert a.expected_slot == pytest.approx(2.0)
    assert a.origin_aware_estimate is not None
    # E[value(slot)] = 0.5*100 + 0.5*20 = 60.
    # value(E[slot]) would be the slot-2 value, 50, and is not used.
    assert a.origin_aware_estimate.distribution.mean == pytest.approx(60.0)
    assert a.origin_aware_estimate.distribution.mean != pytest.approx(50.0)
    assert a.class_strength_status == "not_applied_no_governed_evidence"
    assert a.horizon_adjustment_status == "not_applied_no_governed_evidence"


def test_same_round_different_origins_receive_different_intrinsic_values() -> None:
    results = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(
                a=(0.8, 0.2, 0.0),
                b=(0.0, 0.2, 0.8),
            ),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )

    a = results["pick-2027-r1-a"].origin_aware_estimate
    b = results["pick-2027-r1-b"].origin_aware_estimate
    assert a is not None and b is not None
    assert a.distribution.mean > b.distribution.mean


def test_ownership_transfer_does_not_change_origin_intrinsic_or_dependency_identity() -> None:
    simulation = _simulation(a=(0.7, 0.2, 0.1))
    before = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(owner_a="a"),
            simulation,
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]
    after = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(owner_a="c"),
            simulation,
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]

    assert before.owner_team_id == "a"
    assert after.owner_team_id == "c"
    assert before.original_team_id == after.original_team_id == "a"
    assert before.origin_aware_estimate == after.origin_aware_estimate
    assert before.dependency_fingerprint == after.dependency_fingerprint


def test_dependency_identity_changes_with_simulation_or_slot_economics() -> None:
    state = _state()
    baseline = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            state,
            _simulation(a=(0.7, 0.2, 0.1)),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]
    changed_distribution = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            state,
            _simulation(a=(0.2, 0.3, 0.5)),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]
    changed_curve = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            state,
            _simulation(a=(0.7, 0.2, 0.1)),
            slot_value_observations=(
                _obs(1, 120.0, season=2024, stddev=5.0),
                _obs(1, 120.0, season=2025, stddev=5.0),
                *_curve()[2:],
            ),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]

    assert baseline.dependency_fingerprint != changed_distribution.dependency_fingerprint
    assert baseline.dependency_fingerprint != changed_curve.dependency_fingerprint
    assert (
        baseline.origin_aware_estimate.distribution.mean
        != changed_distribution.origin_aware_estimate.distribution.mean
    )
    assert (
        baseline.origin_aware_estimate.distribution.mean
        != changed_curve.origin_aware_estimate.distribution.mean
    )


def test_bimodal_slot_distribution_retains_between_slot_uncertainty() -> None:
    wide = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(a=(0.5, 0.0, 0.5)),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]
    concentrated = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(a=(0.0, 1.0, 0.0)),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]

    assert wide.expected_slot == pytest.approx(concentrated.expected_slot)
    assert wide.origin_aware_estimate is not None
    assert concentrated.origin_aware_estimate is not None
    assert (
        wide.origin_aware_estimate.distribution.stddev
        > concentrated.origin_aware_estimate.distribution.stddev
    )


def test_structural_draft_position_dominance_is_reused_not_reimplemented() -> None:
    inverted = (
        _obs(1, 80.0, season=2024),
        _obs(2, 100.0, season=2024),
        _obs(3, 20.0, season=2024),
    )
    results = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(a=(1.0, 0.0, 0.0), b=(0.0, 1.0, 0.0)),
            slot_value_observations=inverted,
            slot_value_scale=SCALE,
        )
    )
    first = results["pick-2027-r1-a"].origin_aware_estimate
    second = results["pick-2027-r1-b"].origin_aware_estimate

    assert first is not None and second is not None
    assert first.distribution.mean == pytest.approx(90.0)
    assert second.distribution.mean == pytest.approx(90.0)
    assert first.distribution.mean >= second.distribution.mean


def test_missing_probability_bearing_slot_uses_typed_fallback_not_interpolation() -> None:
    prior = GenericPickValuePrior(
        draft_season=2027,
        round=1,
        distribution=ValueDistribution(mean=42.0, stddev=18.0),
        scale=SCALE,
        as_of=AS_OF,
        model_version="generic-prior-v1",
        provenance="Value-owned generic year/round prior",
    )
    observations = (
        _obs(1, 100.0, season=2024),
        _obs(1, 100.0, season=2025),
        # slot 3 intentionally absent
    )
    result = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(a=(0.5, 0.0, 0.5)),
            slot_value_observations=observations,
            slot_value_scale=SCALE,
            generic_priors=(prior,),
        )
    )["pick-2027-r1-a"]

    assert result.status == OriginAwarePickValueStatus.GENERIC_FALLBACK
    assert result.authoritative is False
    assert result.origin_aware_estimate is None
    assert result.generic_fallback_estimate is not None
    assert result.generic_fallback_estimate.distribution.mean == pytest.approx(42.0)
    assert result.missing_slots == (3,)
    assert "No round-median or early/mid/late interpolation" in result.fallback_reason


def test_generic_fallback_dependency_identity_changes_with_prior_economics() -> None:
    observations = (
        _obs(1, 100.0, season=2024),
        _obs(1, 100.0, season=2025),
    )
    first_prior = GenericPickValuePrior(
        draft_season=2027,
        round=1,
        distribution=ValueDistribution(mean=40.0, stddev=10.0),
        scale=SCALE,
        as_of=AS_OF,
        model_version="generic-prior-v1",
        provenance="Value generic prior v1",
    )
    second_prior = first_prior.model_copy(
        update={
            "distribution": ValueDistribution(mean=55.0, stddev=12.0),
            "model_version": "generic-prior-v2",
            "provenance": "Value generic prior v2",
        }
    )

    first = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(a=(0.5, 0.0, 0.5)),
            slot_value_observations=observations,
            slot_value_scale=SCALE,
            generic_priors=(first_prior,),
        )
    )["pick-2027-r1-a"]
    second = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(a=(0.5, 0.0, 0.5)),
            slot_value_observations=observations,
            slot_value_scale=SCALE,
            generic_priors=(second_prior,),
        )
    )["pick-2027-r1-a"]

    assert first.status == second.status == OriginAwarePickValueStatus.GENERIC_FALLBACK
    assert first.dependency_fingerprint != second.dependency_fingerprint
    assert first.generic_fallback_estimate.distribution.mean == pytest.approx(40.0)
    assert second.generic_fallback_estimate.distribution.mean == pytest.approx(55.0)


def test_next_draft_probabilities_are_never_extrapolated_into_farther_future_season() -> None:
    state = _state(include_2028=True)
    result = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            state,
            _simulation(),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2028-r1-a"]

    assert result.status == OriginAwarePickValueStatus.UNSUPPORTED_FUTURE_SEASON
    assert result.slot_probabilities == ()
    assert result.origin_aware_estimate is None
    assert result.expected_slot is None


def test_preview_simulation_can_compute_preview_value_but_cannot_claim_authority() -> None:
    result = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(count=5_000),
            slot_value_observations=_curve(),
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]

    assert result.status == OriginAwarePickValueStatus.ORIGIN_AWARE_PREVIEW
    assert result.authoritative is False
    assert result.origin_aware_estimate is not None
    assert result.simulation_count == 5_000


def test_future_pit_slot_evidence_is_not_used() -> None:
    future_only = (
        _obs(
            1,
            100.0,
            season=2026,
            available_at=datetime(2026, 10, 3, tzinfo=UTC),
        ),
    )
    result = _by_pick(
        build_origin_aware_pick_values_from_simulation(
            _state(),
            _simulation(a=(1.0, 0.0, 0.0)),
            slot_value_observations=future_only,
            slot_value_scale=SCALE,
        )
    )["pick-2027-r1-a"]

    assert (
        result.status
        == OriginAwarePickValueStatus.PARTIAL_MISSING_SLOT_VALUE_EVIDENCE
    )
    assert result.origin_aware_estimate is None
    assert result.missing_slots == (1,)


def test_value_does_not_feed_back_into_simulation_or_draft_order_probability() -> None:
    simulation_source = Path("src/fsffl/team_utility/simulation.py").read_text(
        encoding="utf-8"
    )
    future_pick_source = Path("src/fsffl/team_utility/future_pick.py").read_text(
        encoding="utf-8"
    )
    assert "fsffl.value" not in simulation_source
    assert "fsffl.value" not in future_pick_source
    assert "origin_aware_pick" not in simulation_source
    assert "origin_aware_pick" not in future_pick_source

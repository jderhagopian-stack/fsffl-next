from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Thread
from typing import Any, cast

import pytest

from fsffl.forecast.in_season_orchestration import build_current_ros_fumbles_lost_supplement_observations
from fsffl.forecast.future_contract import (
    CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE,
    FUTURE_FORECAST_CONTRACT_VERSION,
    ForecastUncertaintyKind,
    FutureForecastContract,
    FutureForecastScenario,
    FuturePlayerHorizonForecast,
)
from fsffl.forecast.integrated_i1 import I1ForecastInput, I1ForecastResult, STATE_NAMES
from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.i1_player_scoring import (
    FUTURE_I1_PLAYER_SCORING_VERSION,
    build_future_i1_player_scoring_multipliers,
    translate_future_i1_result_for_player,
)
from fsffl.product.i1_scoring_bridge import (
    FROZEN_I1_STANDARD_SCORING,
    FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
)
from fsffl.product import dynamic_career_composition as bridge
from fsffl.product.p0_forecast_runtime import (
    P0_FINAL_ROUTE_AUTHORITY_SHA256,
    P0_FINAL_ROUTE_AUTHORITY_VERSION,
    P0_FORECAST_VERSION,
    frozen_p0_source_rows,
)
from fsffl.product.p0_future_forecast_provider import build_p0_future_forecast_contract
from fsffl.product.p0_live_candidate_runtime import _score_complete_single_source_year_one
from fsffl.product.p0_live_candidate_runtime import _single_source_fumbles_gap_player_ids
from fsffl.product.private_beta_shapley_runtime import (
    PrivateBetaShapleyContractLoader,
    intrinsic_input_fingerprint,
)
from fsffl.product.intrinsic_background import (
    IntrinsicBuildStatus,
    ShapleyIntrinsicBackgroundCoordinator,
)
from fsffl.product.runtime import UserRuntimeContext
from fsffl.product.vnext_future_forecast_provider import (
    VNEXT_FORECAST_VERSION,
    build_vnext_future_forecast_contract,
    provide_vnext_future_forecast_contract,
    vnext_future_forecast_input_fingerprint,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    Position,
    ProviderRef,
    Provenance,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.value.private_beta_activation_data import (
    ACTIVATION_BUNDLE_SHA256,
    activation_artifact_text,
)
from fsffl.value.shapley_intrinsic import FROZEN_SHAPLEY_PERMUTATIONS
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability


def _fixture() -> tuple[LeagueState, ForecastObservation]:
    source = next(item for item in frozen_p0_source_rows() if item.position == "QB")
    position = Position.QB
    now = datetime(2026, 9, 16, 12, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    player = Player(
        player_id="canonical-player",
        full_name=source.player_name,
        position=position,
        provider_refs=(
            ProviderRef(provider="sleeper", external_id=source.sleeper_external_id),
        ),
    )
    rules = LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=FROZEN_I1_STANDARD_SCORING,
    )
    state = LeagueState(
        league=League(league_id="league", name="Fixture", season=2026, rules=rules),
        as_of=now,
        teams=(
            Team(team_id="a", league_id="league", display_name="A"),
            Team(team_id="b", league_id="league", display_name="B"),
        ),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(player,),
        player_states=(PlayerState(player_id=player.player_id, as_of=now, provenance=provenance),),
    )
    observation = ForecastObservation(
        player_id=player.player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=now,
        period_end=now + timedelta(days=100),
        distribution=ForecastDistribution(mean=source.standard_y1_points, stddev=25.0),
        source="governed-live-fixture",
        model_version="fixture-forecast-v1",
        as_of=now,
        provenance=provenance,
    )
    return state, observation


def _raw_forecasts(observation: ForecastObservation) -> tuple[ForecastObservation, ...]:
    # A scoring-neutral raw stat reconstructs the exact frozen standard/non-PPR
    # P0 coordinate while still exercising direct scoring from raw evidence.
    metrics = (
        (ForecastMetric.RUSH_YARDS, float(observation.distribution.mean) * 10.0),
        (ForecastMetric.RUSH_TD, 0.0),
        (ForecastMetric.FUMBLES_LOST, 0.0),
    )
    return tuple(
        ForecastObservation(
            player_id=observation.player_id,
            position=observation.position,
            horizon=observation.horizon,
            metric=metric,
            period_start=observation.period_start,
            period_end=observation.period_end,
            distribution=ForecastDistribution(mean=mean, stddev=1.0),
            source="raw-fixture",
            model_version="raw-fixture-v1",
            as_of=observation.as_of,
            provenance=observation.provenance,
        )
        for metric, mean in metrics
    )


def _context(state: LeagueState, observation: ForecastObservation) -> UserRuntimeContext:
    evidence = SimpleNamespace(
        raw_forecasts=_raw_forecasts(observation),
        league_scored_forecasts=(observation,),
    )
    return UserRuntimeContext(
        user_id="user",
        league_state=state,
        forecast_evidence=cast(Any, evidence),
    )

def _legacy_p0_contract_builder(**kwargs):
    return build_p0_future_forecast_contract(**kwargs).contract


def _legacy_p0_loader(**kwargs) -> PrivateBetaShapleyContractLoader:
    """Legacy-reference helper; production composition must inject vNext explicitly."""

    return PrivateBetaShapleyContractLoader(
        future_forecast_builder=_legacy_p0_contract_builder,
        future_forecast_model_version=P0_FORECAST_VERSION,
        future_missing_fact_family="p0_future_forecast_coordinate",
        **kwargs,
    )



def _authority_evidence(observation: ForecastObservation):
    year_one = observation.model_copy(
        update={
            "source": "fsffl:preseason_baseline_league_scored",
            "model_version": "authority-fixture-v1",
        }
    )
    return cast(
        Any,
        SimpleNamespace(
            raw_forecasts=_raw_forecasts(year_one),
            league_scored_forecasts=(year_one,),
            successful_source_ids=("fftoday", "razzball"),
            evidence_basis="preseason_baseline",
            runtime_result=SimpleNamespace(
                evaluation_as_of=year_one.as_of,
                model_version="authority-fixture-v1",
                coverage=SimpleNamespace(
                    independent_source_ids=("fftoday", "razzball"),
                    minimum_independent_sources=2,
                ),
            ),
        ),
    )


def test_pinned_activation_bundle_round_trips_and_has_stable_digest() -> None:
    assert len(ACTIVATION_BUNDLE_SHA256) == 64
    report = json.loads(activation_artifact_text("private_beta_activation_build_report.json"))
    facts = json.loads(activation_artifact_text("current_i1_facts_2026.json"))
    assert report["status"] == "PASS"
    assert report["model_changes"] is False
    assert facts["evaluation_season"] == 2026
    assert facts["completed_source_season"] == 2025


def test_loader_serves_degraded_raw_contract_and_excludes_diagnostic_h1() -> None:
    state, observation = _fixture()
    loader = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )
    contract = loader(_context(state, observation))

    assert contract.status == ShapleyIntrinsicAvailability.READY
    assert contract.display_scaling_applied is False
    assert contract.diagnostic_h1_included is False
    assert contract.coverage.player_count == 1
    assert contract.coverage.year_1_forecast_players == 1
    assert contract.coverage.year_2_i1_players == 1
    assert contract.coverage.year_3_i1_players == 1
    assert contract.coverage.reduced_or_fallback_players == 0
    assert contract.forecast_model_version == P0_FORECAST_VERSION
    assert contract.estimates[0].diagnostic_h1.included_in_intrinsic is False
    assert [item.provenance.direct_i1_horizon for item in contract.estimates[0].contributions] == [None, 2, 3]
    assert contract.horizon_seeds == (contract.seed, contract.seed + 1, contract.seed + 2)
    reconstructed = sum(item.discounted_contribution for item in contract.estimates[0].contributions)
    assert abs(reconstructed - contract.estimates[0].raw_intrinsic_value) <= 1e-9


@pytest.mark.parametrize('blocked_stage', [1, 2])
def test_hosted_career_does_not_allocate_next_stage_above_hard_limit(monkeypatch, blocked_stage):
    from fsffl.product import resource_coordinator as resource
    state, year_one = _fixture()
    state = state.model_copy(update={'team_states': (
        state.team_states[0].model_copy(update={'roster': (
            RosterEntry(player_id=year_one.player_id, slot=RosterSlot.BENCH),)}),
        state.team_states[1],
    )})
    calls = []
    resident = iter(([513] if blocked_stage == 1 else [455, 513]))
    monkeypatch.delenv('FSFFL_MEMORY_LIMIT_BYTES', raising=False)
    monkeypatch.setattr(resource, 'current_rss_bytes', lambda: next(resident) * 1024 * 1024)
    monkeypatch.setattr(bridge, 'clear_shapley_execution_caches', lambda: None)
    monkeypatch.setattr(resource, 'release_unused_process_memory', lambda **kw: None)
    def load(_):
        calls.append('year-one')
        return _authority_evidence(year_one)
    def forbidden(*args, **kwargs):
        pytest.fail('current-input acquisition must not run above the hard cap')
    result = bridge.build_dynamic_rostered_career_contract(
        UserRuntimeContext(user_id='fixture', league_state=state),
        SimpleNamespace(estimates=()),
        current_intrinsic_loader=SimpleNamespace(_year_one_loader=load),
        candidate_builder=forbidden,
    )
    assert calls == ([] if blocked_stage == 1 else ['year-one'])
    assert result.contract is None
    assert set(result.failures) == {year_one.player_id}
    assert 'MemoryError: hard memory limit reached before' in result.failures[year_one.player_id]


def test_hosted_career_releases_preseason_evidence_before_live_p0(monkeypatch):
    from weakref import ref

    state, year_one = _fixture()
    class Evidence:
        pass

    evidence = Evidence()
    evidence.__dict__.update(vars(_authority_evidence(year_one)))
    evidence_ref = ref(evidence)
    retained = [evidence]
    del evidence

    def load(_state):
        return retained.pop()

    def candidate_builder(_state, *, projection_history_as_of=None, **kwargs):
        assert evidence_ref() is None, (
            "full preseason evidence must not overlap live P0 allocations"
        )
        return SimpleNamespace(
            failures={}, future=None, year_one_evidence_modes={},
            source_manifest={}, ros_runtime=SimpleNamespace(),
        )

    result = bridge.build_dynamic_rostered_career_contract(
        UserRuntimeContext(user_id="fixture", league_state=state),
        SimpleNamespace(estimates=()),
        current_intrinsic_loader=SimpleNamespace(
            _year_one_loader=load,
        ),
        candidate_builder=candidate_builder,
    )

    assert result.contract is None
    assert evidence_ref() is None


def test_hosted_dynamic_career_bridge_defers_shapley_until_foundation4_complete(
    monkeypatch,
) -> None:
    from fsffl.product import dynamic_career_composition as bridge
    from fsffl.product.p0_live_candidate_runtime import P0LiveCandidateResult
    from fsffl.product.p0_forecast_runtime import frozen_p0_source_rows

    state, base_year_one = _fixture()
    candidate_id = "sleeper:player:dynamic-career-fixture"
    candidate_player = Player(
        player_id=candidate_id,
        full_name="Dynamic Career Fixture",
        position=Position.QB,
    )
    candidate_as_of = base_year_one.as_of
    candidate_y1 = base_year_one.model_copy(update={
        "player_id": candidate_id,
        "source": "fsffl:sleeper-actuals-plus-governed-ros",
        "model_version": "p0-live-y1-raw-v1",
    })
    dynamic_row = next(
        row for row in frozen_p0_source_rows() if row.position == "QB"
    )
    dynamic_row = dynamic_row.__class__(**{
        **dynamic_row.__dict__,
        "player_id": candidate_id,
        "current_player_id": candidate_id,
        "player_name": candidate_player.full_name,
    })
    players = tuple(state.players) + (candidate_player,)
    roster = RosterEntry(
        player_id=candidate_id,
        slot=RosterSlot.BENCH,
    )
    team_states = tuple(
        row.model_copy(update={"roster": (roster,)})
        if row.team_id == "a" else row
        for row in state.team_states
    )
    state = state.model_copy(update={
        "players": players,
        "team_states": team_states,
        "player_states": tuple(state.player_states) + (
            PlayerState(
                player_id=candidate_id,
                age_years=25.0,
                as_of=candidate_as_of,
                provenance=base_year_one.provenance,
            ),
        ),
    })
    raw = _raw_forecasts(candidate_y1)
    dynamic_future = build_p0_future_forecast_contract(
        league_state=state,
        raw_forecasts=raw,
        league_year_one=(candidate_y1,),
        candidate_source_rows={candidate_id: dynamic_row},
    )
    unrelated_rows = tuple(
        row.model_copy(update={"player_id": "sleeper:player:unrelated"})
        for row in dynamic_future.contract.forecasts
    )
    dynamic_future = replace(
        dynamic_future,
        contract=dynamic_future.contract.model_copy(
            update={"forecasts": dynamic_future.contract.forecasts + unrelated_rows}
        ),
    )
    candidate = P0LiveCandidateResult(
        evaluation_as_of=candidate_as_of,
        completed_through_week=4,
        candidate_ids=(candidate_id,),
        candidate_source_rows={candidate_id: dynamic_row},
        year_one_standard={candidate_id: candidate_y1},
        year_one_league={candidate_id: candidate_y1},
        future=dynamic_future,
        failures={},
        ros_runtime=SimpleNamespace(),
        year_one_evidence_modes={},
    )
    evidence = _authority_evidence(base_year_one)
    base_loader = _legacy_p0_loader(
        year_one_loader=lambda _state: evidence,
    )
    context = UserRuntimeContext(user_id="dynamic", league_state=state)

    original = bridge.build_live_calendar_shapley_estimates
    composed_player_counts = []
    # Missing Foundation 4 must not construct and retain the future scenario
    # graph before the materializer phase has completed.
    monkeypatch.setattr(base_loader, "_resolve_future_contract", lambda **kwargs: pytest.fail(
        "future scenarios were built before Foundation 4 completed"))

    def record_full_cohort(calendar, *, rules):
        composed_player_counts.append(calendar.player_count)
        return original(calendar, rules=rules)

    monkeypatch.setattr(bridge, "build_live_calendar_shapley_estimates", record_full_cohort)
    result = bridge.build_dynamic_rostered_career_contract(
        context,
        SimpleNamespace(),
        current_intrinsic_loader=base_loader,
        candidate_builder=lambda _state, *, projection_history_as_of=None: candidate,
    )

    assert composed_player_counts == []
    assert result.contract is None
    assert set(result.failures) == {candidate_id}
    assert "Foundation 4 dynamic materializer input bundle is not configured" in result.failures[candidate_id]
    assert "route/development modules" in result.failures[candidate_id]

    from weakref import ref as weakref_ref
    unrelated_future_rows = []

    def no_components(_context, retained, ids):
        assert retained.ros_runtime is None
        assert retained.future is not candidate.future
        assert set(retained.future.contract.player_ids) == {candidate_id}
        assert retained.future.scoring_multipliers is candidate.future.scoring_multipliers
        assert len(retained.future.contract.forecasts) == 2
        assert set(candidate.future.contract.player_ids) == {
            candidate_id, "sleeper:player:unrelated"
        }
        assert retained.candidate_source_rows == candidate.candidate_source_rows
        assert retained.year_one_league == {candidate_id: candidate_y1}
        assert retained.year_one_standard == {candidate_id: candidate_y1}
        assert retained.ros_fumbles_lost == ()
        assert retained.source_manifest is candidate.source_manifest
        return bridge.DynamicCareerComponents({}, {}, {candidate_id: "no F4 components"})

    candidate = replace(candidate,
        year_one_standard={**candidate.year_one_standard, "noncandidate": base_year_one},
        year_one_league={**candidate.year_one_league, "noncandidate": base_year_one},
        ros_fumbles_lost=(base_year_one,))
    result = bridge.build_dynamic_rostered_career_contract(
        context, SimpleNamespace(), current_intrinsic_loader=base_loader,
        candidate_builder=lambda _state, *, projection_history_as_of=None: candidate, materializer=no_components,
    )
    assert "noncandidate" in candidate.year_one_standard
    assert "noncandidate" in candidate.year_one_league
    assert candidate.ros_fumbles_lost == (base_year_one,)
    assert candidate.ros_runtime is not None  # public builder result unchanged
    assert result.contract is None
    assert result.failures[candidate_id] == "no F4 components"

    def temporary_future_builder(_state, *, projection_history_as_of=None):
        rows = tuple(row.model_copy() for row in candidate.future.contract.forecasts)
        unrelated_future_rows.append(
            weakref_ref(next(row for row in rows if row.player_id == "sleeper:player:unrelated"))
        )
        isolated_contract = candidate.future.contract.model_copy(update={"forecasts": rows})
        return replace(candidate, future=replace(candidate.future, contract=isolated_contract))

    def compacted_before_fit(_context, retained, ids):
        assert unrelated_future_rows[0]() is None
        return no_components(_context, retained, ids)

    reclaimed_full_graph = bridge.build_dynamic_rostered_career_contract(
        context, SimpleNamespace(), current_intrinsic_loader=base_loader,
        candidate_builder=temporary_future_builder, materializer=compacted_before_fit,
    )
    assert reclaimed_full_graph.failures[candidate_id] == "no F4 components"

    from weakref import ref
    unneeded = []
    class UnusedObservation:
        pass
    def temporary_builder(_state, *, projection_history_as_of=None):
        unused = UnusedObservation()
        unneeded.append(ref(unused))
        return replace(candidate,
            year_one_standard={**candidate.year_one_standard, "unused": unused},
            year_one_league={**candidate.year_one_league, "unused": unused},
            ros_fumbles_lost=(unused,))
    def reclaimed_before_fit(_context, retained, ids):
        assert unneeded[0]() is None, "unused acquisition row still overlaps Foundation4"
        return no_components(_context, retained, ids)
    reclaimed = bridge.build_dynamic_rostered_career_contract(
        context, SimpleNamespace(), current_intrinsic_loader=base_loader,
        candidate_builder=temporary_builder, materializer=reclaimed_before_fit,
    )
    assert reclaimed.failures == result.failures

    # Every later allocation must stop when the preceding workspace leaves
    # RSS above the same hard cap: Future contract, Shapley, final composition.
    from fsffl.product import resource_coordinator as resource
    monkeypatch.delenv('FSFFL_MEMORY_LIMIT_BYTES', raising=False)
    monkeypatch.setattr(resource, 'release_unused_process_memory', lambda **kw: None)
    calls = []
    future_owner_refs = []
    def base_future(**kwargs):
        assert tuple(kwargs["raw_forecasts"]) == tuple(evidence.raw_forecasts)
        assert future_owner_refs[-1]() is None, (
            "full dynamic future contract still retained while building base future"
        )
        calls.append('future')
        return SimpleNamespace(player_ids=(base_year_one.player_id,))
    def merge(**kwargs):
        calls.append('shapley')
        return (), None, (), object()
    monkeypatch.setattr(base_loader, '_resolve_future_contract', base_future)
    monkeypatch.setattr(bridge, '_merge_candidate_inputs', merge)
    monkeypatch.setattr(bridge, '_compose_dynamic_career_contract', lambda **kw: pytest.fail(
        'over-limit final composition must not start'))
    def complete_components(*args):
        return bridge.DynamicCareerComponents({candidate_id: ()}, {candidate_id: object()}, {})
    def fresh_candidate(*args, **kwargs):
        fresh_future = build_p0_future_forecast_contract(
            league_state=state, raw_forecasts=raw, league_year_one=(candidate_y1,),
            candidate_source_rows={candidate_id: dynamic_row},
        )
        future_owner_refs.append(ref(fresh_future))
        return replace(candidate, future=fresh_future)
    for index, label, expected in (
        (4, 'career-foundation4-complete', []),
        (5, 'career-before-expanded-shapley', ['future']),
        (6, 'career-before-final-composition', ['future', 'shapley']),
    ):
        calls.clear()
        samples = iter([455] * (index - 1) + [513])
        monkeypatch.setattr(resource, 'current_rss_bytes', lambda: next(samples) * 1024 * 1024)
        with pytest.raises(MemoryError, match=f'hard memory limit reached before {label}'):
            bridge.build_dynamic_rostered_career_contract(
                context, SimpleNamespace(), current_intrinsic_loader=base_loader,
                candidate_builder=fresh_candidate, materializer=complete_components,
            )
        assert future_owner_refs[-1]() is None
        assert calls == expected


def test_hosted_dynamic_career_bridge_scalarizes_structured_provenance() -> None:
    from fsffl.product.dynamic_career_composition import _scalar_provenance

    encoded = _scalar_provenance(
        {
            "dynamic_candidate_ids": ["sleeper:player:b", "sleeper:player:a"],
            "route_inputs": {"version": 1, "families": ["Y4", "Y5"]},
            "accepted": True,
        }
    )

    assert encoded == {
        "dynamic_candidate_ids": '["sleeper:player:b","sleeper:player:a"]',
        "route_inputs": '{"families":["Y4","Y5"],"version":1}',
        "accepted": True,
    }
    assert all(value is None or isinstance(value, (str, bool, int, float)) for value in encoded.values())


def test_dynamic_career_candidate_acquisition_failure_preserves_frozen_base():
    state, observation = _fixture()
    state = state.model_copy(update={
        "team_states": (
            TeamState(
                team_id="a",
                roster=(RosterEntry(player_id="canonical-player", slot=RosterSlot.BENCH),),
            ),
            TeamState(team_id="b", roster=()),
        )
    })
    loader = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )

    def unavailable(_state, *, projection_history_as_of=None):
        raise RuntimeError("projection history unavailable")

    result = bridge.build_dynamic_rostered_career_contract(
        _context(state, observation),
        SimpleNamespace(estimates=()),
        current_intrinsic_loader=loader,
        candidate_builder=unavailable,
    )
    assert result.contract is None
    assert result.failures
    assert all("projection history unavailable" in reason for reason in result.failures.values())


def test_dynamic_career_candidate_builder_receives_pinned_ros_selection_time():
    state, observation = _fixture()
    cutoff = datetime(2026, 10, 15, 5, 59, tzinfo=UTC)
    context = replace(
        _context(state, observation),
        career_fingerprint_evaluation_as_of=cutoff,
    )
    loader = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )
    seen = []

    def candidate_builder(_state, *, projection_history_as_of=None):
        seen.append(projection_history_as_of)
        return SimpleNamespace(future=None, failures={})

    result = bridge.build_dynamic_rostered_career_contract(
        context,
        SimpleNamespace(estimates=()),
        current_intrinsic_loader=loader,
        candidate_builder=candidate_builder,
    )

    assert seen == [cutoff]
    assert result.contract is None
    assert result.failures == {}


def test_dynamic_career_fingerprint_changes_when_ros_revision_identity_changes():
    state, observation = _fixture()
    context = _context(state, observation)
    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)

    class Reader:
        version = "ros-v1"

        def latest_revision_fingerprints(self, _selector):
            from fsffl.forecast.projection_history import career_ros_projection_selector

            assert _selector == career_ros_projection_selector(
                season=state.league.season,
                completed_through_week=state.completed_through_week or 0,
                as_of=now,
            )
            return ({"provider": "cbs", "content_fingerprint": self.version},)

    reader = Reader()
    first = bridge.dynamic_career_fingerprint(
        context, projection_history_reader=reader, now=now
    )
    reader.version = "ros-v2"
    second = bridge.dynamic_career_fingerprint(
        context, projection_history_reader=reader, now=now
    )
    assert first != second


def test_terminal_career_fingerprint_does_not_select_a_nonexistent_ros_window():
    state, observation = _fixture()
    state = state.model_copy(update={"completed_through_week": 18})

    class Reader:
        def latest_revision_fingerprints(self, _selector):
            raise AssertionError("no regular-season ROS remains after Week 18")

    assert bridge.dynamic_career_fingerprint(
        _context(state, observation), projection_history_reader=Reader(),
        now=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )


def test_dynamic_career_fingerprint_changes_for_each_published_capture():
    state, observation = _fixture()
    context = _context(state, observation)
    start = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)

    first = bridge.dynamic_career_fingerprint(context, now=start)
    within_window = bridge.dynamic_career_fingerprint(
        context, now=start + timedelta(hours=5, minutes=59)
    )
    next_window_at = start + timedelta(hours=6)
    next_window = bridge.dynamic_career_fingerprint(
        context, now=next_window_at
    )

    assert within_window != first  # a new governed capture, even in the same window
    assert next_window != first
    assert bridge.dynamic_career_fingerprint(
        context, now=start, include_freshness_epoch=False
    ) == bridge.dynamic_career_fingerprint(
        context, now=next_window_at, include_freshness_epoch=False
    )


def test_private_beta_live_provider_diagnostics_require_manual_dispatch():
    private_beta_workflow = (
        Path(__file__).resolve().parents[1]
        / ".github/workflows/private-beta-intrinsic-diagnostics.yml"
    ).read_text(encoding="utf-8")
    atlas_workflow = (
        Path(__file__).resolve().parents[1]
        / ".github/workflows/league-atlas-north-star.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in private_beta_workflow
    assert "if: github.event_name == 'workflow_dispatch'" in private_beta_workflow
    assert "if: github.event_name == 'pull_request'" in private_beta_workflow
    assert "Provider diagnostics are skipped on pull requests" in private_beta_workflow

    assert "workflow_dispatch:" in atlas_workflow
    assert atlas_workflow.count("if: github.event_name == 'workflow_dispatch'") == 2
    assert "if: github.event_name == 'pull_request'" in atlas_workflow
    assert "Live-league checks are skipped on pull requests" in atlas_workflow
    assert "Record deferred live-check disposition" in atlas_workflow


def test_live_forecast_change_does_not_replace_preseason_authority() -> None:
    state, observation = _fixture()
    loader = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )
    first = loader(_context(state, observation))
    second = loader(_context(state, observation))
    changed_live = observation.model_copy(
        update={"distribution": ForecastDistribution(mean=999.0, stddev=25.0)}
    )
    third = loader(_context(state, changed_live))
    assert first is second
    assert third is first


def test_loader_fails_closed_when_preseason_standard_coordinate_drifts() -> None:
    state, observation = _fixture()
    changed = observation.model_copy(
        update={
            "distribution": ForecastDistribution(
                mean=observation.distribution.mean + 1.0,
                stddev=25.0,
            )
        }
    )
    loader = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(changed)
    )
    contract = loader(_context(state, observation))
    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert "p0_future_forecast_coordinate" in contract.coverage.missing_required_fact_families


def test_loader_fails_closed_when_governed_forecast_player_lacks_completed_source_mapping() -> None:
    state, observation = _fixture()
    unknown_player = state.players[0].model_copy(
        update={
            "player_id": "unknown",
            "full_name": "No Completed Source Match",
            "provider_refs": (),
        }
    )
    now = state.as_of
    unknown_state = state.model_copy(
        update={
            "players": (unknown_player,),
            "player_states": (
                PlayerState(
                    player_id="unknown",
                    as_of=now,
                    provenance=state.player_states[0].provenance,
                ),
            ),
        }
    )
    unknown_forecast = observation.model_copy(update={"player_id": "unknown"})
    evidence = SimpleNamespace(
        raw_forecasts=tuple(
            raw.model_copy(update={"player_id": "unknown"})
            for raw in _raw_forecasts(observation)
        ),
        league_scored_forecasts=(unknown_forecast,),
    )
    context = UserRuntimeContext(
        user_id="user",
        league_state=unknown_state,
        forecast_evidence=cast(Any, evidence),
    )
    contract = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(unknown_forecast)
    )(context)
    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert contract.coverage.player_count == 0
    assert "p0_future_forecast_coordinate" in contract.coverage.missing_required_fact_families


# This focused file intentionally triggers the lightweight activation/API diagnostic workflow.


def test_loader_fails_closed_without_injected_future_forecast_provider() -> None:
    state, observation = _fixture()
    contract = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )(_context(state, observation))
    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert "future_forecast_coordinate" in contract.coverage.missing_required_fact_families
    assert "not configured" in (contract.status_reason or "")


def test_contract_exposes_preseason_year_one_provenance() -> None:
    state, observation = _fixture()
    contract = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )(_context(state, observation))

    assert contract.completed_source_provenance is not None
    coverage = contract.completed_source_provenance.fact_family_coverage
    assert coverage["year1_forecast_evidence_basis"] == "preseason_baseline"
    assert coverage["year1_forecast_runtime_model_version"] == "authority-fixture-v1"
    assert coverage["year1_forecast_evaluation_as_of"] == observation.as_of.isoformat()
    year_one = contract.estimates[0].contributions[0]
    assert year_one.provenance.authority == "preserved_preseason_year1_forecast"
    assert year_one.provenance.source == "fsffl:preseason_baseline_league_scored"


def test_frozen_i1_standard_scoring_contract_is_explicit_non_ppr() -> None:
    assert tuple((rule.stat, rule.points) for rule in FROZEN_I1_STANDARD_SCORING) == (
        ("pass_yd", 0.04),
        ("pass_td", 4.0),
        ("pass_int", -2.0),
        ("rush_yd", 0.1),
        ("rush_td", 6.0),
        ("rec_yd", 0.1),
        ("rec_td", 6.0),
        ("fum_lost", -2.0),
    )
    assert all(rule.stat != "rec" for rule in FROZEN_I1_STANDARD_SCORING)


def test_same_raw_forecast_builds_standard_and_half_ppr_coordinates() -> None:
    now = datetime(2026, 9, 10, 21, 36, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    raw = tuple(
        ForecastObservation(
            player_id="wr1",
            position=Position.WR,
            horizon=ForecastHorizon.SEASON,
            metric=metric,
            period_start=now,
            period_end=now + timedelta(days=150),
            distribution=ForecastDistribution(mean=mean, stddev=1.0),
            source="same-raw",
            model_version="same-raw-v1",
            as_of=now,
            provenance=provenance,
        )
        for metric, mean in (
            (ForecastMetric.RECEPTIONS, 80.0),
            (ForecastMetric.REC_YARDS, 1000.0),
            (ForecastMetric.REC_TD, 10.0),
            (ForecastMetric.FUMBLES_LOST, 2.0),
        )
    )
    league_rules = LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(),
        scoring=(
            ScoringRule(stat="rec", points=0.5),
            ScoringRule(stat="rec_yd", points=0.1),
            ScoringRule(stat="rec_td", points=6.0),
            ScoringRule(stat="fum_lost", points=-1.0),
        ),
    )
    league = derive_league_fantasy_point_forecasts(raw, rules=league_rules)
    assert len(league) == 1
    assert league[0].distribution.mean == 198.0

    multipliers = build_future_i1_player_scoring_multipliers(
        raw_forecasts=raw,
        league_year_one=league,
        rules=league_rules,
    )
    # Standard/non-PPR = 100 receiving yards points + 60 TD points - 4 fumble points.
    assert multipliers == {"wr1": pytest.approx(198.0 / 156.0)}


class _CoordinatePredictor:
    def __init__(self) -> None:
        self.seen = None

    def predict(self, item, *, fallback_probabilities=None):
        self.seen = item
        probabilities = {
            "out": 0.10,
            "depth": 0.10,
            "usable": 0.20,
            "starter": 0.30,
            "premium": 0.20,
            "elite": 0.10,
        }
        means = {state: float(index * 25) for index, state in enumerate(STATE_NAMES)}
        anticipated = sum(probabilities[state] * means[state] for state in STATE_NAMES)
        return I1ForecastResult(
            probabilities=probabilities,
            persistence_probability=0.90,
            anticipated_points=anticipated,
            state_means=means,
            evidence_path="reduced",
            model_version="frozen-standard-fixture",
        )


def test_player_specific_future_scoring_scales_outputs_once_and_preserves_standard_inputs() -> None:
    predictor = _CoordinatePredictor()
    item = I1ForecastInput(
        position=Position.WR,
        age_band="young",
        current_state="starter",
        horizon=2,
        current_points=150.0,
        prior_points=125.0,
        experience_years=2,
        evidence=None,
    )

    base = predictor.predict(item)
    result = translate_future_i1_result_for_player(
        "wr1",
        base,
        multipliers={"wr1": 1.25},
    )

    assert predictor.seen is item
    assert predictor.seen.current_points == 150.0
    assert predictor.seen.prior_points == 125.0
    assert result.probabilities == {
        "out": 0.10,
        "depth": 0.10,
        "usable": 0.20,
        "starter": 0.30,
        "premium": 0.20,
        "elite": 0.10,
    }
    for index, state in enumerate(STATE_NAMES):
        assert result.state_means[state] == pytest.approx(index * 25.0 * 1.25)
    expected = sum(result.probabilities[state] * result.state_means[state] for state in STATE_NAMES)
    assert result.anticipated_points == pytest.approx(expected)
    assert result.model_version.count(FUTURE_I1_PLAYER_SCORING_VERSION) == 1
    assert FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION not in result.model_version


def test_current_i1_facts_are_locked_to_standard_research_coordinate() -> None:
    facts = json.loads(activation_artifact_text("current_i1_facts_2026.json"))
    report = json.loads(activation_artifact_text("private_beta_activation_build_report.json"))
    metadata = facts["metadata"]

    assert "standard/non-PPR semantics" in metadata["scoring_coordinate"]
    coordinate = metadata["research_coordinate_validation"]
    assert coordinate["status"] == "PASS"
    assert coordinate["max_abs_fantasy_points_diff"] <= 1e-12
    assert report["current_fact_metadata"]["research_coordinate_validation"] == coordinate


def test_contract_future_i1_provenance_contains_exactly_one_player_scoring_translation() -> None:
    state, observation = _fixture()
    contract = _legacy_p0_loader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )(_context(state, observation))
    future = contract.estimates[0].contributions[1:]
    assert len(future) == 2
    for item in future:
        assert item.provenance.model_version.count(
            FUTURE_I1_PLAYER_SCORING_VERSION
        ) == 1
        assert FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION not in item.provenance.model_version

    assert contract.completed_source_provenance is not None
    coverage = contract.completed_source_provenance.fact_family_coverage
    assert coverage["future_forecast_contract_version"] == FUTURE_FORECAST_CONTRACT_VERSION
    assert coverage["future_forecast_scoring_coordinate"] == "connected_league_fantasy_points"
    assert coverage["future_i1_scoring_version"] == FUTURE_I1_PLAYER_SCORING_VERSION
    assert coverage["future_i1_scoring_method"] == "player_specific_year1_league_standard_ratio"
    assert coverage["p0_final_route_authority_sha256"] == P0_FINAL_ROUTE_AUTHORITY_SHA256
    assert coverage["p0_final_route_authority_version"] == P0_FINAL_ROUTE_AUTHORITY_VERSION
    assert coverage["future_i1_scoring_player_count"] == 1
    assert coverage["year1_forecast_source_ids"] == "fftoday,razzball"
    assert coverage["year1_forecast_source_count"] == 2



def test_loader_fails_closed_when_preseason_two_source_lineage_is_missing() -> None:
    state, observation = _fixture()
    evidence = _authority_evidence(observation)
    evidence.successful_source_ids = ("fftoday",)
    evidence.runtime_result.coverage = SimpleNamespace(
        independent_source_ids=("fftoday",),
        minimum_independent_sources=2,
    )
    contract = _legacy_p0_loader(
        year_one_loader=lambda _state: evidence
    )(_context(state, observation))

    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert "preseason_year1_source_lineage" in contract.coverage.missing_required_fact_families


def _runtime_scoring_case(
    position: Position,
    *,
    scoring: tuple[ScoringRule, ...],
):
    source = next(item for item in frozen_p0_source_rows() if item.position == position.value)
    now = datetime(2026, 9, 10, 21, 36, tzinfo=UTC)
    provenance = Provenance(
        source="two-source-fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="two-source-fixture-v1",
    )
    player = Player(
        player_id=f"runtime-{position.value.lower()}",
        full_name=source.player_name,
        position=position,
        provider_refs=(
            ProviderRef(provider="sleeper", external_id=source.sleeper_external_id),
        ),
    )
    slot = {
        Position.QB: RosterSlot.QB,
        Position.RB: RosterSlot.RB,
        Position.WR: RosterSlot.WR,
        Position.TE: RosterSlot.TE,
    }[position]
    rules = LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(LineupRequirement(slot=slot, count=1),),
        scoring=scoring,
    )
    state = LeagueState(
        league=League(league_id=f"league-{position.value}", name="Fixture", season=2026, rules=rules),
        as_of=now,
        teams=(
            Team(team_id="a", league_id=f"league-{position.value}", display_name="A"),
            Team(team_id="b", league_id=f"league-{position.value}", display_name="B"),
        ),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(player,),
        player_states=(PlayerState(player_id=player.player_id, as_of=now, provenance=provenance),),
    )

    if position == Position.QB:
        pass_td = min(10.0, source.standard_y1_points / 8.0)
        remaining = max(0.0, source.standard_y1_points - 4.0 * pass_td)
        metric_values = (
            (ForecastMetric.PASS_YARDS, remaining / 0.04),
            (ForecastMetric.PASS_TD, pass_td),
            (ForecastMetric.INTERCEPTIONS, 0.0),
            (ForecastMetric.FUMBLES_LOST, 0.0),
        )
    else:
        metric_values = (
            (ForecastMetric.RECEPTIONS, 80.0),
            (ForecastMetric.REC_YARDS, source.standard_y1_points / 0.1),
            (ForecastMetric.REC_TD, 0.0),
            (ForecastMetric.FUMBLES_LOST, 0.0),
        )

    raw = tuple(
        ForecastObservation(
            player_id=player.player_id,
            position=position,
            horizon=ForecastHorizon.SEASON,
            metric=metric,
            period_start=now,
            period_end=now + timedelta(days=150),
            distribution=ForecastDistribution(mean=mean, stddev=1.0),
            source="fsffl:live_equal_weight",
            model_version="next2-live-equal-weight-v1",
            as_of=now,
            provenance=Provenance(
                source="fsffl:live_equal_weight[fftoday,razzball]",
                retrieved_at=now,
                effective_at=now,
                source_version="next2-live-equal-weight-v1",
            ),
        )
        for metric, mean in metric_values
    )
    scored = derive_league_fantasy_point_forecasts(
        raw,
        rules=rules,
        source="fsffl:preseason_baseline_league_scored",
        model_version="authority-fixture-v1",
    )
    assert len(scored) == 1
    evidence = cast(
        Any,
        SimpleNamespace(
            raw_forecasts=raw,
            league_scored_forecasts=scored,
            successful_source_ids=("fftoday", "razzball"),
            evidence_basis="preseason_baseline",
            runtime_result=SimpleNamespace(
                evaluation_as_of=now,
                model_version="authority-fixture-v1",
                coverage=SimpleNamespace(
                    independent_source_ids=("fftoday", "razzball"),
                    minimum_independent_sources=2,
                ),
            ),
        ),
    )
    context = UserRuntimeContext(user_id="user", league_state=state)
    contract = _legacy_p0_loader(
        year_one_loader=lambda _state: evidence
    )(context)
    return contract, scored[0]


@pytest.mark.parametrize(
    ("position", "variant_scoring"),
    (
        (
            Position.WR,
            FROZEN_I1_STANDARD_SCORING + (ScoringRule(stat="rec", points=0.5),),
        ),
        (
            Position.WR,
            FROZEN_I1_STANDARD_SCORING + (ScoringRule(stat="rec", points=1.0),),
        ),
        (
            Position.QB,
            tuple(
                ScoringRule(stat=rule.stat, points=(6.0 if rule.stat == "pass_td" else rule.points))
                for rule in FROZEN_I1_STANDARD_SCORING
            ),
        ),
    ),
)
def test_authoritative_runtime_propagates_supported_scoring_family_to_intrinsic_shapley(
    position: Position,
    variant_scoring: tuple[ScoringRule, ...],
) -> None:
    standard_contract, standard_y1 = _runtime_scoring_case(
        position,
        scoring=FROZEN_I1_STANDARD_SCORING,
    )
    variant_contract, variant_y1 = _runtime_scoring_case(
        position,
        scoring=variant_scoring,
    )
    assert standard_contract.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert variant_contract.status != ShapleyIntrinsicAvailability.UNAVAILABLE

    ratio = variant_y1.distribution.mean / standard_y1.distribution.mean
    standard_estimate = standard_contract.estimates[0]
    variant_estimate = variant_contract.estimates[0]
    assert standard_estimate.diagnostic_h1.included_in_intrinsic is False
    assert variant_estimate.diagnostic_h1.included_in_intrinsic is False
    assert standard_estimate.diagnostic_h1.anticipated_points == 0.0
    assert variant_estimate.diagnostic_h1.anticipated_points == 0.0
    for year_index in (2, 3):
        standard_contribution = standard_estimate.contributions[year_index - 1]
        variant_contribution = variant_estimate.contributions[year_index - 1]
        assert variant_contribution.raw_shapley_contribution == pytest.approx(
            standard_contribution.raw_shapley_contribution * ratio
        )
        assert variant_contribution.provenance.model_version.count(
            FUTURE_I1_PLAYER_SCORING_VERSION
        ) == 1
        assert FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION not in (
            variant_contribution.provenance.model_version
        )



def test_te_premium_outside_governed_scoring_coverage_fails_closed() -> None:
    raw = _raw_forecasts(
        _fixture()[1].model_copy(update={"position": Position.TE})
    )
    te_premium_rules = LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.TE, count=1),),
        scoring=FROZEN_I1_STANDARD_SCORING
        + (ScoringRule(stat="bonus_rec_te", points=0.5),),
    )
    with pytest.raises(ValueError, match="unsupported rules"):
        derive_league_fantasy_point_forecasts(raw, rules=te_premium_rules)


class _MemoryShapleyArtifactStore:
    def __init__(self) -> None:
        self.records = {}

    def get_reusable_artifact(self, key):
        return self.records.get(key)

    def put_artifact(self, record) -> None:
        self.records[record.key] = record


def _versioned_future_builder(version: str, calls: list[str]):
    def builder(**kwargs):
        calls.append(version)
        materialized = build_p0_future_forecast_contract(**kwargs)
        contract = materialized.contract.model_copy(
            update={
                "forecast_model_version": version,
                "forecasts": tuple(
                    row.model_copy(update={"model_version": version})
                    for row in materialized.contract.forecasts
                ),
            }
        )
        return contract

    return builder


def _contract_only_fixture_provider(**kwargs) -> FutureForecastContract:
    league_year_one = tuple(kwargs["league_year_one"])
    assert len(league_year_one) == 1
    year_one = league_year_one[0]
    probabilities = {
        "out": 0.10,
        "depth": 0.10,
        "usable": 0.15,
        "starter": 0.30,
        "premium": 0.20,
        "elite": 0.15,
    }
    rows = []
    for year_index, scale in ((2, 1.0), (3, 0.9)):
        means = {
            "out": 0.0,
            "depth": 40.0 * scale,
            "usable": 90.0 * scale,
            "starter": 160.0 * scale,
            "premium": 230.0 * scale,
            "elite": 300.0 * scale,
        }
        expectation = sum(
            probabilities[state] * means[state]
            for state in STATE_NAMES
        )
        rows.append(
            FuturePlayerHorizonForecast(
                player_id=year_one.player_id,
                position=year_one.position,
                evaluation_season=2026,
                year_index=year_index,
                target_season=2026 + year_index - 1,
                central_expectation=expectation,
                scoring_coordinate=CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE,
                model_version="future-model-zeta-v1",
                source="fixture:future-model-zeta",
                uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
                scenarios=tuple(
                    FutureForecastScenario(
                        scenario_id=state,
                        probability=probabilities[state],
                        fantasy_points=means[state],
                    )
                    for state in STATE_NAMES
                ),
                evidence_path="fixture_contract_only_provider",
            )
        )
    return FutureForecastContract(
        evaluation_season=2026,
        scoring_coordinate=CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE,
        forecast_model_version="future-model-zeta-v1",
        forecast_source="fixture:future-model-zeta",
        forecasts=tuple(rows),
        provenance={"provider_neutral_contract": True},
    )


def test_intrinsic_accepts_replacement_future_model_using_contract_only_boundary() -> None:
    state, observation = _fixture()
    loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        future_forecast_builder=_contract_only_fixture_provider,
        future_forecast_model_version="future-model-zeta-v1",
        future_missing_fact_family="future_model_zeta_coordinate",
    )
    contract = loader(_context(state, observation))

    assert contract.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert contract.forecast_model_version == "future-model-zeta-v1"
    assert contract.coverage.player_count == 1
    future = contract.estimates[0].contributions[1:]
    assert len(future) == 2
    assert all(
        item.provenance.authority == "governed_future_forecast_contract"
        for item in future
    )
    assert all(
        item.provenance.source == "forecast_owned_future_contract"
        for item in future
    )


def test_persisted_intrinsic_contract_is_forecast_version_scoped_and_reused() -> None:
    state, observation = _fixture()
    context = _context(state, observation)
    evidence_loader = lambda _state: _authority_evidence(observation)
    store = _MemoryShapleyArtifactStore()
    calls: list[str] = []

    first_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=evidence_loader,
        persistence_store=cast(Any, store),
        future_forecast_builder=_versioned_future_builder("forecast-v1", calls),
        future_forecast_model_version="forecast-v1",
    )
    first = first_loader(context)
    assert first.forecast_model_version == "forecast-v1"
    assert len(store.records) == 1
    first_key = next(iter(store.records))
    assert first_key.model_version.endswith("|forecast=forecast-v1")

    # A fresh loader instance still resolves the Forecast input coordinate, then
    # reuses the durable canonical Shapley contract rather than creating another
    # artifact for the same league/state/Forecast coordinate.
    same_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=evidence_loader,
        persistence_store=cast(Any, store),
        future_forecast_builder=_versioned_future_builder("forecast-v1", calls),
        future_forecast_model_version="forecast-v1",
    )
    same = same_loader(context)
    assert same == first
    assert len(store.records) == 1

    promoted_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=evidence_loader,
        persistence_store=cast(Any, store),
        future_forecast_builder=_versioned_future_builder("forecast-v2", calls),
        future_forecast_model_version="forecast-v2",
    )
    promoted = promoted_loader(context)
    assert promoted.forecast_model_version == "forecast-v2"
    assert len(store.records) == 2
    assert {
        key.model_version
        for key in store.records
    } == {
        f"{first.contract_version}|forecast=forecast-v1",
        f"{promoted.contract_version}|forecast=forecast-v2",
    }



def test_promoted_vnext_shapley_consumes_vnext_y2_y3_and_preserves_y1_authority() -> None:
    state, observation = _fixture()
    loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        future_forecast_builder=provide_vnext_future_forecast_contract,
        future_forecast_model_version=VNEXT_FORECAST_VERSION,
        future_missing_fact_family="vnext_future_forecast_coordinate",
    )

    contract = loader(_context(state, observation))

    assert contract.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert contract.forecast_model_version == VNEXT_FORECAST_VERSION
    estimate = contract.estimates[0]
    assert estimate.diagnostic_h1.included_in_intrinsic is False
    assert estimate.contributions[0].provenance.authority == (
        "preserved_preseason_year1_forecast"
    )
    assert estimate.contributions[0].provenance.source == (
        "fsffl:preseason_baseline_league_scored"
    )
    assert [
        item.provenance.direct_i1_horizon
        for item in estimate.contributions
    ] == [None, 2, 3]
    assert all(
        VNEXT_FORECAST_VERSION in item.provenance.model_version
        for item in estimate.contributions[1:]
    )



def test_frozen_h3_subject_scope_ignores_unrelated_current_state_players_without_changing_values() -> None:
    state, observation = _fixture()
    baseline_materialization = build_vnext_future_forecast_contract(
        league_state=state,
        raw_forecasts=_raw_forecasts(observation),
        league_year_one=(observation,),
    )
    baseline_contract = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        future_forecast_builder=provide_vnext_future_forecast_contract,
        future_forecast_model_version=VNEXT_FORECAST_VERSION,
        future_missing_fact_family="vnext_future_forecast_coordinate",
    )(_context(state, observation))
    assert baseline_contract.status != ShapleyIntrinsicAvailability.UNAVAILABLE

    unknown = Player(
        player_id="outside-h3",
        full_name="Outside H3 Authority",
        position=Position.QB,
        provider_refs=(ProviderRef(provider="sleeper", external_id="outside-h3"),),
    )
    expanded_state = state.model_copy(
        update={
            "players": state.players + (unknown,),
            "player_states": state.player_states
            + (
                PlayerState(
                    player_id=unknown.player_id,
                    as_of=state.as_of,
                    provenance=state.player_states[0].provenance,
                ),
            ),
        }
    )
    unknown_year_one = observation.model_copy(
        update={
            "player_id": unknown.player_id,
            "source": "fsffl:preseason_baseline_league_scored",
            "model_version": "authority-fixture-v1",
        }
    )
    expanded_raw = _raw_forecasts(observation) + tuple(
        item.model_copy(update={"player_id": unknown.player_id})
        for item in _raw_forecasts(observation)
    )
    expanded_materialization = build_vnext_future_forecast_contract(
        league_state=expanded_state,
        raw_forecasts=expanded_raw,
        league_year_one=(observation, unknown_year_one),
    )
    assert expanded_materialization.contract.player_ids == ("canonical-player",)
    assert (
        expanded_materialization.contract.forecasts
        == baseline_materialization.contract.forecasts
    )
    assert (
        expanded_materialization.contract.provenance[
            "excluded_non_h3_subject_count"
        ]
        == 1
    )

    evidence = _authority_evidence(observation)
    evidence.raw_forecasts = expanded_raw
    evidence.league_scored_forecasts = (
        observation.model_copy(
            update={
                "source": "fsffl:preseason_baseline_league_scored",
                "model_version": "authority-fixture-v1",
            }
        ),
        unknown_year_one,
    )
    expanded_context = UserRuntimeContext(
        user_id="user",
        league_state=expanded_state,
        forecast_evidence=cast(
            Any,
            SimpleNamespace(
                raw_forecasts=expanded_raw,
                league_scored_forecasts=(observation, unknown_year_one),
            ),
        ),
    )
    expanded_contract = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: evidence,
        future_forecast_builder=provide_vnext_future_forecast_contract,
        future_forecast_model_version=VNEXT_FORECAST_VERSION,
        future_missing_fact_family="vnext_future_forecast_coordinate",
    )(expanded_context)

    assert expanded_contract.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert expanded_contract.coverage.player_count == 1
    assert [item.player_id for item in expanded_contract.estimates] == [
        "canonical-player"
    ]
    assert (
        expanded_contract.estimates[0].raw_intrinsic_value
        == pytest.approx(baseline_contract.estimates[0].raw_intrinsic_value)
    )
    assert [
        item.discounted_contribution
        for item in expanded_contract.estimates[0].contributions
    ] == pytest.approx(
        [
            item.discounted_contribution
            for item in baseline_contract.estimates[0].contributions
        ]
    )



def test_promoted_vnext_intrinsic_survives_authentic_preseason_raw_without_fumbles_lost() -> None:
    state, observation = _fixture()
    evidence = _authority_evidence(observation)
    evidence.raw_forecasts = tuple(
        item
        for item in evidence.raw_forecasts
        if item.metric != ForecastMetric.FUMBLES_LOST
    )
    assert evidence.raw_forecasts
    assert all(
        item.metric != ForecastMetric.FUMBLES_LOST
        for item in evidence.raw_forecasts
    )

    contract = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: evidence,
        future_forecast_builder=provide_vnext_future_forecast_contract,
        future_forecast_model_version=VNEXT_FORECAST_VERSION,
        future_missing_fact_family="vnext_future_forecast_coordinate",
    )(_context(state, observation))

    assert contract.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert contract.forecast_model_version == VNEXT_FORECAST_VERSION
    assert contract.coverage.player_count == 1
    assert contract.coverage.year_1_forecast_players == 1
    assert contract.estimates[0].contributions[0].provenance.authority == (
        "preserved_preseason_year1_forecast"
    )



def test_vnext_semantic_future_contract_is_materialized_once_across_unrelated_state_advance() -> None:
    state, observation = _fixture()
    calls: list[str] = []

    def counted_builder(**kwargs):
        calls.append("future")
        return provide_vnext_future_forecast_contract(**kwargs)

    loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        future_forecast_builder=counted_builder,
        future_forecast_model_version=VNEXT_FORECAST_VERSION,
        future_missing_fact_family="vnext_future_forecast_coordinate",
        future_forecast_input_fingerprint_resolver=(
            vnext_future_forecast_input_fingerprint
        ),
    )
    context = _context(state, observation)

    baseline_fingerprint = loader.intrinsic_input_fingerprint(context)
    built = loader(context)
    assert built.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert calls == ["future"]

    advanced = state.model_copy(
        update={
            "as_of": state.as_of + timedelta(hours=3),
            "teams": (
                state.teams[0].model_copy(update={"display_name": "A Updated"}),
                state.teams[1],
            ),
            "team_states": tuple(
                item.model_copy(update={"faab_balance": 17})
                for item in state.team_states
            ),
        }
    )
    advanced_context = _context(advanced, observation)
    assert advanced.state_id != state.state_id
    assert loader.intrinsic_input_fingerprint(advanced_context) == baseline_fingerprint
    reused = loader(advanced_context)
    assert reused is built
    assert calls == ["future"]

    changed_rules = state.league.rules.model_copy(
        update={
            "lineup": (
                LineupRequirement(slot=RosterSlot.QB, count=2),
            )
        }
    )
    changed_state = state.model_copy(
        update={
            "league": state.league.model_copy(update={"rules": changed_rules}),
        }
    )
    loader.intrinsic_input_fingerprint(_context(changed_state, observation))
    assert calls == ["future", "future"]


def test_vnext_semantic_future_contract_cache_invalidates_for_coverage_provenance() -> None:
    state, observation = _fixture()
    calls: list[str] = []

    def counted_builder(**kwargs):
        calls.append("future")
        return provide_vnext_future_forecast_contract(**kwargs)

    evidence = _authority_evidence(observation)
    loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: evidence,
        future_forecast_builder=counted_builder,
        future_forecast_model_version=VNEXT_FORECAST_VERSION,
        future_missing_fact_family="vnext_future_forecast_coordinate",
        future_forecast_input_fingerprint_resolver=(
            vnext_future_forecast_input_fingerprint
        ),
    )
    loader.intrinsic_input_fingerprint(_context(state, observation))
    assert calls == ["future"]

    unknown = Player(
        player_id="unsupported-player",
        full_name="Unsupported Player",
        position=Position.QB,
        provider_refs=(ProviderRef(provider="sleeper", external_id="unsupported"),),
    )
    unknown_year_one = observation.model_copy(
        update={"player_id": unknown.player_id}
    )
    expanded_state = state.model_copy(
        update={
            "players": (*state.players, unknown),
            "player_states": (
                *state.player_states,
                PlayerState(
                    player_id=unknown.player_id,
                    as_of=state.as_of,
                    provenance=state.player_states[0].provenance,
                ),
            ),
        }
    )
    expanded_evidence = _authority_evidence(observation)
    expanded_evidence.league_scored_forecasts = (
        observation,
        unknown_year_one,
    )
    expanded_loader_context = UserRuntimeContext(
        user_id="user",
        league_state=expanded_state,
        forecast_evidence=cast(
            Any,
            SimpleNamespace(
                raw_forecasts=expanded_evidence.raw_forecasts,
                league_scored_forecasts=expanded_evidence.league_scored_forecasts,
            ),
        ),
    )
    loader._year_one_loader = lambda _state: expanded_evidence
    loader.intrinsic_input_fingerprint(expanded_loader_context)
    assert calls == ["future", "future"]


def test_intrinsic_input_fingerprint_ignores_unrelated_league_state_changes() -> None:
    state, observation = _fixture()
    context = _context(state, observation)
    evidence = _authority_evidence(observation)
    future = _contract_only_fixture_provider(
        league_state=state,
        raw_forecasts=evidence.raw_forecasts,
        league_year_one=evidence.league_scored_forecasts,
    )
    source_ids = tuple(evidence.successful_source_ids)
    baseline = intrinsic_input_fingerprint(
        context,
        evidence.league_scored_forecasts,
        future,
        source_ids,
        year_one_evidence=evidence,
    )

    changed_team = state.teams[0].model_copy(update={"display_name": "Renamed Team"})
    advanced = state.model_copy(
        update={
            "as_of": state.as_of + timedelta(hours=2),
            "teams": (changed_team, state.teams[1]),
            "team_states": tuple(
                item.model_copy(update={"faab_balance": 17})
                for item in state.team_states
            ),
        }
    )
    advanced_context = _context(advanced, observation)
    advanced_future = _contract_only_fixture_provider(
        league_state=advanced,
        raw_forecasts=evidence.raw_forecasts,
        league_year_one=evidence.league_scored_forecasts,
    )
    assert advanced.state_id != state.state_id
    assert intrinsic_input_fingerprint(
        advanced_context,
        evidence.league_scored_forecasts,
        advanced_future,
        source_ids,
        year_one_evidence=evidence,
    ) == baseline


def test_intrinsic_input_fingerprint_ignores_volatile_pit_and_non_math_metadata() -> None:
    state, observation = _fixture()
    evidence = _authority_evidence(observation)
    future = _contract_only_fixture_provider(
        league_state=state,
        raw_forecasts=evidence.raw_forecasts,
        league_year_one=evidence.league_scored_forecasts,
    )
    baseline = intrinsic_input_fingerprint(
        _context(state, observation),
        evidence.league_scored_forecasts,
        future,
        tuple(evidence.successful_source_ids),
        year_one_evidence=evidence,
    )

    later = observation.as_of + timedelta(minutes=11)
    volatile_provenance = observation.provenance.model_copy(
        update={
            "retrieved_at": later,
            "effective_at": later,
            "source_version": "fixture-audit-refresh-only",
        }
    )
    volatile_year_one = evidence.league_scored_forecasts[0].model_copy(
        update={
            "period_start": evidence.league_scored_forecasts[0].period_start
            + timedelta(minutes=11),
            "period_end": evidence.league_scored_forecasts[0].period_end
            + timedelta(minutes=11),
            "as_of": later,
            "provenance": volatile_provenance,
            # The live calendar retains this for diagnostics, but frozen Shapley
            # math does not consume Year-1 spread.
            "distribution": ForecastDistribution(
                mean=evidence.league_scored_forecasts[0].distribution.mean,
                stddev=evidence.league_scored_forecasts[0].distribution.stddev + 9.0,
            ),
        }
    )
    volatile_evidence = cast(
        Any,
        SimpleNamespace(
            raw_forecasts=tuple(
                item.model_copy(
                    update={
                        "period_start": item.period_start + timedelta(minutes=11),
                        "period_end": item.period_end + timedelta(minutes=11),
                        "as_of": later,
                        "provenance": volatile_provenance,
                    }
                )
                for item in evidence.raw_forecasts
            ),
            league_scored_forecasts=(volatile_year_one,),
            successful_source_ids=tuple(reversed(evidence.successful_source_ids)),
            evidence_basis=evidence.evidence_basis,
            runtime_result=SimpleNamespace(
                evaluation_as_of=later,
                model_version=evidence.runtime_result.model_version,
                coverage=evidence.runtime_result.coverage,
            ),
        ),
    )
    volatile_future = future.model_copy(
        update={
            "provenance": {
                **future.provenance,
                "evaluation_as_of": later.isoformat(),
                "retrieved_at": later.isoformat(),
                "runtime_trace_id": "fresh-load-2",
            },
            "forecasts": tuple(
                row.model_copy(
                    update={"evidence_path": f"fresh-load-{row.year_index}"}
                )
                for row in future.forecasts
            ),
        }
    )

    refreshed = intrinsic_input_fingerprint(
        _context(
            state.model_copy(update={"as_of": later}),
            volatile_year_one,
        ),
        volatile_evidence.league_scored_forecasts,
        volatile_future,
        tuple(volatile_evidence.successful_source_ids),
        year_one_evidence=volatile_evidence,
    )
    assert refreshed == baseline


def test_persisted_intrinsic_reuses_across_fresh_pit_metadata_loads() -> None:
    state, observation = _fixture()
    store = _MemoryShapleyArtifactStore()
    build_calls: list[str] = []
    evidence_calls = 0

    def fresh_evidence(_state):
        nonlocal evidence_calls
        evidence_calls += 1
        base = _authority_evidence(observation)
        shifted = observation.as_of + timedelta(minutes=3 * evidence_calls)
        provenance = observation.provenance.model_copy(
            update={
                "retrieved_at": shifted,
                "effective_at": shifted,
                "source_version": f"audit-refresh-{evidence_calls}",
            }
        )
        y1 = base.league_scored_forecasts[0].model_copy(
            update={"as_of": shifted, "provenance": provenance}
        )
        return cast(
            Any,
            SimpleNamespace(
                raw_forecasts=tuple(
                    item.model_copy(update={"as_of": shifted, "provenance": provenance})
                    for item in base.raw_forecasts
                ),
                league_scored_forecasts=(y1,),
                successful_source_ids=base.successful_source_ids,
                evidence_basis=base.evidence_basis,
                runtime_result=SimpleNamespace(
                    evaluation_as_of=shifted,
                    model_version=base.runtime_result.model_version,
                    coverage=base.runtime_result.coverage,
                ),
            ),
        )

    def fresh_future_builder(**kwargs):
        build_calls.append("future")
        contract = _contract_only_fixture_provider(**kwargs)
        return contract.model_copy(
            update={
                "provenance": {
                    **contract.provenance,
                    "build_trace": f"trace-{len(build_calls)}",
                }
            }
        )

    first_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=fresh_evidence,
        persistence_store=cast(Any, store),
        future_forecast_builder=fresh_future_builder,
        future_forecast_model_version="future-model-zeta-v1",
    )
    first_context = _context(state, observation)
    first_fingerprint = first_loader.intrinsic_input_fingerprint(first_context)
    first = first_loader(first_context)
    assert len(store.records) == 1

    fresh_state = state.model_copy(
        update={"as_of": state.as_of + timedelta(minutes=11)}
    )
    second_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=fresh_evidence,
        persistence_store=cast(Any, store),
        future_forecast_builder=fresh_future_builder,
        future_forecast_model_version="future-model-zeta-v1",
    )
    second_context = _context(fresh_state, observation)
    second_fingerprint = second_loader.intrinsic_input_fingerprint(second_context)
    second = second_loader(second_context)

    assert first_fingerprint == second_fingerprint
    assert second == first
    assert len(store.records) == 1
    assert FROZEN_SHAPLEY_PERMUTATIONS == 2048


def test_intrinsic_input_fingerprint_invalidates_required_dependencies() -> None:
    state, observation = _fixture()
    evidence = _authority_evidence(observation)
    future = _contract_only_fixture_provider(
        league_state=state,
        raw_forecasts=evidence.raw_forecasts,
        league_year_one=evidence.league_scored_forecasts,
    )
    source_ids = tuple(evidence.successful_source_ids)

    def fingerprint(
        target_state: LeagueState = state,
        target_evidence=evidence,
        target_future: FutureForecastContract = future,
    ) -> str:
        return intrinsic_input_fingerprint(
            _context(target_state, observation),
            tuple(target_evidence.league_scored_forecasts),
            target_future,
            tuple(target_evidence.successful_source_ids),
            year_one_evidence=target_evidence,
        )

    baseline = fingerprint()

    scoring_changed = state.model_copy(
        update={
            "league": state.league.model_copy(
                update={
                    "rules": state.league.rules.model_copy(
                        update={
                            "scoring": state.league.rules.scoring
                            + (ScoringRule(stat="rec", points=0.5),)
                        }
                    )
                }
            )
        }
    )
    assert fingerprint(scoring_changed) != baseline

    lineup_changed = state.model_copy(
        update={
            "league": state.league.model_copy(
                update={
                    "rules": state.league.rules.model_copy(
                        update={
                            "lineup": (
                                LineupRequirement(slot=RosterSlot.QB, count=2),
                            )
                        }
                    )
                }
            )
        }
    )
    assert fingerprint(lineup_changed) != baseline

    changed_y1 = _authority_evidence(
        observation.model_copy(
            update={
                "distribution": ForecastDistribution(
                    mean=observation.distribution.mean + 7.0,
                    stddev=observation.distribution.stddev,
                )
            }
        )
    )
    assert fingerprint(target_evidence=changed_y1) != baseline

    changed_future = future.model_copy(
        update={"forecast_model_version": "future-model-zeta-v2"}
    )
    assert fingerprint(target_future=changed_future) != baseline

    changed_y1_model = cast(
        Any,
        SimpleNamespace(
            raw_forecasts=evidence.raw_forecasts,
            league_scored_forecasts=(
                evidence.league_scored_forecasts[0].model_copy(
                    update={"model_version": "authority-fixture-v2"}
                ),
            ),
            successful_source_ids=evidence.successful_source_ids,
            evidence_basis=evidence.evidence_basis,
            runtime_result=SimpleNamespace(
                evaluation_as_of=evidence.runtime_result.evaluation_as_of,
                model_version="authority-fixture-v2",
                coverage=evidence.runtime_result.coverage,
            ),
        ),
    )
    assert fingerprint(target_evidence=changed_y1_model) != baseline

    first_future_row = future.forecasts[0]
    changed_scenarios = tuple(
        scenario.model_copy(
            update={
                "fantasy_points": (
                    scenario.fantasy_points + 10.0
                    if scenario.scenario_id == "elite"
                    else scenario.fantasy_points
                )
            }
        )
        for scenario in first_future_row.scenarios
    )
    changed_expectation = sum(
        scenario.probability * scenario.fantasy_points
        for scenario in changed_scenarios
    )
    numerically_changed_future = future.model_copy(
        update={
            "forecasts": (
                first_future_row.model_copy(
                    update={
                        "central_expectation": changed_expectation,
                        "scenarios": changed_scenarios,
                    }
                ),
            )
            + future.forecasts[1:]
        }
    )
    assert fingerprint(target_future=numerically_changed_future) != baseline

    subject_observation = observation.model_copy(update={"player_id": "different-subject"})
    subject_evidence = _authority_evidence(subject_observation)
    subject_future = future.model_copy(
        update={
            "forecasts": tuple(
                row.model_copy(update={"player_id": "different-subject"})
                for row in future.forecasts
            )
        }
    )
    assert (
        intrinsic_input_fingerprint(
            _context(state, subject_observation),
            tuple(subject_evidence.league_scored_forecasts),
            subject_future,
            tuple(subject_evidence.successful_source_ids),
            year_one_evidence=subject_evidence,
        )
        != baseline
    )

    next_season = state.model_copy(
        update={
            "league": state.league.model_copy(update={"season": 2027})
        }
    )
    assert fingerprint(next_season) != baseline


def test_persisted_intrinsic_reuses_across_unrelated_state_advance() -> None:
    state, observation = _fixture()
    evidence_loader = lambda _state: _authority_evidence(observation)
    store = _MemoryShapleyArtifactStore()
    calls: list[str] = []
    loader = PrivateBetaShapleyContractLoader(
        year_one_loader=evidence_loader,
        persistence_store=cast(Any, store),
        future_forecast_builder=_versioned_future_builder("forecast-v1", calls),
        future_forecast_model_version="forecast-v1",
    )
    first = loader(_context(state, observation))
    assert len(store.records) == 1

    advanced = state.model_copy(
        update={
            "as_of": state.as_of + timedelta(hours=3),
            "teams": (
                state.teams[0].model_copy(update={"display_name": "A Updated"}),
                state.teams[1],
            ),
        }
    )
    fresh_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=evidence_loader,
        persistence_store=cast(Any, store),
        future_forecast_builder=_versioned_future_builder("forecast-v1", calls),
        future_forecast_model_version="forecast-v1",
    )
    reused = fresh_loader(_context(advanced, observation))

    assert advanced.state_id != state.state_id
    assert reused == first
    assert len(store.records) == 1
    only_key = next(iter(store.records))
    assert only_key.scope_id == state.league.league_id
    assert only_key.scope_kind == "league_intrinsic_inputs"



def test_restart_coordinator_restores_persisted_semantic_intrinsic_without_shapley_rebuild() -> None:
    state, observation = _fixture()
    store = _MemoryShapleyArtifactStore()
    future_calls: list[str] = []

    def future_builder(**kwargs):
        future_calls.append("future")
        return _contract_only_fixture_provider(**kwargs)

    first_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        persistence_store=cast(Any, store),
        future_forecast_builder=future_builder,
        future_forecast_model_version="restart-semantic-v1",
    )
    first_context = _context(state, observation)
    built = first_loader(first_context)
    assert built.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert len(store.records) == 1

    advanced = state.model_copy(
        update={
            "as_of": state.as_of + timedelta(hours=4),
            "teams": (
                state.teams[0].model_copy(update={"display_name": "A Restarted"}),
                state.teams[1],
            ),
        }
    )
    restart_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        persistence_store=cast(Any, store),
        future_forecast_builder=future_builder,
        future_forecast_model_version="restart-semantic-v1",
    )
    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        restart_loader,
        max_workers=1,
        intrinsic_input_fingerprint_resolver=restart_loader.intrinsic_input_fingerprint,
    )
    advanced_context = _context(advanced, observation)

    restored = coordinator.restore_compatible(advanced_context)

    assert restored is not None
    assert restored.status == IntrinsicBuildStatus.COMPLETED
    assert restored.contract == built
    assert restored.league_state_id == advanced.state_id
    assert coordinator.current(advanced_context) == restored
    active_player_ids = frozenset(row.player_id for row in built.estimates)
    assert coordinator.completed_player_ids_for_state(advanced_context) == active_player_ids
    assert coordinator.release_completed_contract(advanced_context, restored.contract)
    assert coordinator.completed_player_ids_for_state(advanced_context) == active_player_ids
    assert len(store.records) == 1
    # The future contract is resolved to prove semantic compatibility, but the
    # persisted Shapley artifact is reused instead of another 2,048-permutation build.
    assert FROZEN_SHAPLEY_PERMUTATIONS == 2048



def test_intrinsic_loader_drops_stale_durable_restore_after_cache_epoch_advance() -> None:
    state, observation = _fixture()
    seed_store = _MemoryShapleyArtifactStore()
    seed_loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        persistence_store=cast(Any, seed_store),
        future_forecast_builder=_contract_only_fixture_provider,
        future_forecast_model_version="future-model-zeta-v1",
    )
    context = _context(state, observation)
    built = seed_loader(context)
    assert built.status != ShapleyIntrinsicAvailability.UNAVAILABLE
    assert len(seed_store.records) == 1

    entered = Event()
    release = Event()

    class BlockingStore(_MemoryShapleyArtifactStore):
        def __init__(self, records):
            super().__init__()
            self.records = dict(records)

        def get_reusable_artifact(self, key):
            entered.set()
            assert release.wait(timeout=2.0)
            return self.records.get(key)

    blocking_store = BlockingStore(seed_store.records)
    loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation),
        persistence_store=cast(Any, blocking_store),
        future_forecast_builder=_contract_only_fixture_provider,
        future_forecast_model_version="future-model-zeta-v1",
    )
    result: dict[str, object] = {}

    def restore() -> None:
        result["contract"] = loader.restore_compatible(context)

    thread = Thread(target=restore)
    thread.start()
    assert entered.wait(timeout=1.0)

    # The resource boundary advances cache ownership while the durable read is
    # in-flight. The old restore may finish reading but must not repopulate cache.
    assert loader.clear_user_cache(context.user_id) == 0
    release.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result["contract"] is None
    assert loader.clear_user_cache(context.user_id) == 0

def test_hosted_dynamic_career_bridge_scores_first_party_fumbles_for_complete_single_source_y1() -> None:
    state, _ = _fixture()
    player_id = "canonical-player"
    player = state.players[0]
    now = state.as_of
    provenance = Provenance(
        source="razzball",
        retrieved_at=now,
        effective_at=now,
        source_version="captured-ros-v1",
    )
    period_start = datetime(2026, 10, 8, tzinfo=UTC)
    period_end = datetime(2027, 1, 15, tzinfo=UTC)
    metric_means = (
        (ForecastMetric.PASS_YARDS, 100.0),
        (ForecastMetric.PASS_TD, 1.0),
        (ForecastMetric.INTERCEPTIONS, 1.0),
        (ForecastMetric.RUSH_YARDS, 10.0),
        (ForecastMetric.RUSH_TD, 1.0),
    )
    source_rows = tuple(
        ForecastObservation(
            player_id=player_id,
            position=player.position,
            horizon=ForecastHorizon.REST_OF_SEASON,
            metric=metric,
            period_start=period_start,
            period_end=period_end,
            distribution=ForecastDistribution(mean=mean, stddev=0.0),
            source="razzball",
            model_version="captured-ros-v1",
            as_of=now,
            provenance=provenance,
        )
        for metric, mean in metric_means
    )
    fumbles = ForecastObservation(
        player_id=player_id,
        position=player.position,
        horizon=ForecastHorizon.REST_OF_SEASON,
        metric=ForecastMetric.FUMBLES_LOST,
        period_start=period_start,
        period_end=period_end,
        distribution=ForecastDistribution(mean=0.5, stddev=0.7),
        source="fsffl:first_party:fumbles_lost",
        model_version="accepted-fumbles-lost-rolling-v1",
        as_of=now,
        provenance=Provenance(
            source="fsffl:first_party:fumbles_lost",
            retrieved_at=now,
            effective_at=now,
            source_version="accepted-fumbles-lost-rolling-v1",
        ),
    )

    without_supplement = _score_complete_single_source_year_one(
        player_id=player_id,
        source_rows=source_rows,
        completed_actuals=(),
        league_state=state,
    )
    with_supplement = _score_complete_single_source_year_one(
        player_id=player_id,
        source_rows=source_rows,
        completed_actuals=(),
        league_state=state,
        supplemental_rows=(fumbles,),
    )

    assert without_supplement is None
    assert with_supplement is not None
    raw, standard, league = with_supplement
    assert standard is not None and league is not None
    assert standard.distribution.mean == pytest.approx(12.0)
    assert league.distribution.mean == pytest.approx(12.0)
    assert len([row for row in raw if row.metric == ForecastMetric.FUMBLES_LOST]) == 1
    assert next(row for row in raw if row.metric == ForecastMetric.FUMBLES_LOST).model_version == "p0-live-y1-raw-v1"


def test_hosted_dynamic_career_bridge_rejects_unrelated_supplement_coordinate() -> None:
    state, _ = _fixture()
    now = state.as_of
    period_start = datetime(2026, 10, 8, tzinfo=UTC)
    period_end = datetime(2027, 1, 15, tzinfo=UTC)
    provider = ForecastObservation(
        player_id="canonical-player",
        position=Position.QB,
        horizon=ForecastHorizon.REST_OF_SEASON,
        metric=ForecastMetric.PASS_YARDS,
        period_start=period_start,
        period_end=period_end,
        distribution=ForecastDistribution(mean=1.0, stddev=0.0),
        source="razzball",
        model_version="captured-ros-v1",
        as_of=now,
        provenance=Provenance(source="razzball", retrieved_at=now, effective_at=now),
    )
    other_player = ForecastObservation(
        player_id="different-player",
        position=Position.QB,
        horizon=ForecastHorizon.REST_OF_SEASON,
        metric=ForecastMetric.FUMBLES_LOST,
        period_start=period_start,
        period_end=period_end,
        distribution=ForecastDistribution(mean=0.2, stddev=0.4),
        source="fsffl:first_party:fumbles_lost",
        model_version="accepted-fumbles-lost-rolling-v1",
        as_of=now,
        provenance=Provenance(source="fsffl:first_party:fumbles_lost", retrieved_at=now, effective_at=now),
    )
    assert _score_complete_single_source_year_one(
        player_id="canonical-player",
        source_rows=(provider,),
        completed_actuals=(),
        league_state=state,
        supplemental_rows=(other_player,),
    ) is None


def test_hosted_dynamic_career_bridge_materializes_schedule_scaled_fumbles_ros(monkeypatch) -> None:
    import fsffl.forecast.in_season_orchestration as orchestration

    state, provider_observation = _fixture()
    now = state.as_of
    provider_observation = provider_observation.model_copy(
        update={
            "horizon": ForecastHorizon.REST_OF_SEASON,
            "metric": ForecastMetric.PASS_YARDS,
            "period_start": datetime(2026, 9, 29, tzinfo=UTC),
            "period_end": datetime(2027, 1, 26, tzinfo=UTC),
        }
    )
    season_fumbles = ForecastObservation(
        player_id=provider_observation.player_id,
        position=provider_observation.position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FUMBLES_LOST,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 3, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=0.4, stddev=0.6),
        source="fsffl:first_party:fumbles_lost",
        model_version="accepted-fumbles-lost-rolling-v1",
        as_of=now,
        provenance=Provenance(
            source="fsffl:first_party:fumbles_lost",
            retrieved_at=now,
            effective_at=now,
            source_version="accepted-fumbles-lost-rolling-v1",
        ),
    )
    monkeypatch.setattr(
        orchestration,
        "build_first_party_fumbles_lost_supplement",
        lambda *_args, **_kwargs: SimpleNamespace(
            observations=(season_fumbles,), authority_valid_from=now
        ),
    )
    runtime = SimpleNamespace(
        partial_fantasy_point_forecasts=(),
        source_observations=(provider_observation,),
    )

    ros_rows = build_current_ros_fumbles_lost_supplement_observations(
        state,
        current_runtime=runtime,
        stats_source=cast(Any, object()),
        completed_through_week=4,
        as_of=now,
        eligible_player_ids={provider_observation.player_id},
    )

    assert len(ros_rows) == 1
    assert ros_rows[0].horizon == ForecastHorizon.REST_OF_SEASON
    assert ros_rows[0].source == "fsffl:first_party:fumbles_lost"
    assert ros_rows[0].distribution.mean == pytest.approx(0.4 * 13 / 17)
    assert ros_rows[0].distribution.stddev == pytest.approx(0.6 * 13 / 17)
    assert "remaining_games=13" in ros_rows[0].provenance.source_version


def test_hosted_dynamic_career_bridge_selects_only_complete_provider_rows_missing_fumbles() -> None:
    state, forecast = _fixture()
    now = state.as_of
    period_start = datetime(2026, 9, 29, tzinfo=UTC)
    period_end = datetime(2027, 1, 26, tzinfo=UTC)
    metrics = (
        ForecastMetric.PASS_YARDS,
        ForecastMetric.PASS_TD,
        ForecastMetric.INTERCEPTIONS,
        ForecastMetric.RUSH_YARDS,
        ForecastMetric.RUSH_TD,
    )

    def rows(player_id: str, selected: tuple[ForecastMetric, ...]) -> tuple[ForecastObservation, ...]:
        return tuple(
            forecast.model_copy(
                update={
                    "player_id": player_id,
                    "horizon": ForecastHorizon.REST_OF_SEASON,
                    "metric": metric,
                    "period_start": period_start,
                    "period_end": period_end,
                    "source": "razzball",
                    "model_version": "captured-ros-v1",
                }
            )
            for metric in selected
        )

    complete_except_fumbles = rows("canonical-player", metrics)
    incomplete_other_metric = rows("incomplete-player", metrics[:-1])
    outsider = rows("not-rostered", metrics)
    selected = _single_source_fumbles_gap_player_ids(
        league_state=state,
        candidate_ids={"canonical-player", "incomplete-player"},
        source_observations=complete_except_fumbles + incomplete_other_metric + outsider,
    )

    assert selected == {"canonical-player"}

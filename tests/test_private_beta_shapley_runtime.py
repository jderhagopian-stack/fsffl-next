from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.private_beta_shapley_runtime import PrivateBetaShapleyContractLoader
from fsffl.product.runtime import UserRuntimeContext
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
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.value.private_beta_activation_data import (
    ACTIVATION_BUNDLE_SHA256,
    activation_artifact_text,
)
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability


def _fixture() -> tuple[LeagueState, ForecastObservation]:
    facts = json.loads(activation_artifact_text("current_i1_facts_2026.json"))
    row = facts["rows"][0]
    position = Position(row["position"])
    now = datetime(2026, 9, 16, 12, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    player = Player(
        player_id="canonical-player",
        full_name=row["display_name"],
        position=position,
        provider_refs=(
            ProviderRef(provider=row["identity_provider"], external_id=row["identity_external_id"]),
        ),
    )
    rules = LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(),
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
        distribution=ForecastDistribution(mean=250.0, stddev=25.0),
        source="governed-live-fixture",
        model_version="fixture-forecast-v1",
        as_of=now,
        provenance=provenance,
    )
    return state, observation


def _context(state: LeagueState, observation: ForecastObservation) -> UserRuntimeContext:
    evidence = SimpleNamespace(league_scored_forecasts=(observation,))
    return UserRuntimeContext(
        user_id="user",
        league_state=state,
        forecast_evidence=cast(Any, evidence),
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
    loader = PrivateBetaShapleyContractLoader()
    contract = loader(_context(state, observation))

    assert contract.status == ShapleyIntrinsicAvailability.DEGRADED
    assert contract.display_scaling_applied is False
    assert contract.diagnostic_h1_included is False
    assert contract.coverage.player_count == 1
    assert contract.coverage.year_1_forecast_players == 1
    assert contract.coverage.year_2_i1_players == 1
    assert contract.coverage.year_3_i1_players == 1
    assert contract.coverage.reduced_or_fallback_players == 1
    assert contract.estimates[0].diagnostic_h1.included_in_intrinsic is False
    assert [item.provenance.direct_i1_horizon for item in contract.estimates[0].contributions] == [None, 2, 3]
    reconstructed = sum(item.discounted_contribution for item in contract.estimates[0].contributions)
    assert abs(reconstructed - contract.estimates[0].raw_intrinsic_value) <= 1e-9


def test_loader_reuses_identical_contract_and_invalidates_on_forecast_change() -> None:
    state, observation = _fixture()
    loader = PrivateBetaShapleyContractLoader()
    first = loader(_context(state, observation))
    second = loader(_context(state, observation))
    changed = observation.model_copy(
        update={"distribution": ForecastDistribution(mean=251.0, stddev=25.0)}
    )
    third = loader(_context(state, changed))
    assert first is second
    assert third is not first


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
    contract = PrivateBetaShapleyContractLoader()(_context(unknown_state, unknown_forecast))
    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert contract.coverage.player_count == 0
    assert "completed_source_player_mapping" in contract.coverage.missing_required_fact_families

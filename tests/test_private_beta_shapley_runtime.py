from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from fsffl.forecast.future_contract import FUTURE_FORECAST_CONTRACT_VERSION
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
from fsffl.product.p0_forecast_runtime import (
    P0_FINAL_ROUTE_AUTHORITY_SHA256,
    P0_FINAL_ROUTE_AUTHORITY_VERSION,
    P0_FORECAST_VERSION,
    frozen_p0_source_rows,
)
from fsffl.product.p0_future_forecast_provider import build_p0_future_forecast_contract
from fsffl.product.private_beta_shapley_runtime import PrivateBetaShapleyContractLoader
from fsffl.product.runtime import UserRuntimeContext
from fsffl.product.vnext_future_forecast_provider import (
    VNEXT_FORECAST_VERSION,
    build_vnext_future_forecast_contract,
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
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.value.private_beta_activation_data import (
    ACTIVATION_BUNDLE_SHA256,
    activation_artifact_text,
)
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
    loader = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(observation)
    )
    contract = loader(_context(state, observation))

    assert contract.status == ShapleyIntrinsicAvailability.DEGRADED
    assert contract.display_scaling_applied is False
    assert contract.diagnostic_h1_included is False
    assert contract.coverage.player_count == 1
    assert contract.coverage.year_1_forecast_players == 1
    assert contract.coverage.year_2_i1_players == 1
    assert contract.coverage.year_3_i1_players == 1
    assert contract.coverage.rich_path_players == 1
    assert contract.coverage.reduced_or_fallback_players == 0
    assert contract.forecast_model_version == P0_FORECAST_VERSION
    assert contract.estimates[0].diagnostic_h1.included_in_intrinsic is False
    assert [item.provenance.direct_i1_horizon for item in contract.estimates[0].contributions] == [None, 2, 3]
    assert contract.horizon_seeds == (contract.seed, contract.seed + 1, contract.seed + 2)
    reconstructed = sum(item.discounted_contribution for item in contract.estimates[0].contributions)
    assert abs(reconstructed - contract.estimates[0].raw_intrinsic_value) <= 1e-9


def test_live_forecast_change_does_not_replace_preseason_authority() -> None:
    state, observation = _fixture()
    loader = PrivateBetaShapleyContractLoader(
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
    loader = PrivateBetaShapleyContractLoader(
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
    contract = PrivateBetaShapleyContractLoader(
        year_one_loader=lambda _state: _authority_evidence(unknown_forecast)
    )(context)
    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert contract.coverage.player_count == 0
    assert "p0_future_forecast_coordinate" in contract.coverage.missing_required_fact_families


# This focused file intentionally triggers the lightweight activation/API diagnostic workflow.


def test_loader_fails_closed_without_preseason_authority_loader() -> None:
    state, observation = _fixture()
    contract = PrivateBetaShapleyContractLoader()(_context(state, observation))
    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert "preseason_year1_forecast" in contract.coverage.missing_required_fact_families


def test_contract_exposes_preseason_year_one_provenance() -> None:
    state, observation = _fixture()
    contract = PrivateBetaShapleyContractLoader(
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
    contract = PrivateBetaShapleyContractLoader(
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
    contract = PrivateBetaShapleyContractLoader(
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
    contract = PrivateBetaShapleyContractLoader(
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
        return SimpleNamespace(
            contract=contract,
            scoring_multipliers=materialized.scoring_multipliers,
        )

    return builder


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
        future_forecast_builder=build_vnext_future_forecast_contract,
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

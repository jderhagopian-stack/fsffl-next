from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.simulation_runtime import (
    build_live_simulation_analytics,
    configured_simulation_rng,
    _simulation_rng_from_environment,
)
from fsffl.product.runtime import LiveForecastEvidence, UserRuntimeContext
from fsffl.product.opportunity_search import build_scoped_trade_candidates
from fsffl.product.trade_center_view import build_trade_center_browser_view
from fsffl.product import scenario_cache
from fsffl.persistence.runtime_cache import decode_simulation, simulation_artifact
from fsffl.persistence.contracts import canonical_fingerprint
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    NflTeamBye,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.team_utility.simulation import NUMPY_PCG64_BATCHED_GAUSS_V1
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore
from fsffl.value.models import ValueAssetKind
from fsffl.team_utility import compare_team_utility_vectors
from fsffl.trade_decision import (
    BilateralTradeProposal,
    Direction,
    TradeLeg,
    classify_bilateral_trade_decision,
    evaluate_bilateral_trade_deltas,
)
from fsffl.state.models import PlayerAsset


AS_OF = datetime(2026, 9, 5, 22, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _state() -> LeagueState:
    league = League(
        league_id="league:sim",
        name="Simulation League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            playoff_team_count=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(),
        ),
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=(
            Team(team_id="a", league_id=league.league_id, display_name="A"),
            Team(team_id="b", league_id=league.league_id, display_name="B"),
        ),
        team_states=(
            TeamState(team_id="a", roster=(RosterEntry(player_id="pa", slot=RosterSlot.QB),)),
            TeamState(team_id="b", roster=(RosterEntry(player_id="pb", slot=RosterSlot.QB),)),
        ),
        players=(
            Player(player_id="pa", full_name="A QB", position=Position.QB, nfl_team="NE"),
            Player(player_id="pb", full_name="B QB", position=Position.QB, nfl_team="NYJ"),
        ),
        player_states=(
            PlayerState(player_id="pa", as_of=AS_OF, nfl_team="NE", provenance=PROVENANCE),
            PlayerState(player_id="pb", as_of=AS_OF, nfl_team="NYJ", provenance=PROVENANCE),
        ),
        matchups=tuple(
            LeagueMatchup(week=week, team_a_id="a", team_b_id="b", provenance=PROVENANCE)
            for week in range(1, 5)
        ),
        nfl_team_byes=(
            NflTeamBye(season=2026, nfl_team="NE", week=5, provenance=PROVENANCE),
            NflTeamBye(season=2026, nfl_team="NYJ", week=6, provenance=PROVENANCE),
        ),
    )


def _forecasts() -> tuple[ForecastObservation, ...]:
    return tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.QB,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=AS_OF,
            period_end=AS_OF + timedelta(days=180),
            distribution=ForecastDistribution(mean=mean, stddev=stddev),
            source="fsffl:live_league_scored",
            model_version="next2-live-calibrated-test",
            as_of=AS_OF,
            provenance=PROVENANCE,
        )
        for player_id, mean, stddev in (("pa", 400.0, 80.0), ("pb", 250.0, 60.0))
    )


def test_live_simulation_runtime_populates_next7_competitive_metrics() -> None:
    result = build_live_simulation_analytics(
        _state(),
        forecasts=_forecasts(),
        forecast_model_version="next2-test",
        simulation_count=2_000,
        seed=7,
        generated_at=AS_OF,
    )

    assert result.simulation_result.simulation_count == 2_000
    rows = {row.team_id: row for row in result.league_view.teams}
    assert rows["a"].expected_wins is not None
    assert rows["a"].playoff_probability is not None
    assert rows["a"].first_place_probability is not None
    assert rows["a"].optimized_expected_points == 400.0
    assert rows["a"].expected_wins > rows["b"].expected_wins
    assert rows["a"].playoff_probability > rows["b"].playoff_probability
    assert "empirical-weekly-volatility" in result.simulation_result.model_version
    assert any(warning.code == "weekly_mean_decomposition_provisional" for warning in result.league_view.context.warnings)
    assert any(warning.code == "competitive_state_policy_league_relative" for warning in result.league_view.context.warnings)
    assert not any(warning.code == "competitive_state_policy_not_attached" for warning in result.league_view.context.warnings)
    assert any(
        entry.component == "weekly_volatility" and "next2-weekly-volatility" in entry.model_version
        for entry in result.league_view.context.lineage
    )
    assert any(entry.component == "competitive_state_policy" for entry in result.league_view.context.lineage)
    states = {row.team_id: row.utility.calculated_competitive_state for row in result.team_views}
    assert states["a"].value != "unknown"
    assert states["b"].value != "unknown"


def test_default_hosted_simulation_loader_resolves_foreground_pressure_callback() -> None:
    from fsffl.product import webapp

    evidence = SimpleNamespace(
        league_scored_forecasts=(),
        model_version="forecast-test",
    )
    sentinel = object()
    with patch.object(webapp, "build_live_simulation_analytics", return_value=sentinel) as build:
        result = webapp._default_simulation_loader(_state(), evidence)  # type: ignore[arg-type]

    assert result is sentinel
    assert build.call_args.kwargs["simulation_count"] == 50_000
    callback = build.call_args.kwargs["cooperative_yield"]
    assert callback.__self__ is webapp.foreground_pressure
    assert callback.__func__ is webapp.foreground_pressure.cooperative_yield.__func__


def test_experimental_rng_keeps_player_forecasts_and_persists_distinct_identity() -> None:
    state = _state()
    forecasts = _forecasts()
    legacy = build_live_simulation_analytics(
        state,
        forecasts=forecasts,
        forecast_model_version="next2-test",
        simulation_count=2_000,
        seed=717,
        generated_at=AS_OF,
    )
    experimental = build_live_simulation_analytics(
        state,
        forecasts=forecasts,
        forecast_model_version="next2-test",
        simulation_count=2_000,
        seed=717,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1,
        rng_batch_size=250,
        generated_at=AS_OF,
    )

    def player_projection(result):
        return tuple(
            (team.team_id, player.player_id, player.forecasts, player.season_fantasy_points_projection)
            for team in result.team_views
            for player in team.players
        )

    assert player_projection(legacy) == player_projection(experimental)
    assert legacy.model_version != experimental.model_version
    assert experimental.model_version.endswith("numpy-pcg64-batched-gauss-v1")
    legacy_artifact = simulation_artifact(
        league_state_id=state.state_id,
        forecast_fingerprint="forecast-fixture",
        result=legacy,
    )
    experimental_artifact = simulation_artifact(
        league_state_id=state.state_id,
        forecast_fingerprint="forecast-fixture",
        result=experimental,
    )
    assert legacy_artifact.key.model_version != experimental_artifact.key.model_version
    assert legacy_artifact.key.input_fingerprint == canonical_fingerprint(
        state.state_id, "forecast-fixture"
    )
    # The exact State + Forecast dependency remains directly addressable; the
    # experimental protocol/runtime/batch identity lives in model_version.
    assert legacy_artifact.key.input_fingerprint == experimental_artifact.key.input_fingerprint
    assert ";batch=250;count=2000;seed=717;runtime=python-" in experimental_artifact.key.model_version
    assert ";numpy-" in experimental_artifact.key.model_version
    assert decode_simulation(experimental_artifact.payload) == experimental


def test_experimental_50k_runtime_preserves_forecast_and_search_inputs() -> None:
    state = _state()
    forecasts = _forecasts()
    legacy = build_live_simulation_analytics(
        state,
        forecasts=forecasts,
        forecast_model_version="next2-test",
        simulation_count=50_000,
        seed=20261001,
        generated_at=AS_OF,
    )
    experimental = build_live_simulation_analytics(
        state,
        forecasts=forecasts,
        forecast_model_version="next2-test",
        simulation_count=50_000,
        seed=20261001,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1,
        rng_batch_size=500,
        generated_at=AS_OF,
    )
    replay = build_live_simulation_analytics(
        state,
        forecasts=forecasts,
        forecast_model_version="next2-test",
        simulation_count=50_000,
        seed=20261001,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1,
        rng_batch_size=500,
        generated_at=AS_OF,
    )

    assert experimental.simulation_result.simulation_count == 50_000
    assert experimental.simulation_result == replay.simulation_result
    assert tuple(
        (team.team_id, player.player_id, player.forecasts, player.season_fantasy_points_projection)
        for team in legacy.team_views
        for player in team.players
    ) == tuple(
        (team.team_id, player.player_id, player.forecasts, player.season_fantasy_points_projection)
        for team in experimental.team_views
        for player in team.players
    )
    # Search consumes these already-published Team Utility rows; RNG choice must not
    # change the Forecast-derived position strengths or roster-fragility inputs.
    assert tuple(
        (team.team_id, team.position_strengths, team.utility.roster_resilience)
        for team in legacy.team_views
    ) == tuple(
        (team.team_id, team.position_strengths, team.utility.roster_resilience)
        for team in experimental.team_views
    )
    assert tuple(
        (row.team_id, row.expected_wins > 2.0, row.playoff_probability > 0.5)
        for row in legacy.league_view.teams
    ) == tuple(
        (row.team_id, row.expected_wins > 2.0, row.playoff_probability > 0.5)
        for row in experimental.league_view.teams
    )


def test_hosted_rng_protocol_configuration_is_explicit_and_fail_closed() -> None:
    from fsffl.team_utility.simulation import (
        NUMPY_PCG64_BATCHED_GAUSS_V1,
        PYTHON_RANDOM_GAUSS_V1,
    )

    assert _simulation_rng_from_environment({}) == (PYTHON_RANDOM_GAUSS_V1, None)
    assert _simulation_rng_from_environment({
        "FSFFL_SIMULATION_RNG_PROTOCOL": NUMPY_PCG64_BATCHED_GAUSS_V1
    }) == (NUMPY_PCG64_BATCHED_GAUSS_V1, 500)
    assert _simulation_rng_from_environment({
        "FSFFL_SIMULATION_RNG_PROTOCOL": NUMPY_PCG64_BATCHED_GAUSS_V1,
        "FSFFL_SIMULATION_RNG_BATCH_SIZE": "750",
    }) == (NUMPY_PCG64_BATCHED_GAUSS_V1, 750)

    try:
        _simulation_rng_from_environment({
            "FSFFL_SIMULATION_RNG_PROTOCOL": NUMPY_PCG64_BATCHED_GAUSS_V1,
            "FSFFL_SIMULATION_RNG_BATCH_SIZE": "50001",
        })
    except ValueError as exc:
        assert "between 1 and 50000" in str(exc)
    else:
        raise AssertionError("out-of-range RNG batches must fail closed")

    try:
        _simulation_rng_from_environment({"FSFFL_SIMULATION_RNG_PROTOCOL": "unversioned-rng"})
    except ValueError as exc:
        assert "unsupported FSFFL_SIMULATION_RNG_PROTOCOL" in str(exc)
    else:
        raise AssertionError("unknown RNG protocols must fail closed")


def test_experimental_durable_scenario_artifact_round_trips_under_reader_key() -> None:
    from fsffl.product.simulation_runtime import simulation_model_version_for_rng_protocol

    class Store:
        def __init__(self):
            self.rows = {}

        def get_reusable_artifact(self, key):
            return self.rows.get(key)

        def put_artifact(self, record):
            self.rows[record.key] = record

    evidence_rows = _forecasts()
    evidence = LiveForecastEvidence(
        raw_forecasts=evidence_rows,
        league_scored_forecasts=evidence_rows,
        successful_source_ids=("source-a", "source-b"),
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=None,
    )
    calls = 0

    def experimental_loader(state, forecast_evidence):
        nonlocal calls
        calls += 1
        return build_live_simulation_analytics(
            state,
            forecasts=forecast_evidence.league_scored_forecasts,
            forecast_model_version=forecast_evidence.model_version,
            simulation_count=2_000,
            seed=20261004,
            rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1,
            rng_batch_size=500,
            generated_at=AS_OF,
        )

    experimental_loader.__fsffl_cache_identity__ = "numpy-pcg64-batch-500-test-runtime"
    experimental_loader.__fsffl_simulation_model_version__ = simulation_model_version_for_rng_protocol(
        NUMPY_PCG64_BATCHED_GAUSS_V1
    )
    store = Store()
    scenario_cache.clear_scenario_cache()
    scenario_cache.configure_scenario_cache_persistence(store)
    try:
        first, cache_hit = scenario_cache.run_cached_scenario_simulation(
            _state(), evidence, simulation_loader=experimental_loader
        )
        assert not cache_hit
        assert first.simulation_result.rng_protocol == NUMPY_PCG64_BATCHED_GAUSS_V1
        assert len(store.rows) == 1

        scenario_cache.clear_scenario_cache()
        restored, durable_hit = scenario_cache.run_cached_scenario_simulation(
            _state(), evidence, simulation_loader=experimental_loader
        )
        assert durable_hit
        assert restored == first
        assert calls == 1
    finally:
        scenario_cache.configure_scenario_cache_persistence(None)
        scenario_cache.clear_scenario_cache()


def test_changed_state_utility_decision_and_lineup_replay_across_rng_versions() -> None:
    from fsffl.team_utility.simulation import PYTHON_RANDOM_GAUSS_V1

    def swapped_state(state):
        return state.model_copy(
            update={
                "team_states": (
                    TeamState(team_id="a", roster=(RosterEntry(player_id="pb", slot=RosterSlot.QB),)),
                    TeamState(team_id="b", roster=(RosterEntry(player_id="pa", slot=RosterSlot.QB),)),
                )
            }
        )

    def forecasts(*, near_boundary: bool):
        if not near_boundary:
            return _forecasts()
        return tuple(
            item.model_copy(
                update={"distribution": ForecastDistribution(mean=325.0, stddev=80.0)}
            )
            for item in _forecasts()
        )

    state = _state()
    changed_state = swapped_state(state)
    assert state.state_id != changed_state.state_id
    proposal = BilateralTradeProposal(
        proposal_id="rng-changed-state",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="a", sends=(PlayerAsset(player_id="pa"),)),
        side_b=TradeLeg(team_id="b", sends=(PlayerAsset(player_id="pb"),)),
    )
    for near_boundary in (False, True):
        forecast_rows = forecasts(near_boundary=near_boundary)
        outputs = {}
        for protocol in (PYTHON_RANDOM_GAUSS_V1, NUMPY_PCG64_BATCHED_GAUSS_V1):
            outputs[protocol] = tuple(
                build_live_simulation_analytics(
                    scenario_state,
                    forecasts=forecast_rows,
                    forecast_model_version="next2-test",
                    simulation_count=50_000,
                    seed=20261002,
                    rng_protocol=protocol,
                    rng_batch_size=500 if protocol == NUMPY_PCG64_BATCHED_GAUSS_V1 else None,
                    generated_at=AS_OF,
                )
                for scenario_state in (state, changed_state)
            )

        legacy_before, legacy_after = outputs[PYTHON_RANDOM_GAUSS_V1]
        numpy_before, numpy_after = outputs[NUMPY_PCG64_BATCHED_GAUSS_V1]
        assert legacy_after.simulation_result.simulation_count == 50_000
        assert numpy_after.simulation_result.simulation_count == 50_000

        # Search consumes the published positional context, and this scenario's
        # Forecast/State lineups, unchanged exactly across RNG protocols.
        assert tuple(
            (team.team_id, team.position_strengths, team.utility.roster_resilience)
            for team in legacy_after.team_views
        ) == tuple(
            (team.team_id, team.position_strengths, team.utility.roster_resilience)
            for team in numpy_after.team_views
        )
        assert tuple(
            tuple((row.player_id, row.slot) for row in team.optimized_lineup.assignments)
            for team in legacy_after.team_views
        ) == tuple(
            tuple((row.player_id, row.slot) for row in team.optimized_lineup.assignments)
            for team in numpy_after.team_views
        )

        legacy_evaluation = evaluate_bilateral_trade_deltas(
            proposal,
            before_a=legacy_before.team_views[0].utility,
            after_a=legacy_after.team_views[0].utility,
            before_b=legacy_before.team_views[1].utility,
            after_b=legacy_after.team_views[1].utility,
        )
        numpy_evaluation = evaluate_bilateral_trade_deltas(
            proposal,
            before_a=numpy_before.team_views[0].utility,
            after_a=numpy_after.team_views[0].utility,
            before_b=numpy_before.team_views[1].utility,
            after_b=numpy_after.team_views[1].utility,
        )
        legacy_decision = classify_bilateral_trade_decision(legacy_evaluation)
        numpy_decision = classify_bilateral_trade_decision(numpy_evaluation)
        assert legacy_decision == numpy_decision
        expected_direction = Direction.UNCHANGED if near_boundary else Direction.WORSENS
        expected_counterparty_direction = (
            Direction.UNCHANGED if near_boundary else Direction.IMPROVES
        )
        for result in (legacy_decision, numpy_decision):
            assert result.side_a.expected_wins == expected_direction
            assert result.side_a.playoff_probability == expected_direction
            assert result.side_a.first_place_probability == expected_direction
            assert result.side_b.expected_wins == expected_counterparty_direction
            assert result.side_b.playoff_probability == expected_counterparty_direction
            assert result.side_b.first_place_probability == expected_counterparty_direction

        # The test intentionally reports both signed effects for boundary cases;
        # it does not force a tie/noise result into an equivalence assertion.
        for before, after in ((legacy_before, legacy_after), (numpy_before, numpy_after)):
            for team_id in ("a", "b"):
                delta = compare_team_utility_vectors(
                    next(row.utility for row in before.team_views if row.team_id == team_id),
                    next(row.utility for row in after.team_views if row.team_id == team_id),
                )
                assert delta.competitive is not None


def test_changed_state_search_candidates_and_order_match_across_rng_versions() -> None:
    from fsffl.team_utility.simulation import PYTHON_RANDOM_GAUSS_V1

    original = _state()
    rules = original.league.rules.model_copy(
        update={"lineup": (LineupRequirement(slot=RosterSlot.WR, count=1),)}
    )
    league = original.league.model_copy(update={"rules": rules})
    state = original.model_copy(
        update={
            "league": league,
            "team_states": tuple(
                TeamState(
                    team_id=row.team_id,
                    roster=(RosterEntry(player_id=row.roster[0].player_id, slot=RosterSlot.WR),),
                )
                for row in original.team_states
            ),
            "players": tuple(row.model_copy(update={"position": Position.WR}) for row in original.players),
        }
    )
    forecast_rows = tuple(row.model_copy(update={"position": Position.WR}) for row in _forecasts())
    evidence = LiveForecastEvidence(
        raw_forecasts=forecast_rows,
        league_scored_forecasts=forecast_rows,
        successful_source_ids=("source-a", "source-b"),
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=None,
    )
    cardinal = {
        player_id: FSFFLCardinalValueScore(
            asset_id=player_id,
            asset_kind=ValueAssetKind.PLAYER,
            score=value,
            as_of=AS_OF,
            market_context_id="changed-state-rng-test",
        )
        for player_id, value in (("pa", 1000.0), ("pb", 900.0))
    }

    for scenario_state in (state, state.model_copy(update={
        "team_states": (
            TeamState(team_id="a", roster=(RosterEntry(player_id="pb", slot=RosterSlot.WR),)),
            TeamState(team_id="b", roster=(RosterEntry(player_id="pa", slot=RosterSlot.WR),)),
        )
    })):
        observed = {}
        for protocol in (PYTHON_RANDOM_GAUSS_V1, NUMPY_PCG64_BATCHED_GAUSS_V1):
            simulation = build_live_simulation_analytics(
                scenario_state,
                forecasts=forecast_rows,
                forecast_model_version="next2-search-test",
                simulation_count=50_000,
                seed=20261003,
                rng_protocol=protocol,
                rng_batch_size=500 if protocol == NUMPY_PCG64_BATCHED_GAUSS_V1 else None,
                generated_at=AS_OF,
            )
            runtime = UserRuntimeContext(
                user_id="rng-validation",
                league_state=scenario_state,
                selected_team_id="a",
                forecast_evidence=evidence,
                simulation_analytics=simulation,
            )
            browser = build_trade_center_browser_view(scenario_state, focal_team_id="a")
            candidates = build_scoped_trade_candidates(runtime, browser, cardinal)
            assert candidates, "fixture must exercise a non-empty Search candidate set"
            observed[protocol] = tuple(
                (
                    row["counterparty_team_id"],
                    tuple(item["asset_ref"] for item in row["send"]),
                    tuple(item["asset_ref"] for item in row["receive"]),
                )
                for row in candidates
            )
        assert observed[PYTHON_RANDOM_GAUSS_V1] == observed[NUMPY_PCG64_BATCHED_GAUSS_V1]

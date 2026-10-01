from __future__ import annotations

from datetime import UTC, datetime
import importlib.metadata
import os
import platform
from typing import Callable, Literal

from fsffl.analytics.league import LeagueAnalyticsView, build_league_analytics_view
from fsffl.analytics.models import (
    AnalyticsContext,
    AnalyticsWarning,
    AnalyticsWarningKind,
    ModelLineageEntry,
)
from fsffl.analytics.team import TeamAnalyticsView, build_team_analytics_view
from fsffl.forecast import (
    PROVISIONAL_POSITION_FLOOR_SOURCE,
    attach_provisional_position_floor_forecasts,
)
from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.memory_attribution import log_object_graph, sample_rss_phase
from fsffl.state.models import FrozenModel, LeagueState
from fsffl.team_utility import (
    LeagueScoringDispersionDiagnostic,
    RegularSeasonSimulationResult,
    TeamUtilityVector,
    assemble_team_utility_vector,
    build_bye_aware_weekly_team_scoring_panel,
    build_league_relative_position_strengths,
    build_regular_season_simulation_input,
    build_scoring_dispersion_diagnostic,
    classify_calculated_competitive_state,
    derive_league_relative_competitive_state_policy,
    optimize_team_lineup,
    simulate_regular_season,
)
from fsffl.team_utility.simulation import (
    NUMPY_PCG64_BATCHED_GAUSS_V1,
    PYTHON_RANDOM_GAUSS_V1,
)

LIVE_SIMULATION_MODEL_VERSION = "next9-live-simulation-analytics-v9:league-configured-postseason"
EXPERIMENTAL_NUMPY_SIMULATION_MODEL_VERSION = "next9-live-simulation-analytics-v9:numpy-pcg64-batched-gauss-v1:league-configured-postseason"


def _simulation_rng_from_environment(environment: dict[str, str]) -> tuple[str, int | None]:
    protocol = environment.get("FSFFL_SIMULATION_RNG_PROTOCOL", PYTHON_RANDOM_GAUSS_V1).strip()
    if protocol == PYTHON_RANDOM_GAUSS_V1:
        raw_batch_size = environment.get("FSFFL_SIMULATION_RNG_BATCH_SIZE", "").strip()
        if raw_batch_size:
            raise ValueError("FSFFL_SIMULATION_RNG_BATCH_SIZE requires the NumPy protocol")
        return protocol, None
    if protocol == NUMPY_PCG64_BATCHED_GAUSS_V1:
        raw_batch_size = environment.get("FSFFL_SIMULATION_RNG_BATCH_SIZE", "500").strip()
        try:
            batch_size = int(raw_batch_size)
        except ValueError as exc:
            raise ValueError("FSFFL_SIMULATION_RNG_BATCH_SIZE must be an integer") from exc
        if not 1 <= batch_size <= 50_000:
            raise ValueError("FSFFL_SIMULATION_RNG_BATCH_SIZE must be between 1 and 50000")
        return protocol, batch_size
    raise ValueError(f"unsupported FSFFL_SIMULATION_RNG_PROTOCOL: {protocol}")


_CONFIGURED_SIMULATION_RNG = _simulation_rng_from_environment(dict(os.environ))


def configured_simulation_rng() -> tuple[str, int | None]:
    """Return the process-start RNG protocol; deployment changes require a restart."""

    return _CONFIGURED_SIMULATION_RNG


def configured_simulation_model_version() -> str:
    protocol, _ = configured_simulation_rng()
    model_version = simulation_model_version_for_rng_protocol(protocol)
    return f"{model_version}:{configured_simulation_cache_identity()}"


def simulation_artifact_model_version(result: object) -> str:
    protocol = getattr(result, "rng_protocol", None)
    model_version = simulation_model_version_for_rng_protocol(protocol)
    if protocol == PYTHON_RANDOM_GAUSS_V1:
        runtime = str(getattr(result, "rng_runtime_version", ""))
        if runtime == "legacy-unrecorded":
            # Preserve lookup compatibility for pre-identity Python artifacts.
            return model_version
        if not runtime.startswith("python-"):
            return f"{model_version}:invalid-runtime-identity"
        return (
            f"{model_version}:{protocol};batch=None;"
            f"count={getattr(result, 'simulation_count', None)};"
            f"seed={getattr(result, 'seed', None)};runtime={runtime}"
        )
    runtime = str(getattr(result, "rng_runtime_version", ""))
    numpy_runtime, separator, python_runtime = runtime.partition(";")
    if not separator or not numpy_runtime.startswith("numpy-") or not python_runtime.startswith("python-"):
        return f"{model_version}:invalid-runtime-identity"
    identity = (
        f"{protocol};batch={getattr(result, 'rng_batch_size', None)};"
        f"count={getattr(result, 'simulation_count', None)};seed={getattr(result, 'seed', None)};"
        f"runtime={python_runtime};{numpy_runtime}"
    )
    return f"{model_version}:{identity}"


def simulation_matches_configured_rng(result: object) -> bool:
    """Reject durable Simulation created for another process RNG/runtime config."""

    protocol, batch_size = configured_simulation_rng()
    if getattr(result, "rng_protocol", None) != protocol:
        return False

    if protocol == PYTHON_RANDOM_GAUSS_V1:
        if getattr(result, "rng_batch_size", None) is not None:
            return False
        runtime_version = f"python-{platform.python_version()}"
        bit_generator = "python-random-mt19937"
        draw_layout = "trial-major;compiled-schedule-major;home-away-v1"
        seed_derivation = "python-regular-root-seed-v1;python-playoff-xor-0x5F3759DF-v1"
    else:
        if (
            getattr(result, "simulation_count", None) != 50_000
            or getattr(result, "seed", None) != 20260905
            or getattr(result, "rng_batch_size", None) != batch_size
        ):
            return False
        runtime_version = (
            f"numpy-{importlib.metadata.version('numpy')};python-{platform.python_version()}"
        )
        bit_generator = "PCG64"
        draw_layout = "batch-major;trial-major;compiled-schedule-major;home-away-v1"
        seed_derivation = "pcg64-regular-root-seed-v1;python-playoff-xor-0x5F3759DF-v1"

    # Pre-protocol legacy artifacts did not record a replay identity. Continue to
    # accept those only on the legacy path; experimental results must be explicit.
    if protocol == PYTHON_RANDOM_GAUSS_V1 and getattr(result, "rng_runtime_version", None) == "legacy-unrecorded":
        return True
    return bool(
        getattr(result, "rng_runtime_version", None) == runtime_version
        and getattr(result, "rng_bit_generator", None) == bit_generator
        and getattr(result, "rng_draw_dtype", None) == "float64"
        and getattr(result, "rng_draw_layout", None) == draw_layout
        and getattr(result, "rng_seed_derivation", None) == seed_derivation
    )


def configured_simulation_cache_identity() -> str:
    protocol, batch_size = configured_simulation_rng()
    runtime = f"python-{platform.python_version()}"
    if protocol == NUMPY_PCG64_BATCHED_GAUSS_V1:
        runtime += f";numpy-{importlib.metadata.version('numpy')}"
    return (
        f"{protocol};batch={batch_size};count=50000;seed=20260905;"
        f"runtime={runtime}"
    )


def simulation_model_version_for_rng_protocol(rng_protocol: str) -> str:
    if rng_protocol == PYTHON_RANDOM_GAUSS_V1:
        return LIVE_SIMULATION_MODEL_VERSION
    if rng_protocol == NUMPY_PCG64_BATCHED_GAUSS_V1:
        return EXPERIMENTAL_NUMPY_SIMULATION_MODEL_VERSION
    raise ValueError(f"unsupported Simulation RNG protocol: {rng_protocol}")


class LiveSimulationAnalyticsResult(FrozenModel):
    """NEXT-7 views backed by authoritative NEXT-4 simulation outcomes."""

    league_view: LeagueAnalyticsView
    team_views: tuple[TeamAnalyticsView, ...]
    simulation_result: RegularSeasonSimulationResult
    scoring_dispersion_diagnostic: LeagueScoringDispersionDiagnostic
    model_version: str = LIVE_SIMULATION_MODEL_VERSION


def build_live_simulation_analytics(
    league_state: LeagueState,
    *,
    forecasts: tuple[ForecastObservation, ...],
    forecast_model_version: str,
    simulation_count: int = 50_000,
    seed: int = 20260905,
    rng_protocol: Literal[
        "python-random-gauss-v1", "numpy-pcg64-batched-gauss-v1"
    ] = PYTHON_RANDOM_GAUSS_V1,
    rng_batch_size: int | None = None,
    generated_at: datetime | None = None,
    cooperative_yield: Callable[[], object] | None = None,
) -> LiveSimulationAnalyticsResult:
    """Run Forecast -> week-specific NEXT-4 Simulation -> NEXT-7.

    Canonical NFL bye state is consumed from State authority. NEXT-4 re-optimizes
    every fantasy roster when canonical weekly availability actually changes.
    Identical no-bye/identical-bye lineup states are reused rather than recomputed.
    Season forecast means are still decomposed to equal active-NFL-game means as
    a provisional bridge, while weekly scoring variance comes from the independently
    calibrated NEXT-2 weekly-volatility model. Calculated competitive state is a
    Team Utility interpretation of the completed Simulation distribution, never a
    replacement for or adjustment to Simulation itself.

    The attached scoring-dispersion diagnostic is read-only. It separates the
    between-team weekly scoring signal from ordinary within-week scoring noise so
    forecast-compression calibration can target the earliest authoritative cause.
    """

    if any(item.as_of > league_state.as_of for item in forecasts):
        raise ValueError("simulation forecast evidence cannot postdate LeagueState")
    if not league_state.nfl_team_byes:
        raise ValueError("canonical NFL bye-week state is required for live simulation")
    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    generated = max(generated, league_state.as_of)

    with sample_rss_phase("simulation.forecast_attachment"):
        effective_forecasts = attach_provisional_position_floor_forecasts(
            league_state,
            forecasts,
            as_of=league_state.as_of,
            horizon=ForecastHorizon.SEASON,
        )
    fallback_ids = {
        item.player_id
        for item in effective_forecasts
        if item.source == PROVISIONAL_POSITION_FLOOR_SOURCE
    }

    fantasy_weeks = tuple(sorted({matchup.week for matchup in league_state.matchups}))
    if not fantasy_weeks:
        raise ValueError("canonical fantasy regular-season schedule is required")

    ordered_teams = tuple(sorted(league_state.teams, key=lambda item: item.team_id))
    lineups = {}
    incomplete_team_names: list[str] = []
    with sample_rss_phase("simulation.lineup_compilation"):
        for team in ordered_teams:
            lineup = optimize_team_lineup(
                league_state,
                effective_forecasts,
                team_id=team.team_id,
                as_of=league_state.as_of,
                horizon=ForecastHorizon.SEASON,
                allow_unfilled_slots=True,
            )
            lineups[team.team_id] = lineup
            if lineup.unfilled_slots:
                slots = ", ".join(
                    f"{item.slot.value}{item.slot_index}" for item in lineup.unfilled_slots
                )
                incomplete_team_names.append(f"{team.display_name} ({slots})")

    position_strength_rows = build_league_relative_position_strengths(
        tuple(lineups[team.team_id] for team in ordered_teams)
    )
    position_strengths_by_team = {
        team.team_id: tuple(
            row for row in position_strength_rows if row.team_id == team.team_id
        )
        for team in ordered_teams
    }

    with sample_rss_phase("simulation.weekly_scoring_panel"):
        weekly_scoring = build_bye_aware_weekly_team_scoring_panel(
            league_state,
            effective_forecasts,
            team_ids=tuple(team.team_id for team in ordered_teams),
            weeks=fantasy_weeks,
            as_of=league_state.as_of,
            baseline_lineups=lineups,
        )
    team_names = {team.team_id: team.display_name for team in ordered_teams}
    bye_week_unfilled = [
        f"{team_names[row.team_id]} W{row.week}"
        for row in weekly_scoring
        if "explicit_unfilled_zero" in row.model_version
        and not lineups[row.team_id].unfilled_slots
    ]

    with sample_rss_phase("simulation.input_and_schedule_materialization"):
        request = build_regular_season_simulation_input(
            league_state,
            weekly_scoring=weekly_scoring,
            simulation_count=simulation_count,
            seed=seed,
            model_version="next4-live-regular-season-v5:empirical-weekly-volatility:league-configured-postseason",
            rng_protocol=rng_protocol,
            rng_batch_size=rng_batch_size,
        )
    log_object_graph(
        "simulation.forecast_boundary",
        raw_forecasts=forecasts,
        effective_forecasts=effective_forecasts,
        lineups=lineups,
        weekly_scoring=weekly_scoring,
        request=request,
        all_inputs=(forecasts, effective_forecasts, lineups, weekly_scoring, request),
    )
    with sample_rss_phase("simulation.kernel_and_result_aggregation"):
        simulation = simulate_regular_season(request, cooperative_yield=cooperative_yield)
    with sample_rss_phase("simulation.post_kernel_analytics_aggregation"):
        scoring_dispersion_diagnostic = build_scoring_dispersion_diagnostic(
            weekly_scoring,
            simulation,
            baseline_lineups=lineups,
            fallback_player_ids=fallback_ids,
        )
        outcomes = {item.team_id: item for item in simulation.outcomes}
        competitive_state_policy = derive_league_relative_competitive_state_policy(
            simulation.outcomes,
            as_of=league_state.as_of,
        )

    warnings: list[AnalyticsWarning] = [
        AnalyticsWarning(
            kind=AnalyticsWarningKind.MISSING_EVIDENCE,
            code="value_not_enriched",
            message=(
                "Authoritative NEXT-2 forecasts and NEXT-4 competitive simulation/team consequences are attached. "
                "NEXT-3 dynasty value and downstream trade/opportunity evidence remain pending."
            ),
            source_component="product-runtime",
        ),
        AnalyticsWarning(
            kind=AnalyticsWarningKind.PROVISIONAL,
            code="weekly_mean_decomposition_provisional",
            message=(
                "Simulation is bye-aware and re-optimizes each roster whenever weekly availability changes. "
                "Identical availability states reuse the same optimized lineup. Player season means are currently "
                "converted to equal active-NFL-game means until direct multi-source weekly NEXT-2 forecast means "
                "are promoted. Weekly scoring volatility is independently calibrated from actual historical weekly "
                "outcomes and is not derived from season forecast uncertainty."
            ),
            source_component="forecast",
        ),
        AnalyticsWarning(
            kind=AnalyticsWarningKind.PROVISIONAL,
            code="competitive_state_policy_league_relative",
            message=(
                "Calculated competitive state is now classified from the current authoritative Simulation "
                "distribution using transparent league-relative quartiles. The classification is useful for the "
                "private beta but remains provisional until historical competitive-state calibration is promoted."
            ),
            source_component="team-utility",
        ),
    ]
    if fallback_ids:
        warnings.append(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.PROVISIONAL,
                code="position_floor_forecast_fallback",
                message=(
                    f"{len(fallback_ids)} active roster player(s) lacked direct live forecast coverage and use the "
                    "governed conservative same-position floor forecast with widest observed position uncertainty."
                ),
                source_component="forecast",
            )
        )
    if incomplete_team_names:
        warnings.append(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.PROVISIONAL,
                code="explicit_unfilled_lineup_slots",
                message=(
                    "Roster state cannot legally fill every starter slot for: "
                    + "; ".join(incomplete_team_names)
                    + ". Unfilled slots contribute zero points; no taxi/free-agent player is fabricated."
                ),
                source_component="team-utility",
            )
        )
    if bye_week_unfilled:
        warnings.append(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.PROVISIONAL,
                code="bye_week_unfilled_lineup_slots",
                message=(
                    "Bye-week availability leaves at least one legal starter slot unfilled for: "
                    + "; ".join(bye_week_unfilled)
                    + ". Those week-specific slots contribute zero points."
                ),
                source_component="team-utility",
            )
        )

    context = AnalyticsContext(
        schema_version="1",
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        as_of=league_state.as_of,
        generated_at=generated,
        lineage=(
            ModelLineageEntry(component="state", model_version=league_state.schema_version),
            ModelLineageEntry(component="forecast", model_version=forecast_model_version),
            ModelLineageEntry(component="lineup", model_version="next4-lineup-v3:bye-aware"),
            ModelLineageEntry(
                component="position_strength",
                model_version="next4-league-relative-position-strength-v1",
            ),
            ModelLineageEntry(
                component="weekly_volatility",
                model_version="next2-weekly-volatility-v1:2023-2025-position-cv",
            ),
            ModelLineageEntry(
                component="team_scoring",
                model_version="next4-weekly-team-scoring-v4:bye_aware_empirical_weekly_volatility",
            ),
            ModelLineageEntry(component="simulation", model_version=simulation.model_version),
            ModelLineageEntry(
                component="scoring_dispersion_diagnostic",
                model_version=scoring_dispersion_diagnostic.model_version,
            ),
            ModelLineageEntry(
                component="competitive_state_policy",
                model_version=competitive_state_policy.model_version,
            ),
            ModelLineageEntry(component="team_utility", model_version="next4-live-team-utility-v5:resilience-driver-identity"),
        ),
        warnings=tuple(warnings),
    )

    team_views: list[TeamAnalyticsView] = []
    for team in ordered_teams:
        try:
            utility = assemble_team_utility_vector(
                league_state,
                effective_forecasts,
                team_id=team.team_id,
                as_of=league_state.as_of,
                horizon=ForecastHorizon.SEASON,
                competitive_outcome=outcomes[team.team_id],
                competitive_state_policy=competitive_state_policy,
                model_version="next4-live-team-utility-v5:resilience-driver-identity",
            )
        except ValueError:
            if not lineups[team.team_id].unfilled_slots:
                raise
            utility = TeamUtilityVector(
                team_id=team.team_id,
                as_of=league_state.as_of,
                competitive_outcome=outcomes[team.team_id],
                calculated_competitive_state=classify_calculated_competitive_state(
                    outcomes[team.team_id],
                    competitive_state_policy,
                    as_of=league_state.as_of,
                ),
                model_version="next4-live-team-utility-v5:resilience-driver-identity:resilience_unavailable_incomplete_roster",
            )
        team_views.append(
            build_team_analytics_view(
                league_state,
                context=context,
                team_id=team.team_id,
                forecasts=forecasts,
                optimized_lineup=lineups[team.team_id],
                position_strengths=position_strengths_by_team[team.team_id],
                utility=utility,
            )
        )

    views = tuple(team_views)
    return LiveSimulationAnalyticsResult(
        league_view=build_league_analytics_view(context=context, team_views=views),
        team_views=views,
        simulation_result=simulation,
        scoring_dispersion_diagnostic=scoring_dispersion_diagnostic,
        model_version=simulation_model_version_for_rng_protocol(rng_protocol),
    )

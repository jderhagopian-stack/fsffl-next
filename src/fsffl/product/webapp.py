Warning: truncated output (original token count: 29922)
Total output lines: 2731

from __future__ import annotations

import hashlib
import logging
from contextlib import nullcontext
import os
import secrets
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from fsffl.analytics.league import LeagueAnalyticsView, LeagueMetric
from fsffl.opportunity import WaiverMove
from fsffl.persistence.contracts import PersistenceStore
from fsffl.state.history import StateSnapshotStore
from fsffl.state.matchups import completed_matchups
from fsffl.state.models import FrozenModel, LeagueState
from fsffl.trade_decision.models import BilateralTradeProposal
from fsffl.value.models import (
    AssetValueProfile,
    MarketPriceEstimate,
    ValueAssetKind,
    ValueDistribution,
)

from .foreground_pressure import foreground_pressure
from .background_jobs import (
    IntelligenceJob,
    IntelligenceJobCoordinator,
    IntelligenceJobInterrupted,
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)
from .behavioral_runtime import BehavioralRuntimeCoordinator, BehavioralRuntimeStatus
from .dashboard import build_league_metric_chart
from .frontier_runtime import build_negotiation_frontier
from .league_atlas import build_league_atlas_payload
from .league_atlas_preseason import (
    capture_preseason_baseline_if_eligible,
    load_preseason_baseline,
)
from .origin_aware_pick_value_runtime import build_live_origin_aware_pick_values
from .intelligence_runtime import (
    build_forecast_lineup_analytics,
    build_state_only_league_view,
    state_first_runtime_status,
)
from .opportunity_workspace import build_opportunity_workspace
from .resource_coordinator import (
    HeavyWorkCoordinator,
    ResourceTransition,
    current_rss_bytes,
    process_peak_rss_bytes,
)
from .runtime import (
    LiveForecastEvidence,
    LiveForecastLoader,
    LiveValueLoader,
    PrivateBetaRuntimeStore,
    UserRuntimeContext,
    default_live_forecast_loader,
    league_material_fingerprint,
    default_live_value_loader,
    default_sleeper_state_loader,
)
from .scenario_cache import ScenarioComputationStage
from .static_assets import ContentFingerprintStaticFiles
from .simulation_runtime import (
    LiveSimulationAnalyticsResult,
    build_live_simulation_analytics,
    configured_simulation_cache_identity,
    configured_simulation_model_version,
    configured_simulation_rng,
)
from .team_page import build_forecast_team_view, build_state_only_team_view
from .trade_analysis_runtime import build_private_beta_trade_analysis
from .trade_center import TradeDraft, TradeDraftSide, submit_trade_draft
from .trade_center_view import build_trade_center_browser_view, resolve_owned_asset_ref
from .trade_opportunity_runtime import build_trade_opportunity_evaluation
from .trade_simulation_runtime import build_post_trade_simulation_comparison
from .waiver_action_runtime import build_actionable_waiver_comparison
from .what_if_runtime import build_player_unavailable_scenario


_STATIC_DIR = Path(__file__).with_name("static")
_security = HTTPBasic(auto_error=False)
_logger = logging.getLogger("fsffl.product.forecast")
LeagueViewProvider = Callable[[], LeagueAnalyticsView | None]
StateLoader = Callable[[str], LeagueState]
TradeEvaluator = Callable[[LeagueState, BilateralTradeProposal, str], dict[str, object]]
SimulationLoader = Callable[[LeagueState, LiveForecastEvidence], LiveSimulationAnalyticsResult]
CapabilityReadinessReader = Callable[[object], dict[str, object]]
ProductCapabilityReconciler = Callable[[object], dict[str, object]]
PresentationPayloadLoader = Callable[[str, UserRuntimeContext, str], dict[str, object] | None]
RuntimeMemoryReclaimer = Callable[[str], object]
StateResourceBoundaryHandler = Callable[[ResourceTransition], object]


class ConnectSleeperLeagueRequest(FrozenModel):
    league_external_id: str


class SelectTeamRequest(FrozenModel):
    team_id: str


class AnalyzeTradeRequest(FrozenModel):
    counterparty_team_id: str
    focal_asset_refs: tuple[str, ...]
    counterparty_asset_refs: tuple[str, ...]
    scenario_stage: ScenarioComputationStage = ScenarioComputationStage.CONFIRMATION


class EvaluateWaiverRequest(FrozenModel):
    add_player_id: str
    drop_player_id: str | None = None
    scenario_stage: ScenarioComputationStage = ScenarioComputationStage.CONFIRMATION


class PlayerUnavailableRequest(FrozenModel):
    player_id: str
    scenario_stage: ScenarioComputationStage = ScenarioComputationStage.CONFIRMATION


def _beta_auth_enabled() -> bool:
    return os.getenv("FSFFL_BETA_AUTH", "0").strip().lower() in {"1", "true", "yes", "on"}


def _password_digest(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def require_beta_user(credentials: HTTPBasicCredentials | None = Depends(_security)) -> str:
    if not _beta_auth_enabled():
        return "local-beta-user"
    expected_username = os.getenv("FSFFL_BETA_USERNAME")
    expected_password_sha256 = os.getenv("FSFFL_BETA_PASSWORD_SHA256")
    if not expected_username or not expected_password_sha256:
        raise RuntimeError("beta auth is enabled but runtime credentials are not configured")
    valid = (
        credentials is not None
        and secrets.compare_digest(credentials.username, expected_username)
        and secrets.compare_digest(_password_digest(password=credentials.password), expected_password_sha256.lower())
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid private-beta credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return expected_username


def _runtime_capability_readiness(runtime) -> dict[str, object]:
    """Describe governed capability availability independently of job lifecycle."""

    evidence = runtime.forecast_evidence
    runtime_result = getattr(evidence, "runtime_result", None) if evidence is not None else None
    blockers = tuple(getattr(runtime_result, "simulation_authority_blockers", ()) or ())
    partial_rows = tuple(getattr(runtime_result, "partial_fantasy_point_forecasts", ()) or ())
    material_partial_player_ids = tuple(
        getattr(runtime_result, "simulation_material_partial_player_ids", ()) or ()
    )
    non_material_partial_player_ids = tuple(
        getattr(
            runtime_result,
            "fumbles_lost_non_material_partial_player_ids",
            (),
        )
        or ()
    )
    all_material_partial_player_ids = tuple(
        getattr(
            runtime_result,
            "fumbles_lost_material_partial_player_ids",
            (),
        )
        or ()
    )
    authoritative_rows = tuple(getattr(evidence, "league_scored_forecasts", ()) or ()) if evidence is not None else ()
    raw_rows = tuple(getattr(evidence, "raw_forecasts", ()) or ()) if evidence is not None else ()
    non_material_partial_id_set = set(non_material_partial_player_ids)
    all_partial_rows_have_explicit_non_material_fumbles_authority = bool(
        partial_rows
        and non_material_partial_id_set
        and all(
            getattr(row, "player_id", None) in non_material_partial_id_set
            and set(getattr(row, "omitted_rule_stats", ()) or ()) == {"fum_lost"}
            for row in partial_rows
        )
    )

    if evidence is None or not (raw_rows or authoritative_rows or partial_rows):
        forecast_status = "unavailable"
        forecast_reason = "Governed Forecast evidence is not loaded."
    elif blockers or material_partial_player_ids or not authoritative_rows:
        forecast_status = "partial_provisional"
        forecast_reason = (
            "Shared raw Forecast evidence is populated, but complete scored authority "
            "for the current downstream consumer is unavailable"
            + (": " + ", ".join(blockers) if blockers else "")
            + "."
        )
    elif all_partial_rows_have_explicit_non_material_fumbles_authority:
        forecast_status = "non_material_partial"
        forecast_reason = (
            "Governed downstream Forecast use is allowed under explicit "
            "NON_MATERIAL_PARTIAL authority. FUMBLES_LOST remains omitted/degraded "
            f"for {len(non_material_partial_player_ids)} subject(s); scoring coverage "
            "is not FULL."
        )
    elif partial_rows:
        forecast_status = "partial_nonblocking"
        forecast_reason = (
            "Forecast scoring coverage remains partial for non-consumed subjects. "
            "The current downstream consumer is not blocked, but coverage is not FULL "
            "and no specialized omission authority is inferred for those subjects."
        )
    else:
        forecast_status = "full"
        forecast_reason = (
            "Governed league-scored Forecast authority is fully covered for the "
            "current downstream consumer."
        )

    if runtime.simulation_analytics is not None:
        simulation_status = "full"
        simulation_reason = "Governed current Simulation is available."
    else:
        simulation_status = "unavailable"
        simulation_reason = (
            "Simulation is unavailable under current Forecast authority"
            + (": " + ", ".join(blockers) if blockers else "")
            + "."
        )

    value_evidence = runtime.value_evidence
    value_available = bool(
        value_evidence is not None
        and (
            getattr(value_evidence, "estimates", ())
            or getattr(value_evidence, "fsffl_cardinal_values", ())
            or getattr(value_evidence, "pick_variant_market_values", ())
        )
    )
    value_status = "full" if value_available else "unavailable"
    value_reason = (
        "Governed current Broad Market / Cardinal Value evidence is available."
        if value_available
        else "Governed current Value evidence is unavailable."
    )

    league_state = getattr(runtime, "league_state", None)
    served_state_as_of = (
        league_state.as_of.isoformat()
        if league_state is not None
        else None
    )
    forecast_as_of = (
        runtime_result.evaluation_as_of.isoformat()
        if runtime_result is not None
        and getattr(runtime_result, "evaluation_as_of", None) is not None
        else None
    )
    simulation_context = (
        getattr(getattr(runtime, "simulation_analytics", None), "league_view", None)
    )
    simulation_context = getattr(simulation_context, "context", None)
    simulation_as_of = (
        simulation_context.as_of.isoformat()
        if simulation_context is not None
        and getattr(simulation_context, "as_of", None) is not None
        else None
    )
    value_as_of_candidates = [
        item.as_of
        for item in (
            tuple(getattr(value_evidence, "estimates", ()) or ())
            + tuple(getattr(value_evidence, "fsffl_cardinal_values", ()) or ())
        )
        if getattr(item, "as_of", None) is not None
    ]
    value_as_of = (
        max(value_as_of_candidates).isoformat()
        if value_as_of_candidates
        else None
    )

    statuses = (forecast_status, simulation_status, value_status)
    served = getattr(runtime, "served_intelligence", None)
    served_available = bool(
        served is not None
        and league_state is not None
        and served.league_id == league_state.league.league_id
        and served.league_state_id != league_state.state_id
    )
    served_publication_generation_id = (
        served.publication_generation_id
        if served_available
        else None
    )
    core_consumer_usable = (
        forecast_status in {"full", "non_material_partial", "partial_nonblocking"}
        and simulation_status == "full"
        and value_status == "full"
    )
    overall_status = (
        "rebuilding"
        if served_available
        else "full"
        if core_consumer_usable
        else "partial"
        if any(item != "unavailable" for item in statuses)
        else "unavailable"
    )
    return {
        "overall_status": overall_status,
        "forecast": {
            "status": forecast_status,
            "reason": forecast_reason,
            "raw_observation_count": len(raw_rows),
            "authoritative_scored_count": len(authoritative_rows),
            "partial_scored_count": len(partial_rows),
            "material_partial_player_ids": list(material_partial_player_ids),
            "non_material_partial_scored_count": len(
                non_material_partial_player_ids
            ),
            "non_material_partial_player_ids": list(
                non_material_partial_player_ids
            ),
            "scoring_coverage_full": not bool(partial_rows),
            "consumer_usable": forecast_status in {"full", "non_material_partial", "partial_nonblocking"},
            "simulation_blockers": list(blockers),
        },
        "simulation": {"status": simulation_status, "reason": simulation_reason},
        "current_value": {"status": value_status, "reason": value_reason},
        "as_of": served_state_as_of,
        "as_of_basis": "canonical_league_state",
        "as_of_detail": {
            "served_state": served_state_as_of,
            "forecast": forecast_as_of,
            "simulation": simulation_as_of,
            "current_value": value_as_of,
        },
        "intrinsic": {
            "status": "separate_surface",
            "reason": (
                "FSFFL Intrinsic has independent preserved-preseason Forecast authority "
                "and readiness; it is not inferred from current Value attachment."
            ),
        },
        "target_state": {
            "league_state_id": league_state.state_id if league_state is not None else None,
            "as_of": served_state_as_of,
            "status": (
                "rebuilding"
                if served_available
                else "current"
                if league_state is not None
                else "unavailable"
            ),
        },
        "served_last_good": {
            "available": served_available,
            "league_state_id": (
                served.league_state_id if served_available else None
            ),
            "as_of": (
                served.as_of.isoformat()
                if served_available
                else None
            ),
            "stale": served_available,
            "publication_generation_id": served_publication_generation_id,
            "label": (
                "Last-good intelligence remains visible while current State rebuilds."
                if served_available
                else None
            ),
        },
    }


def _cached_forecast_replay_decision(
    store: PrivateBetaRuntimeStore,
    user_id: str,
) -> dict[str, object] | None:
    """Expose replay diagnostics only when already cached in memory.

    First-load foreground reads must never acquire durable Forecast diagnostics.
    Background reconciliation owns persisted replay restoration and will populate the
    cache as soon as it determines exact reuse, raw replay, or fresh acquisition.
    """

    cached_reader = getattr(store, "forecast_replay_decision_cached", None)
    if callable(cached_reader):
        return cached_reader(user_id)
    reader = getattr(store, "forecast_replay_decision", None)
    return reader(user_id) if callable(reader) else None


def _runtime_context_payload(
    store: PrivateBetaRuntimeStore,
    user_id: str,
    *,
    capability_reader: CapabilityReadinessReader = _runtime_capability_readiness,
) -> dict[str, object]:
    runtime = store.get(user_id)
    league_state = runtime.league_state
    evidence = runtime.forecast_evidence
    simulation = runtime.simulation_analytics
    value_evidence = runtime.value_evidence
    capability_readiness = capability_reader(runtime)
    served = getattr(runtime, "served_intelligence", None)
    served_status = dict(capability_readiness.get("served_last_good") or {})
    served_available = bool(
        served is not None
        and league_state is not None
        and served.league_id == league_state.league.league_id
        and served.league_state_id != league_state.state_id
        and served_status.get("available") is True
    )
    served_presentation_available = served_status.get("presentation_available")
    served_visible = bool(
        served_available
        and served.publication_generation_id
        and served_presentation_available is not False
    )
    visible_publication_generation_id = (
        runtime.publication_generation_id
        or (
            served.publication_generation_id
            if served_visible
            else None
        )
    )
    return {
        "user_id": user_id,
        "league_id": league_state.league.league_id if league_state is not None else None,
        "league_name": league_state.league.name if league_state is not None else None,
        "team_id": runtime.selected_team_id,
        "state_id": league_state.state_id if league_state is not None else None,
        "evidence_as_of": league_state.as_of.isoformat() if league_state is not None else None,
        "teams": ([{"team_id": team.team_id, "display_name": team.display_name} for team in league_state.teams] if league_state is not None else []),
        "forecast_ready": (
            evidence is not None
            and bool(
                evidence.raw_forecasts
                or evidence.league_scored_forecasts
                or evidence.runtime_result.partial_fantasy_point_forecasts
            )
        ),
        "forecast_sources": list(evidence.successful_source_ids) if evidence is not None else [],
        "forecast_raw_observation_count": len(evidence.raw_forecasts) if evidence is not None else 0,
        "forecast_scored_player_count": len(evidence.league_scored_forecasts) if evidence is not None else 0,
        "forecast_partial_player_count": (
            len(evidence.runtime_result.partial_fantasy_point_forecasts)
            if evidence is not None
            else 0
        ),
        "forecast_family_coverage": (
            [
                item.model_dump(mode="json")
                for item in evidence.runtime_result.family_coverage
            ]
            if evidence is not None
            else []
        ),
        "forecast_simulation_blockers": (
            list(evidence.runtime_result.simulation_authority_blockers)
            if evidence is not None
            else []
        ),
        "simulation_ready": simulation is not None,
        "simulation_count": simulation.simulation_result.simulation_count if simulation is not None else None,
        "value_ready": value_evidence is not None and bool(value_evidence.estimates),
        "value_sources": list(value_evidence.successful_source_ids) if value_evidence is not None else [],
        "value_coverage": value_evidence.coverage if value_evidence is not None else None,
        "cardinal_value_ready": value_evidence is not None and bool(value_evidence.fsffl_cardinal_values),
        "cardinal_value_coverage": value_evidence.cardinal_player_coverage if value_evidence is not None else None,
        "capability_readiness": capability_readiness,
        "publication_generation_id": visible_publication_generation_id,
        "target_publication_generation_id": runtime.publication_generation_id,
        "forecast_replay_decision": _cached_forecast_replay_decision(
            store,
            user_id,
        ),
        "served_last_good": (
            {
                "available": True,
                "league_state_id": served.league_state_id,
                "as_of": served.as_of.isoformat(),
                "publication_generation_id": (
                    served.publication_generation_id if served_visible else None
                ),
                "stale": True,
            }
            if served_available
            else {
                "available": False,
                "league_state_id": None,
                "as_of": None,
                "publication_generation_id": None,
                "stale": False,
            }
        ),
        "product_version": "next8-product-v1",
    }


def _job_payload(job: IntelligenceJob | None) -> dict[str, object]:
    if job is None:
        return {
            "job_id": None,
            "status": "idle",
            "phase": "idle",
            "message": "No intelligence refresh is running.",
            "error": None,
            "failure_phase": None,
            "league_state_id": None,
            "created_at": None,
            "updated_at": None,
        }
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "phase": job.phase.value,
        "message": job.message,
        "error": job.error,
        "failure_phase": job.failure_phase.value if job.failure_phase is not None else None,
        "league_state_id": job.league_state_id,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


def _sleeper_external_id(league_state: LeagueState) -> str:
    for ref in league_state.league.provider_refs:
        if ref.provider == "sleeper":
            return ref.external_id
    prefix = "sleeper:"
    if league_state.league.league_id.startswith(prefix):
        return league_state.league.league_id[len(prefix):]
    raise ValueError("loaded league does not expose a Sleeper external id")


def _forecast_lineup_result(runtime):
    evidence = runtime.forecast_evidence
    if runtime.league_state is None or evidence is None or not evidence.league_scored_forecasts:
        return None
    forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
    return build_forecast_lineup_analytics(
        runtime.league_state,
        forecasts=forecasts,
        forecast_model_version=evidence.model_version,
    )


def _team_market_value_payload(value_evidence, team_id: str) -> dict[str, object] | None:
    if value_evidence is None:
        return None
    portfolio = next(
        (row for row in value_evidence.team_market_value_portfolios if row.team_id == team_id),
        None,
    )
    return portfolio.model_dump(mode="json") if portfolio is not None else None


def _attach_live_value_profiles(view, value_evidence):
    if value_evidence is None:
        return view
    profiles = {
        estimate.asset_id: AssetValueProfile(
            asset_id=estimate.asset_id,
            asset_kind=estimate.asset_kind,
            market_price=estimate,
        )
        for estimate in value_evidence.estimates
    }
    for score in getattr(value_evidence, "fsffl_cardinal_values", ()):
        if score.asset_kind != ValueAssetKind.PICK:
            continue
        profiles[score.asset_id] = AssetValueProfile(
            asset_id=score.asset_id,
            asset_kind=ValueAssetKind.PICK,
            market_price=MarketPriceEstimate(
                asset_id=score.asset_id,
                asset_kind=ValueAssetKind.PICK,
                distribution=ValueDistribution(mean=score.score),
                scale=score.scale,
                as_of=score.as_of,
                market_context_id=score.market_context_id,
                model_version=score.model_version,
                evidence_sources=(score.evidence_source_id,),
            ),
        )
    players = tuple(
        row.model_copy(update={"value_profile": profiles.get(row.player_id)})
        for row in view.players
    )
    draft_picks = tuple(
        row.model_copy(update={"value_profile": profiles.get(row.pick.pick_id)})
        for row in view.draft_picks
    )
    return view.model_copy(update={"players": players, "draft_picks": draft_picks})


def _team_view_payload(view, value_evidence, forecast_evidence=None) -> dict[str, object]:
    enriched = _attach_live_value_profiles(view, value_evidence)
    runtime_result = (
       …17922 tokens truncated…ntelligence/jobs")
    def start_intelligence_job(
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        refresh = active_hosted_refresh_payload(user_id)
        if refresh is not None:
            logging.getLogger("uvicorn.error").info(
                "FSFFL intelligence refresh joined active State sync job=%s",
                refresh["job_id"],
            )
            return {**runtime_context_payload(user_id), **refresh}
        return _start_intelligence_reconciliation(
            user_id,
            sync_state=True,
        )

    @application.get("/api/intelligence/jobs/current")
    def current_intelligence_job(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        refresh = active_hosted_refresh_payload(user_id)
        if refresh is not None:
            return {**runtime_context_payload(user_id), **refresh}
        resumed = resume_restart_interrupted_job(user_id)
        if resumed is not None:
            return {**runtime_context_payload(user_id), **resumed}
        return {**_job_payload(jobs.current(user_id)), **runtime_context_payload(user_id)}

    @application.post("/api/intelligence/refresh-forecasts")
    def refresh_forecasts(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        """Compatibility route: all manual refreshes use one State-first reconciler."""

        return _start_intelligence_reconciliation(
            user_id,
            sync_state=True,
        )

    @application.get("/api/values")
    def current_values(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        evidence = runtime.value_evidence
        if evidence is None:
            raise HTTPException(status_code=409, detail="Current NEXT-3 Value evidence is not loaded")
        player_names = {player.player_id: player.full_name for player in runtime.league_state.players}
        team_names = {team.team_id: team.display_name for team in runtime.league_state.teams}
        return {
            "league_state_id": evidence.league_state_id,
            "market_context_id": evidence.market_context_id,
            "model_version": evidence.model_version,
            "successful_sources": list(evidence.successful_source_ids),
            "failed_sources": list(evidence.failed_sources),
            "source_errors": evidence.errors_by_source_id,
            "roster_player_count": evidence.roster_player_count,
            "valued_roster_player_count": evidence.valued_roster_player_count,
            "coverage": evidence.coverage,
            "cardinal_player_coverage": evidence.cardinal_player_coverage,
            "team_market_value_portfolios": [
                {
                    **portfolio.model_dump(mode="json"),
                    "team_name": team_names.get(portfolio.team_id, portfolio.team_id),
                }
                for portfolio in evidence.team_market_value_portfolios
            ],
            "team_cardinal_portfolios": [
                {
                    **portfolio.model_dump(mode="json"),
                    "team_name": team_names.get(portfolio.team_id, portfolio.team_id),
                }
                for portfolio in evidence.team_cardinal_portfolios
            ],
            "estimates": [
                {
                    **estimate.model_dump(mode="json"),
                    "display_name": player_names.get(estimate.asset_id, estimate.asset_id),
                }
                for estimate in evidence.estimates
            ],
            "fsffl_cardinal_values": [
                {
                    **score.model_dump(mode="json"),
                    "display_name": player_names.get(score.asset_id, score.asset_id),
                }
                for score in evidence.fsffl_cardinal_values
            ],
            "provisional_fsffl_values": [
                {
                    **score.model_dump(mode="json"),
                    "display_name": player_names.get(score.asset_id, score.asset_id),
                }
                for score in evidence.provisional_fsffl_values
            ],
        }

    @application.get("/api/home")
    def home_north_star(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        """Compose Home strictly from already-attached governed evidence."""

        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if runtime.selected_team_id is None:
            raise HTTPException(status_code=409, detail="No managed team is selected")
        if presentation_payload_loader is not None:
            stale = presentation_payload_loader(user_id, runtime, "home")
            if stale is not None:
                return stale

        current_job = jobs.current(user_id)
        enrichment_running = bool(
            current_job is not None
            and current_job.status.value in {"queued", "running"}
        )
        team_view = _managed_team_view_payload(
            runtime,
            state_only_while_enriching=enrichment_running,
        )
        presentation_runtime = _presentation_runtime(runtime)
        atlas = build_league_atlas_payload(
            presentation_runtime,
            preseason_reason=(
                "Home intentionally does not resolve or reconstruct preseason evidence."
            ),
        )
        freshness = _intelligence_freshness(
            runtime,
            using_last_good=(presentation_runtime is not runtime),
        )
        return tag_publication_generation(runtime, {
            "status": "ready",
            "contract_version": "home-north-star-v1",
            "league_id": runtime.league_state.league.league_id,
            "league_state_id": runtime.league_state.state_id,
            "managed_team_id": runtime.selected_team_id,
            "intelligence_freshness": freshness,
            "team_view": team_view,
            "standings": atlas["standings"],
            "simulation": atlas["simulation"],
            "authority": {
                "state": "canonical point-in-time LeagueState",
                "team_view": (
                    "existing attached Simulation/Forecast/State team view; "
                    "Home launches no Forecast, Simulation, Value, Decision, or Search work"
                ),
                "simulation": "existing matching governed 50,000-run Simulation only",
                "position_strength": "existing league-relative position-strength evidence",
                "fragility": "existing Team Utility roster-resilience evidence",
                "presentation_creates_model_truth": False,
                "market_search_launched": False,
                "changed_state_simulation_launched": False,
            },
        })

    @application.get("/api/my-team")
    def my_team(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if presentation_payload_loader is not None:
            stale = presentation_payload_loader(user_id, runtime, "franchise")
            if stale is not None:
                return stale
        current_job = jobs.current(user_id)
        enrichment_running = bool(
            current_job is not None
            and current_job.status.value in {"queued", "running"}
        )
        try:
            return tag_publication_generation(
                runtime,
                _managed_team_view_payload(
                    runtime,
                    state_only_while_enriching=enrichment_running,
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/league/team-views")
    def league_team_views(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        """Expose league-wide read-only Analytics team views without changing user context."""

        runtime = store.get(user_id)
        league_state = runtime.league_state
        if league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if presentation_payload_loader is not None:
            stale = presentation_payload_loader(
                user_id,
                runtime,
                "league_team_views",
            )
            if stale is not None:
                return stale

        source_level: str
        if runtime.simulation_analytics is not None:
            views = runtime.simulation_analytics.team_views
            source_level = "simulation_analytics"
        else:
            lineup_result = _forecast_lineup_result(runtime)
            if lineup_result is not None:
                views = lineup_result.team_views
                source_level = "forecast_lineup_analytics"
            elif runtime.forecast_evidence is not None:
                evidence = runtime.forecast_evidence
                forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
                views = tuple(
                    build_forecast_team_view(
                        league_state,
                        team_id=team.team_id,
                        forecasts=forecasts,
                        forecast_model_version=evidence.model_version,
                    )
                    for team in sorted(league_state.teams, key=lambda item: item.team_id)
                )
                source_level = "forecast_team_views"
            else:
                views = tuple(
                    build_state_only_team_view(league_state, team_id=team.team_id)
                    for team in sorted(league_state.teams, key=lambda item: item.team_id)
                )
                source_level = "state_only"

        enriched = tuple(
            _attach_live_value_profiles(view, runtime.value_evidence)
            for view in views
        )
        freshness = _intelligence_freshness(
            runtime,
            using_last_good=False,
        )
        return tag_publication_generation(runtime, {
            "league_state_id": league_state.state_id,
            "intelligence_freshness": freshness,
            "as_of": league_state.as_of.isoformat(),
            "source_level": source_level,
            "team_market_value_portfolios": (
                [portfolio.model_dump(mode="json") for portfolio in runtime.value_evidence.team_market_value_portfolios]
                if runtime.value_evidence is not None
                else []
            ),
            "team_views": [view.model_dump(mode="json") for view in enriched],
        })

    @application.get("/api/league/atlas")
    def league_atlas(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        """Compose the scan-first League Atlas without creating new model authority."""

        runtime = store.get(user_id)
        league_state = runtime.league_state
        if league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if presentation_payload_loader is not None:
            stale = presentation_payload_loader(user_id, runtime, "league_atlas")
            if stale is not None:
                return stale

        preseason_views = None
        preseason_as_of = None
        preseason_reason = None
        preseason_baseline = load_preseason_baseline(
            persistence_store,
            state=league_state,
        )
        if preseason_baseline is None:
            if preseason_forecast_loader is None:
                preseason_reason = (
                    "Preserved preseason Forecast authority is not configured in this runtime."
                )
            elif state_snapshot_store is None:
                preseason_reason = (
                    "Historical point-in-time State storage is unavailable; preseason player "
                    "Forecast evidence is not enough to fabricate a team expectation."
                )
            else:
                try:
                    preseason_evidence = preseason_forecast_loader(league_state)
                    cutoff = preseason_evidence.runtime_result.evaluation_as_of
                    preseason_state = state_snapshot_store.latest_at_or_before(
                        league_state.league.league_id,
                        cutoff,
                    )
                    if preseason_state is None:
                        preseason_reason = (
                            "No canonical preseason State snapshot exists at or before the "
                            "preserved Forecast cutoff."
                        )
                    elif preseason_state.league.season != league_state.league.season:
                        preseason_reason = (
                            "The available historical State snapshot belongs to a different season."
                        )
                    elif completed_matchups(preseason_state):
                        preseason_reason = (
                            "No exact pre-kickoff 2026 State can be proven: the earliest canonical "
                            "State is post-opener, and captured transaction history does not preserve "
                            "historical TAXI/IR/active-slot moves needed to prove lineup eligibility. "
                            "Current rosters are never backfilled."
                        )
                    elif not preseason_evidence.uncertainty_ready:
                        preseason_reason = (
                            "The preserved pre-kickoff Forecast does not carry governed uncertainty "
                            "needed for the 50,000-run preseason Simulation."
                        )
                    else:
                        reconstructed = simulation_loader(
                            preseason_state,
                            preseason_evidence,
                        )
                        preseason_baseline = capture_preseason_baseline_if_eligible(
                            persistence_store,
                            state=preseason_state,
                            forecast=preseason_evidence,
                            simulation=reconstructed,
                        )
                        if preseason_baseline is None:
                            preseason_reason = (
                                "A compatible pregame State + Forecast exists, but the governed "
                                "opener coordinate required to freeze a no-hindsight preseason "
                                "baseline is unavailable."
                            )
                except Exception as exc:
                    preseason_reason = (
                        "Frozen preseason team expectation unavailable: "
                        f"{type(exc).__name__}: {exc}"
                    )

        presentation_runtime = _presentation_runtime(runtime)
        origin_aware_pick_values = ()
        if (
            presentation_runtime.league_state is not None
            and presentation_runtime.simulation_analytics is not None
        ):
            origin_aware_pick_values = build_live_origin_aware_pick_values(
                presentation_runtime.league_state,
                presentation_runtime.simulation_analytics.simulation_result,
            )
        atlas_payload = build_league_atlas_payload(
            presentation_runtime,
            preseason_team_views=preseason_views,
            preseason_as_of=preseason_as_of,
            preseason_reason=preseason_reason,
            preseason_baseline=preseason_baseline,
            origin_aware_pick_values=origin_aware_pick_values,
        )
        atlas_payload["intelligence_freshness"] = _intelligence_freshness(
            runtime,
            using_last_good=(presentation_runtime is not runtime),
        )
        logging.getLogger("uvicorn.error").info(
            "FSFFL League Atlas served state=%s standings=%s simulation=%s preseason=%s",
            league_state.state_id,
            len(atlas_payload.get("standings", ())),
            runtime.simulation_analytics is not None,
            atlas_payload.get("preseason_status"),
        )
        return tag_publication_generation(runtime, atlas_payload)

    @application.get("/api/opportunities/workspace")
    def opportunity_workspace(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if presentation_payload_loader is not None:
            stale = presentation_payload_loader(
                user_id,
                runtime,
                "market_workspace",
            )
            if stale is not None:
                return stale
        try:
            # Ordinary Market navigation is presentation/read authority only.
            # Full structural Search and bilateral Decision work are explicit
            # progressive actions and must never execute on this GET.
            return tag_publication_generation(
                runtime,
                build_opportunity_workspace(
                    runtime,
                    candidate_limit=0,
                    bilateral_evaluation_limit=0,
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/opportunities/waiver")
    def evaluate_waiver(request: EvaluateWaiverRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if runtime.selected_team_id is None:
            raise HTTPException(status_code=409, detail="No managed team is selected")
        move = WaiverMove(
            focal_team_id=runtime.selected_team_id,
            add_player_id=request.add_player_id,
            drop_player_id=request.drop_player_id,
        )
        try:
            return build_actionable_waiver_comparison(
                runtime,
                move,
                simulation_loader=simulation_loader,
                scenario_stage=request.scenario_stage,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/opportunities/trade")
    def evaluate_trade_opportunity(request: AnalyzeTradeRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        try:
            proposal = _proposal_from_request(
                runtime,
                request,
                draft_prefix="opportunity-trade",
            )
            return build_trade_opportunity_evaluation(
                runtime,
                proposal,
                focal_team_id=runtime.selected_team_id,
                simulation_loader=simulation_loader,
                scenario_stage=request.scenario_stage,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/what-if/player-unavailable")
    def player_unavailable_what_if(request: PlayerUnavailableRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        try:
            return build_player_unavailable_scenario(
                runtime,
                player_id=request.player_id,
                simulation_loader=simulation_loader,
                scenario_stage=request.scenario_stage,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/trade-center/browser")
    def trade_center_browser(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if runtime.selected_team_id is None:
            raise HTTPException(status_code=409, detail="No managed team is selected")
        return build_trade_center_browser_view(runtime.league_state, focal_team_id=runtime.selected_team_id).model_dump(mode="json")

    @application.post("/api/trade-center/analyze")
    def analyze_trade(request: AnalyzeTradeRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if runtime.selected_team_id is None:
            raise HTTPException(status_code=409, detail="No managed team is selected")
        try:
            proposal = _proposal_from_request(runtime, request, draft_prefix="product")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if trade_evaluator is not None:
            return trade_evaluator(runtime.league_state, proposal, runtime.selected_team_id)
        try:
            return build_private_beta_trade_analysis(
                runtime,
                proposal,
                focal_team_id=runtime.selected_team_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @application.post("/api/trade-center/frontier")
    def explore_trade_frontier(request: AnalyzeTradeRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        try:
            proposal = _proposal_from_request(
                runtime,
                request,
                draft_prefix="product-frontier",
            )
            return build_negotiation_frontier(
                runtime,
                proposal,
                focal_team_id=runtime.selected_team_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @application.post("/api/trade-center/simulate")
    def simulate_trade(request: AnalyzeTradeRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        try:
            proposal = _proposal_from_request(
                runtime,
                request,
                draft_prefix="product-simulation",
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            return build_post_trade_simulation_comparison(
                runtime,
                proposal,
                focal_team_id=runtime.selected_team_id,
                simulation_loader=simulation_loader,
                scenario_stage=request.scenario_stage,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/league/chart")
    def league_chart(metric: LeagueMetric, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        view = league_view_provider() if league_view_provider is not None else None
        if view is None:
            runtime = store.get(user_id)
            if runtime.league_state is None:
                raise HTTPException(status_code=409, detail="No league is loaded")
            if runtime.simulation_analytics is not None:
                view = runtime.simulation_analytics.league_view
            else:
                lineup_result = _forecast_lineup_result(runtime)
                view = lineup_result.league_view if lineup_result is not None else build_state_only_league_view(runtime.league_state)
        return build_league_metric_chart(view, metric=metric).model_dump(mode="json")

    return application


app = create_app()

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
    IntelligenceJobBusy,
    IntelligenceJobInterrupted,
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)
from .behavioral_runtime import BehavioralRuntimeCoordinator, BehavioralRuntimeStatus
from .dashboard import build_league_metric_chart
from .current_position_depth import (
    CurrentPositionDepthContract,
    unavailable_current_position_depth,
)
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
CurrentPositionDepthProvider = Callable[[LeagueState], CurrentPositionDepthContract]
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
    runtime_context: UserRuntimeContext | None = None,
) -> dict[str, object]:
    runtime = runtime_context or store.get(user_id)
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
        forecast_evidence.runtime_result
        if forecast_evidence is not None
        else None
    )
    return {
        **enriched.model_dump(mode="json"),
        "team_market_value": _team_market_value_payload(value_evidence, enriched.team_id),
        "forecast_authority": {
            "evidence_basis": (
                forecast_evidence.evidence_basis
                if forecast_evidence is not None
                else None
            ),
            "evidence_model_version": (
                forecast_evidence.model_version
                if forecast_evidence is not None
                else None
            ),
            "runtime_model_version": (
                runtime_result.model_version
                if runtime_result is not None
                else None
            ),
            "evaluation_as_of": (
                runtime_result.evaluation_as_of.isoformat()
                if runtime_result is not None
                else None
            ),
            "successful_source_ids": (
                list(forecast_evidence.successful_source_ids)
                if forecast_evidence is not None
                else []
            ),
            "failed_sources": (
                list(forecast_evidence.failed_sources)
                if forecast_evidence is not None
                else []
            ),
            "fallback_active": (
                forecast_evidence is not None
                and forecast_evidence.evidence_basis == "preseason_baseline"
            ),
        },
    }


def _presentation_runtime(runtime):
    """Presentation uses current runtime unless shared persisted continuity resolves first."""

    return runtime


def _intelligence_freshness(
    runtime,
    *,
    using_last_good: bool,
) -> dict[str, object]:
    current = runtime.league_state
    served = getattr(runtime, "served_intelligence", None)
    return {
        "status": "stale_last_good" if using_last_good else "current",
        "stale": using_last_good,
        "target_state_id": current.state_id if current is not None else None,
        "target_as_of": current.as_of.isoformat() if current is not None else None,
        "served_state_id": (
            served.league_state_id
            if using_last_good and served is not None
            else (current.state_id if current is not None else None)
        ),
        "served_as_of": (
            served.as_of.isoformat()
            if using_last_good and served is not None
            else (current.as_of.isoformat() if current is not None else None)
        ),
        "message": (
            "Last-good governed presentation is being served while exact-State "
            "intelligence rebuilds."
            if using_last_good
            else "Derived presentation matches the current canonical State."
        ),
    }


def _managed_team_view_payload(
    runtime,
    *,
    state_only_while_enriching: bool = False,
) -> dict[str, object]:
    """Return the strongest already-attached managed-team view without launching new work.

    On the first governed enrichment, there may be no completed Simulation bundle to
    serve yet. While that background job is active, prefer the cheap canonical
    State-only team view instead of rebuilding forecast-lineup analytics on every
    foreground read. This is presentation/read-path degradation only; it does not
    change Forecast, Simulation, Value, or the pending intelligence bundle.
    """

    if runtime.league_state is None:
        raise ValueError("No league is loaded")
    if runtime.selected_team_id is None:
        raise ValueError("No managed team is selected")
    if runtime.simulation_analytics is not None:
        view = next(
            item
            for item in runtime.simulation_analytics.team_views
            if item.team_id == runtime.selected_team_id
        )
        payload = _team_view_payload(view, runtime.value_evidence, runtime.forecast_evidence)
        payload["intelligence_freshness"] = _intelligence_freshness(runtime, using_last_good=False)
        return payload
    if state_only_while_enriching:
        view = build_state_only_team_view(
            runtime.league_state,
            team_id=runtime.selected_team_id,
        )
        payload = _team_view_payload(view, runtime.value_evidence)
        payload["intelligence_freshness"] = _intelligence_freshness(runtime, using_last_good=False)
        return payload
    lineup_result = _forecast_lineup_result(runtime)
    if lineup_result is not None:
        view = next(
            item
            for item in lineup_result.team_views
            if item.team_id == runtime.selected_team_id
        )
        payload = _team_view_payload(view, runtime.value_evidence)
        payload["intelligence_freshness"] = _intelligence_freshness(runtime, using_last_good=False)
        return payload
    if runtime.forecast_evidence is not None:
        evidence = runtime.forecast_evidence
        forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
        view = build_forecast_team_view(
            runtime.league_state,
            team_id=runtime.selected_team_id,
            forecasts=forecasts,
            forecast_model_version=evidence.model_version,
        )
        payload = _team_view_payload(view, runtime.value_evidence)
        payload["intelligence_freshness"] = _intelligence_freshness(runtime, using_last_good=False)
        return payload
    view = build_state_only_team_view(
        runtime.league_state,
        team_id=runtime.selected_team_id,
    )
    payload = _team_view_payload(view, runtime.value_evidence)
    payload["intelligence_freshness"] = _intelligence_freshness(runtime, using_last_good=False)
    return payload


def _build_default_simulation(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
    *,
    simulation_count: int,
    scenario_reuse=None,
    affected_team_ids: frozenset[str] | None = None,
    reuse_simulation_result=None,
) -> LiveSimulationAnalyticsResult:
    rng_protocol, rng_batch_size = configured_simulation_rng()
    return build_live_simulation_analytics(
        league_state,
        forecasts=evidence.league_scored_forecasts,
        forecast_model_version=evidence.model_version,
        simulation_count=simulation_count,
        rng_protocol=rng_protocol,
        rng_batch_size=rng_batch_size,
        cooperative_yield=foreground_pressure.cooperative_yield,
        scenario_reuse=scenario_reuse,
        affected_team_ids=affected_team_ids,
        reuse_simulation_result=reuse_simulation_result,
    )


def _default_simulation_loader(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
) -> LiveSimulationAnalyticsResult:
    return _build_default_simulation(
        league_state,
        evidence,
        simulation_count=50_000,
    )


def _selective_runner_for_count(simulation_count: int):
    def run(changed_state, evidence, baseline_result, plan, reuse_canonical):
        return _build_default_simulation(
            changed_state,
            evidence,
            simulation_count=(
                baseline_result.simulation_result.simulation_count
                if reuse_canonical
                else simulation_count
            ),
            scenario_reuse=baseline_result.scenario_preparation,
            affected_team_ids=frozenset(plan.affected_team_ids),
            reuse_simulation_result=(
                baseline_result.simulation_result if reuse_canonical else None
            ),
        )

    return run


def _progressive_loader_factory(simulation_count: int, stage_label: str):
    def loader(
        league_state: LeagueState,
        evidence: LiveForecastEvidence,
    ) -> LiveSimulationAnalyticsResult:
        return _build_default_simulation(
            league_state,
            evidence,
            simulation_count=simulation_count,
        )

    loader.__fsffl_cache_identity__ = (
        f"{configured_simulation_cache_identity()}:scenario-stage={stage_label}:"
        f"count={simulation_count}"
    )
    loader.__fsffl_simulation_model_version__ = (
        f"{configured_simulation_model_version()}:scenario-stage={stage_label}:"
        f"count={simulation_count}"
    )
    loader.__fsffl_selective_runner__ = _selective_runner_for_count(simulation_count)
    return loader


_default_simulation_loader.__fsffl_cache_identity__ = configured_simulation_cache_identity()
_default_simulation_loader.__fsffl_simulation_model_version__ = configured_simulation_model_version()
_default_simulation_loader.__fsffl_progressive_loader_factory__ = _progressive_loader_factory
_default_simulation_loader.__fsffl_selective_runner__ = _selective_runner_for_count(50_000)


def _proposal_from_request(runtime, request: AnalyzeTradeRequest, *, draft_prefix: str) -> BilateralTradeProposal:
    if runtime.league_state is None:
        raise ValueError("No league is loaded")
    if runtime.selected_team_id is None:
        raise ValueError("No managed team is selected")
    if request.counterparty_team_id == runtime.selected_team_id:
        raise ValueError("Trade counterparty must be a different team")
    focal_assets = tuple(
        resolve_owned_asset_ref(
            runtime.league_state,
            team_id=runtime.selected_team_id,
            asset_ref=ref,
        )
        for ref in request.focal_asset_refs
    )
    counterparty_assets = tuple(
        resolve_owned_asset_ref(
            runtime.league_state,
            team_id=request.counterparty_team_id,
            asset_ref=ref,
        )
        for ref in request.counterparty_asset_refs
    )
    draft = TradeDraft(
        draft_id=(
            f"{draft_prefix}:{runtime.league_state.state_id}:"
            f"{runtime.selected_team_id}:{request.counterparty_team_id}"
        ),
        focal_team_id=runtime.selected_team_id,
        counterparty_team_id=request.counterparty_team_id,
        focal_side=TradeDraftSide(team_id=runtime.selected_team_id, assets=focal_assets),
        counterparty_side=TradeDraftSide(
            team_id=request.counterparty_team_id,
            assets=counterparty_assets,
        ),
    )
    return submit_trade_draft(draft, as_of=runtime.league_state.as_of)


def create_app(
    *,
    league_view_provider: LeagueViewProvider | None = None,
    runtime_store: PrivateBetaRuntimeStore | None = None,
    state_loader: StateLoader = default_sleeper_state_loader,
    forecast_loader: LiveForecastLoader = default_live_forecast_loader,
    preseason_forecast_loader: LiveForecastLoader | None = None,
    state_snapshot_store: StateSnapshotStore | None = None,
    persistence_store: PersistenceStore | None = None,
    simulation_loader: SimulationLoader = _default_simulation_loader,
    value_loader: LiveValueLoader = default_live_value_loader,
    trade_evaluator: TradeEvaluator | None = None,
    behavioral_coordinator: BehavioralRuntimeCoordinator | None = None,
    capability_readiness_reader: CapabilityReadinessReader | None = None,
    product_capability_reconciler: ProductCapabilityReconciler | None = None,
    heavy_work_coordinator: HeavyWorkCoordinator | None = None,
    presentation_payload_loader: PresentationPayloadLoader | None = None,
    current_position_depth_provider: CurrentPositionDepthProvider | None = None,
    state_resource_boundary: StateResourceBoundaryHandler | None = None,
    state_transition_reclaimer: RuntimeMemoryReclaimer | None = None,
    phase_memory_reclaimer: RuntimeMemoryReclaimer | None = None,
) -> FastAPI:
    application = FastAPI(title="FSFFL NEXT Private Beta", version="next8-beta-v1", docs_url="/api/docs", redoc_url=None)
    store = runtime_store or PrivateBetaRuntimeStore()
    jobs = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence_store)
    reconciliation_lock = RLock()
    reconciliation_league_by_user: dict[str, str] = {}
    reconciliation_generation_by_user: dict[str, int] = {}
    behavior_jobs = behavioral_coordinator or BehavioralRuntimeCoordinator(max_workers=2)
    base_read_capabilities = capability_readiness_reader or _runtime_capability_readiness

    def read_capabilities(
        runtime,
        *,
        presentation_payload=None,
        presentation_resolved: bool = False,
    ) -> dict[str, object]:
        """Bind readiness to the immutable published generation, never working state."""

        if presentation_resolved:
            # The hosted reader supplies the result from the same exact manifest
            # resolution that loaded this surface. Generic app compositions retain
            # their one-argument readiness callback contract.
            try:
                payload = dict(
                    base_read_capabilities(
                        runtime,
                        presentation_payload=presentation_payload,
                        presentation_resolved=True,
                    )
                )
            except TypeError as exc:
                if "unexpected keyword argument" not in str(exc):
                    raise
                payload = dict(base_read_capabilities(runtime))
        else:
            payload = dict(base_read_capabilities(runtime))
        working_active = store.working_generation_active(runtime.user_id)
        target_state_id = store.working_target_state_id(runtime.user_id)
        target_generation_id = getattr(
            runtime,
            "publication_generation_id",
            None,
        )
        served = getattr(runtime, "served_intelligence", None)
        served_status = dict(payload.get("served_last_good") or {})
        served_visible = bool(
            target_generation_id is None
            and served is not None
            and runtime.league_state is not None
            and served.league_id == runtime.league_state.league.league_id
            and served.league_state_id != runtime.league_state.state_id
            and served.publication_generation_id
            and served_status.get("available") is True
            and served_status.get("presentation_available") is not False
        )
        published_generation_id = (
            target_generation_id
            or (
                served.publication_generation_id
                if served_visible
                else None
            )
        )
        payload["publication_generation_id"] = published_generation_id
        payload["publication"] = {
            "generation_id": published_generation_id,
            "target_generation_id": target_generation_id,
            "league_state_id": (
                served.league_state_id
                if served_visible
                else (
                    runtime.league_state.state_id
                    if runtime.league_state is not None
                    else None
                )
            ),
            "working_generation_active": working_active,
            "target_state_id": target_state_id,
            "status": (
                "serving_last_good_during_update"
                if working_active and served_visible
                else "serving_published_during_update"
                if working_active
                else "published"
                if runtime.league_state is not None
                else "unavailable"
            ),
        }
        if working_active:
            target = dict(payload.get("target_state") or {})
            target["league_state_id"] = target_state_id
            target["status"] = "rebuilding"
            payload["target_state"] = target
            payload["reconciliation"] = {
                "status": "running",
                "target_state_id": target_state_id,
                "published_state_id": (
                    runtime.league_state.state_id
                    if runtime.league_state is not None
                    else None
                ),
            }
            if (
                runtime.league_state is not None
                and target_state_id is not None
                and target_state_id != runtime.league_state.state_id
            ):
                served = dict(payload.get("served_last_good") or {})
                served.update(
                    available=True,
                    league_state_id=runtime.league_state.state_id,
                    as_of=runtime.league_state.as_of.isoformat(),
                    stale=True,
                    label=(
                        "Updating intelligence — serving the prior published generation."
                    ),
                )
                payload["served_last_good"] = served
        else:
            payload["reconciliation"] = {
                "status": "idle",
                "target_state_id": None,
                "published_state_id": (
                    runtime.league_state.state_id
                    if runtime.league_state is not None
                    else None
                ),
            }
        return payload

    def heavy_claim(kind: str, key: str):
        if heavy_work_coordinator is None:
            return nullcontext()
        return heavy_work_coordinator.claim(kind=kind, key=key)

    def reclaim_phase_memory(label: str) -> None:
        if phase_memory_reclaimer is not None:
            phase_memory_reclaimer(label)

    def log_reconciliation_memory(user_id: str, phase: str) -> None:
        """Record RSS at lifecycle boundaries in the hosted application log."""

        snapshot = (
            heavy_work_coordinator.snapshot()
            if heavy_work_coordinator is not None
            else None
        )
        logging.getLogger("uvicorn.error").info(
            "FSFFL intelligence memory phase=%s current_rss=%s peak_rss=%s active=%s waiting=%s budget=%s",
            phase,
            snapshot.current_rss_bytes if snapshot is not None else current_rss_bytes(),
            snapshot.peak_rss_bytes if snapshot is not None else process_peak_rss_bytes(),
            snapshot.active_kind if snapshot is not None else None,
            snapshot.waiting_count if snapshot is not None else None,
            snapshot.memory_budget_bytes if snapshot is not None else None,
        )

    def apply_state_resource_boundary(
        user_id: str,
        *,
        previous: UserRuntimeContext,
        next_state: LeagueState,
        next_team_id: str | None,
        reason: str,
    ) -> object | None:
        previous_state = previous.league_state
        if previous_state is None or previous_state.state_id == next_state.state_id:
            return None
        transition = ResourceTransition(
            user_id=user_id,
            reason=reason,
            previous_league_id=previous_state.league.league_id,
            previous_state_id=previous_state.state_id,
            previous_team_id=previous.selected_team_id,
            next_league_id=next_state.league.league_id,
            next_state_id=next_state.state_id,
            next_team_id=next_team_id,
        )
        if state_resource_boundary is not None:
            return state_resource_boundary(transition)
        # Compatibility fallback for generic/test composition. Hosted production
        # wires the single governed StateResourceBoundary.
        label = f"{reason}:{next_state.state_id}"
        if state_transition_reclaimer is not None:
            return state_transition_reclaimer(label)
        if phase_memory_reclaimer is not None:
            return phase_memory_reclaimer(label)
        return None

    def activate_state_with_resource_boundary(
        user_id: str,
        league_state: LeagueState,
        *,
        reason: str,
        expected_generation: int | None = None,
        expected_league_id: str | None = None,
    ) -> UserRuntimeContext | None:
        # State authority and process-resource ownership are one same-user lifecycle
        # sequence. A later B->C transition cannot become canonical between B's
        # activation and B's cleanup/revalidation, then have the older B transition
        # resume and evict C-owned execution state.
        with store.lifecycle_operation(user_id):
            previous = store.get(user_id)
            if expected_generation is None:
                fast_connect_activation = (
                    getattr(store, "activate_league_state_for_connect", None)
                    if reason in {"background_connect", "synchronous_connect"}
                    else None
                )
                if callable(fast_connect_activation):
                    activated = fast_connect_activation(user_id, league_state)
                else:
                    store.set_league_state(user_id, league_state)
                    activated = store.get(user_id)
            else:
                conditional = getattr(store, "set_league_state_if_generation", None)
                if not callable(conditional):
                    raise RuntimeError(
                        "conditional State activation requires generation-aware runtime store"
                    )
                result = conditional(
                    user_id,
                    league_state,
                    expected_generation=expected_generation,
                    expected_league_id=expected_league_id,
                )
                if result is None:
                    return None
                activated = store.get(user_id)

            apply_state_resource_boundary(
                user_id,
                previous=previous,
                next_state=league_state,
                next_team_id=activated.selected_team_id,
                reason=reason,
            )
            current = store.get(user_id)
            if (
                current.league_state is None
                or current.league_state.state_id != league_state.state_id
                or current.selected_team_id != activated.selected_team_id
            ):
                return None
            return current

    def runtime_context_payload(
        user_id: str,
        *,
        presentation_surface: str | None = None,
    ) -> dict[str, object]:
        runtime = store.get(user_id)
        presentation_resolved = bool(
            presentation_surface and presentation_payload_loader is not None
        )
        presentation = (
            presentation_payload_loader(user_id, runtime, presentation_surface)
            if presentation_resolved
            else None
        )
        payload = _runtime_context_payload(
            store,
            user_id,
            capability_reader=lambda context: read_capabilities(
                context,
                presentation_payload=presentation,
                presentation_resolved=presentation_resolved,
            ),
            runtime_context=runtime,
        )
        if presentation_surface:
            # This response is consumed once by the active surface during boot or
            # rehydration. No mutable manifest is retained between HTTP requests.
            payload["presentation_payload"] = presentation
        return payload

    def tag_publication_generation(
        runtime: UserRuntimeContext,
        payload: dict[str, object],
    ) -> dict[str, object]:
        generation_id = runtime.publication_generation_id
        if generation_id is None:
            return payload
        tagged = dict(payload)
        tagged["publication_generation_id"] = generation_id
        return tagged

    def presentation_payload(
        user_id: str,
        runtime: UserRuntimeContext,
        surface: str,
        builder: Callable[[], dict[str, object]],
    ) -> dict[str, object]:
        if presentation_payload_loader is not None:
            stale = presentation_payload_loader(user_id, runtime, surface)
            if stale is not None:
                return stale
        return tag_publication_generation(runtime, builder())

    def publish_working_generation(
        user_id: str,
        *,
        expected_generation: int | None = None,
        expected_league_id: str | None = None,
    ) -> UserRuntimeContext:
        """Durably compose one owned working generation, then expose it in one swap."""

        # Prepare any presentation-only dependency before taking the publication
        # sequence lock. A slow shadow restore/build must never block team/league
        # lifecycle changes; ownership is revalidated under the lock below.
        preparer = getattr(application.state, "presentation_preparer", None)
        if callable(preparer):
            preparer(user_id, store.working_context(user_id))

        # Team/league identity changes serialize against the final atomic sequence.
        # Revalidate the worker's ownership *inside* that serialization boundary so
        # an older job can never checkpoint/promote/publish a newer job's generation.
        with store.publication_sequence(user_id):
            published_identity = store.get(user_id)
            if (
                expected_generation is not None
                and store.league_generation(user_id) != expected_generation
            ):
                raise IntelligenceJobInterrupted("league_switch")
            if (
                expected_league_id is not None
                and (
                    published_identity.league_state is None
                    or published_identity.league_state.league.league_id
                    != expected_league_id
                )
            ):
                raise IntelligenceJobInterrupted("league_switch")
            working = store.working_context(user_id)
            if working.league_state is None:
                raise RuntimeError("working intelligence generation has no LeagueState")

            checkpoint = getattr(store, "checkpoint_working_generation", None)
            if callable(checkpoint) and not checkpoint(user_id):
                raise RuntimeError(
                    "Working intelligence generation could not be durably checkpointed"
                )

            promoter = getattr(application.state, "presentation_promoter", None)
            if callable(promoter):
                with store.read_context(user_id, working):
                    result = promoter(user_id, working)
                if result is None:
                    raise RuntimeError(
                        "Published presentation generation could not be durably promoted"
                    )
                generation_id = str(result.publication_generation_id)
            else:
                generation_id = (
                    f"runtime:{working.league_state.state_id}:{uuid4().hex}"
                )

            published = store.publish_working_generation(
                user_id,
                publication_generation_id=generation_id,
            )
            wait_for_checkpoint = getattr(store, "wait_for_checkpoint", None)
            if callable(wait_for_checkpoint) and not wait_for_checkpoint(
                user_id,
                timeout=180.0,
            ):
                raise RuntimeError(
                    "Published intelligence generation could not be durably checkpointed"
                )
            return published

    application.mount(
        "/static",
        ContentFingerprintStaticFiles(directory=_STATIC_DIR),
        name="static",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "product": "fsffl-next", "version": "next8-beta-v1"}

    @application.get("/")
    def index(_: str = Depends(require_beta_user)) -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    @application.get("/api/product-context")
    def product_context(
        presentation_surface: str | None = None,
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        runtime_payload = runtime_context_payload(
            user_id,
            presentation_surface=presentation_surface,
        )
        if runtime_payload["league_id"] is not None:
            return runtime_payload
        view = league_view_provider() if league_view_provider is not None else None
        if view is None:
            return runtime_payload
        return {**runtime_payload, "league_id": view.context.league_id, "state_id": view.context.league_state_id, "evidence_as_of": view.context.as_of.isoformat()}

    @application.get("/api/forecast/current/coverage")
    def current_forecast_coverage(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        """Expose shared Forecast population separately from downstream authority."""

        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        evidence = runtime.forecast_evidence
        if evidence is None:
            raise HTTPException(status_code=409, detail="Current Forecast evidence is not loaded")
        player_names = {
            player.player_id: player.full_name
            for player in runtime.league_state.players
        }
        return {
            "league_id": runtime.league_state.league.league_id,
            "league_state_id": runtime.league_state.state_id,
            "evidence_basis": evidence.evidence_basis,
            "successful_sources": list(evidence.successful_source_ids),
            "failed_sources": list(evidence.failed_sources),
            "raw_observation_count": len(evidence.raw_forecasts),
            "authoritative_scored_count": len(evidence.league_scored_forecasts),
            "partial_scored_count": len(
                evidence.runtime_result.partial_fantasy_point_forecasts
            ),
            "family_coverage": [
                item.model_dump(mode="json")
                for item in evidence.runtime_result.family_coverage
            ],
            "simulation_authority_blockers": list(
                evidence.runtime_result.simulation_authority_blockers
            ),
            "simulation_material_partial_player_ids": list(
                evidence.runtime_result.simulation_material_partial_player_ids
            ),
            "partial_forecasts": [
                {
                    **item.model_dump(mode="json"),
                    "display_name": player_names.get(item.player_id, item.player_id),
                }
                for item in evidence.runtime_result.partial_fantasy_point_forecasts
            ],
        }

    @application.get("/api/intelligence/status")
    def intelligence_status(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        evidence = runtime.forecast_evidence
        message = None
        if evidence is not None:
            if evidence.evidence_basis == "preseason_baseline":
                message = (
                    "Governed preserved preseason Forecast authority is in use after "
                    "the live full-season refresh failed or was quarantined; preserved "
                    "sources: " + ", ".join(evidence.successful_source_ids) + "."
                )
            else:
                message = (
                    "Authoritative NEXT-2 ensemble loaded from independent sources: "
                    + ", ".join(evidence.successful_source_ids) + "."
                )
        forecast_ready = bool(
            evidence is not None
            and (
                evidence.raw_forecasts
                or evidence.league_scored_forecasts
                or evidence.runtime_result.partial_fantasy_point_forecasts
            )
        )
        if evidence is not None and evidence.runtime_result.simulation_authority_blockers:
            message = (
                "Canonical shared Forecast evidence is populated. Full downstream "
                "Simulation authority remains blocked by: "
                + ", ".join(evidence.runtime_result.simulation_authority_blockers)
                + "."
            )
        payload = state_first_runtime_status(
            runtime.league_state,
            forecast_ready=forecast_ready,
            forecast_message=message,
        ).model_dump(mode="json")
        payload["forecast_evidence_basis"] = evidence.evidence_basis if evidence is not None else None
        payload["forecast_failed_sources"] = list(evidence.failed_sources) if evidence is not None else []
        payload["forecast_raw_observation_count"] = len(evidence.raw_forecasts) if evidence is not None else 0
        payload["forecast_scored_player_count"] = len(evidence.league_scored_forecasts) if evidence is not None else 0
        payload["forecast_partial_player_count"] = (
            len(evidence.runtime_result.partial_fantasy_point_forecasts)
            if evidence is not None
            else 0
        )
        payload["forecast_family_coverage"] = (
            [
                item.model_dump(mode="json")
                for item in evidence.runtime_result.family_coverage
            ]
            if evidence is not None
            else []
        )
        payload["forecast_simulation_blockers"] = (
            list(evidence.runtime_result.simulation_authority_blockers)
            if evidence is not None
            else []
        )
        value_ready = runtime.value_evidence is not None and bool(runtime.value_evidence.estimates)
        for stage in payload["stages"]:
            if stage["stage"] == "value" and value_ready:
                stage["readiness"] = "ready"
                stage["message"] = "Governed NEXT-3 current market values are attached from authoritative market evidence."
            if runtime.simulation_analytics is not None:
                if stage["stage"] == "team_utility":
                    stage["readiness"] = "ready"
                    stage["message"] = "NEXT-4 50,000-run competitive simulation is attached from calibrated forecast evidence."
                elif stage["stage"] == "analytics":
                    stage["readiness"] = "ready"
                    stage["message"] = "NEXT-7 includes projected scoring, expected wins and playoff/first-place probabilities."
        behavior = behavior_jobs.current(user_id)
        payload["behavioral_intelligence"] = {
            "status": behavior.status.value,
            "profile_count": behavior.result.profile_count if behavior.result is not None else 0,
            "event_count": behavior.result.total_event_count if behavior.result is not None else 0,
            "reused_historical_seasons": len(behavior.result.reused_historical_league_ids) if behavior.result is not None else 0,
            "error": behavior.error,
        }
        selected_team_state = next(
            (
                row
                for row in runtime.league_state.team_states
                if row.team_id == runtime.selected_team_id
            ),
            None,
        )
        current_job = jobs.current(user_id)
        failure_stage_by_phase = {
            IntelligenceJobPhase.BUILDING_FORECASTS: "forecast",
            IntelligenceJobPhase.REFRESHING_STATE: "state_refresh",
            IntelligenceJobPhase.RUNNING_SIMULATION: "simulation",
            IntelligenceJobPhase.BUILDING_VALUES: "value",
            IntelligenceJobPhase.BUILDING_INTRINSIC: "intrinsic",
            IntelligenceJobPhase.ATTACHING_RESULTS: "promotion",
        }
        blocked_stage = (
            failure_stage_by_phase.get(current_job.failure_phase)
            if current_job is not None
            and current_job.status in {IntelligenceJobStatus.FAILED, IntelligenceJobStatus.INTERRUPTED}
            else None
        )
        if blocked_stage == "forecast":
            for stage in payload["stages"]:
                if stage["stage"] == "forecast":
                    stage["readiness"] = "blocked"
                    stage["message"] = (
                        "Current Forecast authority is blocked by governed source-health / "
                        "scoring-coverage requirements. Canonical roster State remains usable."
                    )
        payload["value_ready"] = value_ready
        payload["value_coverage"] = runtime.value_evidence.coverage if runtime.value_evidence is not None else None
        payload["cardinal_value_ready"] = runtime.value_evidence is not None and bool(runtime.value_evidence.fsffl_cardinal_values)
        payload["cardinal_value_coverage"] = runtime.value_evidence.cardinal_player_coverage if runtime.value_evidence is not None else None
        served_last_good = getattr(runtime, "served_intelligence", None)
        payload["target_state"] = {
            "league_id": runtime.league_state.league.league_id,
            "league_name": runtime.league_state.league.name,
            "league_state_id": runtime.league_state.state_id,
            "as_of": runtime.league_state.as_of.isoformat(),
            "selected_team_id": runtime.selected_team_id,
            "roster_usable": selected_team_state is not None,
            "roster_count": len(selected_team_state.roster) if selected_team_state is not None else 0,
        }
        # Backward-compatible served_state remains the canonical roster State.
        # Derived last-good intelligence is identified separately and never
        # masquerades as the target State.
        payload["served_state"] = {
            **payload["target_state"],
            "last_good_intelligence": served_last_good is not None,
        }
        payload["served_intelligence"] = {
            "available": served_last_good is not None,
            "stale": served_last_good is not None,
            "league_state_id": (
                served_last_good.league_state_id
                if served_last_good is not None
                else runtime.league_state.state_id
            ),
            "as_of": (
                served_last_good.as_of.isoformat()
                if served_last_good is not None
                else runtime.league_state.as_of.isoformat()
            ),
            "target_state_id": runtime.league_state.state_id,
            "message": (
                "Last-good derived intelligence remains visible while the current "
                "canonical State is rebuilding."
                if served_last_good is not None
                else "Derived intelligence is not being served from an older State."
            ),
        }
        payload["blocked_stage"] = blocked_stage
        payload["blocking_error"] = (
            current_job.error
            if blocked_stage is not None and current_job is not None
            else None
        )
        payload["capability_readiness"] = read_capabilities(runtime)
        payload["forecast_replay_decision"] = _cached_forecast_replay_decision(
            store,
            user_id,
        )
        payload["job"] = _job_payload(current_job)
        return payload

    @application.post("/api/connect/sleeper")
    def connect_sleeper(request: ConnectSleeperLeagueRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        previous_runtime = store.get(user_id)
        previous_league_id = (
            previous_runtime.league_state.league.league_id
            if previous_runtime.league_state is not None
            else None
        )
        league_external_id = request.league_external_id.strip()
        if not league_external_id:
            raise HTTPException(status_code=422, detail="Sleeper league id cannot be blank")
        try:
            league_state = state_loader(league_external_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Unable to load Sleeper league: {exc}") from exc
        with store.lifecycle_operation(user_id):
            activated = activate_state_with_resource_boundary(
                user_id,
                league_state,
                reason="synchronous_connect",
            )
            if activated is None:
                raise HTTPException(
                    status_code=409,
                    detail="Sleeper league activation was superseded",
                )
            activated_runtime = store.get(user_id)
            if (
                activated_runtime.league_state is None
                or activated_runtime.league_state.state_id != league_state.state_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Sleeper league ownership changed after activation",
                )
            behavior_jobs.start(
                user_id=user_id,
                league_state=league_state,
                sleeper_league_external_id=league_external_id,
            )
            reconcile = getattr(
                application.state,
                "start_intelligence_reconciliation",
                None,
            )
            if (
                callable(reconcile)
                and previous_league_id is not None
                and previous_league_id != league_state.league.league_id
                and activated_runtime.selected_team_id is not None
            ):
                reconcile(user_id)
        return runtime_context_payload(user_id)

    @application.get("/api/behavioral/status")
    def behavioral_status(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        record = behavior_jobs.current(user_id)
        result = record.result
        return {
            "status": record.status.value,
            "league_state_id": record.league_state_id,
            "started_at": record.started_at.isoformat() if record.started_at is not None else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at is not None else None,
            "league_family_id": result.league_family_id if result is not None else None,
            "profile_count": result.profile_count if result is not None else 0,
            "event_count": result.total_event_count if result is not None else 0,
            "new_event_count": result.inserted_event_count if result is not None else 0,
            "reused_historical_league_ids": list(result.reused_historical_league_ids) if result is not None else [],
            "scanned_league_ids": list(result.scanned_league_ids) if result is not None else [],
            "error": record.error,
            "cache": "sqlite_configurable_path",
            "hosted_durability": "requires durable deployment storage",
        }

    @application.get("/api/behavioral/profiles")
    def behavioral_profiles(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        record = behavior_jobs.current(user_id)
        if record.status == BehavioralRuntimeStatus.FAILED:
            raise HTTPException(status_code=502, detail=record.error or "Behavioral Intelligence build failed")
        if record.result is None:
            return {"status": record.status.value, "profiles": []}

        roster_to_team = {}
        for team in runtime.league_state.teams:
            sleeper_ref = next((ref for ref in team.provider_refs if ref.provider == "sleeper"), None)
            if sleeper_ref is None:
                continue
            try:
                roster_to_team[int(sleeper_ref.external_id)] = team
            except ValueError:
                continue
        owner_to_team = {
            owner_id: roster_to_team[roster_id]
            for roster_id, owner_id in record.result.current_owner_by_roster
            if roster_id in roster_to_team
        }
        return {
            "status": record.status.value,
            "league_family_id": record.result.league_family_id,
            "profiles": [
                {
                    **profile.model_dump(mode="json"),
                    "current_team_id": owner_to_team[profile.owner_id].team_id if profile.owner_id in owner_to_team else None,
                    "current_team_name": owner_to_team[profile.owner_id].display_name if profile.owner_id in owner_to_team else None,
                }
                for profile in record.result.profiles
            ],
        }

    @application.post("/api/select-team")
    def select_team(request: SelectTeamRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        try:
            store.select_team(user_id, request.team_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        # Managed-team identity is part of reconciliation/publication authority.
        # The team-selection request owns the handoff so a browser timing gap can
        # never leave a valid selected team without a current replacement job.
        _start_intelligence_reconciliation(
            user_id,
            sync_state=False,
        )
        return runtime_context_payload(user_id)

    def _start_intelligence_reconciliation(
        user_id: str,
        *,
        sync_state: bool,
    ) -> dict[str, object]:
        published = store.get(user_id)
        if published.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if published.selected_team_id is None:
            raise HTTPException(
                status_code=409,
                detail="Select the managed team before starting intelligence",
            )
        starting_state = published.league_state
        starting_league_id = starting_state.league.league_id
        starting_team_id = published.selected_team_id
        starting_external_id = _sleeper_external_id(starting_state)
        expected_generation = store.league_generation(user_id)
        active_job = jobs.current(user_id)
        with reconciliation_lock:
            same_reconciliation_league = (
                reconciliation_league_by_user.get(user_id) == starting_league_id
            )
            same_reconciliation_generation = (
                reconciliation_generation_by_user.get(user_id) == expected_generation
            )
        active_job_running = bool(
            active_job is not None
            and active_job.status in {
                IntelligenceJobStatus.QUEUED,
                IntelligenceJobStatus.RUNNING,
            }
        )
        can_coalesce_current = bool(
            active_job_running
            and same_reconciliation_league
            and same_reconciliation_generation
        )
        if can_coalesce_current:
            return {
                **_job_payload(active_job),
                **runtime_context_payload(user_id),
                "coalesced": True,
            }

        def published_generation_fully_current(context) -> bool:
            evidence = context.forecast_evidence
            terminal_core = bool(
                evidence is not None
                and context.value_evidence is not None
                and (
                    context.simulation_analytics is not None
                    or not evidence.uncertainty_ready
                )
            )
            return bool(
                context.publication_generation_id
                and terminal_core
                and not store.working_generation_active(user_id)
                and read_capabilities(context).get("overall_status") == "full"
            )

        def require_active_league_identity() -> LeagueState:
            active_context = store.get(user_id)
            active_published = active_context.league_state
            if (
                store.league_generation(user_id) != expected_generation
                or active_published is None
                or active_published.league.league_id != starting_league_id
                or active_context.selected_team_id != starting_team_id
            ):
                raise IntelligenceJobInterrupted("lifecycle_switch")
            active_working = store.working_context(user_id).league_state
            return active_working or active_published

        def require_heavy_phase_ownership(
            phase: str,
            *,
            expected_state_id: str,
        ) -> None:
            """Revalidate lifecycle ownership after heavy-work admission.

            A State refresh can legitimately advance lifecycle identity while an
            older reconciliation is waiting behind another heavy task. The older
            waiter must therefore prove that its unpublished generation still owns
            the target *after* admission and before spending CPU/RSS on Forecast,
            Simulation, or Value. This is execution sequencing only; model
            authority and inputs are unchanged.
            """

            with store.lifecycle_operation(user_id):
                current_generation = store.league_generation(user_id)
                published_now = store.get(user_id)
                published_state = published_now.league_state
                working_active = store.working_generation_active(user_id)
                working_target = store.working_target_state_id(user_id)
                reason = None
                if current_generation != expected_generation:
                    reason = "league_generation_changed"
                elif (
                    published_state is None
                    or published_state.league.league_id != starting_league_id
                ):
                    reason = "league_changed"
                elif published_now.selected_team_id != starting_team_id:
                    reason = "managed_team_changed"
                elif not working_active:
                    reason = "working_generation_missing"
                elif working_target != expected_state_id:
                    reason = "working_target_changed"

            if reason is not None:
                # We are still inside the admitted heavy-work lane, but no longer
                # hold lifecycle identity. Reclaim the just-finished prior phase
                # before releasing admission to the replacement owner, so a stale
                # waiter cannot hand transient RSS directly into the next build.
                reclaim_phase_memory(
                    f"{user_id}:{expected_state_id}:stale_{phase}_admission"
                )
                logging.getLogger("uvicorn.error").info(
                    "FSFFL intelligence stale heavy phase skipped user=%s "
                    "phase=%s reason=%s expected_generation=%s "
                    "current_generation=%s expected_state=%s working_target=%s",
                    user_id,
                    phase,
                    reason,
                    expected_generation,
                    current_generation,
                    expected_state_id,
                    working_target,
                )
                raise IntelligenceJobInterrupted(
                    f"{reason}_before_{phase}"
                )

        def reconcile(progress) -> str | None:
            log_reconciliation_memory(user_id, "job_start")
            if sync_state:
                progress(
                    IntelligenceJobPhase.REFRESHING_STATE,
                    "Syncing canonical Sleeper State into an unpublished working generation.",
                )
                synced_state = state_loader(starting_external_id)
                log_reconciliation_memory(user_id, "state_sync_complete")
                with store.lifecycle_operation(user_id):
                    active_before_write = require_active_league_identity()
                    if (
                        synced_state.league.league_id
                        != active_before_write.league.league_id
                    ):
                        raise IntelligenceJobInterrupted("league_switch")
                    published_now = store.get(user_id)
                    materially_unchanged = (
                        league_material_fingerprint(active_before_write)
                        == league_material_fingerprint(synced_state)
                    )
                    if (
                        materially_unchanged
                        and published_generation_fully_current(published_now)
                    ):
                        progress(
                            IntelligenceJobPhase.ATTACHING_RESULTS,
                            "Canonical Sleeper State and all required product intelligence "
                            "are already current; no rebuild is required.",
                        )
                        return (
                            "Canonical Sleeper State and all required product intelligence "
                            "were verified current; no rebuild was required."
                        )
                    store.begin_working_generation(
                        user_id,
                        league_state=synced_state,
                    )
                    if active_before_write.state_id != synced_state.state_id:
                        checkpointed_job = jobs.update_current_league_state_id(
                            user_id=user_id,
                            expected_state_id=active_before_write.state_id,
                            league_state_id=synced_state.state_id,
                        )
                        if checkpointed_job is None:
                            raise IntelligenceJobInterrupted("refresh_job_replaced")
                        apply_state_resource_boundary(
                            user_id,
                            previous=published,
                            next_state=synced_state,
                            next_team_id=starting_team_id,
                            reason="sync_reconciliation_state_change",
                        )
                        # Cleanup and replacement execution ownership remain inside
                        # the same lifecycle sequence. A newer transition cannot land
                        # between clear/revalidation and this Behavioral handoff.
                        require_active_league_identity()
                        behavior_jobs.start(
                            user_id=user_id,
                            league_state=synced_state,
                            sleeper_league_external_id=starting_external_id,
                        )
                        require_active_league_identity()
            else:
                with store.lifecycle_operation(user_id):
                    require_active_league_identity()
                    published_now = store.get(user_id)
                    if published_generation_fully_current(published_now):
                        progress(
                            IntelligenceJobPhase.ATTACHING_RESULTS,
                            "Published State and all required product intelligence "
                            "are already current; no reconciliation is required.",
                        )
                        return (
                            "Published State and all required product intelligence "
                            "were verified current; no rebuild was required."
                        )
                    store.begin_working_generation(
                        user_id,
                        league_state=starting_state,
                    )

            restore_exact = getattr(store, "restore_exact_state_intelligence", None)
            with store.lifecycle_operation(user_id):
                working_state = require_active_league_identity()
                if callable(restore_exact):
                    restore_exact(user_id)
                context = store.working_context(user_id)
            if context.league_state is None:
                raise IntelligenceJobInterrupted("league_switch")
            working_state = context.league_state

            evidence = context.forecast_evidence
            simulation = context.simulation_analytics
            values = context.value_evidence
            terminal_reuse = bool(
                evidence is not None
                and values is not None
                and (
                    simulation is not None
                    or not evidence.uncertainty_ready
                )
            )
            if terminal_reuse:
                product_capability = None
                if product_capability_reconciler is not None:
                    progress(
                        IntelligenceJobPhase.BUILDING_INTRINSIC,
                        "Preparing governed FSFFL Intrinsic inside the working generation.",
                    )
                    product_capability = product_capability_reconciler(context)
                    require_active_league_identity()
                product_status = (
                    str(product_capability.get("status"))
                    if product_capability is not None
                    else "not_configured"
                )
                progress(
                    IntelligenceJobPhase.ATTACHING_RESULTS,
                    "Atomically publishing the coherent intelligence generation.",
                )
                published_context = publish_working_generation(
                    user_id,
                    expected_generation=expected_generation,
                    expected_league_id=starting_league_id,
                )
                if product_status not in {"full", "ready"}:
                    return (
                        "Canonical Sleeper State is current. Compatible governed core "
                        "intelligence was reused and atomically published. Product "
                        f"intelligence remains partially available: Intrinsic {product_status}."
                    )
                return (
                    "Canonical Sleeper State and compatible governed intelligence were "
                    "atomically published from one coherent generation."
                    if published_context.simulation_analytics is not None
                    else
                    "Canonical Sleeper State is current. Compatible governed Forecast, "
                    "Value and FSFFL Intrinsic were atomically published; Simulation "
                    "remains unavailable under current Forecast authority."
                )

            if evidence is None:
                progress(
                    IntelligenceJobPhase.BUILDING_FORECASTS,
                    "Building governed multi-source projections in the working generation.",
                )
                with heavy_claim(
                    "forecast",
                    f"{user_id}:{working_state.state_id}:forecast",
                ):
                    require_heavy_phase_ownership(
                        "forecast",
                        expected_state_id=working_state.state_id,
                    )
                    reclaim_phase_memory(
                        f"{user_id}:{working_state.state_id}:before_forecast"
                    )
                    evidence = forecast_loader(working_state)
                    log_reconciliation_memory(user_id, "forecast_build_complete")
                    with store.lifecycle_operation(user_id):
                        require_active_league_identity()
                        store.set_forecast_evidence(
                            user_id,
                            evidence,
                            refreshed_league_state=working_state,
                            require_working_generation=True,
                        )
                    reclaim_phase_memory(
                        f"{user_id}:{working_state.state_id}:after_forecast"
                    )
            else:
                progress(
                    IntelligenceJobPhase.BUILDING_FORECASTS,
                    "Reusing compatible governed Forecast evidence in the working generation.",
                )

            progress(
                IntelligenceJobPhase.RUNNING_SIMULATION,
                "Evaluating governed NEXT-4 simulation authority in the working generation.",
            )
            simulation_ready = evidence.uncertainty_ready
            current = store.working_context(user_id)
            simulation = current.simulation_analytics
            if simulation_ready and simulation is None:
                with heavy_claim(
                    "simulation",
                    f"{user_id}:{working_state.state_id}:simulation",
                ):
                    require_heavy_phase_ownership(
                        "simulation",
                        expected_state_id=working_state.state_id,
                    )
                    reclaim_phase_memory(
                        f"{user_id}:{working_state.state_id}:before_simulation"
                    )
                    simulation = simulation_loader(working_state, evidence)
                    log_reconciliation_memory(user_id, "simulation_build_complete")
                    with store.lifecycle_operation(user_id):
                        require_active_league_identity()
                        store.set_simulation_analytics(
                            user_id,
                            simulation,
                            require_working_generation=True,
                        )
                    reclaim_phase_memory(
                        f"{user_id}:{working_state.state_id}:after_simulation"
                    )
            elif not simulation_ready:
                _logger.warning(
                    "FSFFL simulation not promoted league=%s state=%s blockers=%s partial_players=%s",
                    working_state.league.league_id,
                    working_state.state_id,
                    list(evidence.runtime_result.simulation_authority_blockers),
                    len(evidence.runtime_result.partial_fantasy_point_forecasts),
                )

            progress(
                IntelligenceJobPhase.BUILDING_VALUES,
                "Building or reusing governed NEXT-3 current market values in the working generation.",
            )
            current = store.working_context(user_id)
            values = current.value_evidence
            if values is None or values.league_state_id != working_state.state_id:
                with heavy_claim(
                    "value",
                    f"{user_id}:{working_state.state_id}:value",
                ):
                    require_heavy_phase_ownership(
                        "value",
                        expected_state_id=working_state.state_id,
                    )
                    reclaim_phase_memory(
                        f"{user_id}:{working_state.state_id}:before_value"
                    )
                    values = value_loader(working_state)
                    log_reconciliation_memory(user_id, "value_build_complete")
                    with store.lifecycle_operation(user_id):
                        require_active_league_identity()
                        store.set_value_evidence(
                            user_id,
                            values,
                            require_working_generation=True,
                        )
                    reclaim_phase_memory(
                        f"{user_id}:{working_state.state_id}:after_value"
                    )

            product_capability = None
            working_context = store.working_context(user_id)
            if product_capability_reconciler is not None:
                progress(
                    IntelligenceJobPhase.BUILDING_INTRINSIC,
                    "Preparing governed FSFFL Intrinsic and future Forecast evidence against the working generation.",
                )
                product_capability = product_capability_reconciler(working_context)
                log_reconciliation_memory(user_id, "intrinsic_reconcile_complete")
                require_active_league_identity()
                reclaim_phase_memory(
                    f"{user_id}:{working_state.state_id}:after_intrinsic"
                )

            progress(
                IntelligenceJobPhase.ATTACHING_RESULTS,
                "Durably checkpointing and atomically publishing the coherent generation.",
            )
            published_context = publish_working_generation(
                user_id,
                expected_generation=expected_generation,
                expected_league_id=starting_league_id,
            )
            log_reconciliation_memory(user_id, "publication_complete")
            intrinsic_status = (
                str(product_capability.get("status"))
                if product_capability is not None
                else "not_configured"
            )
            intrinsic_ready = intrinsic_status in {"full", "ready"}
            if not simulation_ready:
                blockers = (
                    ", ".join(evidence.runtime_result.simulation_authority_blockers)
                    or "Forecast authority requirements"
                )
                return (
                    "Canonical Sleeper State is current. Governed Forecast and current "
                    "Value evidence were atomically published. Simulation remains "
                    "unavailable under current Forecast authority: "
                    + blockers
                    + (
                        ". FSFFL Intrinsic is ready."
                        if intrinsic_ready
                        else f". FSFFL Intrinsic is {intrinsic_status}."
                    )
                )
            if published_context.simulation_analytics is None:
                return (
                    "Canonical Sleeper State, governed Forecast and current Value are "
                    "published. Simulation did not produce an authoritative result. "
                    f"FSFFL Intrinsic is {intrinsic_status}."
                )
            if not intrinsic_ready and product_capability_reconciler is not None:
                return (
                    "Canonical Sleeper State and governed core intelligence are "
                    "atomically published. Product intelligence remains partially "
                    f"available: FSFFL Intrinsic is {intrinsic_status}."
                )
            return (
                "Canonical Sleeper State and all currently governed product intelligence "
                "were atomically published."
            )

        def work(progress) -> str | None:
            try:
                return reconcile(progress)
            except BaseException as exc:
                log_reconciliation_memory(user_id, "job_aborted")
                logging.getLogger("uvicorn.error").info(
                    "FSFFL intelligence lifecycle abort user=%s reason=%s "
                    "expected_generation=%s current_generation=%s "
                    "expected_state=%s working_target=%s",
                    user_id,
                    str(exc) or type(exc).__name__,
                    expected_generation,
                    store.league_generation(user_id),
                    starting_state.state_id,
                    store.working_target_state_id(user_id),
                )
                store.abort_working_generation_if_generation(
                    user_id,
                    expected_generation=expected_generation,
                )
                raise
            finally:
                # Successful publication removes the working generation itself. An
                # interrupted older job may finish after a newer lifecycle starts, so
                # cleanup is ownership-aware and can never erase replacement work.
                if store.working_generation_active(user_id):
                    store.abort_working_generation_if_generation(
                        user_id,
                        expected_generation=expected_generation,
                    )

        # Recheck/coalesce immediately before job admission while holding the
        # reconciliation ownership lock. The early check above is a fast path; this
        # closing check prevents two near-simultaneous startup/browser triggers from
        # both observing stale ownership metadata and creating replacement jobs.
        with reconciliation_lock:
            current_job = jobs.current(user_id)
            current_running = bool(
                current_job is not None
                and current_job.status in {
                    IntelligenceJobStatus.QUEUED,
                    IntelligenceJobStatus.RUNNING,
                }
            )
            current_same_owner = bool(
                current_running
                and reconciliation_league_by_user.get(user_id)
                == starting_league_id
                and reconciliation_generation_by_user.get(user_id)
                == expected_generation
            )
            if current_same_owner:
                return {
                    **_job_payload(current_job),
                    **runtime_context_payload(user_id),
                    "coalesced": True,
                }
            replace_current = bool(current_running and not current_same_owner)
            try:
                job = jobs.start(
                    user_id=user_id,
                    league_state_id=starting_state.state_id,
                    work=work,
                    coalesce_current=not replace_current,
                )
            except IntelligenceJobBusy as exc:
                # Do not change reconciliation ownership or create a durable
                # queued job when the bounded executor is at capacity.
                raise HTTPException(
                    status_code=503,
                    detail=str(exc),
                    headers={"Retry-After": "5"},
                ) from exc
            reconciliation_league_by_user[user_id] = starting_league_id
            reconciliation_generation_by_user[user_id] = expected_generation
        return {
            **_job_payload(job),
            **runtime_context_payload(user_id),
            "coalesced": False,
        }

    # Hosted league switching activates State first, then calls this non-blocking
    # reconciler. Manual Refresh Intelligence uses the same worker with sync_state=True.
    application.state.activate_state_with_resource_boundary = (
        activate_state_with_resource_boundary
    )
    application.state.apply_state_resource_boundary = apply_state_resource_boundary
    application.state.start_intelligence_reconciliation = (
        lambda user_id: _start_intelligence_reconciliation(
            user_id,
            sync_state=False,
        )
    )
    application.state.start_intelligence_sync_reconciliation = (
        lambda user_id: _start_intelligence_reconciliation(
            user_id,
            sync_state=True,
        )
    )
    application.state.intelligence_jobs = jobs
    application.state.capability_readiness_reader = read_capabilities
    application.state.product_capability_reconciler = product_capability_reconciler
    application.state.heavy_work_coordinator = heavy_work_coordinator

    def active_hosted_refresh_payload(user_id: str) -> dict[str, object] | None:
        """Expose an already-running browser State refresh as the active job.

        The hosted connect coordinator owns its State loader and, after activation,
        hands off to the same intelligence reconciler. Returning that lifecycle here
        prevents an explicit Refresh Intelligence tap from starting a second State
        loader while Safari is still polling the automatic refresh.
        """

        connect_jobs = getattr(application.state, "hosted_connect_jobs", None)
        current = connect_jobs.current(user_id) if connect_jobs is not None else None
        status = getattr(getattr(current, "status", None), "value", None)
        if (
            current is None
            or getattr(current, "operation", None) != "refresh"
            or status not in {"queued", "running"}
        ):
            return None
        runtime = store.get(user_id)
        state = runtime.league_state
        if (
            state is None
            or _sleeper_external_id(state)
            != str(getattr(current, "league_external_id", ""))
        ):
            return None
        return {
            "job_id": str(current.job_id),
            "status": str(status),
            "phase": IntelligenceJobPhase.REFRESHING_STATE.value,
            "message": str(current.message),
            "error": None,
            "failure_phase": None,
            "league_state_id": state.state_id,
            "state_id": state.state_id,
            "created_at": current.created_at.isoformat(),
            "updated_at": current.updated_at.isoformat(),
            "coalesced": True,
            "state_sync_owner": "hosted_connect_refresh",
        }

    def resume_restart_interrupted_job(user_id: str) -> dict[str, object] | None:
        """Resume a lost in-memory build when durable State survived restart."""

        current_job = jobs.current(user_id)
        runtime = store.get(user_id)
        state = runtime.league_state
        if (
            current_job is None
            or current_job.status != IntelligenceJobStatus.INTERRUPTED
            or current_job.error != "server_restart"
            or state is None
            or runtime.selected_team_id is None
            or current_job.league_state_id != state.state_id
            or (
                runtime.forecast_evidence is not None
                and runtime.value_evidence is not None
                and (
                    runtime.simulation_analytics is not None
                    or not runtime.forecast_evidence.uncertainty_ready
                )
            )
        ):
            return None
        resumed = _start_intelligence_reconciliation(user_id, sync_state=False)
        return {**resumed, "resumed_after_restart": True}

    @application.post("/api/intelligence/jobs")
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

        if current_position_depth_provider is None:
            current_position_depth = unavailable_current_position_depth(
                league_state,
                reason=(
                    "Governed completed-actuals + ROS Current Position & Depth "
                    "authority is not configured in this runtime."
                ),
            )
        else:
            try:
                current_position_depth = current_position_depth_provider(league_state)
            except Exception as exc:
                current_position_depth = unavailable_current_position_depth(
                    league_state,
                    reason=(
                        "Governed completed-actuals + ROS Current Position & Depth "
                        f"authority failed: {type(exc).__name__}: {exc}"
                    ),
                )

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
            "current_position_depth": current_position_depth.model_dump(mode="json"),
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

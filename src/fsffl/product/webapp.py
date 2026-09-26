from __future__ import annotations

import hashlib
import logging
import os
import secrets
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

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
from .intelligence_runtime import (
    build_forecast_lineup_analytics,
    build_state_only_league_view,
    state_first_runtime_status,
)
from .opportunity_workspace import build_opportunity_workspace
from .runtime import (
    LiveForecastEvidence,
    LiveForecastLoader,
    LiveValueLoader,
    PrivateBetaRuntimeStore,
    default_live_forecast_loader,
    default_live_value_loader,
    default_sleeper_state_loader,
)
from .simulation_runtime import LiveSimulationAnalyticsResult, build_live_simulation_analytics
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


class ConnectSleeperLeagueRequest(FrozenModel):
    league_external_id: str


class SelectTeamRequest(FrozenModel):
    team_id: str


class AnalyzeTradeRequest(FrozenModel):
    counterparty_team_id: str
    focal_asset_refs: tuple[str, ...]
    counterparty_asset_refs: tuple[str, ...]


class EvaluateWaiverRequest(FrozenModel):
    add_player_id: str
    drop_player_id: str | None = None


class PlayerUnavailableRequest(FrozenModel):
    player_id: str


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
    authoritative_rows = tuple(getattr(evidence, "league_scored_forecasts", ()) or ()) if evidence is not None else ()
    raw_rows = tuple(getattr(evidence, "raw_forecasts", ()) or ()) if evidence is not None else ()

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
    else:
        forecast_status = "full"
        forecast_reason = (
            "Governed league-scored Forecast authority is available for the current "
            "downstream consumer."
            + (
                f" {len(partial_rows)} non-material subject(s) retain explicit partial "
                "coverage diagnostics."
                if partial_rows
                else ""
            )
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

    statuses = (forecast_status, simulation_status, value_status)
    overall_status = (
        "full"
        if all(item == "full" for item in statuses)
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
            "non_material_partial_scored_count": max(
                0, len(partial_rows) - len(material_partial_player_ids)
            ),
            "simulation_blockers": list(blockers),
        },
        "simulation": {"status": simulation_status, "reason": simulation_reason},
        "current_value": {"status": value_status, "reason": value_reason},
        "intrinsic": {
            "status": "separate_surface",
            "reason": (
                "FSFFL Intrinsic has independent preserved-preseason Forecast authority "
                "and readiness; it is not inferred from current Value attachment."
            ),
        },
    }


def _runtime_context_payload(store: PrivateBetaRuntimeStore, user_id: str) -> dict[str, object]:
    runtime = store.get(user_id)
    league_state = runtime.league_state
    evidence = runtime.forecast_evidence
    simulation = runtime.simulation_analytics
    value_evidence = runtime.value_evidence
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
        "capability_readiness": _runtime_capability_readiness(runtime),
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
        return _team_view_payload(view, runtime.value_evidence, runtime.forecast_evidence)
    if state_only_while_enriching:
        view = build_state_only_team_view(
            runtime.league_state,
            team_id=runtime.selected_team_id,
        )
        return _team_view_payload(view, runtime.value_evidence)
    lineup_result = _forecast_lineup_result(runtime)
    if lineup_result is not None:
        view = next(
            item
            for item in lineup_result.team_views
            if item.team_id == runtime.selected_team_id
        )
        return _team_view_payload(view, runtime.value_evidence)
    if runtime.forecast_evidence is not None:
        evidence = runtime.forecast_evidence
        forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
        view = build_forecast_team_view(
            runtime.league_state,
            team_id=runtime.selected_team_id,
            forecasts=forecasts,
            forecast_model_version=evidence.model_version,
        )
        return _team_view_payload(view, runtime.value_evidence)
    view = build_state_only_team_view(
        runtime.league_state,
        team_id=runtime.selected_team_id,
    )
    return _team_view_payload(view, runtime.value_evidence)


def _default_simulation_loader(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
) -> LiveSimulationAnalyticsResult:
    return build_live_simulation_analytics(
        league_state,
        forecasts=evidence.league_scored_forecasts,
        forecast_model_version=evidence.model_version,
        simulation_count=50_000,
        cooperative_yield=foreground_pressure.cooperative_yield,
    )


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
) -> FastAPI:
    application = FastAPI(title="FSFFL NEXT Private Beta", version="next8-beta-v1", docs_url="/api/docs", redoc_url=None)
    store = runtime_store or PrivateBetaRuntimeStore()
    jobs = IntelligenceJobCoordinator(max_workers=2, persistence_store=persistence_store)
    behavior_jobs = behavioral_coordinator or BehavioralRuntimeCoordinator(max_workers=2)
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "product": "fsffl-next", "version": "next8-beta-v1"}

    @application.get("/")
    def index(_: str = Depends(require_beta_user)) -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    @application.get("/api/product-context")
    def product_context(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime_payload = _runtime_context_payload(store, user_id)
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
        payload["served_state"] = {
            "league_id": runtime.league_state.league.league_id,
            "league_name": runtime.league_state.league.name,
            "league_state_id": runtime.league_state.state_id,
            "as_of": runtime.league_state.as_of.isoformat(),
            "selected_team_id": runtime.selected_team_id,
            "roster_usable": selected_team_state is not None,
            "roster_count": len(selected_team_state.roster) if selected_team_state is not None else 0,
            "last_good_intelligence": bool(
                runtime.forecast_evidence is not None
                and runtime.simulation_analytics is not None
                and runtime.value_evidence is not None
            ),
        }
        payload["blocked_stage"] = blocked_stage
        payload["blocking_error"] = (
            current_job.error
            if blocked_stage is not None and current_job is not None
            else None
        )
        payload["capability_readiness"] = _runtime_capability_readiness(runtime)
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
        store.set_league_state(user_id, league_state)
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
        ):
            reconcile(user_id)
        return _runtime_context_payload(store, user_id)

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
        return _runtime_context_payload(store, user_id)

    def _start_intelligence_reconciliation(
        user_id: str,
        *,
        sync_state: bool,
    ) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        starting_state = runtime.league_state
        starting_league_id = starting_state.league.league_id
        starting_external_id = _sleeper_external_id(starting_state)
        expected_generation = [store.league_generation(user_id)]

        def require_active_league_identity() -> LeagueState:
            active = store.get(user_id).league_state
            if (
                store.league_generation(user_id) != expected_generation[0]
                or active is None
                or active.league.league_id != starting_league_id
            ):
                raise IntelligenceJobInterrupted("league_switch")
            return active

        def work(progress) -> str | None:
            if sync_state:
                progress(
                    IntelligenceJobPhase.REFRESHING_STATE,
                    "Syncing canonical Sleeper State before intelligence reconciliation.",
                )
                synced_state = state_loader(starting_external_id)
                active_before_write = require_active_league_identity()
                if synced_state.league.league_id != active_before_write.league.league_id:
                    raise IntelligenceJobInterrupted("league_switch")
                activated = store.set_league_state_if_generation(
                    user_id,
                    synced_state,
                    expected_generation=expected_generation[0],
                    expected_league_id=starting_league_id,
                )
                if activated is None:
                    raise IntelligenceJobInterrupted("league_switch")
                expected_generation[0] = store.league_generation(user_id)
                wait_for_checkpoint = getattr(store, "wait_for_checkpoint", None)
                if callable(wait_for_checkpoint) and not wait_for_checkpoint(
                    user_id,
                    timeout=30.0,
                ):
                    raise RuntimeError(
                        "Synced Sleeper State could not be durably checkpointed"
                    )

            working_state = require_active_league_identity()
            restore_exact = getattr(store, "restore_exact_state_intelligence", None)
            if callable(restore_exact):
                restore_exact(user_id)
            context = store.get(user_id)
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
                return (
                    "Canonical Sleeper State is current. Compatible governed "
                    "intelligence was reused for this exact State."
                    if simulation is not None
                    else
                    "Canonical Sleeper State is current. Compatible governed Forecast "
                    "and Value were reused; Simulation remains unavailable under current "
                    "Forecast authority."
                )

            if evidence is None:
                progress(
                    IntelligenceJobPhase.BUILDING_FORECASTS,
                    "Building governed multi-source projections for the synced State.",
                )
                evidence = forecast_loader(working_state)
                require_active_league_identity()
                store.set_forecast_evidence(
                    user_id,
                    evidence,
                    refreshed_league_state=working_state,
                )
            else:
                progress(
                    IntelligenceJobPhase.BUILDING_FORECASTS,
                    "Reusing compatible governed Forecast evidence for the synced State.",
                )

            progress(
                IntelligenceJobPhase.RUNNING_SIMULATION,
                "Evaluating governed NEXT-4 simulation authority for the synced State.",
            )
            simulation_ready = evidence.uncertainty_ready
            current = store.get(user_id)
            simulation = current.simulation_analytics
            if simulation_ready and simulation is None:
                simulation = simulation_loader(working_state, evidence)
                require_active_league_identity()
                store.set_simulation_analytics(user_id, simulation)
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
                "Building or reusing governed NEXT-3 current market values for the synced State.",
            )
            current = store.get(user_id)
            values = current.value_evidence
            if values is None or values.league_state_id != working_state.state_id:
                values = value_loader(working_state)
                require_active_league_identity()
                store.set_value_evidence(user_id, values)

            progress(
                IntelligenceJobPhase.ATTACHING_RESULTS,
                "Reconciling governed intelligence with the exact current LeagueState.",
            )
            current = store.get(user_id)
            if not simulation_ready:
                blockers = (
                    ", ".join(evidence.runtime_result.simulation_authority_blockers)
                    or "Forecast authority requirements"
                )
                return (
                    "Canonical Sleeper State is current. Governed Forecast and current "
                    "Value evidence are ready. Simulation remains unavailable under current Forecast "
                    "authority: "
                    + blockers
                    + "."
                )
            if current.simulation_analytics is None:
                return (
                    "Canonical Sleeper State, governed Forecast and current Value are "
                    "ready. Simulation did not produce an authoritative result."
                )
            return (
                "Canonical Sleeper State and all currently governed core intelligence "
                "are reconciled."
            )

        job = jobs.start(
            user_id=user_id,
            league_state_id=starting_state.state_id,
            work=work,
        )
        return {**_job_payload(job), **_runtime_context_payload(store, user_id)}

    # Hosted league switching activates State first, then calls this non-blocking
    # reconciler. Manual Refresh Intelligence uses the same worker with sync_state=True.
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

    @application.post("/api/intelligence/jobs")
    def start_intelligence_job(
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        return _start_intelligence_reconciliation(
            user_id,
            sync_state=True,
        )

    @application.get("/api/intelligence/jobs/current")
    def current_intelligence_job(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        return {**_job_payload(jobs.current(user_id)), **_runtime_context_payload(store, user_id)}

    @application.post("/api/intelligence/refresh-forecasts")
    def refresh_forecasts(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        try:
            refreshed_state = state_loader(_sleeper_external_id(runtime.league_state))
            if refreshed_state.league.league_id != runtime.league_state.league.league_id:
                raise ValueError("Sleeper state loader returned a different league")
            store.set_league_state(user_id, refreshed_state)
            evidence: LiveForecastEvidence = forecast_loader(refreshed_state)
            store.set_forecast_evidence(
                user_id,
                evidence,
                refreshed_league_state=refreshed_state,
            )
        except Exception as exc:
            _logger.warning(
                "FSFFL forecast refresh failed league=%s team=%s error=%s",
                runtime.league_state.league.league_id,
                runtime.selected_team_id,
                exc,
            )
            raise HTTPException(status_code=502, detail=f"Unable to refresh FSFFL forecasts: {exc}") from exc

        simulation_failure = None
        value_failure = None
        if evidence.uncertainty_ready:
            try:
                simulation = simulation_loader(refreshed_state, evidence)
                store.set_simulation_analytics(user_id, simulation)
            except Exception as exc:
                simulation_failure = f"{type(exc).__name__}: {exc}"
                _logger.warning(
                    "FSFFL simulation enrichment unavailable league=%s error=%s",
                    refreshed_state.league.league_id,
                    exc,
                )
        try:
            values = value_loader(refreshed_state)
            store.set_value_evidence(user_id, values)
        except Exception as exc:
            value_failure = f"{type(exc).__name__}: {exc}"
            _logger.warning(
                "FSFFL Cardinal Value enrichment unavailable league=%s error=%s",
                refreshed_state.league.league_id,
                exc,
            )

        current = store.get(user_id)
        simulation = current.simulation_analytics
        values = current.value_evidence
        return {
            **_runtime_context_payload(store, user_id),
            "successful_sources": list(evidence.successful_source_ids),
            "failed_sources": list(evidence.failed_sources),
            "forecast_evidence_basis": evidence.evidence_basis,
            "forecast_runtime_model_version": evidence.runtime_result.model_version,
            "forecast_evaluation_as_of": evidence.runtime_result.evaluation_as_of.isoformat(),
            "ensemble_groups": len(evidence.raw_forecasts),
            "league_scored_players": len(evidence.league_scored_forecasts),
            "partial_scored_players": len(evidence.runtime_result.partial_fantasy_point_forecasts),
            "forecast_family_coverage": [
                item.model_dump(mode="json")
                for item in evidence.runtime_result.family_coverage
            ],
            "simulation_authority_blockers": list(
                evidence.runtime_result.simulation_authority_blockers
            ),
            "uncertainty_ready": evidence.uncertainty_ready,
            "simulation_ready": simulation is not None,
            "simulation_count": simulation.simulation_result.simulation_count if simulation is not None else None,
            "simulation_failure": simulation_failure,
            "value_ready": values is not None and bool(values.estimates),
            "value_failure": value_failure,
        }

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

        current_job = jobs.current(user_id)
        enrichment_running = bool(
            current_job is not None
            and current_job.status.value in {"queued", "running"}
        )
        team_view = _managed_team_view_payload(
            runtime,
            state_only_while_enriching=enrichment_running,
        )
        atlas = build_league_atlas_payload(
            runtime,
            preseason_reason=(
                "Home intentionally does not resolve or reconstruct preseason evidence."
            ),
        )
        return {
            "status": "ready",
            "contract_version": "home-north-star-v1",
            "league_state_id": runtime.league_state.state_id,
            "managed_team_id": runtime.selected_team_id,
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
        }

    @application.get("/api/my-team")
    def my_team(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        current_job = jobs.current(user_id)
        enrichment_running = bool(
            current_job is not None
            and current_job.status.value in {"queued", "running"}
        )
        try:
            return _managed_team_view_payload(
                runtime,
                state_only_while_enriching=enrichment_running,
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
        return {
            "league_state_id": league_state.state_id,
            "as_of": league_state.as_of.isoformat(),
            "source_level": source_level,
            "team_market_value_portfolios": (
                [portfolio.model_dump(mode="json") for portfolio in runtime.value_evidence.team_market_value_portfolios]
                if runtime.value_evidence is not None
                else []
            ),
            "team_views": [view.model_dump(mode="json") for view in enriched],
        }

    @application.get("/api/league/atlas")
    def league_atlas(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        """Compose the scan-first League Atlas without creating new model authority."""

        runtime = store.get(user_id)
        league_state = runtime.league_state
        if league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")

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

        return build_league_atlas_payload(
            runtime,
            preseason_team_views=preseason_views,
            preseason_as_of=preseason_as_of,
            preseason_reason=preseason_reason,
            preseason_baseline=preseason_baseline,
        )

    @application.get("/api/opportunities/workspace")
    def opportunity_workspace(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        try:
            return build_opportunity_workspace(runtime)
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

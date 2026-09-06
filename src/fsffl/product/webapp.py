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
from fsffl.state.models import FrozenModel, LeagueState
from fsffl.trade_decision.models import BilateralTradeProposal
from fsffl.value.models import AssetValueProfile

from .background_jobs import IntelligenceJob, IntelligenceJobCoordinator, IntelligenceJobPhase
from .dashboard import build_league_metric_chart
from .intelligence_runtime import (
    build_forecast_lineup_analytics,
    build_state_only_league_view,
    state_first_runtime_status,
)
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
from .trade_center import TradeDraft, TradeDraftSide, submit_trade_draft
from .trade_center_view import build_trade_center_browser_view, resolve_owned_asset_ref


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
        and secrets.compare_digest(_password_digest(credentials.password), expected_password_sha256.lower())
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid private-beta credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return expected_username


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
        "forecast_ready": evidence is not None and bool(evidence.league_scored_forecasts),
        "forecast_sources": list(evidence.successful_source_ids) if evidence is not None else [],
        "simulation_ready": simulation is not None,
        "simulation_count": simulation.simulation_result.simulation_count if simulation is not None else None,
        "value_ready": value_evidence is not None and bool(value_evidence.estimates),
        "value_sources": list(value_evidence.successful_source_ids) if value_evidence is not None else [],
        "value_coverage": value_evidence.coverage if value_evidence is not None else None,
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


def _attach_live_value_profiles(view, value_evidence):
    if value_evidence is None or not value_evidence.estimates:
        return view
    profiles = {
        estimate.asset_id: AssetValueProfile(
            asset_id=estimate.asset_id,
            asset_kind=estimate.asset_kind,
            market_price=estimate,
        )
        for estimate in value_evidence.estimates
    }
    players = tuple(
        row.model_copy(update={"value_profile": profiles.get(row.player_id)})
        for row in view.players
    )
    draft_picks = tuple(
        row.model_copy(update={"value_profile": profiles.get(row.pick.pick_id)})
        for row in view.draft_picks
    )
    return view.model_copy(update={"players": players, "draft_picks": draft_picks})


def _default_simulation_loader(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
) -> LiveSimulationAnalyticsResult:
    return build_live_simulation_analytics(
        league_state,
        forecasts=evidence.league_scored_forecasts,
        forecast_model_version=evidence.model_version,
        simulation_count=50_000,
    )


def create_app(
    *,
    league_view_provider: LeagueViewProvider | None = None,
    runtime_store: PrivateBetaRuntimeStore | None = None,
    state_loader: StateLoader = default_sleeper_state_loader,
    forecast_loader: LiveForecastLoader = default_live_forecast_loader,
    simulation_loader: SimulationLoader = _default_simulation_loader,
    value_loader: LiveValueLoader = default_live_value_loader,
    trade_evaluator: TradeEvaluator | None = None,
) -> FastAPI:
    application = FastAPI(title="FSFFL NEXT Private Beta", version="next8-beta-v1", docs_url="/api/docs", redoc_url=None)
    store = runtime_store or PrivateBetaRuntimeStore()
    jobs = IntelligenceJobCoordinator(max_workers=2)
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

    @application.get("/api/intelligence/status")
    def intelligence_status(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        evidence = runtime.forecast_evidence
        message = None
        if evidence is not None:
            message = "Authoritative NEXT-2 ensemble loaded from independent sources: " + ", ".join(evidence.successful_source_ids) + "."
        payload = state_first_runtime_status(
            runtime.league_state,
            forecast_ready=evidence is not None and bool(evidence.league_scored_forecasts),
            forecast_message=message,
        ).model_dump(mode="json")
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
        payload["value_ready"] = value_ready
        payload["value_coverage"] = runtime.value_evidence.coverage if runtime.value_evidence is not None else None
        payload["job"] = _job_payload(jobs.current(user_id))
        return payload

    @application.post("/api/connect/sleeper")
    def connect_sleeper(request: ConnectSleeperLeagueRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        league_external_id = request.league_external_id.strip()
        if not league_external_id:
            raise HTTPException(status_code=422, detail="Sleeper league id cannot be blank")
        try:
            league_state = state_loader(league_external_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Unable to load Sleeper league: {exc}") from exc
        store.set_league_state(user_id, league_state)
        return _runtime_context_payload(store, user_id)

    @application.post("/api/select-team")
    def select_team(request: SelectTeamRequest, user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        try:
            store.select_team(user_id, request.team_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _runtime_context_payload(store, user_id)

    @application.post("/api/intelligence/jobs")
    def start_intelligence_job(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        initial_state = runtime.league_state
        initial_state_id = initial_state.state_id

        def work(progress) -> None:
            progress(IntelligenceJobPhase.BUILDING_FORECASTS, "Building governed multi-source projections.")
            evidence: LiveForecastEvidence = forecast_loader(initial_state)

            progress(IntelligenceJobPhase.REFRESHING_STATE, "Refreshing canonical Sleeper state at the evidence cutoff.")
            refreshed_state = state_loader(_sleeper_external_id(initial_state))
            store.set_forecast_evidence(user_id, evidence, refreshed_league_state=refreshed_state)

            if not evidence.uncertainty_ready:
                raise ValueError("forecast uncertainty is not ready for authoritative simulation")

            progress(IntelligenceJobPhase.RUNNING_SIMULATION, "Running 50,000 governed NEXT-4 season simulations.")
            simulation = simulation_loader(refreshed_state, evidence)
            store.set_simulation_analytics(user_id, simulation)

            progress(IntelligenceJobPhase.BUILDING_VALUES, "Building governed NEXT-3 current market values.")
            values = value_loader(refreshed_state)

            progress(IntelligenceJobPhase.ATTACHING_RESULTS, "Attaching simulation and Value results to the current canonical league state.")
            store.set_value_evidence(user_id, values)

        job = jobs.start(user_id=user_id, league_state_id=initial_state_id, work=work)
        return {**_job_payload(job), **_runtime_context_payload(store, user_id)}

    @application.get("/api/intelligence/jobs/current")
    def current_intelligence_job(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        return {**_job_payload(jobs.current(user_id)), **_runtime_context_payload(store, user_id)}

    @application.post("/api/intelligence/refresh-forecasts")
    def refresh_forecasts(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        try:
            evidence: LiveForecastEvidence = forecast_loader(runtime.league_state)
            refreshed_state = state_loader(_sleeper_external_id(runtime.league_state))
            store.set_forecast_evidence(user_id, evidence, refreshed_league_state=refreshed_state)
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
                "FSFFL Value enrichment unavailable league=%s error=%s",
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
            "ensemble_groups": len(evidence.raw_forecasts),
            "league_scored_players": len(evidence.league_scored_forecasts),
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
            "estimates": [
                {
                    **estimate.model_dump(mode="json"),
                    "display_name": player_names.get(estimate.asset_id, estimate.asset_id),
                }
                for estimate in evidence.estimates
            ],
        }

    @application.get("/api/my-team")
    def my_team(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if runtime.selected_team_id is None:
            raise HTTPException(status_code=409, detail="No managed team is selected")
        if runtime.simulation_analytics is not None:
            view = next(
                item
                for item in runtime.simulation_analytics.team_views
                if item.team_id == runtime.selected_team_id
            )
            return _attach_live_value_profiles(view, runtime.value_evidence).model_dump(mode="json")
        lineup_result = _forecast_lineup_result(runtime)
        if lineup_result is not None:
            view = next(item for item in lineup_result.team_views if item.team_id == runtime.selected_team_id)
            return _attach_live_value_profiles(view, runtime.value_evidence).model_dump(mode="json")
        if runtime.forecast_evidence is not None:
            evidence = runtime.forecast_evidence
            forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
            view = build_forecast_team_view(
                runtime.league_state,
                team_id=runtime.selected_team_id,
                forecasts=forecasts,
                forecast_model_version=evidence.model_version,
            )
            return _attach_live_value_profiles(view, runtime.value_evidence).model_dump(mode="json")
        view = build_state_only_team_view(runtime.league_state, team_id=runtime.selected_team_id)
        return _attach_live_value_profiles(view, runtime.value_evidence).model_dump(mode="json")

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
        if request.counterparty_team_id == runtime.selected_team_id:
            raise HTTPException(status_code=422, detail="Trade counterparty must be a different team")
        try:
            focal_assets = tuple(resolve_owned_asset_ref(runtime.league_state, team_id=runtime.selected_team_id, asset_ref=ref) for ref in request.focal_asset_refs)
            counterparty_assets = tuple(resolve_owned_asset_ref(runtime.league_state, team_id=request.counterparty_team_id, asset_ref=ref) for ref in request.counterparty_asset_refs)
            draft = TradeDraft(
                draft_id=f"product:{runtime.league_state.state_id}:{runtime.selected_team_id}:{request.counterparty_team_id}",
                focal_team_id=runtime.selected_team_id,
                counterparty_team_id=request.counterparty_team_id,
                focal_side=TradeDraftSide(team_id=runtime.selected_team_id, assets=focal_assets),
                counterparty_side=TradeDraftSide(team_id=request.counterparty_team_id, assets=counterparty_assets),
            )
            proposal = submit_trade_draft(draft, as_of=runtime.league_state.as_of)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if trade_evaluator is None:
            raise HTTPException(status_code=409, detail="Trade analysis runtime is not configured yet")
        return trade_evaluator(runtime.league_state, proposal, runtime.selected_team_id)

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

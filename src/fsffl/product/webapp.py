from __future__ import annotations

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

from .dashboard import build_league_metric_chart
from .runtime import PrivateBetaRuntimeStore, default_sleeper_state_loader
from .team_page import build_state_only_team_view


_STATIC_DIR = Path(__file__).with_name("static")
_security = HTTPBasic(auto_error=False)
LeagueViewProvider = Callable[[], LeagueAnalyticsView | None]
StateLoader = Callable[[str], LeagueState]


class ConnectSleeperLeagueRequest(FrozenModel):
    league_external_id: str


class SelectTeamRequest(FrozenModel):
    team_id: str


def _beta_auth_enabled() -> bool:
    return os.getenv("FSFFL_BETA_AUTH", "0").strip().lower() in {"1", "true", "yes", "on"}


def require_beta_user(
    credentials: HTTPBasicCredentials | None = Depends(_security),
) -> str:
    """Protect the private beta when FSFFL_BETA_AUTH is enabled."""

    if not _beta_auth_enabled():
        return "local-beta-user"
    expected_username = os.getenv("FSFFL_BETA_USERNAME")
    expected_password = os.getenv("FSFFL_BETA_PASSWORD")
    if not expected_username or not expected_password:
        raise RuntimeError("beta auth is enabled but runtime credentials are not configured")
    valid = (
        credentials is not None
        and secrets.compare_digest(credentials.username, expected_username)
        and secrets.compare_digest(credentials.password, expected_password)
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
    return {
        "user_id": user_id,
        "league_id": league_state.league.league_id if league_state is not None else None,
        "league_name": league_state.league.name if league_state is not None else None,
        "team_id": runtime.selected_team_id,
        "state_id": league_state.state_id if league_state is not None else None,
        "evidence_as_of": league_state.as_of.isoformat() if league_state is not None else None,
        "teams": ([{"team_id": team.team_id, "display_name": team.display_name} for team in league_state.teams] if league_state is not None else []),
        "product_version": "next8-product-v1",
    }


def create_app(
    *,
    league_view_provider: LeagueViewProvider | None = None,
    runtime_store: PrivateBetaRuntimeStore | None = None,
    state_loader: StateLoader = default_sleeper_state_loader,
) -> FastAPI:
    application = FastAPI(title="FSFFL NEXT Private Beta", version="next8-beta-v1", docs_url="/api/docs", redoc_url=None)
    store = runtime_store or PrivateBetaRuntimeStore()
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

    @application.get("/api/my-team")
    def my_team(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        runtime = store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if runtime.selected_team_id is None:
            raise HTTPException(status_code=409, detail="No managed team is selected")
        return build_state_only_team_view(runtime.league_state, team_id=runtime.selected_team_id).model_dump(mode="json")

    @application.get("/api/league/chart")
    def league_chart(metric: LeagueMetric, _: str = Depends(require_beta_user)) -> dict[str, object]:
        if league_view_provider is None:
            raise HTTPException(status_code=409, detail="League analytics are not available yet")
        view = league_view_provider()
        if view is None:
            raise HTTPException(status_code=409, detail="League analytics are not loaded")
        return build_league_metric_chart(view, metric=metric).model_dump(mode="json")

    return application


app = create_app()

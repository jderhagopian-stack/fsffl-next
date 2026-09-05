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

from .dashboard import build_league_metric_chart


_STATIC_DIR = Path(__file__).with_name("static")
_security = HTTPBasic(auto_error=False)
LeagueViewProvider = Callable[[], LeagueAnalyticsView | None]


def _beta_auth_enabled() -> bool:
    return os.getenv("FSFFL_BETA_AUTH", "0").strip().lower() in {"1", "true", "yes", "on"}


def require_beta_user(
    credentials: HTTPBasicCredentials | None = Depends(_security),
) -> str:
    """Protect the private beta when FSFFL_BETA_AUTH is enabled.

    Credentials are runtime secrets supplied through environment variables and
    never stored in source control. Local development may leave auth disabled.
    """

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


def create_app(*, league_view_provider: LeagueViewProvider | None = None) -> FastAPI:
    application = FastAPI(
        title="FSFFL NEXT Private Beta",
        version="next8-beta-v1",
        docs_url="/api/docs",
        redoc_url=None,
    )

    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "product": "fsffl-next", "version": "next8-beta-v1"}

    @application.get("/")
    def index(_: str = Depends(require_beta_user)) -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    @application.get("/api/product-context")
    def product_context(user_id: str = Depends(require_beta_user)) -> dict[str, object]:
        view = league_view_provider() if league_view_provider is not None else None
        return {
            "user_id": user_id,
            "league_id": view.context.league_id if view is not None else None,
            "team_id": None,
            "state_id": view.context.league_state_id if view is not None else None,
            "evidence_as_of": view.context.as_of.isoformat() if view is not None else None,
            "product_version": "next8-product-v1",
        }

    @application.get("/api/league/chart")
    def league_chart(
        metric: LeagueMetric,
        _: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        if league_view_provider is None:
            raise HTTPException(status_code=409, detail="No league analytics provider is configured")
        view = league_view_provider()
        if view is None:
            raise HTTPException(status_code=409, detail="No league analytics are loaded")
        return build_league_metric_chart(view, metric=metric).model_dump(mode="json")

    return application


app = create_app()

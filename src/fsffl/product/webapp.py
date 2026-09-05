from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles


_STATIC_DIR = Path(__file__).with_name("static")
_security = HTTPBasic(auto_error=False)


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


def create_app() -> FastAPI:
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
        # Runtime league/team selection will replace these nulls. The endpoint is
        # intentionally identity/context-only and contains no model calculation.
        return {
            "user_id": user_id,
            "league_id": None,
            "team_id": None,
            "state_id": None,
            "product_version": "next8-product-v1",
        }

    return application


app = create_app()

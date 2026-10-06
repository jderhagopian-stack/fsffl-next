from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.foundation4_shadow_routes import install_career_intrinsic_routes
from fsffl.product.intrinsic_background import IntrinsicBuildStatus
from fsffl.product.webapp import require_beta_user


def test_dynasty_route_rejects_captured_stale_state_presentation_fallback() -> None:
    target_state_id = "ee05aa91bd112f40542327a537e24a0efed619dfa307bf0bb9983bfea3176ca2"
    stale_state_id = "3d7808d45587314cafa3e8fb1e694a57158cd16524b2c2a86b9dfb0e5b5176bf"
    target_generation_id = "94543b5881a35a381c3766b2a8f1acb1a7229fe19626fe3e4b327b3e489de788"
    context = SimpleNamespace(
        league_state=SimpleNamespace(
            state_id=target_state_id,
            league=SimpleNamespace(league_id="captured-league"),
            as_of=datetime(2026, 10, 6, tzinfo=timezone.utc),
        ),
        selected_team_id="captured-team",
        publication_generation_id=target_generation_id,
    )
    runtime_store = SimpleNamespace(get=lambda _user_id: context)
    request_calls: list[object] = []

    def request(current_context):
        request_calls.append(current_context)
        return SimpleNamespace(
            status=IntrinsicBuildStatus.QUEUED,
            league_state_id=target_state_id,
            intrinsic_input_fingerprint="current-input",
        )

    coordinator = SimpleNamespace(current=lambda _context: None, request=request)
    stale_payload = {
        "status": "ready",
        "capability": "career_intrinsic",
        "league_id": "captured-league",
        "league_state_id": stale_state_id,
        "publication_generation_id": "verified-last-good-generation",
        "rooms": [{"position": "QB", "value": 123.0}],
    }
    app = FastAPI()
    app.dependency_overrides[require_beta_user] = lambda: "user-1"
    install_career_intrinsic_routes(
        app,
        runtime_store=runtime_store,
        loader=None,
        coordinator=coordinator,
        presentation_payload_loader=lambda _user, _context, _surface: stale_payload,
    )

    response = TestClient(app).get(
        "/api/league/dynasty-position-rooms",
        params={"state_id": target_state_id, "publication_generation_id": target_generation_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "preparing"
    assert payload["league_state_id"] == target_state_id
    assert payload["publication_generation_id"] == target_generation_id
    assert "rooms" not in payload
    assert request_calls == [context]


def test_dynasty_request_for_visible_publication_a_is_superseded_when_runtime_is_b() -> None:
    atlas_state_id = "3d7808d45587314cafa3e8fb1e694a57158cd16524b2c2a86b9dfb0e5b5176bf"
    atlas_generation_id = "da5a06b340a8ab7868f1876a91500d53b6da67c89338185d7944fa8eace8a8ab"
    runtime_state_id = "e582e5ce160226c0ab65f88277c12d5dd4b957a97eacc4d70841f6f360f3a21d"
    runtime_generation_id = "runtime-generation-b"
    context = SimpleNamespace(
        league_state=SimpleNamespace(
            state_id=runtime_state_id,
            league=SimpleNamespace(league_id="captured-league"),
            as_of=datetime(2026, 10, 6, tzinfo=timezone.utc),
        ),
        selected_team_id="captured-team",
        publication_generation_id=runtime_generation_id,
    )
    calls: list[str] = []
    coordinator = SimpleNamespace(
        current=lambda _context: calls.append("current"),
        request=lambda _context: calls.append("request"),
    )
    loader_calls: list[str] = []
    app = FastAPI()
    app.dependency_overrides[require_beta_user] = lambda: "user-1"
    install_career_intrinsic_routes(
        app,
        runtime_store=SimpleNamespace(get=lambda _user_id: context),
        loader=None,
        coordinator=coordinator,
        presentation_payload_loader=lambda *_args: loader_calls.append("presentation"),
    )

    response = TestClient(app).get(
        "/api/league/dynasty-position-rooms",
        params={"state_id": atlas_state_id, "publication_generation_id": atlas_generation_id},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "superseded",
        "requested_state_id": atlas_state_id,
        "requested_publication_generation_id": atlas_generation_id,
        "superseding_state_id": runtime_state_id,
        "superseding_publication_generation_id": runtime_generation_id,
        "reason": "The League Atlas publication has advanced; promote Atlas before retrying.",
    }
    assert calls == []
    assert loader_calls == []


def test_dynasty_browser_sends_atlas_identity_and_promotes_on_superseded() -> None:
    source = (
        Path(__file__).parents[1]
        / "src/fsffl/product/static/league_comparison.js"
    ).read_text(encoding="utf-8")

    assert "new URLSearchParams({state_id:requestedStateId||'',publication_generation_id:requestedGeneration||''})" in source
    assert "`/api/league/dynasty-position-rooms?${query}`" in source
    assert "if(payload?.status==='superseded')" in source
    assert "await loadContext()" in source

from __future__ import annotations

from datetime import datetime, timezone
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

    response = TestClient(app).get("/api/league/dynasty-position-rooms")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "preparing"
    assert payload["league_state_id"] == target_state_id
    assert payload["publication_generation_id"] == target_generation_id
    assert "rooms" not in payload
    assert request_calls == [context]

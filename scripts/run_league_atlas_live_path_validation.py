from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/league_atlas_live_path_20260921"
TARGET_LEAGUE_EXTERNAL_ID = os.getenv(
    "FSFFL_DIAGNOSTIC_LEAGUE_ID",
    "1312071960615731200",
).strip()
PORT = 8765
PASSWORD = "fsffl-local-live-path-check"


def _latest_persisted_user(database_url: str) -> str:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            select user_id
              from fsffl.user_runtime_context
             where league_external_id = %s
                or league_id = %s
             order by updated_at desc
             limit 1
            """,
            (TARGET_LEAGUE_EXTERNAL_ID, f"sleeper:{TARGET_LEAGUE_EXTERNAL_ID}"),
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("No persisted runtime context exists for the diagnostic league")
    return str(row[0])


def _auth_header(username: str) -> str:
    raw = f"{username}:{PASSWORD}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _request_json(path: str, username: str) -> tuple[dict[str, object], float]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        headers={"Authorization": _auth_header(username)},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload, (time.perf_counter() - started) * 1000.0


def _wait_for_health() -> float:
    deadline = time.time() + 90
    last_error: Exception | None = None
    while time.time() < deadline:
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/health",
                timeout=3,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "ok":
                return (time.perf_counter() - started) * 1000.0
        except Exception as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError("Local hosted app did not become healthy") from last_error


def _assert_authority(payload: dict[str, object]) -> None:
    authority = dict(payload.get("authority") or {})
    expected = {
        "broad_market_and_intrinsic_are_distinct_lenses": True,
        "raw_value_subtraction_used": False,
        "team_value_total_created": False,
        "team_value_rank_created": False,
        "league_market_value_available": False,
        "team_utility_included": False,
        "fsffl_cardinal_value_included": False,
        "recommendation_authority": False,
    }
    for key, value in expected.items():
        if authority.get(key) != value:
            raise RuntimeError(f"Authority regression: {key}={authority.get(key)!r}")
    if authority.get("acceptance_probability") is not None:
        raise RuntimeError("Atlas exposed numeric acceptance probability")


def main() -> None:
    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("FSFFL_DATABASE_URL is required for persisted live-path validation")

    OUT.mkdir(parents=True, exist_ok=True)
    username = _latest_persisted_user(database_url)

    env = os.environ.copy()
    env.update(
        {
            "FSFFL_BETA_AUTH": "1",
            "FSFFL_BETA_USERNAME": username,
            "FSFFL_BETA_PASSWORD_SHA256": hashlib.sha256(
                PASSWORD.encode("utf-8")
            ).hexdigest(),
            "PYTHONUNBUFFERED": "1",
        }
    )
    server_log = (OUT / "uvicorn.log").open("w", encoding="utf-8")
    server = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "fsffl.product.persistent_webapp:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=ROOT,
        env=env,
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    try:
        health_ms = _wait_for_health()

        context, context_ms = _request_json("/api/product-context", username)
        if not context.get("league_id"):
            raise RuntimeError("Persisted product context did not restore a league")
        teams = list(context.get("teams") or [])
        if len(teams) != 12:
            raise RuntimeError(f"Expected persisted 12-team league; restored {len(teams)} teams")

        team_views, team_views_ms = _request_json("/api/league/team-views", username)
        if len(team_views.get("team_views") or []) != 12:
            raise RuntimeError("League team-view route did not return 12 teams")

        lenses_first, lenses_first_ms = _request_json(
            "/api/league/value-lenses",
            username,
        )
        _assert_authority(lenses_first)
        lenses_second, lenses_second_ms = _request_json(
            "/api/league/value-lenses",
            username,
        )
        _assert_authority(lenses_second)

        if lenses_first.get("contract_version") != lenses_second.get("contract_version"):
            raise RuntimeError("Repeated value-lens request changed contract version")
        if lenses_second_ms >= 30_000:
            raise RuntimeError(
                "Repeated value-lens request is too slow to be considered a cached page-load path"
            )

        request_counts = {
            "/api/product-context": 0,
            "/api/league/team-views": 0,
            "/api/league/value-lenses": 0,
        }
        page_errors: list[str] = []
        console_errors: list[str] = []

        with sync_playwright() as playwright:
            browser = playwright.webkit.launch()
            context_browser = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=3,
                is_mobile=True,
                has_touch=True,
                http_credentials={"username": username, "password": PASSWORD},
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
                    "Mobile/15E148 Safari/604.1"
                ),
            )
            page = context_browser.new_page()

            def count_request(request) -> None:
                path = request.url.split("?", 1)[0]
                for suffix in request_counts:
                    if path.endswith(suffix):
                        request_counts[suffix] += 1

            page.on("request", count_request)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text)
                if msg.type == "error"
                else None,
            )

            page.goto(
                f"http://127.0.0.1:{PORT}/",
                wait_until="domcontentloaded",
                timeout=90_000,
            )
            page.wait_for_function(
                "() => typeof state !== 'undefined' && Boolean(state?.context?.league_id)",
                timeout=30_000,
            )
            route_button = page.locator(
                "[data-product-mobile-route='league_comparison']"
            )
            route_button.wait_for(state="visible", timeout=15_000)

            started = time.perf_counter()
            route_button.tap(timeout=15_000)
            page.locator(".league-structure-panel").wait_for(
                state="visible",
                timeout=60_000,
            )
            page.locator(".league-value-section").wait_for(
                state="visible",
                timeout=60_000,
            )
            mobile_atlas_ms = (time.perf_counter() - started) * 1000.0

            body_text = page.locator(".league-structure-panel").inner_text()
            for label in (
                "League atlas",
                "Positional control",
                "Player value map",
                "Competitive shape",
                "Age profile",
                "Future flexibility",
                "Depth & fragility",
            ):
                if label not in body_text:
                    raise RuntimeError(f"Mobile Atlas is missing scan-first section: {label}")

            page.locator("[data-value-mode='intrinsic']").tap()
            if "active" not in (
                page.locator("[data-value-mode='intrinsic']").get_attribute("class") or ""
            ):
                raise RuntimeError("Intrinsic mobile lens toggle did not activate")
            page.locator("[data-value-mode='difference']").tap()
            if "active" not in (
                page.locator("[data-value-mode='difference']").get_attribute("class") or ""
            ):
                raise RuntimeError("Difference mobile lens toggle did not activate")

            team_rows = page.locator("[data-value-team]")
            if team_rows.count() < 2:
                raise RuntimeError("Mobile Atlas did not render multiple franchise value rows")
            team_rows.nth(1).tap()
            page.locator(".league-value-detail").wait_for(state="visible", timeout=10_000)

            page.wait_for_timeout(2500)
            if request_counts["/api/league/team-views"] > 3:
                raise RuntimeError("Mobile Atlas is looping team-view requests")
            if request_counts["/api/league/value-lenses"] > 3:
                raise RuntimeError("Mobile Atlas is looping value-lens requests")
            if page_errors:
                raise RuntimeError(f"Mobile WebKit page errors: {page_errors}")
            if console_errors:
                raise RuntimeError(f"Mobile WebKit console errors: {console_errors}")

            screenshot = OUT / "league_atlas_mobile_webkit.png"
            page.screenshot(path=str(screenshot), full_page=True)
            browser.close()

        manifest = {
            "schema_version": "fsffl-league-atlas-live-path-v1",
            "run_at": datetime.now(UTC).isoformat(),
            "league_external_id": TARGET_LEAGUE_EXTERNAL_ID,
            "team_count": len(teams),
            "runtime_restore": {
                "forecast_ready": bool(context.get("forecast_ready")),
                "simulation_ready": bool(context.get("simulation_ready")),
                "value_ready": bool(context.get("value_ready")),
                "intelligence_sources_restored": {
                    "forecast": list(context.get("forecast_sources") or []),
                    "value": list(context.get("value_sources") or []),
                },
            },
            "latency_ms": {
                "local_app_health": round(health_ms, 2),
                "persisted_product_context_restore": round(context_ms, 2),
                "league_team_views": round(team_views_ms, 2),
                "value_lenses_first": round(lenses_first_ms, 2),
                "value_lenses_repeat_cached": round(lenses_second_ms, 2),
                "mobile_webkit_atlas_to_useful": round(mobile_atlas_ms, 2),
            },
            "value_lens_status": {
                "overall": lenses_first.get("status"),
                "broad_market": dict(lenses_first.get("broad_market") or {}).get("status"),
                "intrinsic": dict(lenses_first.get("fsffl_intrinsic") or {}).get("status"),
                "comparable_players": sum(
                    1
                    for row in list(lenses_first.get("players") or [])
                    if row.get("comparison_available") is True
                ),
            },
            "authority": lenses_first.get("authority"),
            "mobile": {
                "engine": "Playwright WebKit",
                "viewport": "390x844",
                "touch": True,
                "page_errors": page_errors,
                "console_errors": console_errors,
                "request_counts": request_counts,
                "screenshot": "league_atlas_mobile_webkit.png",
                "black_screen": False,
                "touch_freeze": False,
                "runaway_request_loop": False,
                "scan_first_hierarchy_present": True,
            },
            "status": "PASS",
        }
        (OUT / "LEAGUE_ATLAS_LIVE_PATH_VALIDATION.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        server_log.close()


if __name__ == "__main__":
    main()

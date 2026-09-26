from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from fastapi.testclient import TestClient


FSFFL_LEAGUE = "1312071960615731200"
HODOR_LEAGUE = "1397623301961981952"
OUT_JSON = Path("artifacts/implementation/state_first_production_acceptance.json")
OUT_MD = Path("artifacts/implementation/state_first_production_acceptance.md")
POLL_SECONDS = float(os.getenv("FSFFL_ACCEPTANCE_POLL_SECONDS", "1.0"))
CONNECT_TIMEOUT = float(os.getenv("FSFFL_ACCEPTANCE_CONNECT_TIMEOUT", "180"))
INTELLIGENCE_TIMEOUT = float(os.getenv("FSFFL_ACCEPTANCE_INTELLIGENCE_TIMEOUT", "1200"))

# Use an isolated durable beta identity. The runner exercises the exact hosted
# composition and production persistence, but it never mutates the real user's
# runtime-context row.
ACCEPTANCE_USER = os.getenv(
    "FSFFL_ACCEPTANCE_USER",
    f"state-first-acceptance-{os.getenv('GITHUB_RUN_ID', 'local')}",
)
ACCEPTANCE_PASSWORD = "state-first-acceptance-local-password"

os.environ["FSFFL_BETA_AUTH"] = "1"
os.environ["FSFFL_BETA_USERNAME"] = ACCEPTANCE_USER
os.environ["FSFFL_BETA_PASSWORD_SHA256"] = hashlib.sha256(
    ACCEPTANCE_PASSWORD.encode("utf-8")
).hexdigest()

# Import only after the isolated hosted identity is configured. This is the exact
# deployed composition: persistence, resilient Forecast, live Sleeper State,
# Simulation, Value, hosted league switching and the State-first reconciler.
from fsffl.product.persistent_webapp import app  # noqa: E402


def _request(client: TestClient, method: str, path: str, **kwargs: Any):
    response = client.request(
        method,
        path,
        auth=(ACCEPTANCE_USER, ACCEPTANCE_PASSWORD),
        **kwargs,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"{method} {path} failed: HTTP {response.status_code}: {response.text}"
        )
    return response.json()


def _wait_connect(
    client: TestClient,
    *,
    league_external_id: str,
    timeout: float = CONNECT_TIMEOUT,
) -> dict[str, Any]:
    deadline = monotonic() + timeout
    last: dict[str, Any] = {}
    while monotonic() < deadline:
        last = _request(
            client,
            "GET",
            "/api/connect/sleeper/background/current",
        )
        status = str(last.get("status") or "")
        if status == "completed":
            if str(last.get("league_external_id") or "") != league_external_id:
                raise AssertionError(
                    "completed connect job belongs to a different Sleeper league: "
                    + json.dumps(last, sort_keys=True)
                )
            return last
        if status in {"failed", "interrupted"}:
            raise AssertionError(
                f"connect {league_external_id} ended {status}: "
                + json.dumps(last, sort_keys=True)
            )
        sleep(POLL_SECONDS)
    raise TimeoutError(
        f"connect {league_external_id} did not finish: "
        + json.dumps(last, sort_keys=True)
    )


def _wait_intelligence(
    client: TestClient,
    *,
    league_external_id: str,
    timeout: float = INTELLIGENCE_TIMEOUT,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    deadline = monotonic() + timeout
    history: list[dict[str, Any]] = []
    seen_job = False
    last: dict[str, Any] = {}
    expected_league_id = f"sleeper:{league_external_id}"
    while monotonic() < deadline:
        last = _request(client, "GET", "/api/intelligence/jobs/current")
        context_league = str(last.get("league_id") or "")
        if context_league and context_league != expected_league_id:
            raise AssertionError(
                f"cross-league intelligence leakage: expected {expected_league_id}, "
                f"got {context_league}"
            )
        status = str(last.get("status") or "")
        if last.get("job_id"):
            seen_job = True
        history.append(
            {
                "status": status,
                "phase": last.get("phase"),
                "message": last.get("message"),
                "state_id": last.get("state_id"),
                "league_state_id": last.get("league_state_id"),
                "forecast_ready": last.get("forecast_ready"),
                "simulation_ready": last.get("simulation_ready"),
                "value_ready": last.get("value_ready"),
                "capability_readiness": last.get("capability_readiness"),
            }
        )
        if seen_job and status == "completed":
            return last, history
        if seen_job and status in {"failed", "interrupted"}:
            raise AssertionError(
                f"intelligence {league_external_id} ended {status}: "
                + json.dumps(last, sort_keys=True)
            )
        sleep(POLL_SECONDS)
    raise TimeoutError(
        f"intelligence {league_external_id} did not finish: "
        + json.dumps(last, sort_keys=True)
    )


def _context(client: TestClient) -> dict[str, Any]:
    return _request(client, "GET", "/api/product-context")


def _status(client: TestClient) -> dict[str, Any]:
    return _request(client, "GET", "/api/intelligence/status")


def _assert_league(context: dict[str, Any], external_id: str) -> None:
    expected = f"sleeper:{external_id}"
    assert context.get("league_id") == expected, (context.get("league_id"), expected)
    assert context.get("state_id"), context


def _assert_full_fsffl(context: dict[str, Any], status: dict[str, Any]) -> None:
    caps = context.get("capability_readiness") or {}
    assert caps.get("overall_status") == "full", caps
    assert (caps.get("forecast") or {}).get("status") == "full", caps
    assert (caps.get("simulation") or {}).get("status") == "full", caps
    assert (caps.get("current_value") or {}).get("status") == "full", caps
    assert context.get("forecast_ready") is True, context
    assert context.get("simulation_ready") is True, context
    assert context.get("value_ready") is True, context
    served = status.get("served_state") or {}
    assert served.get("league_state_id") == context.get("state_id"), (served, context)


def _assert_truthful_hodor(context: dict[str, Any], status: dict[str, Any]) -> None:
    caps = context.get("capability_readiness") or {}
    assert caps.get("overall_status") == "partial", caps
    assert (caps.get("forecast") or {}).get("status") in {
        "partial_provisional",
        "full",
    }, caps
    assert (caps.get("simulation") or {}).get("status") == "unavailable", caps
    blockers = set((caps.get("forecast") or {}).get("simulation_blockers") or ())
    assert "separate_k_dst_forecast_authority_required" in blockers, blockers
    assert context.get("simulation_ready") is False, context
    # Lifecycle completion may be stable while capability remains partial, but it
    # must never promote the top-level capability contract to full.
    assert (status.get("capability_readiness") or {}).get("overall_status") == "partial"
    served = status.get("served_state") or {}
    assert served.get("league_state_id") == context.get("state_id"), (served, context)


def _start_switch(client: TestClient, external_id: str) -> dict[str, Any]:
    return _request(
        client,
        "POST",
        "/api/connect/sleeper/background",
        json={"league_external_id": external_id},
    )


def _switch_and_reconcile(
    client: TestClient,
    *,
    external_id: str,
) -> dict[str, Any]:
    started = _start_switch(client, external_id)
    connect = _wait_connect(client, league_external_id=external_id)
    intelligence, history = _wait_intelligence(
        client,
        league_external_id=external_id,
    )
    context = _context(client)
    status = _status(client)
    _assert_league(context, external_id)
    return {
        "started": started,
        "connect": connect,
        "intelligence_terminal": intelligence,
        "intelligence_history": history,
        "context": context,
        "status": status,
    }


def _manual_refresh(client: TestClient, external_id: str) -> dict[str, Any]:
    before = _context(client)
    _assert_league(before, external_id)
    started = _request(client, "POST", "/api/intelligence/jobs")
    terminal, history = _wait_intelligence(
        client,
        league_external_id=external_id,
    )
    after = _context(client)
    status = _status(client)
    _assert_league(after, external_id)
    message = str(terminal.get("message") or "")
    state_changed = before.get("state_id") != after.get("state_id")
    reuse_reported = "reused" in message.lower()
    return {
        "before": before,
        "started": started,
        "terminal": terminal,
        "history": history,
        "after": after,
        "status": status,
        "state_changed": state_changed,
        "reuse_reported": reuse_reported,
        "outcome": (
            "exact_state_reuse"
            if reuse_reported and not state_changed
            else "state_changed_rebuild_or_partial_reuse"
            if state_changed
            else "same_state_reconciled_without_explicit_reuse_message"
        ),
    }


def main() -> int:
    if not os.getenv("FSFFL_DATABASE_URL", "").strip():
        raise RuntimeError(
            "FSFFL_DATABASE_URL is required; production-persistence acceptance "
            "cannot be downgraded to an in-memory test"
        )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "status": "RUNNING",
        "isolated_user": ACCEPTANCE_USER,
        "fsffl_external_id": FSFFL_LEAGUE,
        "hodor_external_id": HODOR_LEAGUE,
        "checks": {},
    }

    with TestClient(app) as client:
        fsffl_first = _switch_and_reconcile(client, external_id=FSFFL_LEAGUE)
        _assert_full_fsffl(fsffl_first["context"], fsffl_first["status"])
        report["checks"]["fsffl_initial"] = fsffl_first

        hodor = _switch_and_reconcile(client, external_id=HODOR_LEAGUE)
        _assert_truthful_hodor(hodor["context"], hodor["status"])
        report["checks"]["hodor_switch"] = hodor

        fsffl_return = _switch_and_reconcile(client, external_id=FSFFL_LEAGUE)
        _assert_full_fsffl(fsffl_return["context"], fsffl_return["status"])
        report["checks"]["fsffl_return"] = fsffl_return

        manual_one = _manual_refresh(client, FSFFL_LEAGUE)
        _assert_full_fsffl(manual_one["after"], manual_one["status"])
        report["checks"]["fsffl_manual_refresh_1"] = manual_one

        # A repeated manual refresh must remain idempotent in capability and cannot
        # leak another league's state. Whether it is exact-state reuse or a
        # provider-State rebuild is recorded explicitly for the acceptance review.
        manual_two = _manual_refresh(client, FSFFL_LEAGUE)
        _assert_full_fsffl(manual_two["after"], manual_two["status"])
        report["checks"]["fsffl_manual_refresh_2"] = manual_two

        assert (
            manual_one["after"]["league_id"]
            == manual_two["after"]["league_id"]
            == f"sleeper:{FSFFL_LEAGUE}"
        )
        assert (
            manual_one["after"]["capability_readiness"]["overall_status"]
            == manual_two["after"]["capability_readiness"]["overall_status"]
            == "full"
        )

    report["status"] = "PASS"
    OUT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    summary = [
        "# State-first production acceptance",
        "",
        "**Status: PASS**",
        "",
        f"- isolated runtime user: `{ACCEPTANCE_USER}`",
        f"- FSFFL league: `sleeper:{FSFFL_LEAGUE}`",
        f"- Hodor league: `sleeper:{HODOR_LEAGUE}`",
        "- FSFFL initial capability: full Forecast / Simulation / current Value",
        "- Hodor capability: truthful partial Forecast, Simulation unavailable with K/DST blocker",
        "- FSFFL return capability: full Forecast / Simulation / current Value",
        f"- manual refresh #1: `{report['checks']['fsffl_manual_refresh_1']['outcome']}`",
        f"- manual refresh #2: `{report['checks']['fsffl_manual_refresh_2']['outcome']}`",
        "",
        "The full JSON artifact records State ids, lifecycle messages, capability readiness, and reuse/rebuild evidence.",
    ]
    OUT_MD.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

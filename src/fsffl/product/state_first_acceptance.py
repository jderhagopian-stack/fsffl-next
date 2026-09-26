from __future__ import annotations

import json
import logging
from time import monotonic, sleep
from typing import Callable

from fsffl.state.models import LeagueState

from .background_jobs import IntelligenceJobCoordinator, IntelligenceJobStatus
from .persistent_runtime import PersistentPrivateBetaRuntimeStore


_logger = logging.getLogger("uvicorn.error")
FSFFL_ACCEPTANCE_LEAGUE = "1312071960615731200"
HODOR_ACCEPTANCE_LEAGUE = "1397623301961981952"


class StateFirstAcceptanceError(RuntimeError):
    pass


def _wait_for_job(
    *,
    jobs: IntelligenceJobCoordinator,
    user_id: str,
    job_id: str,
    timeout_seconds: float,
    poll_seconds: float,
) -> dict[str, object]:
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        current = jobs.current(user_id)
        if current is None:
            sleep(poll_seconds)
            continue
        if current.job_id != job_id:
            raise StateFirstAcceptanceError(
                f"acceptance job identity changed {job_id} -> {current.job_id}"
            )
        if current.status == IntelligenceJobStatus.COMPLETED:
            return {
                "job_id": current.job_id,
                "status": current.status.value,
                "phase": current.phase.value,
                "message": current.message,
                "error": current.error,
                "league_state_id": current.league_state_id,
            }
        if current.status in {
            IntelligenceJobStatus.FAILED,
            IntelligenceJobStatus.INTERRUPTED,
        }:
            raise StateFirstAcceptanceError(
                f"acceptance job {current.job_id} ended {current.status.value}: "
                f"{current.error or current.message}"
            )
        sleep(poll_seconds)
    raise StateFirstAcceptanceError(f"acceptance job {job_id} timed out")


def _snapshot(
    store: PersistentPrivateBetaRuntimeStore,
    user_id: str,
    capability_reader: Callable[[object], dict[str, object]],
) -> dict[str, object]:
    runtime = store.get(user_id)
    state = runtime.league_state
    evidence = runtime.forecast_evidence
    runtime_result = getattr(evidence, "runtime_result", None)
    return {
        "league_id": state.league.league_id if state is not None else None,
        "state_id": state.state_id if state is not None else None,
        "state_as_of": state.as_of.isoformat() if state is not None else None,
        "forecast": evidence is not None,
        "simulation": runtime.simulation_analytics is not None,
        "value": runtime.value_evidence is not None,
        "intelligence_reused": runtime.intelligence_reused,
        "forecast_evidence_basis": getattr(evidence, "evidence_basis", None),
        "forecast_runtime_model_version": getattr(runtime_result, "model_version", None),
        "fumbles_lost_supplement": {
            "authority_fingerprint": getattr(
                runtime_result,
                "fumbles_lost_supplement_authority_fingerprint",
                None,
            ),
            "player_count": int(
                getattr(runtime_result, "fumbles_lost_supplement_player_count", 0)
                or 0
            ),
            "failure": getattr(
                runtime_result,
                "fumbles_lost_supplement_failure",
                None,
            ),
        },
        "capability_readiness": capability_reader(runtime),
    }


def _require_full_fsffl(snapshot: dict[str, object]) -> None:
    if snapshot.get("league_id") != f"sleeper:{FSFFL_ACCEPTANCE_LEAGUE}":
        raise StateFirstAcceptanceError(f"wrong FSFFL league identity: {snapshot}")
    caps = snapshot.get("capability_readiness") or {}
    if not isinstance(caps, dict) or caps.get("overall_status") != "full":
        raise StateFirstAcceptanceError(
            f"FSFFL did not reach full capability: {snapshot}"
        )
    for key in ("forecast", "simulation", "current_value"):
        row = caps.get(key) or {}
        if not isinstance(row, dict) or row.get("status") != "full":
            raise StateFirstAcceptanceError(
                f"FSFFL {key} was not full: {snapshot}"
            )
    supplement = snapshot.get("fumbles_lost_supplement") or {}
    if (
        not isinstance(supplement, dict)
        or not supplement.get("authority_fingerprint")
        or int(supplement.get("player_count") or 0) <= 0
        or supplement.get("failure") is not None
    ):
        raise StateFirstAcceptanceError(
            f"FSFFL first-party FUMBLES_LOST was not consumed: {snapshot}"
        )


def _require_truthful_hodor(snapshot: dict[str, object]) -> None:
    if snapshot.get("league_id") != f"sleeper:{HODOR_ACCEPTANCE_LEAGUE}":
        raise StateFirstAcceptanceError(f"wrong Hodor league identity: {snapshot}")
    caps = snapshot.get("capability_readiness") or {}
    if not isinstance(caps, dict) or caps.get("overall_status") != "partial":
        raise StateFirstAcceptanceError(
            f"Hodor must remain truthful partial authority: {snapshot}"
        )
    simulation = caps.get("simulation") or {}
    if not isinstance(simulation, dict) or simulation.get("status") != "unavailable":
        raise StateFirstAcceptanceError(
            f"Hodor Simulation must remain unavailable: {snapshot}"
        )
    forecast = caps.get("forecast") or {}
    blockers = set(
        forecast.get("simulation_blockers") or ()
        if isinstance(forecast, dict)
        else ()
    )
    if "separate_k_dst_forecast_authority_required" not in blockers:
        raise StateFirstAcceptanceError(
            f"Hodor K/DST blocker was not explicit: {snapshot}"
        )


def run_state_first_production_acceptance(
    *,
    store: PersistentPrivateBetaRuntimeStore,
    user_id: str,
    state_loader: Callable[[str], LeagueState],
    start_reconciliation: Callable[[str], dict[str, object]],
    start_sync_reconciliation: Callable[[str], dict[str, object]],
    jobs: IntelligenceJobCoordinator,
    capability_reader: Callable[[object], dict[str, object]],
    timeout_seconds: float = 1200.0,
    poll_seconds: float = 1.0,
) -> dict[str, object]:
    """Exercise real State-first reuse/rebuild with an isolated production user."""

    report: dict[str, object] = {
        "status": "RUNNING",
        "user_id": user_id,
        "fsffl_external_id": FSFFL_ACCEPTANCE_LEAGUE,
        "hodor_external_id": HODOR_ACCEPTANCE_LEAGUE,
        "steps": [],
    }
    steps: list[dict[str, object]] = report["steps"]  # type: ignore[assignment]

    def activate(external_id: str, *, label: str) -> dict[str, object]:
        state = state_loader(external_id)
        expected = f"sleeper:{external_id}"
        if state.league.league_id != expected:
            raise StateFirstAcceptanceError(
                f"{label} provider returned {state.league.league_id}, expected {expected}"
            )
        store.set_league_state(user_id, state)
        wait_for_checkpoint = getattr(store, "wait_for_checkpoint", None)
        if callable(wait_for_checkpoint) and not wait_for_checkpoint(
            user_id, timeout=30.0
        ):
            raise StateFirstAcceptanceError(
                f"{label} canonical State did not durably checkpoint"
            )
        started = start_reconciliation(user_id)
        job_id = str(started.get("job_id") or "")
        if not job_id:
            raise StateFirstAcceptanceError(f"{label} did not start reconciliation")
        terminal = _wait_for_job(
            jobs=jobs,
            user_id=user_id,
            job_id=job_id,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        snapshot = _snapshot(store, user_id, capability_reader)
        row = {
            "label": label,
            "provider_state_id": state.state_id,
            "job": terminal,
            "snapshot": snapshot,
        }
        steps.append(row)
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE step=%s data=%s",
            label,
            json.dumps(row, sort_keys=True, default=str),
        )
        return snapshot

    fsffl_initial = activate(FSFFL_ACCEPTANCE_LEAGUE, label="fsffl_initial")
    _require_full_fsffl(fsffl_initial)

    hodor = activate(HODOR_ACCEPTANCE_LEAGUE, label="hodor_switch")
    _require_truthful_hodor(hodor)

    fsffl_return = activate(FSFFL_ACCEPTANCE_LEAGUE, label="fsffl_return")
    _require_full_fsffl(fsffl_return)

    for index in (1, 2):
        before = _snapshot(store, user_id, capability_reader)
        started = start_sync_reconciliation(user_id)
        job_id = str(started.get("job_id") or "")
        if not job_id:
            raise StateFirstAcceptanceError(
                f"manual refresh {index} did not start reconciliation"
            )
        terminal = _wait_for_job(
            jobs=jobs,
            user_id=user_id,
            job_id=job_id,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        after = _snapshot(store, user_id, capability_reader)
        _require_full_fsffl(after)
        state_changed = before.get("state_id") != after.get("state_id")
        message = str(terminal.get("message") or "")
        row = {
            "label": f"fsffl_manual_refresh_{index}",
            "before": before,
            "job": terminal,
            "after": after,
            "state_changed": state_changed,
            "reported_reuse": "reused" in message.lower(),
            "outcome": (
                "exact_state_reuse"
                if not state_changed and "reused" in message.lower()
                else "changed_state_rebuild_or_partial_reuse"
                if state_changed
                else "same_state_reconciled"
            ),
        }
        steps.append(row)
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE step=%s data=%s",
            row["label"],
            json.dumps(row, sort_keys=True, default=str),
        )

    report["status"] = "PASS"
    _logger.info(
        "FSFFL STATE-FIRST ACCEPTANCE RESULT %s",
        json.dumps(report, sort_keys=True, default=str),
    )
    return report

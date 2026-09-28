from __future__ import annotations

import json
import logging
from threading import Thread
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


SurfaceProbe = Callable[[str, object], dict[str, object]]
HistoryProbe = Callable[[str, object], dict[str, object]]
ResourceReader = Callable[[], dict[str, object]]
ProcessIdentityReader = Callable[[], str]


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
            "subject_universe_player_count": int(
                getattr(
                    runtime_result,
                    "fumbles_lost_subject_universe_player_count",
                    0,
                )
                or 0
            ),
            "provider_absent_player_ids": list(
                getattr(
                    runtime_result,
                    "fumbles_lost_provider_absent_player_ids",
                    (),
                )
                or ()
            ),
            "frozen_prior_absent_player_ids": list(
                getattr(
                    runtime_result,
                    "fumbles_lost_frozen_prior_absent_player_ids",
                    (),
                )
                or ()
            ),
            "omitted_player_ids": list(
                getattr(
                    runtime_result,
                    "fumbles_lost_omitted_player_ids",
                    (),
                )
                or ()
            ),
            "supplement_model_version": getattr(
                runtime_result,
                "fumbles_lost_supplement_model_version",
                None,
            ),
            "simulation_material_partial_player_ids": list(
                getattr(
                    runtime_result,
                    "simulation_material_partial_player_ids",
                    (),
                )
                or ()
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
        or int(supplement.get("subject_universe_player_count") or 0)
        != int(supplement.get("player_count") or 0)
        or bool(supplement.get("omitted_player_ids"))
        or bool(supplement.get("simulation_material_partial_player_ids"))
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
    surface_probe: SurfaceProbe | None = None,
    history_probe: HistoryProbe | None = None,
    resource_reader: ResourceReader | None = None,
    process_identity_reader: ProcessIdentityReader | None = None,
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
        "resources": [],
        "surface_probes": [],
        "history_probes": [],
    }
    steps: list[dict[str, object]] = report["steps"]  # type: ignore[assignment]
    resources: list[dict[str, object]] = report["resources"]  # type: ignore[assignment]
    surface_rows: list[dict[str, object]] = report["surface_probes"]  # type: ignore[assignment]
    history_rows: list[dict[str, object]] = report["history_probes"]  # type: ignore[assignment]
    process_identity_start = (
        process_identity_reader() if process_identity_reader is not None else None
    )
    report["process_identity_start"] = process_identity_start

    def sample_resources(label: str) -> dict[str, object] | None:
        if resource_reader is None:
            return None
        sample = {"label": label, **resource_reader()}
        resources.append(sample)
        if sample.get("within_memory_budget") is False:
            sample["soft_memory_budget_exceeded"] = True
            _logger.warning(
                "FSFFL STATE-FIRST ACCEPTANCE soft memory headroom target exceeded resource=%s data=%s",
                label,
                json.dumps(sample, sort_keys=True, default=str),
            )
        limit = int(sample.get("memory_limit_bytes") or 0)
        observed = max(
            int(sample.get("current_rss_bytes") or 0),
            int(sample.get("max_rss_observed_bytes") or 0),
            int(sample.get("peak_rss_bytes") or 0),
        )
        if limit > 0 and observed >= limit:
            raise StateFirstAcceptanceError(
                f"hard memory limit reached at {label}: {sample}"
            )
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE resource=%s data=%s",
            label,
            json.dumps(sample, sort_keys=True, default=str),
        )
        return sample

    def probe_surface(label: str) -> dict[str, object] | None:
        if surface_probe is None:
            return None
        row = {"label": label, **surface_probe(label, store.get(user_id))}
        surface_rows.append(row)
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE surface=%s data=%s",
            label,
            json.dumps(row, sort_keys=True, default=str),
        )
        return row

    def probe_history(label: str) -> dict[str, object] | None:
        if history_probe is None:
            return None
        row = {"label": label, **history_probe(label, store.get(user_id))}
        history_rows.append(row)
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE history=%s data=%s",
            label,
            json.dumps(row, sort_keys=True, default=str),
        )
        return row


    def activate(external_id: str, *, label: str) -> dict[str, object]:
        state = state_loader(external_id)
        expected = f"sleeper:{external_id}"
        if state.league.league_id != expected:
            raise StateFirstAcceptanceError(
                f"{label} provider returned {state.league.league_id}, expected {expected}"
            )
        store.set_league_state(user_id, state)
        current = store.get(user_id)
        if current.selected_team_id is None and state.teams:
            roster_by_team = {
                item.team_id: tuple(item.roster)
                for item in state.team_states
            }
            selected = next(
                (
                    team.team_id
                    for team in state.teams
                    if roster_by_team.get(team.team_id)
                ),
                state.teams[0].team_id,
            )
            store.select_team(user_id, selected)
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

        overlap_thread = None
        overlap_error: list[BaseException] = []
        if label == "fsffl_initial":
            # This is the historical failure shape: cold State reconciliation is
            # active while browser-equivalent surface reads and PI history are
            # requested. Reads must remain usable and heavy work must queue rather
            # than overlap unboundedly.
            probe_surface("cold_surfaces_during_initial_reconciliation")
            if history_probe is not None:
                def cold_history() -> None:
                    try:
                        probe_history("cold_pi_history_during_initial_reconciliation")
                    except BaseException as exc:  # pragma: no cover - hosted propagation
                        overlap_error.append(exc)

                overlap_thread = Thread(
                    target=cold_history,
                    name="fsffl-acceptance-cold-history",
                    daemon=True,
                )
                overlap_thread.start()

        terminal = _wait_for_job(
            jobs=jobs,
            user_id=user_id,
            job_id=job_id,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        if overlap_thread is not None:
            overlap_thread.join(timeout=timeout_seconds)
            if overlap_thread.is_alive():
                raise StateFirstAcceptanceError(
                    f"{label} cold PI history did not finish"
                )
            if overlap_error:
                raise StateFirstAcceptanceError(
                    f"{label} cold PI history failed: "
                    f"{type(overlap_error[0]).__name__}: {overlap_error[0]}"
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

    sample_resources("acceptance_start")
    fsffl_initial = activate(FSFFL_ACCEPTANCE_LEAGUE, label="fsffl_initial")
    _require_full_fsffl(fsffl_initial)
    sample_resources("fsffl_initial")
    probe_surface("initial_home_franchise_league")

    # Reproduce the availability incident shape: while a real State-first sync is
    # active, issue presentation reads and PI/history work. Heavy model work must
    # remain serialized by the process coordinator and the read path must stay usable.
    before_auto = _snapshot(store, user_id, capability_reader)
    started_auto = start_sync_reconciliation(user_id)
    auto_job_id = str(started_auto.get("job_id") or "")
    if not auto_job_id:
        raise StateFirstAcceptanceError("automatic State sync did not start reconciliation")
    history_box: dict[str, object] = {}
    history_error: list[BaseException] = []

    def run_history_overlap() -> None:
        try:
            row = probe_history("pi_history_during_active_reconciliation")
            if row is not None:
                history_box.update(row)
        except BaseException as exc:  # pragma: no cover - hosted diagnostic propagation
            history_error.append(exc)

    history_thread = None
    if history_probe is not None:
        history_thread = Thread(
            target=run_history_overlap,
            name="fsffl-acceptance-history-overlap",
            daemon=True,
        )
        history_thread.start()

    # Give the State-first worker a bounded opportunity to activate a newer State
    # before probing presentation continuity. If no material State change exists,
    # the same-State reuse path remains valid and no stale presentation is expected.
    state_change_deadline = monotonic() + min(60.0, timeout_seconds / 4)
    observed_state_change = False
    while monotonic() < state_change_deadline:
        current_state = store.get(user_id).league_state
        current_job = jobs.current(user_id)
        if (
            current_state is not None
            and current_state.state_id != before_auto.get("state_id")
        ):
            observed_state_change = True
            break
        if (
            current_job is not None
            and current_job.job_id == auto_job_id
            and current_job.status in {
                IntelligenceJobStatus.COMPLETED,
                IntelligenceJobStatus.FAILED,
                IntelligenceJobStatus.INTERRUPTED,
            }
        ):
            break
        sleep(poll_seconds)

    active_surface = probe_surface("reload_during_active_reconciliation")
    if observed_state_change and active_surface is not None:
        if not active_surface.get("presentation_snapshot_available"):
            raise StateFirstAcceptanceError(
                "changed-State reconciliation lost persisted last-good presentation"
            )
        if int(active_surface.get("stale_surface_count") or 0) < 5:
            raise StateFirstAcceptanceError(
                "changed-State reconciliation did not keep all primary stale surfaces usable: "
                f"{active_surface}"
            )

    auto_terminal = _wait_for_job(
        jobs=jobs,
        user_id=user_id,
        job_id=auto_job_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    if history_thread is not None:
        history_thread.join(timeout=timeout_seconds)
        if history_thread.is_alive():
            raise StateFirstAcceptanceError("PI history overlap did not finish")
    if history_error:
        raise StateFirstAcceptanceError(
            f"PI history overlap failed: {type(history_error[0]).__name__}: {history_error[0]}"
        )
    after_auto = _snapshot(store, user_id, capability_reader)
    _require_full_fsffl(after_auto)
    steps.append(
        {
            "label": "fsffl_automatic_state_sync",
            "before": before_auto,
            "job": auto_terminal,
            "after": after_auto,
            "observed_state_change": observed_state_change,
            "active_surface": active_surface,
        }
    )
    promoted_surface = probe_surface("post_reconciliation_promoted_surfaces")
    if promoted_surface is not None and int(
        promoted_surface.get("stale_surface_count") or 0
    ) != 0:
        raise StateFirstAcceptanceError(
            "new exact-State presentation was not atomically promoted: "
            f"{promoted_surface}"
        )
    sample_resources("after_automatic_state_sync")

    hodor = activate(HODOR_ACCEPTANCE_LEAGUE, label="hodor_switch")
    _require_truthful_hodor(hodor)
    probe_surface("hodor_home_franchise_league")
    sample_resources("hodor_switch")

    fsffl_return = activate(FSFFL_ACCEPTANCE_LEAGUE, label="fsffl_return")
    _require_full_fsffl(fsffl_return)
    probe_surface("fsffl_return_home_franchise_league")
    sample_resources("fsffl_return")
    probe_history("pi_history_repeat_after_fsffl_return")
    sample_resources("after_repeat_pi")

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

    sample_resources("acceptance_end")
    process_identity_end = (
        process_identity_reader() if process_identity_reader is not None else None
    )
    report["process_identity_end"] = process_identity_end
    if (
        process_identity_start is not None
        and process_identity_end is not None
        and process_identity_start != process_identity_end
    ):
        raise StateFirstAcceptanceError(
            "hosted process identity changed during acceptance journey: "
            f"{process_identity_start} -> {process_identity_end}"
        )

    if resources:
        peak = max(int(row.get("max_rss_observed_bytes") or 0) for row in resources)
        budget = min(
            int(row.get("memory_budget_bytes") or 0)
            for row in resources
            if int(row.get("memory_budget_bytes") or 0) > 0
        )
        report["peak_rss_bytes"] = peak
        report["memory_budget_bytes"] = budget
        report["memory_headroom_bytes"] = budget - peak
        report["soft_memory_budget_exceeded"] = peak > budget
        hard_limits = [
            int(row.get("memory_limit_bytes") or 0)
            for row in resources
            if int(row.get("memory_limit_bytes") or 0) > 0
        ]
        if hard_limits:
            hard_limit = min(hard_limits)
            report["memory_limit_bytes"] = hard_limit
            report["hard_memory_headroom_bytes"] = hard_limit - peak
            if peak >= hard_limit:
                raise StateFirstAcceptanceError(
                    f"hosted acceptance peak RSS {peak} reached hard memory limit {hard_limit}"
                )

    report["status"] = "PASS"
    _logger.info(
        "FSFFL STATE-FIRST ACCEPTANCE RESULT %s",
        json.dumps(report, sort_keys=True, default=str),
    )
    return report

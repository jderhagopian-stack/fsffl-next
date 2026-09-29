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
StateTransitionReclaimer = Callable[[str], object]


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
        "selected_team_id": runtime.selected_team_id,
        "forecast": evidence is not None,
        "simulation": runtime.simulation_analytics is not None,
        "value": runtime.value_evidence is not None,
        "intelligence_reused": runtime.intelligence_reused,
        "publication_generation_id": getattr(
            runtime,
            "publication_generation_id",
            None,
        ),
        "working_generation_active": store.working_generation_active(user_id),
        "working_target_state_id": store.working_target_state_id(user_id),
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
    state_transition_reclaimer: StateTransitionReclaimer | None = None,
    restore_only: bool = False,
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
        "state_transition_reclaims": [],
    }
    steps: list[dict[str, object]] = report["steps"]  # type: ignore[assignment]
    resources: list[dict[str, object]] = report["resources"]  # type: ignore[assignment]
    surface_rows: list[dict[str, object]] = report["surface_probes"]  # type: ignore[assignment]
    history_rows: list[dict[str, object]] = report["history_probes"]  # type: ignore[assignment]
    transition_rows: list[dict[str, object]] = report["state_transition_reclaims"]  # type: ignore[assignment]
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
        previous_state = store.get(user_id).league_state
        previous_league_id = (
            previous_state.league.league_id if previous_state is not None else None
        )
        state = state_loader(external_id)
        expected = f"sleeper:{external_id}"
        if state.league.league_id != expected:
            raise StateFirstAcceptanceError(
                f"{label} provider returned {state.league.league_id}, expected {expected}"
            )
        store.set_league_state(user_id, state)
        if (
            state_transition_reclaimer is not None
            and previous_league_id is not None
            and previous_league_id != state.league.league_id
        ):
            before = sample_resources(f"{label}_before_transition_reclaim")
            reclaimed = state_transition_reclaimer(
                f"{user_id}:{state.state_id}:{label}:league_switch"
            )
            after = sample_resources(f"{label}_after_transition_reclaim")
            transition_row = {
                "label": label,
                "from_league_id": previous_league_id,
                "to_league_id": state.league.league_id,
                "before": before,
                "reclaim": reclaimed if isinstance(reclaimed, dict) else str(reclaimed),
                "after": after,
            }
            transition_rows.append(transition_row)
            _logger.info(
                "FSFFL STATE-FIRST ACCEPTANCE transition_reclaim=%s data=%s",
                label,
                json.dumps(transition_row, sort_keys=True, default=str),
            )
        current = store.get(user_id)

        # A true clean first run exposes canonical State before any managed-team
        # identity or intelligence exists. This is the original first-load contract:
        # league-wide State surfaces are usable immediately, then team choice owns
        # the enrichment handoff.
        if label == "fsffl_initial":
            clean_snapshot = _snapshot(store, user_id, capability_reader)
            if clean_snapshot.get("selected_team_id") is not None:
                raise StateFirstAcceptanceError(
                    "clean first-run acceptance unexpectedly restored a managed team: "
                    f"{clean_snapshot}"
                )
            if any(
                bool(clean_snapshot.get(key))
                for key in ("forecast", "simulation", "value")
            ):
                raise StateFirstAcceptanceError(
                    "clean first-run acceptance unexpectedly restored intelligence: "
                    f"{clean_snapshot}"
                )
            clean_surface = probe_surface("clean_state_before_team_selection")
            if clean_surface is not None and not clean_surface.get("state_only"):
                raise StateFirstAcceptanceError(
                    "clean first-run surface probe was not State-only: "
                    f"{clean_surface}"
                )
            clean_row = {
                "label": "fsffl_clean_state_before_team_selection",
                "snapshot": clean_snapshot,
                "surface": clean_surface,
            }
            steps.append(clean_row)
            _logger.info(
                "FSFFL STATE-FIRST ACCEPTANCE step=%s data=%s",
                clean_row["label"],
                json.dumps(clean_row, sort_keys=True, default=str),
            )

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
            current = store.get(user_id)

        if current.selected_team_id is None:
            raise StateFirstAcceptanceError(
                f"{label} did not establish an explicit managed-team identity"
            )

        wait_for_managed_team = getattr(store, "wait_for_managed_team_checkpoint", None)
        if callable(wait_for_managed_team):
            team_durable = wait_for_managed_team(
                user_id,
                team_id=current.selected_team_id,
                state_id=state.state_id,
                timeout=30.0,
            )
        else:
            wait_for_checkpoint = getattr(store, "wait_for_checkpoint", None)
            team_durable = (
                not callable(wait_for_checkpoint)
                or wait_for_checkpoint(user_id, timeout=30.0)
            )
        if not team_durable:
            raise StateFirstAcceptanceError(
                f"{label} managed-team State did not durably checkpoint"
            )

        if label == "fsffl_initial":
            selected_row = {
                "label": "fsffl_initial_managed_team_selected",
                "selected_team_id": current.selected_team_id,
                "snapshot": _snapshot(store, user_id, capability_reader),
            }
            steps.append(selected_row)
            _logger.info(
                "FSFFL STATE-FIRST ACCEPTANCE step=%s data=%s",
                selected_row["label"],
                json.dumps(selected_row, sort_keys=True, default=str),
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
            cold_surface = probe_surface("cold_surfaces_during_initial_reconciliation")
            if (
                cold_surface is not None
                and cold_surface.get("readiness_status") != "rebuilding"
            ):
                raise StateFirstAcceptanceError(
                    "clean first-run did not expose visible intelligence progress: "
                    f"{cold_surface}"
                )
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
        if label == "fsffl_initial":
            # Terminal first-load publication must upgrade the previously State-only
            # PI surface to governed future intelligence, including Y2/Y3.
            probe_history("pi_history_after_initial_publication")
        replay_reader = getattr(store, "forecast_replay_decision_cached", None)
        row = {
            "label": label,
            "provider_state_id": state.state_id,
            "job": terminal,
            "snapshot": snapshot,
            "forecast_replay_decision": (
                replay_reader(user_id) if callable(replay_reader) else None
            ),
        }
        steps.append(row)
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE step=%s data=%s",
            label,
            json.dumps(row, sort_keys=True, default=str),
        )
        return snapshot

    if restore_only:
        sample_resources("restored_session_start")
        restored = store.restore_user(user_id)
        restored_snapshot = _snapshot(store, user_id, capability_reader)
        _require_full_fsffl(restored_snapshot)
        if restored_snapshot.get("selected_team_id") is None:
            raise StateFirstAcceptanceError(
                "restart restore did not recover managed-team identity"
            )
        if not restored_snapshot.get("publication_generation_id"):
            raise StateFirstAcceptanceError(
                "restart restore did not recover published generation identity"
            )
        restored_surface = probe_surface("restored_session_surfaces")
        if (
            restored_surface is not None
            and restored_surface.get("franchise_team_id")
            != restored_snapshot.get("selected_team_id")
        ):
            raise StateFirstAcceptanceError(
                "restored-session Franchise identity diverged from durable runtime: "
                f"{restored_surface}"
            )
        if (
            restored_surface is not None
            and restored_surface.get("publication_generation_id")
            != restored_snapshot.get("publication_generation_id")
        ):
            raise StateFirstAcceptanceError(
                "restored-session surfaces diverged from durable publication generation: "
                f"{restored_surface}"
            )
        restored_history = probe_history("restored_session_pi_history")
        row = {
            "label": "fsffl_restart_restored_session",
            "snapshot": restored_snapshot,
            "surface": restored_surface,
            "history": restored_history,
        }
        steps.append(row)
        sample_resources("restored_session_end")
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
                "hosted process identity changed during restored-session acceptance: "
                f"{process_identity_start} -> {process_identity_end}"
            )
        if resources:
            peak = max(
                int(item.get("max_rss_observed_bytes") or 0)
                for item in resources
            )
            report["peak_rss_bytes"] = peak
            hard_limits = [
                int(item.get("memory_limit_bytes") or 0)
                for item in resources
                if int(item.get("memory_limit_bytes") or 0) > 0
            ]
            if hard_limits:
                hard_limit = min(hard_limits)
                report["memory_limit_bytes"] = hard_limit
                report["hard_memory_headroom_bytes"] = hard_limit - peak
                if peak >= hard_limit:
                    raise StateFirstAcceptanceError(
                        "restored-session acceptance reached hard memory limit"
                    )
        report["status"] = "PASS"
        report["mode"] = "restore"
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE RESULT %s",
            json.dumps(report, sort_keys=True, default=str),
        )
        return report

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

    # Wait only for the off-side working generation to become active. The published
    # State must *not* change while reconciliation is in progress.
    working_deadline = monotonic() + min(30.0, timeout_seconds / 4)
    working_seen = False
    observed_state_change = False
    while monotonic() < working_deadline:
        current_job = jobs.current(user_id)
        if store.working_generation_active(user_id):
            working_seen = True
            observed_state_change = (
                store.working_target_state_id(user_id)
                != before_auto.get("state_id")
            )
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
        sleep(min(poll_seconds, 0.25))

    active_surface = probe_surface("reload_during_active_reconciliation")
    if working_seen and active_surface is not None:
        if active_surface.get("readiness_status") != "rebuilding":
            raise StateFirstAcceptanceError(
                "active reconciliation did not report published-generation rebuilding: "
                f"{active_surface}"
            )
        before_generation = before_auto.get("publication_generation_id")
        active_generation = active_surface.get("publication_generation_id")
        if before_generation and active_generation != before_generation:
            raise StateFirstAcceptanceError(
                "working reconciliation leaked a new runtime generation before publish: "
                f"before={before_generation} active={active_generation}"
            )
        surface_generations = {
            str(value)
            for value in (
                active_surface.get("publication_generations") or {}
            ).values()
            if value is not None and str(value).strip()
        }
        if len(surface_generations) > 1:
            raise StateFirstAcceptanceError(
                "active reconciliation exposed mixed surface generations: "
                f"{active_surface}"
            )
        if (
            before_generation
            and surface_generations
            and surface_generations != {str(before_generation)}
        ):
            raise StateFirstAcceptanceError(
                "active reconciliation surfaces left the prior published generation: "
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
    if promoted_surface is not None:
        if int(promoted_surface.get("stale_surface_count") or 0) != 0:
            raise StateFirstAcceptanceError(
                "new exact-State presentation was not atomically promoted: "
                f"{promoted_surface}"
            )
        if (
            promoted_surface.get("publication_generation_id")
            != after_auto.get("publication_generation_id")
        ):
            raise StateFirstAcceptanceError(
                "promoted surfaces do not match the published runtime generation: "
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

    # Managed-team publication race: switch teams only after a working generation
    # is visibly active. The guarded publication boundary may resolve this as either
    # an interruption (team switch wins first) or a coherent old-team publish followed
    # by the queued team switch (publication critical section wins first). Both are
    # valid; split durable/runtime authority, FAILED state, or a lost team switch is not.
    before_team_switch = _snapshot(store, user_id, capability_reader)
    current_runtime = store.get(user_id)
    current_state = current_runtime.league_state
    if current_state is None or current_runtime.selected_team_id is None:
        raise StateFirstAcceptanceError(
            "managed-team acceptance requires a published FSFFL team"
        )
    alternate_team_id = next(
        (
            team_state.team_id
            for team_state in current_state.team_states
            if team_state.team_id != current_runtime.selected_team_id
            and bool(team_state.roster)
        ),
        None,
    )
    if alternate_team_id is None:
        raise StateFirstAcceptanceError(
            "managed-team acceptance found no alternate rostered FSFFL team"
        )

    team_started = start_reconciliation(user_id)
    team_job_id = str(team_started.get("job_id") or "")
    if not team_job_id:
        raise StateFirstAcceptanceError(
            "managed-team publication acceptance did not start reconciliation"
        )
    # Guarantee the switch occurs inside the working-generation window. Merely
    # observing activity and then probing a full surface is insufficient: that probe
    # can outlive a fast reconciliation and turn this into a false race proof.
    #
    # The store owns the publication-sequence lock. The conditional team switch
    # acquires that authority, verifies unpublished work is still active, and changes
    # the managed team in the same serialized operation. If final publication already
    # won, this cannot falsely claim an interleaving.
    team_working_deadline = monotonic() + min(30.0, timeout_seconds / 4)
    team_interleaving: dict[str, object] | None = None
    while monotonic() < team_working_deadline:
        current_job = jobs.current(user_id)
        if (
            current_job is not None
            and current_job.job_id == team_job_id
            and current_job.status in {
                IntelligenceJobStatus.COMPLETED,
                IntelligenceJobStatus.FAILED,
                IntelligenceJobStatus.INTERRUPTED,
            }
        ):
            break
        switched = store.select_team_if_working_generation_active(
            user_id,
            alternate_team_id,
        )
        if switched is not None:
            working, selected = switched
            team_interleaving = {
                "working_state_id": (
                    working.league_state.state_id
                    if working.league_state is not None
                    else None
                ),
                "working_team_id": working.selected_team_id,
                "selected_team_id": selected.selected_team_id,
                "published_generation_id": (
                    store.get(user_id).publication_generation_id
                ),
            }
            break
        sleep(0.01)
    if team_interleaving is None:
        raise StateFirstAcceptanceError(
            "managed-team acceptance could not switch while a working generation "
            "was still active"
        )

    team_terminal = None
    team_deadline = monotonic() + timeout_seconds
    while monotonic() < team_deadline:
        current_job = jobs.current(user_id)
        if current_job is None or current_job.job_id != team_job_id:
            sleep(min(poll_seconds, 0.25))
            continue
        if current_job.status in {
            IntelligenceJobStatus.COMPLETED,
            IntelligenceJobStatus.INTERRUPTED,
        }:
            team_terminal = {
                "job_id": current_job.job_id,
                "status": current_job.status.value,
                "phase": current_job.phase.value,
                "message": current_job.message,
                "error": current_job.error,
                "league_state_id": current_job.league_state_id,
            }
            break
        if current_job.status == IntelligenceJobStatus.FAILED:
            raise StateFirstAcceptanceError(
                "managed-team reconciliation failed instead of serializing/interruption: "
                f"{current_job.error or current_job.message}"
            )
        sleep(min(poll_seconds, 0.25))
    if team_terminal is None:
        raise StateFirstAcceptanceError(
            "managed-team reconciliation did not reach a serialized terminal state"
        )

    wait_for_managed_team = getattr(store, "wait_for_managed_team_checkpoint", None)
    if callable(wait_for_managed_team):
        team_durable = wait_for_managed_team(
            user_id,
            team_id=alternate_team_id,
            state_id=current_state.state_id,
            timeout=30.0,
        )
    else:
        wait_for_checkpoint = getattr(store, "wait_for_checkpoint", None)
        team_durable = (
            not callable(wait_for_checkpoint)
            or wait_for_checkpoint(user_id, timeout=30.0)
        )
    if not team_durable:
        raise StateFirstAcceptanceError(
            "managed-team selection did not durably checkpoint"
        )
    after_team_switch = _snapshot(store, user_id, capability_reader)
    if after_team_switch.get("selected_team_id") != alternate_team_id:
        raise StateFirstAcceptanceError(
            "managed-team selection was lost across publication boundary: "
            f"{after_team_switch}"
        )
    if after_team_switch.get("working_generation_active"):
        raise StateFirstAcceptanceError(
            "managed-team terminal state retained an unpublished working generation"
        )
    team_surface = probe_surface(
        "managed_team_after_reconciliation_interruption"
    )
    if (
        team_surface is not None
        and team_surface.get("franchise_team_id") != alternate_team_id
    ):
        raise StateFirstAcceptanceError(
            "managed-team Franchise response did not follow the selected team: "
            f"{team_surface}"
        )
    steps.append(
        {
            "label": "fsffl_managed_team_publication_interruption",
            "before": before_team_switch,
            "interleaving": team_interleaving,
            "selected_team_id": alternate_team_id,
            "job": team_terminal,
            "after": after_team_switch,
            "surface": team_surface,
        }
    )

    # Explicit same-State publication isolation: non-sync reconciliation must keep
    # every foreground surface on the prior generation until one terminal swap.
    before_same_state = _snapshot(store, user_id, capability_reader)
    same_started = start_reconciliation(user_id)
    same_job_id = str(same_started.get("job_id") or "")
    if not same_job_id:
        raise StateFirstAcceptanceError(
            "same-State publication acceptance did not start reconciliation"
        )
    same_deadline = monotonic() + min(30.0, timeout_seconds / 4)
    while (
        not store.working_generation_active(user_id)
        and monotonic() < same_deadline
    ):
        current_job = jobs.current(user_id)
        if (
            current_job is not None
            and current_job.job_id == same_job_id
            and current_job.status in {
                IntelligenceJobStatus.COMPLETED,
                IntelligenceJobStatus.FAILED,
                IntelligenceJobStatus.INTERRUPTED,
            }
        ):
            break
        sleep(0.1)
    same_active = probe_surface("same_state_during_active_reconciliation")
    if store.working_generation_active(user_id) and same_active is not None:
        if same_active.get("readiness_status") != "rebuilding":
            raise StateFirstAcceptanceError(
                "same-State working generation was not reported as rebuilding"
            )
        if (
            same_active.get("publication_generation_id")
            != before_same_state.get("publication_generation_id")
        ):
            raise StateFirstAcceptanceError(
                "same-State reconciliation changed publication before terminal promotion"
            )
    same_terminal = _wait_for_job(
        jobs=jobs,
        user_id=user_id,
        job_id=same_job_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    after_same_state = _snapshot(store, user_id, capability_reader)
    _require_full_fsffl(after_same_state)
    if (
        before_same_state.get("publication_generation_id")
        and after_same_state.get("publication_generation_id")
        == before_same_state.get("publication_generation_id")
    ):
        raise StateFirstAcceptanceError(
            "same-State terminal reconciliation did not publish a new generation"
        )
    same_promoted = probe_surface("same_state_post_atomic_publication")
    if (
        same_promoted is not None
        and same_promoted.get("publication_generation_id")
        != after_same_state.get("publication_generation_id")
    ):
        raise StateFirstAcceptanceError(
            "same-State surfaces do not match the terminal published generation"
        )
    if after_same_state.get("selected_team_id") != alternate_team_id:
        raise StateFirstAcceptanceError(
            "same-State publication did not preserve managed-team selection"
        )
    if (
        same_promoted is not None
        and same_promoted.get("franchise_team_id") != alternate_team_id
    ):
        raise StateFirstAcceptanceError(
            "same-State promoted Franchise response does not match managed-team selection"
        )
    steps.append(
        {
            "label": "fsffl_same_state_atomic_publication",
            "before": before_same_state,
            "active_surface": same_active,
            "job": same_terminal,
            "after": after_same_state,
        }
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

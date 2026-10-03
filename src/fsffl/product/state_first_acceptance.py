from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Thread
from time import monotonic, process_time, sleep
from typing import Callable

from fsffl.persistence.runtime_cache import FORECAST_MODEL_VERSION
from fsffl.state.models import LeagueState

from .background_jobs import (
    IntelligenceJobCoordinator,
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)
from .persistent_runtime import PersistentPrivateBetaRuntimeStore
from .runtime import league_material_fingerprint, replay_live_forecast_evidence_for_state
from .scenario_cache import _forecast_fingerprint
from .simulation_runtime import simulation_artifact_model_version


_logger = logging.getLogger("uvicorn.error")
FSFFL_ACCEPTANCE_LEAGUE = "1312071960615731200"
HODOR_ACCEPTANCE_LEAGUE = "1397623301961981952"


class StateFirstAcceptanceError(RuntimeError):
    pass


SurfaceProbe = Callable[[str, object], dict[str, object]]
HistoryProbe = Callable[[str, object], dict[str, object]]
ResourceReader = Callable[[], dict[str, object]]
ProcessIdentityReader = Callable[[], str]
StateActivator = Callable[..., object | None]
PresentationSnapshotCloner = Callable[[str, str, object], str]


def resolve_staged_acceptance_user(
    *,
    source_user_id: str,
    configured_acceptance_user_id: str,
) -> str:
    """Keep acceptance staging isolated even under a legacy same-user env value."""

    source = source_user_id.strip()
    configured = configured_acceptance_user_id.strip()
    if not source:
        raise StateFirstAcceptanceError("acceptance staging source user id is blank")
    if configured and configured != source:
        return configured
    return "runtime-availability-production-acceptance"


def stage_restored_refresh_partial_acceptance(
    *,
    store: PersistentPrivateBetaRuntimeStore,
    source_user_id: str,
    acceptance_user_id: str,
    clone_presentation_snapshot: PresentationSnapshotCloner,
) -> dict[str, object]:
    """Stage an isolated durable partial restore from a governed full FSFFL runtime.

    The source runtime and persistence are read-only. The isolated acceptance user
    first receives the exact full S0 bundle and presentation, then advances to an S1
    snapshot that differs only by as_of. Forecast is replayed through the governed
    compatible-State path, Value is rebound to S1, and Simulation is deliberately
    omitted. S1 is persisted, process-local acceptance state is cleared, and S1 is
    restored cold before the normal manual-refresh acceptance begins.
    """

    if not source_user_id.strip() or not acceptance_user_id.strip():
        raise StateFirstAcceptanceError("acceptance staging user ids cannot be blank")
    if source_user_id == acceptance_user_id:
        raise StateFirstAcceptanceError(
            "acceptance staging must use an isolated user distinct from production"
        )

    source = store.restore_user(source_user_id)
    if (
        source.league_state is None
        or source.league_state.league.league_id
        != f"sleeper:{FSFFL_ACCEPTANCE_LEAGUE}"
        or source.selected_team_id is None
        or source.forecast_evidence is None
        or source.simulation_analytics is None
        or source.value_evidence is None
    ):
        raise StateFirstAcceptanceError(
            "acceptance staging source is not a complete canonical FSFFL runtime"
        )

    if not store.wait_for_checkpoint(acceptance_user_id, timeout=180.0):
        raise StateFirstAcceptanceError(
            "acceptance staging could not drain the isolated checkpoint queue"
        )
    store.reset_in_memory_for_acceptance_restore(acceptance_user_id)

    s0 = source.league_state
    store.set_league_state(acceptance_user_id, s0)
    store.select_team(acceptance_user_id, source.selected_team_id)
    store.set_intelligence_bundle(
        acceptance_user_id,
        league_state=s0,
        forecast_evidence=source.forecast_evidence,
        simulation_analytics=source.simulation_analytics,
        value_evidence=source.value_evidence,
    )
    if not store.wait_for_checkpoint(acceptance_user_id, timeout=180.0):
        raise StateFirstAcceptanceError(
            "acceptance staging could not persist the full last-good baseline"
        )

    presentation_generation_id = clone_presentation_snapshot(
        source_user_id,
        acceptance_user_id,
        source,
    )
    if not presentation_generation_id:
        raise StateFirstAcceptanceError(
            "acceptance staging could not clone the full presentation generation"
        )
    store.bind_publication_generation_id(
        acceptance_user_id,
        presentation_generation_id,
    )

    now = datetime.now(timezone.utc)
    target_as_of = max(now, s0.as_of + timedelta(microseconds=1))
    s1 = s0.model_copy(update={"as_of": target_as_of})
    if s1.state_id == s0.state_id:
        raise StateFirstAcceptanceError(
            "acceptance staging failed to create a distinct target State identity"
        )
    if league_material_fingerprint(s1) != league_material_fingerprint(s0):
        raise StateFirstAcceptanceError(
            "acceptance staging changed substantive football State"
        )

    s1_forecast = replay_live_forecast_evidence_for_state(
        s1,
        source.forecast_evidence,
    )
    s1_value = replace(
        source.value_evidence,
        league_state_id=s1.state_id,
    )
    store.set_league_state(acceptance_user_id, s1)
    store.set_intelligence_bundle(
        acceptance_user_id,
        league_state=s1,
        forecast_evidence=s1_forecast,
        simulation_analytics=None,
        value_evidence=s1_value,
    )
    if not store.wait_for_checkpoint(acceptance_user_id, timeout=180.0):
        raise StateFirstAcceptanceError(
            "acceptance staging could not persist the partial target snapshot"
        )

    partial = store.get(acceptance_user_id)
    if (
        partial.league_state is None
        or partial.league_state.state_id != s1.state_id
        or partial.forecast_evidence is None
        or partial.simulation_analytics is not None
        or partial.value_evidence is None
        or partial.served_intelligence is None
        or partial.served_intelligence.league_state_id != s0.state_id
    ):
        raise StateFirstAcceptanceError(
            "acceptance staging did not produce the expected S0-served/S1-partial state"
        )

    store.reset_in_memory_for_acceptance_restore(acceptance_user_id)
    restored = store.restore_user(acceptance_user_id)
    if (
        restored.league_state is None
        or restored.league_state.state_id != s1.state_id
        or restored.forecast_evidence is None
        or restored.simulation_analytics is not None
        or restored.value_evidence is None
        or restored.served_intelligence is None
        or restored.served_intelligence.league_state_id != s0.state_id
    ):
        raise StateFirstAcceptanceError(
            "acceptance staging cold restore did not reproduce the required partial shape"
        )

    return {
        "status": "staged",
        "source_user_id": source_user_id,
        "acceptance_user_id": acceptance_user_id,
        "served_state_id": s0.state_id,
        "target_state_id": s1.state_id,
        "selected_team_id": restored.selected_team_id,
        "publication_generation_id": restored.publication_generation_id,
        "presentation_generation_id": presentation_generation_id,
        "material_fingerprint": league_material_fingerprint(s1),
    }


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
                "total_elapsed_seconds": current.total_elapsed_seconds,
                "phase_timings": [
                    {
                        "phase": timing.phase.value,
                        "elapsed_seconds": timing.elapsed_seconds,
                    }
                    for timing in current.phase_timings
                ],
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
        "artifact_identities": _artifact_identity_snapshot(runtime),
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


def _artifact_identity_snapshot(runtime: object) -> dict[str, object]:
    """Report bounded State-bound identity fields without copying artifact payloads."""

    state = getattr(runtime, "league_state", None)
    state_id = getattr(state, "state_id", None)
    forecast = getattr(runtime, "forecast_evidence", None)
    simulation = getattr(runtime, "simulation_analytics", None)
    value = getattr(runtime, "value_evidence", None)
    forecast_identity = None
    if state_id is not None and forecast is not None:
        forecast_identity = {
            "state_id": state_id,
            "artifact_model_version": FORECAST_MODEL_VERSION,
            "evidence_model_version": getattr(forecast, "model_version", None),
            "evidence_basis": getattr(forecast, "evidence_basis", None),
            "simulation_input_fingerprint": _forecast_fingerprint(forecast),
        }
    simulation_identity = None
    if state_id is not None and simulation is not None:
        result = simulation.simulation_result
        simulation_context = getattr(
            getattr(simulation, "league_view", None), "context", None
        )
        simulation_identity = {
            "state_id": getattr(simulation_context, "league_state_id", None),
            "artifact_model_version": simulation_artifact_model_version(result),
            "result_model_version": getattr(result, "model_version", None),
            "simulation_count": getattr(result, "simulation_count", None),
            "seed": getattr(result, "seed", None),
            "rng_protocol": getattr(result, "rng_protocol", None),
            "rng_batch_size": getattr(result, "rng_batch_size", None),
            "rng_runtime_version": getattr(result, "rng_runtime_version", None),
            "input_fingerprint": getattr(
                result, "simulation_input_fingerprint", None
            ),
        }
    return {
        "state_id": state_id,
        "forecast": forecast_identity,
        "simulation": simulation_identity,
        "current_value_model_version": getattr(value, "model_version", None),
        "publication_generation_id": getattr(
            runtime, "publication_generation_id", None
        ),
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


def _probe_surface_during_simulation(
    *,
    jobs: IntelligenceJobCoordinator,
    user_id: str,
    job_id: str,
    surface_probe: SurfaceProbe,
    store: PersistentPrivateBetaRuntimeStore,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        current = jobs.current(user_id)
        if current is not None and current.job_id != job_id:
            raise StateFirstAcceptanceError(
                f"refresh acceptance job identity changed {job_id} -> {current.job_id}"
            )
        if (
            current is not None
            and current.job_id == job_id
            and current.status == IntelligenceJobStatus.RUNNING
            and current.phase == IntelligenceJobPhase.RUNNING_SIMULATION
        ):
            return surface_probe(
                "restored_refresh_during_simulation",
                store.get(user_id),
            )
        if (
            current is not None
            and current.job_id == job_id
            and current.status
            in {
                IntelligenceJobStatus.COMPLETED,
                IntelligenceJobStatus.FAILED,
                IntelligenceJobStatus.INTERRUPTED,
            }
        ):
            break
        sleep(0.25)
    raise StateFirstAcceptanceError(
        f"refresh acceptance did not expose active Simulation phase for {job_id}"
    )


def _require_last_good_presentation_during_rebuild(
    observed_surface: dict[str, object],
) -> None:
    """Validate truthful rebuilding status while one atomic last-good generation is served."""

    publication_generations = observed_surface.get("publication_generations")
    generation_id = str(observed_surface.get("publication_generation_id") or "")
    generation_values = (
        {
            str(value)
            for value in publication_generations.values()
            if value
        }
        if isinstance(publication_generations, dict)
        else set()
    )
    presentation_modes = observed_surface.get("presentation_modes")
    served_modes = (
        tuple(value for value in presentation_modes.values() if value is not None)
        if isinstance(presentation_modes, dict)
        else ()
    )
    if (
        observed_surface.get("reconciliation_status") != "running"
        or observed_surface.get("working_generation_active") is not True
        or observed_surface.get("readiness_status") != "rebuilding"
        or observed_surface.get("publication_status")
        != "serving_last_good_during_update"
        or observed_surface.get("presentation_snapshot_available") is not True
        or not generation_id
        or generation_values != {generation_id}
        or not served_modes
        or any(mode != "stale_last_good" for mode in served_modes)
    ):
        raise StateFirstAcceptanceError(
            "restored refresh did not truthfully serve one atomic last-good "
            f"publication while reporting working-generation progress: {observed_surface}"
        )


def run_state_first_restored_refresh_acceptance(
    *,
    store: PersistentPrivateBetaRuntimeStore,
    user_id: str,
    start_sync_reconciliation: Callable[[str], dict[str, object]],
    jobs: IntelligenceJobCoordinator,
    capability_reader: Callable[[object], dict[str, object]],
    surface_probe: SurfaceProbe,
    resource_reader: ResourceReader,
    timeout_seconds: float = 1200.0,
) -> dict[str, object]:
    """Restore a production user, then run the normal synchronized refresh path."""

    store.restore_user(user_id)
    before = _snapshot(store, user_id, capability_reader)
    if before.get("league_id") != f"sleeper:{FSFFL_ACCEPTANCE_LEAGUE}":
        raise StateFirstAcceptanceError(
            f"restored refresh user is not the canonical FSFFL runtime: {before}"
        )
    if not before.get("forecast") or not before.get("value"):
        raise StateFirstAcceptanceError(
            f"restored refresh did not begin from the expected Forecast/Value partial state: {before}"
        )
    if before.get("simulation"):
        raise StateFirstAcceptanceError(
            "restored refresh did not reproduce the startup Simulation-unavailable state"
        )

    initial_resources = resource_reader()
    started = start_sync_reconciliation(user_id)
    job_id = str(started.get("job_id") or "")
    if not job_id:
        raise StateFirstAcceptanceError(
            "restored refresh did not schedule the normal synchronized reconciliation"
        )

    observed_surface: dict[str, object] = {}
    surface_error: list[BaseException] = []

    def probe_during_simulation() -> None:
        try:
            observed_surface.update(
                _probe_surface_during_simulation(
                    jobs=jobs,
                    user_id=user_id,
                    job_id=job_id,
                    surface_probe=surface_probe,
                    store=store,
                    timeout_seconds=timeout_seconds,
                )
            )
        except BaseException as exc:  # pragma: no cover - hosted propagation
            surface_error.append(exc)

    surface_thread = Thread(
        target=probe_during_simulation,
        name="fsffl-restored-refresh-surface-probe",
        daemon=True,
    )
    surface_thread.start()
    terminal = _wait_for_job(
        jobs=jobs,
        user_id=user_id,
        job_id=job_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=0.5,
    )
    surface_thread.join(timeout=timeout_seconds)
    if surface_thread.is_alive():
        raise StateFirstAcceptanceError(
            "restored refresh Simulation foreground probe did not finish"
        )
    if surface_error:
        raise StateFirstAcceptanceError(
            f"restored refresh Simulation foreground probe failed: {surface_error[0]}"
        )

    _require_last_good_presentation_during_rebuild(observed_surface)
    if observed_surface.get("state_id") != before.get("state_id"):
        raise StateFirstAcceptanceError(
            "restored refresh changed the served State before atomic publication"
        )

    after = _snapshot(store, user_id, capability_reader)
    _require_full_fsffl(after)
    identities = after.get("artifact_identities") or {}
    simulation_identity = identities.get("simulation") if isinstance(identities, dict) else None
    forecast_identity = identities.get("forecast") if isinstance(identities, dict) else None
    if not isinstance(simulation_identity, dict) or not isinstance(forecast_identity, dict):
        raise StateFirstAcceptanceError(
            f"restored refresh did not publish exact Forecast and Simulation identities: {after}"
        )
    state_id = after.get("state_id")
    if (
        terminal.get("league_state_id") != state_id
        or forecast_identity.get("state_id") != state_id
        or simulation_identity.get("state_id") != state_id
        or identities.get("publication_generation_id")
        != after.get("publication_generation_id")
    ):
        raise StateFirstAcceptanceError(
            f"restored refresh artifact/publication identities diverged: {after}"
        )
    if (
        simulation_identity.get("simulation_count") != 50_000
        or simulation_identity.get("rng_protocol") != "numpy-pcg64-batched-gauss-v1"
        or simulation_identity.get("rng_batch_size") != 500
        or not str(simulation_identity.get("rng_runtime_version") or "").endswith(
            "python-3.12.10"
        )
    ):
        raise StateFirstAcceptanceError(
            f"restored refresh Simulation configuration is not canonical: {simulation_identity}"
        )
    if after.get("working_generation_active"):
        raise StateFirstAcceptanceError(
            "restored refresh left an unpublished working generation active"
        )
    if not after.get("publication_generation_id"):
        raise StateFirstAcceptanceError(
            "restored refresh completed without a publication generation identity"
        )
    intrinsic = (after.get("capability_readiness") or {}).get("intrinsic") or {}
    if intrinsic.get("status") != "full":
        raise StateFirstAcceptanceError(
            f"restored refresh did not reach full Intrinsic readiness: {intrinsic}"
        )
    active_generation = observed_surface.get("publication_generation_id")
    prior_generation = before.get("publication_generation_id")
    if prior_generation and active_generation != prior_generation:
        raise StateFirstAcceptanceError(
            "Simulation foreground read observed a replacement generation before publication"
        )
    active_generations = {
        str(value)
        for value in (observed_surface.get("publication_generations") or {}).values()
        if value is not None and str(value).strip()
    }
    if prior_generation and active_generations and active_generations != {str(prior_generation)}:
        raise StateFirstAcceptanceError(
            "Simulation foreground surfaces mixed publication generations"
        )

    final_surface = surface_probe("restored_refresh_after_publication", store.get(user_id))
    if final_surface.get("publication_generation_id") != after.get("publication_generation_id"):
        raise StateFirstAcceptanceError(
            f"post-refresh foreground surfaces do not match publication: {final_surface}"
        )
    if int(final_surface.get("stale_surface_count") or 0) != 0:
        raise StateFirstAcceptanceError(
            f"post-refresh surfaces include stale publication output: {final_surface}"
        )
    final_resources = resource_reader()
    peak_rss = max(
        int(initial_resources.get(key) or 0)
        for key in ("current_rss_bytes", "max_rss_observed_bytes", "peak_rss_bytes")
    )
    peak_rss = max(
        peak_rss,
        *(
            int(final_resources.get(key) or 0)
            for key in ("current_rss_bytes", "max_rss_observed_bytes", "peak_rss_bytes")
        ),
    )
    hard_limit = 536_870_900
    if peak_rss >= hard_limit:
        raise StateFirstAcceptanceError(
            f"restored refresh reached hard RSS gate: peak={peak_rss} limit={hard_limit}"
        )

    report = {
        "status": "PASS",
        "mode": "restored_refresh",
        "user_id": user_id,
        "before": before,
        "job": terminal,
        "during_simulation_surface": observed_surface,
        "after": after,
        "after_surface": final_surface,
        "initial_resources": initial_resources,
        "final_resources": final_resources,
        "peak_rss_bytes": peak_rss,
        "hard_memory_limit_bytes": hard_limit,
        "hard_memory_headroom_bytes": hard_limit - peak_rss,
    }
    _logger.info(
        "FSFFL STATE-FIRST ACCEPTANCE RESULT %s",
        json.dumps(report, sort_keys=True, default=str),
    )
    return report


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
    state_activator: StateActivator | None = None,
    restore_only: bool = False,
    journey_only: bool = False,
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
        prior = store.get(user_id)
        previous_league_id = (
            prior.league_state.league.league_id
            if prior.league_state is not None
            else None
        )
        # Do not retain the prior full runtime/State in the acceptance frame while
        # the replacement league performs heavy work. The resource boundary owns
        # transition evidence; the harness retains only scalar identity summaries.
        del prior

        state_load_started = monotonic()
        state_load_cpu_started = process_time()
        state = state_loader(external_id)
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE phase=state_acquisition label=%s league=%s "
            "state=%s wall=%.3fs cpu=%.3fs",
            label,
            state.league.league_id,
            state.state_id,
            monotonic() - state_load_started,
            process_time() - state_load_cpu_started,
        )
        expected = f"sleeper:{external_id}"
        if state.league.league_id != expected:
            raise StateFirstAcceptanceError(
                f"{label} provider returned {state.league.league_id}, expected {expected}"
            )
        before = sample_resources(f"{label}_pre_state_activation")
        if state_activator is not None:
            activated = state_activator(
                user_id,
                state,
                reason=f"acceptance_{label}",
            )
            if activated is None:
                raise StateFirstAcceptanceError(
                    f"{label} State activation was superseded"
                )
        else:
            store.set_league_state(user_id, state)
        after = sample_resources(f"{label}_post_resource_boundary")
        if previous_league_id is not None and previous_league_id != state.league.league_id:
            transition_row = {
                "label": label,
                "from_league_id": previous_league_id,
                "to_league_id": state.league.league_id,
                "before": before,
                "after": after,
            }
            transition_rows.append(transition_row)
            _logger.info(
                "FSFFL STATE-FIRST ACCEPTANCE transition_boundary=%s data=%s",
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
                and (
                    cold_surface.get("reconciliation_status") != "running"
                    or cold_surface.get("working_generation_active") is not True
                )
            ):
                raise StateFirstAcceptanceError(
                    "clean first-run did not expose working-generation progress "
                    "independently of published readiness: "
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

        # Restart authority is staged by design: the exact durable runtime generation
        # restores State + managed-team + Forecast/Simulation/Value immediately,
        # while Intrinsic/PI product capability can rehydrate on first product use.
        # Validate the durable core before asking any product-capability probe to run.
        if restored_snapshot.get("league_id") != f"sleeper:{FSFFL_ACCEPTANCE_LEAGUE}":
            raise StateFirstAcceptanceError(
                "restart restore did not recover the FSFFL league identity: "
                f"{restored_snapshot}"
            )
        if not all(
            restored_snapshot.get(key)
            for key in ("forecast", "simulation", "value")
        ):
            raise StateFirstAcceptanceError(
                "restart restore did not recover durable core intelligence: "
                f"{restored_snapshot}"
            )
        if restored_snapshot.get("working_generation_active"):
            raise StateFirstAcceptanceError(
                "restart restore exposed an unpublished working generation"
            )
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

        # First governed PI use is the normal product path that rehydrates Intrinsic.
        # After that bounded staged restore settles, the full product contract must
        # again be satisfied without changing the durable publication generation.
        restored_history = probe_history("restored_session_pi_history")
        settled_snapshot = _snapshot(store, user_id, capability_reader)
        _require_full_fsffl(settled_snapshot)
        if (
            settled_snapshot.get("publication_generation_id")
            != restored_snapshot.get("publication_generation_id")
        ):
            raise StateFirstAcceptanceError(
                "restored-session product rehydration changed durable publication "
                "generation identity"
            )
        settled_surface = probe_surface("restored_session_settled_surfaces")
        if (
            settled_surface is not None
            and settled_surface.get("publication_generation_id")
            != restored_snapshot.get("publication_generation_id")
        ):
            raise StateFirstAcceptanceError(
                "settled restored-session surfaces diverged from durable publication "
                "generation"
            )
        row = {
            "label": "fsffl_restart_restored_session",
            "snapshot": restored_snapshot,
            "surface": restored_surface,
            "history": restored_history,
            "settled_snapshot": settled_snapshot,
            "settled_surface": settled_surface,
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

    if journey_only:
        # Management's normal private-beta acceptance is intentionally narrower than
        # the historical full stress harness: settle FSFFL, switch and settle Hodor,
        # return and settle FSFFL. Publication-race and active-overlap proofs remain
        # covered by deterministic CI and are not repeated in this capacity gate.
        hodor = activate(HODOR_ACCEPTANCE_LEAGUE, label="hodor_switch")
        _require_truthful_hodor(hodor)
        probe_surface("hodor_home_franchise_league")
        sample_resources("hodor_switch")

        fsffl_return = activate(FSFFL_ACCEPTANCE_LEAGUE, label="fsffl_return")
        _require_full_fsffl(fsffl_return)
        probe_surface("fsffl_return_home_franchise_league")
        sample_resources("fsffl_return")
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
                "hosted process identity changed during realistic journey: "
                f"{process_identity_start} -> {process_identity_end}"
            )

        if resources:
            peak = max(
                int(row.get("max_rss_observed_bytes") or 0)
                for row in resources
            )
            current = int(resources[-1].get("current_rss_bytes") or 0)
            report["peak_rss_bytes"] = peak
            report["current_rss_bytes"] = current
            budget = min(
                int(row.get("memory_budget_bytes") or 0)
                for row in resources
                if int(row.get("memory_budget_bytes") or 0) > 0
            )
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
                        "realistic hosted acceptance peak RSS "
                        f"{peak} reached hard memory limit {hard_limit}"
                    )

        report["status"] = "PASS"
        report["mode"] = "journey"
        _logger.info(
            "FSFFL STATE-FIRST ACCEPTANCE RESULT %s",
            json.dumps(report, sort_keys=True, default=str),
        )
        return report

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
        expected_published_readiness = (
            before_auto.get("capability_readiness") or {}
        ).get("overall_status")
        if (
            active_surface.get("reconciliation_status") != "running"
            or active_surface.get("working_generation_active") is not True
            or active_surface.get("readiness_status") != expected_published_readiness
        ):
            raise StateFirstAcceptanceError(
                "active reconciliation did not preserve published readiness while "
                f"reporting replacement progress: {active_surface}"
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

    # A fully current same-State reconciliation is verification only. It must
    # not create a working generation, rebuild governed capabilities, or mint a new
    # presentation generation.
    before_same_state = _snapshot(store, user_id, capability_reader)
    same_started = start_reconciliation(user_id)
    same_job_id = str(same_started.get("job_id") or "")
    if not same_job_id:
        raise StateFirstAcceptanceError(
            "same-State verification acceptance did not start a bounded job"
        )
    same_terminal = _wait_for_job(
        jobs=jobs,
        user_id=user_id,
        job_id=same_job_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    if store.working_generation_active(user_id):
        raise StateFirstAcceptanceError(
            "fully current same-State verification created a working generation"
        )
    if "no rebuild was required" not in str(same_terminal.get("message") or "").lower():
        raise StateFirstAcceptanceError(
            f"same-State verification did not report no-op reuse: {same_terminal}"
        )
    after_same_state = _snapshot(store, user_id, capability_reader)
    _require_full_fsffl(after_same_state)
    if (
        after_same_state.get("publication_generation_id")
        != before_same_state.get("publication_generation_id")
    ):
        raise StateFirstAcceptanceError(
            "same-State verification changed the published generation"
        )
    same_verified = probe_surface("same_state_post_noop_verification")
    if (
        same_verified is not None
        and same_verified.get("publication_generation_id")
        != before_same_state.get("publication_generation_id")
    ):
        raise StateFirstAcceptanceError(
            "same-State verification changed the served surface generation"
        )
    if after_same_state.get("selected_team_id") != alternate_team_id:
        raise StateFirstAcceptanceError(
            "same-State verification did not preserve managed-team selection"
        )
    if (
        same_verified is not None
        and same_verified.get("franchise_team_id") != alternate_team_id
    ):
        raise StateFirstAcceptanceError(
            "same-State verified Franchise response does not match managed-team selection"
        )
    steps.append(
        {
            "label": "fsffl_same_state_noop_verification",
            "before": before_same_state,
            "verified_surface": same_verified,
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

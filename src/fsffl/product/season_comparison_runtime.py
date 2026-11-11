"""One bounded, State-scoped comparison artifact; player requests only read it."""
from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from threading import Lock, RLock

from fsffl.forecast.season_comparison import SEASON_COMPARISON_VERSION, build_season_comparison
from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord, canonical_fingerprint
from fsffl.memory_attribution import sample_rss_phase


class SeasonComparisonService:
    def __init__(self, *, persistence_store=None, baseline_loader=None,
                 history_store=None, heavy_work=None, ownership_validator=None,
                 builder=build_season_comparison, max_entries=2, frozen_baseline_loader=None):
        self.store, self.baseline_loader = persistence_store, baseline_loader
        self.history_store, self.heavy_work = history_store, heavy_work
        self.owned, self.builder = ownership_validator, builder
        self.frozen_baseline_loader = frozen_baseline_loader
        self._cache, self._lock = OrderedDict(), RLock()
        self._build_lock = Lock()
        if not 1 <= max_entries <= 4:
            raise ValueError("season comparison cache must retain between one and four States")
        self._max_entries = max_entries
        self._active_state = None

    @contextmanager
    def _preparing(self, state):
        with self._lock:
            self._active_state = state.state_id
        try:
            yield
        finally:
            with self._lock:
                self._active_state = None

    @staticmethod
    def key(state):
        return ArtifactKey(
            artifact_kind="season_comparison", scope_kind="league_state",
            scope_id=state.state_id,
            input_fingerprint=canonical_fingerprint(state.state_id, SEASON_COMPARISON_VERSION),
            model_version=SEASON_COMPARISON_VERSION,
        )

    def _remember(self, key, payload):
        self._cache[key] = payload
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)

    def _read(self, state):
        key = self.key(state)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        record = self.store.get_reusable_artifact(key) if self.store is not None else None
        if record is None or not record.reusable:
            return None
        payload = record.payload
        if (payload.get("version") != SEASON_COMPARISON_VERSION
                or payload.get("league_state_id") != state.state_id
                or payload.get("season") != state.league.season):
            return None
        self._remember(key, payload)
        return payload

    def prepare(self, context, *, force=False, already_admitted=False):
        """Called only by the existing owned refresh, never a player GET/startup."""
        state = context.league_state
        if state is None or (self.owned is not None and not self.owned(context)):
            return
        # All producers acquire heavy admission before the build lock. The
        # owned refresh already holds admission; reverse ordering can deadlock
        # it against a standalone preparation waiting for the same admission.
        with self._lock:
            if not force and self._read(state) is not None:
                return
        claim = (self.heavy_work.claim(kind="forecast", key=f"season-comparison:{state.state_id}")
                 if self.heavy_work is not None and not already_admitted else nullcontext())
        with claim, self._build_lock:
            if self.owned is not None and not self.owned(context):
                return
            with self._lock:
                if not force and self._read(state) is not None:
                    return
            with self._preparing(state), sample_rss_phase("forecast.season_comparison"):
                baseline = None
                if self.baseline_loader is not None:
                    try:
                        baseline = self.baseline_loader(state)
                    except ValueError:
                        pass  # An uncaptured preseason is unavailable, not invented.
                frozen = (self.frozen_baseline_loader(state) if self.frozen_baseline_loader
                          else {"forecasts": (), "as_of": None, "basis": "not_captured"})
                payload = self.builder(
                    state,
                    preseason_forecasts=frozen["forecasts"],
                    preseason_as_of=frozen["as_of"], preseason_basis=frozen["basis"],
                    fallback_forecasts=tuple(baseline.league_scored_forecasts) if baseline else (),
                    history_store=self.history_store,
                )
                if self.owned is not None and not self.owned(context):
                    return
                if payload.get("league_state_id") != state.state_id:
                    raise ValueError("comparison producer returned a different State")
                if self.store is not None:
                    self.store.put_artifact(ReusableArtifactRecord(
                        key=self.key(state), payload=payload, computed_at=datetime.now(UTC),
                    ))
                with self._lock:
                    self._remember(self.key(state), payload)

    def current_position_depth(self, state, evidence=None):
        """Reuse the same governed outlook prepared for this State, if available."""
        from fsffl.forecast.models import ForecastObservation
        from .current_position_depth import build_current_position_depth_from_outlook, unavailable_current_position_depth
        with self._lock:
            payload = self._read(state)
            bound = getattr(evidence, "simulation_forward_forecasts", None)
            if bound is not None and (payload is None
                    or datetime.fromisoformat(payload["as_of"]) != evidence.simulation_evaluation_as_of
                    or evidence.simulation_source_state_id != state.state_id
                    or tuple(ForecastObservation.model_validate(row) for row in payload.get("forward_forecasts", ())) != bound):
                return unavailable_current_position_depth(state,
                    reason="Current outlook does not match the published Simulation cohort; Refresh Intelligence")
            if payload is None or "season_outlook" not in payload:
                return None
            outlook = tuple(ForecastObservation.model_validate(row) for row in payload["season_outlook"])
            metadata = {pid: {key: value for key, value in row.items()
                if key.startswith("participation_") or key in ("ros_basis", "low_confidence")}
                for pid, row in payload.get("players", {}).items()}
            for row in payload.get("forward_forecasts", ()):
                metadata.setdefault(row["player_id"], {}).update({
                    "ros_model_version": row["model_version"], "ros_as_of": row["as_of"]})
            basis, completed = payload["evidence_basis"], payload["completed_through_week"]
            failures = dict(payload.get("season_outlook_failures", {}))
        return build_current_position_depth_from_outlook(state, season_outlook=outlook,
            evidence_basis=basis, completed_through_week=completed,
            season_outlook_failures=failures, player_outlook_evidence=metadata)

    def simulation_evidence(self, context, evidence):
        """Read the existing producer; no acquisition from Simulation or player GETs."""
        from dataclasses import replace
        from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
        state = context.league_state
        with self._lock:
            payload = self._read(state)
            if payload is None or payload.get("completed_through_week") != state.completed_through_week:
                raise ValueError("Current participation-adjusted ROS evidence requires Refresh Intelligence")
            rows = tuple(ForecastObservation.model_validate(row) for row in payload.get("forward_forecasts", ()))
            cutoff = datetime.fromisoformat(payload["as_of"])
            if state.completed_through_week == 18:
                return replace(evidence, uncertainty_ready=False,
                    simulation_forward_forecasts=(), simulation_evaluation_as_of=cutoff,
                    simulation_source_state_id=state.state_id, simulation_basis="completed_actuals_only")
            if not rows or cutoff.tzinfo is None or cutoff < state.as_of:
                raise ValueError("Current participation-adjusted ROS evidence is unavailable")
            if any(row.horizon != ForecastHorizon.REST_OF_SEASON
                   or row.metric != ForecastMetric.FANTASY_POINTS or row.as_of > cutoff for row in rows):
                raise ValueError("Invalid Simulation forward evidence coordinates")
            return replace(evidence,
                           uncertainty_ready=(evidence.uncertainty_ready and payload.get("evidence_basis") != "preseason_remaining_prior"),
                           simulation_forward_forecasts=rows,
                           simulation_evaluation_as_of=cutoff,
                           simulation_source_state_id=state.state_id,
                           simulation_basis=payload.get("evidence_basis", "governed_ros"))

    def player(self, context, player_id):
        state = context.league_state
        if state is None:
            return {"status": "unavailable"}
        with self._lock:
            payload = self._read(state)
            if payload is None:
                return {"status": "preparing" if self._active_state == state.state_id else "needs_refresh", "season": state.league.season,
                        "message": "Refresh Intelligence to prepare the season comparison."}
            row = payload.get("players", {}).get(player_id)
            return {**(row or {"status": "unavailable"}),
                    "season": payload["season"], "as_of": payload["as_of"],
                    "league_state_id": state.state_id,
                    "publication_generation_id": context.publication_generation_id,
                    "scoring_basis": "current_league_rules"}

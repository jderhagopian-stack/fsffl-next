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

    def prepare(self, context, *, force=False):
        """Called only by the existing owned refresh, never a player GET/startup."""
        state = context.league_state
        if state is None or (self.owned is not None and not self.owned(context)):
            return
        # Serialize duplicate producers and cold persisted reads; cache is bounded.
        with self._build_lock:
            with self._lock:
                if not force and self._read(state) is not None:
                    return
            claim = (self.heavy_work.claim(kind="forecast", key=f"season-comparison:{state.state_id}")
                     if self.heavy_work is not None else nullcontext())
            with self._preparing(state), claim, sample_rss_phase("forecast.season_comparison"):
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

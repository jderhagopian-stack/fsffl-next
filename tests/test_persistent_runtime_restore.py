from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic, sleep

from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord
from fsffl.persistence.session import (
    LAST_GOOD_ARTIFACT_KIND, LAST_GOOD_MODEL_VERSION, LAST_GOOD_SCOPE_KIND,
    persist_runtime_snapshot, restore_runtime_snapshot,
)
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    ProviderRef,
    RosterSlot,
    Team,
    TeamState,
)


class MemoryPersistence:
    def __init__(self) -> None:
        self.user = None
        self.league = None
        self.teams = {}
        self.artifacts = []
        self.market = []

    def get_user_runtime_context(self, *, user_id):
        return self.user if self.user and self.user.user_id == user_id else None

    def put_user_runtime_context(self, record):
        self.user = record

    def get_league_snapshot(self, *, provider, league_id, season):
        row = self.league
        return row if row and (row.provider, row.league_id, row.season) == (provider, league_id, season) else None

    def put_league_snapshot(self, record):
        self.league = record

    def get_team_snapshot(self, *, provider, league_id, team_id):
        return self.teams.get((provider, league_id, team_id))

    def put_team_snapshot(self, record):
        self.teams[(record.provider, record.league_id, record.team_id)] = record

    def get_sync_cursor(self, **kwargs):
        return None

    def put_sync_cursor(self, record):
        pass

    def get_reusable_artifact(self, key):
        return next((row for row in self.artifacts if row.key == key and row.reusable), None)

    def get_latest_reusable_artifact(self, *, artifact_kind, scope_kind, scope_id, model_version):
        rows = [
            row for row in self.artifacts
            if row.reusable
            and row.key.artifact_kind == artifact_kind
            and row.key.scope_kind == scope_kind
            and row.key.scope_id == scope_id
            and row.key.model_version == model_version
        ]
        return max(rows, key=lambda row: row.computed_at) if rows else None

    def put_artifact(self, record):
        self.artifacts.append(record)

    def invalidate_scope(self, **kwargs):
        pass

    def append_market_value_snapshot(self, **kwargs):
        self.market.append(kwargs)


def _league_state(*, as_of: datetime | None = None) -> LeagueState:
    league_id = "sleeper:123"
    rules = LeagueRules(
        team_count=2,
        roster_size=1,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(),
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Test League",
            season=2026,
            rules=rules,
            provider_refs=(ProviderRef(provider="sleeper", external_id="123"),),
        ),
        as_of=as_of or datetime(2026, 9, 8, 12, 0, tzinfo=UTC),
        teams=(
            Team(team_id="t1", league_id=league_id, display_name="One"),
            Team(team_id="t2", league_id=league_id, display_name="Two"),
        ),
        team_states=(TeamState(team_id="t1", roster=()), TeamState(team_id="t2", roster=())),
        players=(),
        player_states=(),
    )


def test_state_and_selected_team_restore_without_reingestion() -> None:
    persistence = MemoryPersistence()
    state = _league_state()

    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="t2",
    )
    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state == state
    assert restored.league_state.state_id == state.state_id
    assert restored.selected_team_id == "t2"
    assert restored.forecast_evidence is None
    assert len(persistence.teams) == 2


def test_restore_fails_closed_when_snapshot_hash_does_not_match_context() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    persist_runtime_snapshot(persistence, user_id="jimmy", league_state=state, selected_team_id=None)
    persistence.user = persistence.user.__class__(
        **{**persistence.user.__dict__, "state_hash": "wrong"}
    )

    assert restore_runtime_snapshot(persistence, user_id="jimmy") is None


def test_runtime_restore_backfills_exact_state_into_history_off_request_path() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="t2",
    )
    captured: list[LeagueState] = []

    class CapturingHistory:
        def save(self, restored_state: LeagueState) -> None:
            captured.append(restored_state)

        def latest_at_or_before(self, league_id: str, as_of: datetime) -> LeagueState | None:
            return None

    runtime = PersistentPrivateBetaRuntimeStore(
        persistence,
        state_snapshot_store=CapturingHistory(),
    )

    before = monotonic()
    restored = runtime.get("jimmy")
    assert monotonic() - before < 0.25
    assert restored.league_state == state
    assert restored.selected_team_id == "t2"

    deadline = monotonic() + 2
    while not captured and monotonic() < deadline:
        sleep(0.01)

    assert captured == [state]


def test_explicit_startup_restore_makes_followup_get_memory_only() -> None:
    class CountingPersistence(MemoryPersistence):
        def __init__(self) -> None:
            super().__init__()
            self.context_reads = 0

        def get_user_runtime_context(self, *, user_id):
            self.context_reads += 1
            return super().get_user_runtime_context(user_id=user_id)

    persistence = CountingPersistence()
    state = _league_state()
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="t2",
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)

    restored = runtime.restore_user("jimmy")
    reads_after_startup_restore = persistence.context_reads
    first_request = runtime.get("jimmy")

    assert restored.league_state == state
    assert restored.selected_team_id == "t2"
    assert first_request == restored
    assert reads_after_startup_restore == 1
    assert persistence.context_reads == reads_after_startup_restore


def test_incompatible_persisted_state_still_fails_closed_on_startup_restore() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="t2",
    )
    persistence.user = persistence.user.__class__(
        **{**persistence.user.__dict__, "state_hash": "incompatible"}
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)

    restored = runtime.restore_user("jimmy")

    assert restored.league_state is None
    assert restored.forecast_evidence is None
    assert restored.simulation_analytics is None
    assert restored.value_evidence is None


def test_running_refresh_restores_durable_last_good_identity() -> None:
    persistence = MemoryPersistence()
    last_good = _league_state()
    persist_runtime_snapshot(persistence, user_id="jimmy", league_state=last_good, selected_team_id="t2")
    persistence.put_artifact(ReusableArtifactRecord(
        key=ArtifactKey(artifact_kind=LAST_GOOD_ARTIFACT_KIND, scope_kind=LAST_GOOD_SCOPE_KIND, scope_id="jimmy", input_fingerprint=last_good.state_id, model_version=LAST_GOOD_MODEL_VERSION),
        payload={"league_state": last_good.model_dump(mode="json"), "selected_team_id": "t2"},
        computed_at=datetime.now(UTC),
    ))
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind="intelligence_job_lifecycle",
                scope_kind="user",
                scope_id="jimmy",
                input_fingerprint="job-running",
                model_version="intelligence-job-lifecycle-v1",
            ),
            payload={"status": "running"},
            computed_at=datetime.now(UTC),
        )
    )
    partial = _league_state(as_of=datetime(2026, 9, 8, 12, 5, tzinfo=UTC))
    persist_runtime_snapshot(persistence, user_id="jimmy", league_state=partial, selected_team_id="t1")

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")
    assert restored is not None
    assert restored.league_state.state_id == last_good.state_id
    assert restored.selected_team_id == "t2"
    assert any(
        row.key.artifact_kind == LAST_GOOD_ARTIFACT_KIND
        and row.key.input_fingerprint == last_good.state_id
        for row in persistence.artifacts
    )


def test_failed_refresh_restores_durable_last_good_identity() -> None:
    persistence = MemoryPersistence()
    last_good = _league_state()
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=last_good,
        selected_team_id="t2",
    )
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=LAST_GOOD_ARTIFACT_KIND,
                scope_kind=LAST_GOOD_SCOPE_KIND,
                scope_id="jimmy",
                input_fingerprint=last_good.state_id,
                model_version=LAST_GOOD_MODEL_VERSION,
            ),
            payload={
                "league_state": last_good.model_dump(mode="json"),
                "selected_team_id": "t2",
            },
            computed_at=datetime.now(UTC),
        )
    )
    failed_state = _league_state(
        as_of=datetime(2026, 9, 8, 12, 10, tzinfo=UTC)
    )
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=failed_state,
        selected_team_id="t1",
    )
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind="intelligence_job_lifecycle",
                scope_kind="user",
                scope_id="jimmy",
                input_fingerprint="job-failed",
                model_version="intelligence-job-lifecycle-v1",
            ),
            payload={"status": "failed"},
            computed_at=datetime.now(UTC),
        )
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state.state_id == last_good.state_id
    assert restored.selected_team_id == "t2"
    assert any(
        row.key.artifact_kind == LAST_GOOD_ARTIFACT_KIND
        and row.key.input_fingerprint == last_good.state_id
        for row in persistence.artifacts
    )


def test_interrupted_refresh_restores_durable_last_good_identity() -> None:
    persistence = MemoryPersistence()
    last_good = _league_state()
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=last_good,
        selected_team_id="t2",
    )
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=LAST_GOOD_ARTIFACT_KIND,
                scope_kind=LAST_GOOD_SCOPE_KIND,
                scope_id="jimmy",
                input_fingerprint=last_good.state_id,
                model_version=LAST_GOOD_MODEL_VERSION,
            ),
            payload={
                "league_state": last_good.model_dump(mode="json"),
                "selected_team_id": "t2",
            },
            computed_at=datetime.now(UTC),
        )
    )
    interrupted_state = _league_state(
        as_of=datetime(2026, 9, 8, 12, 15, tzinfo=UTC)
    )
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=interrupted_state,
        selected_team_id="t1",
    )
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind="intelligence_job_lifecycle",
                scope_kind="user",
                scope_id="jimmy",
                input_fingerprint="job-interrupted",
                model_version="intelligence-job-lifecycle-v1",
            ),
            payload={"status": "interrupted"},
            computed_at=datetime.now(UTC),
        )
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state.state_id == last_good.state_id
    assert restored.selected_team_id == "t2"
    assert any(
        row.key.artifact_kind == LAST_GOOD_ARTIFACT_KIND
        and row.key.input_fingerprint == last_good.state_id
        for row in persistence.artifacts
    )


def test_failed_refresh_never_restores_last_good_from_different_league() -> None:
    persistence = MemoryPersistence()
    old = _league_state()
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=LAST_GOOD_ARTIFACT_KIND,
                scope_kind=LAST_GOOD_SCOPE_KIND,
                scope_id="jimmy",
                input_fingerprint=old.state_id,
                model_version=LAST_GOOD_MODEL_VERSION,
            ),
            payload={"league_state": old.model_dump(mode="json"), "selected_team_id": "t2"},
            computed_at=datetime.now(UTC),
        )
    )
    new = old.model_copy(
        update={
            "league": old.league.model_copy(
                update={
                    "league_id": "sleeper:456",
                    "provider_refs": (ProviderRef(provider="sleeper", external_id="456"),),
                }
            ),
            "teams": (
                Team(team_id="n1", league_id="sleeper:456", display_name="New One"),
                Team(team_id="n2", league_id="sleeper:456", display_name="New Two"),
            ),
            "team_states": (
                TeamState(team_id="n1", roster=()),
                TeamState(team_id="n2", roster=()),
            ),
        }
    )
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=new,
        selected_team_id="n1",
    )
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind="intelligence_job_lifecycle",
                scope_kind="user",
                scope_id="jimmy",
                input_fingerprint="new-job-failed",
                model_version="intelligence-job-lifecycle-v1",
            ),
            payload={"status": "failed"},
            computed_at=datetime.now(UTC),
        )
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state.league.league_id == "sleeper:456"

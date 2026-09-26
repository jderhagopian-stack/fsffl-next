from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic, sleep

from fsffl.forecast.current_runtime import (
    LiveForecastRuntimeResult,
    LiveForecastSourceHealthEvent,
    LiveForecastSourceProvenance,
)
from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
)
from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
from fsffl.forecast.source_health import CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION
from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord
from fsffl.persistence.session import (
    LAST_GOOD_ARTIFACT_KIND, LAST_GOOD_MODEL_VERSION, LAST_GOOD_SCOPE_KIND,
    persist_runtime_snapshot, restore_runtime_snapshot,
)
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    ProviderRef,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult


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



def _stale_forecast_without_first_party_fumbles_lost(
    state: LeagueState,
) -> LiveForecastEvidence:
    provenance = tuple(
        LiveForecastSourceProvenance(
            provider=provider,
            source_version=f"{provider}-v1",
            captured_at=state.as_of,
            effective_at=state.as_of,
            usage_class="projection",
            provider_payload_sha256=(char * 64),
            health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
        )
        for provider, char in (("one", "a"), ("two", "b"))
    )
    health = tuple(
        LiveForecastSourceHealthEvent(
            provider=provider,
            disposition="accepted",
            check="revision_agnostic_scale_health",
            reason="synthetic valid legacy cache fixture",
            health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
            provider_payload_sha256=(char * 64),
        )
        for provider, char in (("one", "a"), ("two", "b"))
    )
    runtime = LiveForecastRuntimeResult(
        raw_ensemble=(),
        fantasy_point_forecasts=(),
        coverage=LiveEnsembleCoverage(
            independent_source_ids=("one", "two"),
            excluded_aggregate_source_ids=(),
            active_source_ids=("one", "two"),
            observation_count=0,
            minimum_independent_sources=2,
        ),
        successful_source_ids=("one", "two"),
        failed_sources=(),
        evaluation_as_of=state.as_of,
        source_provenance=provenance,
        source_health_events=health,
    )
    assert runtime.fumbles_lost_supplement_authority_fingerprint is None
    return LiveForecastEvidence(
        raw_forecasts=(),
        league_scored_forecasts=(),
        successful_source_ids=("one", "two"),
        failed_sources=(),
        uncertainty_ready=False,
        runtime_result=runtime,
    )


def _empty_value(state: LeagueState) -> CurrentMarketValueRuntimeResult:
    return CurrentMarketValueRuntimeResult(
        league_state_id=state.state_id,
        estimates=(),
        successful_source_ids=(),
        failed_sources=(),
        errors_by_source_id={},
        roster_player_count=0,
        valued_roster_player_count=0,
        market_context_id="test-market",
    )


def test_restore_selectively_rejects_pre_supplement_fum_lost_forecast_but_keeps_value() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    consuming = state.model_copy(
        update={
            "league": state.league.model_copy(
                update={
                    "rules": state.league.rules.model_copy(
                        update={
                            "scoring": (
                                ScoringRule(stat="fum_lost", points=-2.0),
                            )
                        }
                    )
                }
            )
        }
    )
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=consuming,
        selected_team_id="t2",
        forecast_evidence=_stale_forecast_without_first_party_fumbles_lost(consuming),
        value_evidence=_empty_value(consuming),
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state.state_id == consuming.state_id
    assert restored.forecast_evidence is None
    assert restored.simulation_analytics is None
    assert restored.value_evidence is not None
    assert restored.value_evidence.league_state_id == consuming.state_id


def test_restore_keeps_same_legacy_forecast_for_non_fum_lost_league() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    forecast = _stale_forecast_without_first_party_fumbles_lost(state)
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=_empty_value(state),
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.forecast_evidence is not None
    assert restored.forecast_evidence.model_version == forecast.model_version
    assert restored.value_evidence is not None



def test_restore_rejects_prior_first_party_supplement_contract_but_preserves_value() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    consuming = state.model_copy(
        update={
            "league": state.league.model_copy(
                update={
                    "rules": state.league.rules.model_copy(
                        update={
                            "scoring": (
                                ScoringRule(stat="fum_lost", points=-2.0),
                            )
                        }
                    )
                }
            )
        }
    )
    forecast = _stale_forecast_without_first_party_fumbles_lost(consuming)
    old_runtime = forecast.runtime_result.model_copy(
        update={
            "fumbles_lost_supplement_authority_fingerprint": "legacy-authority",
            "fumbles_lost_supplement_player_count": 330,
            "fumbles_lost_supplement_model_version": (
                "current-supplemental-coordinate-v3:first-party-fumbles-lost"
            ),
        }
    )
    assert (
        old_runtime.fumbles_lost_supplement_model_version
        != FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
    )
    old_forecast = LiveForecastEvidence(
        raw_forecasts=forecast.raw_forecasts,
        league_scored_forecasts=forecast.league_scored_forecasts,
        successful_source_ids=forecast.successful_source_ids,
        failed_sources=forecast.failed_sources,
        uncertainty_ready=forecast.uncertainty_ready,
        runtime_result=old_runtime,
        evidence_basis=forecast.evidence_basis,
    )
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=consuming,
        selected_team_id="t2",
        forecast_evidence=old_forecast,
        value_evidence=_empty_value(consuming),
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.forecast_evidence is None
    assert restored.simulation_analytics is None
    assert restored.value_evidence is not None

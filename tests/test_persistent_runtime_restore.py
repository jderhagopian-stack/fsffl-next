from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from threading import Event, RLock, Thread

from fsffl.forecast.current_runtime import (
    LiveForecastRuntimeResult,
    LiveForecastSourceHealthEvent,
    LiveForecastSourceProvenance,
)
from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
)
from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.source_health import CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION
from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord
from fsffl.persistence.session import (
    LAST_GOOD_ARTIFACT_KIND, LAST_GOOD_MODEL_VERSION, LAST_GOOD_SCOPE_KIND,
    PUBLISHED_GENERATION_ARTIFACT_KIND,
    LEAGUE_LAST_GOOD_ARTIFACT_KIND, LEAGUE_LAST_GOOD_MODEL_VERSION,
    LEAGUE_LAST_GOOD_SCOPE_KIND,
    persist_runtime_snapshot, restore_last_good_intelligence, restore_runtime_snapshot,
    restore_state_bound_intelligence, restore_state_bound_raw_forecast_evidence,
)
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.product.presentation_continuity import (
    PresentationContinuityStore,
    REQUIRED_PRESENTATION_SURFACES,
)
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.product.simulation_runtime import build_live_simulation_analytics
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    NflTeamBye,
    Player,
    PlayerState,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
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


def _simulation_state(*, as_of: datetime | None = None) -> LeagueState:
    state_as_of = as_of or datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
    league_id = "sleeper:sim-restart"
    provenance = Provenance(
        source="test",
        retrieved_at=state_as_of,
        effective_at=state_as_of,
    )
    rules = LeagueRules(
        team_count=2,
        roster_size=1,
        playoff_team_count=1,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(ScoringRule(stat="fum_lost", points=-2.0),),
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Simulation Restart League",
            season=2026,
            rules=rules,
            provider_refs=(ProviderRef(provider="sleeper", external_id="sim-restart"),),
        ),
        as_of=state_as_of,
        teams=(
            Team(team_id="a", league_id=league_id, display_name="A"),
            Team(team_id="b", league_id=league_id, display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=(RosterEntry(player_id="pa", slot=RosterSlot.QB),),
            ),
            TeamState(
                team_id="b",
                roster=(RosterEntry(player_id="pb", slot=RosterSlot.QB),),
            ),
        ),
        players=(
            Player(
                player_id="pa",
                full_name="A QB",
                position=Position.QB,
                nfl_team="NE",
            ),
            Player(
                player_id="pb",
                full_name="B QB",
                position=Position.QB,
                nfl_team="NYJ",
            ),
        ),
        player_states=(
            PlayerState(
                player_id="pa",
                as_of=state_as_of,
                nfl_team="NE",
                provenance=provenance,
            ),
            PlayerState(
                player_id="pb",
                as_of=state_as_of,
                nfl_team="NYJ",
                provenance=provenance,
            ),
        ),
        matchups=tuple(
            LeagueMatchup(
                week=week,
                team_a_id="a",
                team_b_id="b",
                provenance=provenance,
            )
            for week in range(1, 5)
        ),
        nfl_team_byes=(
            NflTeamBye(
                season=2026,
                nfl_team="NE",
                week=5,
                provenance=provenance,
            ),
            NflTeamBye(
                season=2026,
                nfl_team="NYJ",
                week=6,
                provenance=provenance,
            ),
        ),
    )


def _simulation_forecasts(
    state: LeagueState,
) -> tuple[ForecastObservation, ...]:
    provenance = Provenance(
        source="test",
        retrieved_at=state.as_of,
        effective_at=state.as_of,
    )
    return tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.QB,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=state.as_of,
            period_end=state.as_of + timedelta(days=180),
            distribution=ForecastDistribution(mean=mean, stddev=stddev),
            source="fsffl:live_league_scored",
            model_version="restart-simulation-forecast-v1",
            as_of=state.as_of,
            provenance=provenance,
        )
        for player_id, mean, stddev in (
            ("pa", 400.0, 80.0),
            ("pb", 250.0, 60.0),
        )
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


def test_restore_uses_user_exact_last_good_when_shared_league_snapshot_advances() -> None:
    persistence = MemoryPersistence()
    exact = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=exact,
        selected_team_id="t2",
    )
    jimmy_context = persistence.user
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=LAST_GOOD_ARTIFACT_KIND,
                scope_kind=LAST_GOOD_SCOPE_KIND,
                scope_id="jimmy",
                input_fingerprint=exact.state_id,
                model_version=LAST_GOOD_MODEL_VERSION,
            ),
            payload={
                "league_state": exact.model_dump(mode="json"),
                "selected_team_id": "t2",
            },
            computed_at=datetime.now(UTC),
        )
    )

    # Reproduce the production acceptance-user interaction: another isolated
    # session advances the shared latest league_snapshot while Jimmy's own
    # user_runtime_context still points to his exact prior State.
    advanced = _league_state(as_of=datetime(2026, 9, 8, 12, 5, tzinfo=UTC))
    persist_runtime_snapshot(
        persistence,
        user_id="state-first-production-acceptance",
        league_state=advanced,
        selected_team_id="t1",
    )
    persistence.user = jimmy_context

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state.state_id == exact.state_id
    assert restored.league_state.state_id != persistence.league.state_hash
    assert restored.selected_team_id == "t2"
    assert restored.restored_from_last_good is True


def test_restore_does_not_use_nonmatching_last_good_after_shared_snapshot_advances() -> None:
    persistence = MemoryPersistence()
    exact = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=exact,
        selected_team_id="t2",
    )
    jimmy_context = persistence.user

    unrelated_last_good = _league_state(
        as_of=datetime(2026, 9, 8, 11, 55, tzinfo=UTC)
    )
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=LAST_GOOD_ARTIFACT_KIND,
                scope_kind=LAST_GOOD_SCOPE_KIND,
                scope_id="jimmy",
                input_fingerprint=unrelated_last_good.state_id,
                model_version=LAST_GOOD_MODEL_VERSION,
            ),
            payload={
                "league_state": unrelated_last_good.model_dump(mode="json"),
                "selected_team_id": "t1",
            },
            computed_at=datetime.now(UTC),
        )
    )
    advanced = _league_state(as_of=datetime(2026, 9, 8, 12, 5, tzinfo=UTC))
    persist_runtime_snapshot(
        persistence,
        user_id="state-first-production-acceptance",
        league_state=advanced,
        selected_team_id="t1",
    )
    persistence.user = jimmy_context

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
    assert restored.league_state.state_id == partial.state_id
    assert restored.selected_team_id == "t1"
    # Last-good is restored only as lightweight presentation identity; no stale
    # Forecast/Simulation/Value graph is materialized into the runtime snapshot.
    assert restored.served_league_state_id == last_good.state_id
    assert restored.served_league_id == last_good.league.league_id
    assert restored.served_team_ids == ("t1", "t2")
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
    assert restored.league_state.state_id == failed_state.state_id
    assert restored.selected_team_id == "t1"
    # Last-good is restored only as lightweight presentation identity; no stale
    # Forecast/Simulation/Value graph is materialized into the runtime snapshot.
    assert restored.served_league_state_id == last_good.state_id
    assert restored.served_league_id == last_good.league.league_id
    assert restored.served_team_ids == ("t1", "t2")
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
    assert restored.league_state.state_id == interrupted_state.state_id
    assert restored.selected_team_id == "t1"
    # Last-good is restored only as lightweight presentation identity; no stale
    # Forecast/Simulation/Value graph is materialized into the runtime snapshot.
    assert restored.served_league_state_id == last_good.state_id
    assert restored.served_league_id == last_good.league.league_id
    assert restored.served_team_ids == ("t1", "t2")
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


def _with_replayable_raw_forecast(
    forecast: LiveForecastEvidence,
    state: LeagueState,
) -> LiveForecastEvidence:
    raw = ForecastObservation(
        player_id="fixture-player",
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.PASS_YARDS,
        period_start=state.as_of,
        period_end=state.as_of + timedelta(days=1),
        distribution=ForecastDistribution(mean=4000.0, stddev=250.0),
        source="fsffl:live_ensemble",
        model_version="fixture-raw-v1",
        as_of=state.as_of,
        provenance=Provenance(
            source="fixture",
            retrieved_at=state.as_of,
            effective_at=state.as_of,
        ),
    )
    runtime = forecast.runtime_result.model_copy(
        update={
            "raw_ensemble": (raw,),
            "coverage": forecast.runtime_result.coverage.model_copy(
                update={"observation_count": 1}
            ),
        }
    )
    return replace(
        forecast,
        raw_forecasts=(raw,),
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



def test_restart_restores_new_target_state_and_lightweight_last_good_identity_separately() -> None:
    persistence = MemoryPersistence()
    last_good = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    forecast = _stale_forecast_without_first_party_fumbles_lost(last_good)
    assert forecast.uncertainty_ready is False
    value = _empty_value(last_good)

    persist_runtime_snapshot(
        persistence,
        user_id="jimmy-dual",
        league_state=last_good,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
    )
    assert any(
        row.key.artifact_kind == LEAGUE_LAST_GOOD_ARTIFACT_KIND
        and row.key.scope_kind == LEAGUE_LAST_GOOD_SCOPE_KIND
        and row.key.model_version == LEAGUE_LAST_GOOD_MODEL_VERSION
        for row in persistence.artifacts
    )

    target = _league_state(as_of=datetime(2026, 9, 8, 12, 10, tzinfo=UTC))
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy-dual",
        league_state=target,
        selected_team_id="t1",
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy-dual")
    assert restored is not None
    assert restored.league_state.state_id == target.state_id
    assert restored.selected_team_id == "t1"
    assert restored.forecast_evidence is None
    assert restored.value_evidence is None
    assert restored.served_league_id == last_good.league.league_id
    assert restored.served_league_state_id == last_good.state_id
    assert restored.served_as_of == last_good.as_of
    assert restored.served_team_ids == ("t1", "t2")
    assert not hasattr(restored, "served_forecast_evidence")
    assert not hasattr(restored, "served_simulation_analytics")
    assert not hasattr(restored, "served_value_evidence")


def test_per_league_last_good_survives_switch_away_and_back() -> None:
    persistence = MemoryPersistence()
    fsffl = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    fsffl_forecast = _stale_forecast_without_first_party_fumbles_lost(fsffl)
    persist_runtime_snapshot(
        persistence,
        user_id="switch-user",
        league_state=fsffl,
        selected_team_id="t2",
        forecast_evidence=fsffl_forecast,
        value_evidence=_empty_value(fsffl),
    )

    hodor_id = "sleeper:456"
    hodor = fsffl.model_copy(
        update={
            "league": fsffl.league.model_copy(
                update={
                    "league_id": hodor_id,
                    "name": "Hodor",
                    "provider_refs": (
                        ProviderRef(provider="sleeper", external_id="456"),
                    ),
                }
            ),
            "teams": (
                Team(team_id="h1", league_id=hodor_id, display_name="H One"),
                Team(team_id="h2", league_id=hodor_id, display_name="H Two"),
            ),
            "team_states": (
                TeamState(team_id="h1", roster=()),
                TeamState(team_id="h2", roster=()),
            ),
        }
    )
    hodor_forecast = _stale_forecast_without_first_party_fumbles_lost(hodor)
    persist_runtime_snapshot(
        persistence,
        user_id="switch-user",
        league_state=hodor,
        selected_team_id="h1",
        forecast_evidence=hodor_forecast,
        value_evidence=_empty_value(hodor),
    )

    restored_fsffl = restore_last_good_intelligence(
        persistence,
        user_id="switch-user",
        league_id=fsffl.league.league_id,
    )
    restored_hodor = restore_last_good_intelligence(
        persistence,
        user_id="switch-user",
        league_id=hodor_id,
    )
    assert restored_fsffl is not None
    assert restored_fsffl.league_state.state_id == fsffl.state_id
    assert restored_fsffl.value_evidence is not None
    assert restored_hodor is not None
    assert restored_hodor.league_state.state_id == hodor.state_id
    assert restored_hodor.value_evidence is not None



def test_partial_current_restore_migrates_legacy_served_identity_into_league_scope() -> None:
    persistence = MemoryPersistence()
    last_good = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    forecast = _stale_forecast_without_first_party_fumbles_lost(last_good)
    value = _empty_value(last_good)

    persist_runtime_snapshot(
        persistence,
        user_id="legacy-migrate",
        league_state=last_good,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
    )
    # Simulate an upgraded deployment that has only the historical user-scoped
    # last-good pointer, not the newer per-league identity record.
    persistence.artifacts = [
        row
        for row in persistence.artifacts
        if row.key.artifact_kind != LEAGUE_LAST_GOOD_ARTIFACT_KIND
    ]

    current = _league_state(as_of=datetime(2026, 9, 8, 12, 15, tzinfo=UTC))
    persist_runtime_snapshot(
        persistence,
        user_id="legacy-migrate",
        league_state=current,
        selected_team_id="t1",
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.restore_user("legacy-migrate")
    assert restored.league_state is not None
    assert restored.league_state.state_id == current.state_id
    assert restored.served_intelligence is not None
    assert restored.served_intelligence.league_state_id == last_good.state_id

    migrated = [
        row
        for row in persistence.artifacts
        if row.key.artifact_kind == LEAGUE_LAST_GOOD_ARTIFACT_KIND
        and row.key.scope_kind == LEAGUE_LAST_GOOD_SCOPE_KIND
        and row.key.scope_id == "legacy-migrate:sleeper:123"
        and row.key.model_version == LEAGUE_LAST_GOOD_MODEL_VERSION
    ]
    assert len(migrated) == 1
    migrated_state = LeagueState.model_validate(migrated[0].payload["league_state"])
    assert migrated_state.state_id == last_good.state_id
    assert migrated[0].payload["selected_team_id"] == "t2"



def test_compatible_last_good_forecast_is_replayed_for_new_exact_state(
    monkeypatch,
) -> None:
    persistence = MemoryPersistence()
    base = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    consuming_rules = base.league.rules.model_copy(
        update={"scoring": (ScoringRule(stat="fum_lost", points=-2.0),)}
    )
    prior = base.model_copy(
        update={"league": base.league.model_copy(update={"rules": consuming_rules})}
    )
    legacy = _stale_forecast_without_first_party_fumbles_lost(prior)
    prior_runtime = legacy.runtime_result.model_copy(
        update={
            "fumbles_lost_supplement_authority_fingerprint": "prior-authority",
            "fumbles_lost_supplement_player_count": 1,
            "fumbles_lost_supplement_model_version": FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
            "fumbles_lost_supplement_league_state_id": prior.state_id,
        }
    )
    forecast = _with_replayable_raw_forecast(
        replace(legacy, runtime_result=prior_runtime),
        prior,
    )
    value = _empty_value(prior)
    persist_runtime_snapshot(
        persistence,
        user_id="reuse-user",
        league_state=prior,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
    )

    target = prior.model_copy(
        update={"as_of": datetime(2026, 9, 8, 12, 10, tzinfo=UTC)}
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.set_league_state("reuse-user", target)
    # Existing direct in-memory reuse must reject the prior State-bound supplement.
    assert runtime.get("reuse-user").forecast_evidence is None

    replay_calls: list[tuple[str, str]] = []

    def replay(target_state, prior_evidence):
        replay_calls.append((target_state.state_id, prior_evidence.model_version))
        replay_runtime = prior_evidence.runtime_result.model_copy(
            update={
                "fumbles_lost_supplement_authority_fingerprint": "target-authority",
                "fumbles_lost_supplement_league_state_id": target_state.state_id,
            }
        )
        return replace(prior_evidence, runtime_result=replay_runtime)

    monkeypatch.setattr(
        "fsffl.product.persistent_runtime.replay_live_forecast_evidence_for_state",
        replay,
    )
    restored = runtime.restore_exact_state_intelligence("reuse-user")

    assert replay_calls == [(target.state_id, forecast.model_version)]
    assert restored.league_state is not None
    assert restored.league_state.state_id == target.state_id
    assert restored.forecast_evidence is not None
    assert (
        restored.forecast_evidence.runtime_result.fumbles_lost_supplement_league_state_id
        == target.state_id
    )
    assert restored.simulation_analytics is None
    assert restored.value_evidence is None
    assert restored.intelligence_reused is True

def test_downstream_scoring_change_replays_raw_forecast_and_rebuilds_scoring(
    monkeypatch,
) -> None:
    persistence = MemoryPersistence()
    prior = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    forecast = _with_replayable_raw_forecast(
        _stale_forecast_without_first_party_fumbles_lost(prior),
        prior,
    )
    persist_runtime_snapshot(
        persistence,
        user_id="scoring-user",
        league_state=prior,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=_empty_value(prior),
    )
    changed_rules = prior.league.rules.model_copy(
        update={"scoring": (ScoringRule(stat="pass_td", points=6.0),)}
    )
    target = prior.model_copy(
        update={
            "as_of": datetime(2026, 9, 8, 12, 10, tzinfo=UTC),
            "league": prior.league.model_copy(update={"rules": changed_rules}),
        }
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.set_league_state("scoring-user", target)

    replay_calls: list[str] = []

    def replay(target_state, prior_evidence):
        replay_calls.append(target_state.state_id)
        return replace(
            prior_evidence,
            runtime_result=prior_evidence.runtime_result.model_copy(
                update={"evaluation_as_of": prior_evidence.runtime_result.evaluation_as_of}
            ),
        )

    monkeypatch.setattr(
        "fsffl.product.persistent_runtime.replay_live_forecast_evidence_for_state",
        replay,
    )
    restored = runtime.restore_exact_state_intelligence("scoring-user")

    assert replay_calls == [target.state_id]
    assert restored.forecast_evidence is not None
    assert restored.simulation_analytics is None
    assert restored.value_evidence is None
    decision = runtime.forecast_replay_decision("scoring-user")
    assert decision is not None
    assert decision["selection"] == "raw_replay"
    assert decision["raw_compatibility"] == "compatible"
    assert decision["rejection_components"] == []
    assert "league_scoring" in decision["downstream_rebuild_components"]
    assert decision["fresh_acquisition_required"] is False

    assert runtime.wait_for_checkpoint("scoring-user", timeout=2.0)
    restarted = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored_after_restart = restarted.restore_user("scoring-user")
    assert restored_after_restart.league_state is not None
    assert restored_after_restart.league_state.state_id == target.state_id
    persisted_decision = restarted.forecast_replay_decision("scoring-user")
    assert persisted_decision is not None
    assert persisted_decision["selection"] == "raw_replay"
    assert persisted_decision["prior_state_id"] == prior.state_id
    assert persisted_decision["target_state_id"] == target.state_id


def test_raw_forecast_material_change_rejects_replay_with_component_reason(
    monkeypatch,
) -> None:
    persistence = MemoryPersistence()
    prior = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    forecast = _with_replayable_raw_forecast(
        _stale_forecast_without_first_party_fumbles_lost(prior),
        prior,
    )
    persist_runtime_snapshot(
        persistence,
        user_id="reject-user",
        league_state=prior,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=_empty_value(prior),
    )
    target = prior.model_copy(
        update={
            "as_of": datetime(2026, 9, 8, 12, 10, tzinfo=UTC),
            "league": prior.league.model_copy(update={"season": 2027}),
        }
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.set_league_state("reject-user", target)

    def unexpected_replay(*_args, **_kwargs):
        raise AssertionError("raw-material changes must not replay prior raw evidence")

    monkeypatch.setattr(
        "fsffl.product.persistent_runtime.replay_live_forecast_evidence_for_state",
        unexpected_replay,
    )
    restored = runtime.restore_exact_state_intelligence("reject-user")

    assert restored.forecast_evidence is None
    assert restored.simulation_analytics is None
    assert restored.value_evidence is None
    decision = runtime.forecast_replay_decision("reject-user")
    assert decision is not None
    assert decision["selection"] == "fresh_acquisition"
    assert decision["raw_compatibility"] == "incompatible"
    assert decision["reason"] == "raw_forecast_material_inputs_changed"
    assert decision["rejection_components"] == ["nfl_season_changed"]
    assert decision["fresh_acquisition_required"] is True


def test_raw_forecast_restore_ignores_stale_downstream_supplement_contract() -> None:
    persistence = MemoryPersistence()
    base = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    rules = base.league.rules.model_copy(
        update={"scoring": (ScoringRule(stat="fum_lost", points=-2.0),)}
    )
    state = base.model_copy(
        update={"league": base.league.model_copy(update={"rules": rules})}
    )
    stale = _with_replayable_raw_forecast(
        _stale_forecast_without_first_party_fumbles_lost(state),
        state,
    )
    old_runtime = stale.runtime_result.model_copy(
        update={
            "fumbles_lost_supplement_authority_fingerprint": "legacy-authority",
            "fumbles_lost_supplement_model_version": "legacy-supplement-v0",
            "fumbles_lost_supplement_league_state_id": state.state_id,
        }
    )
    stale = replace(stale, runtime_result=old_runtime)
    persist_runtime_snapshot(
        persistence,
        user_id="raw-restore",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=stale,
        value_evidence=_empty_value(state),
    )

    restored = restore_state_bound_raw_forecast_evidence(
        persistence,
        league_state=state,
    )

    assert restored is not None
    assert restored.raw_forecasts == stale.raw_forecasts
    assert restored.successful_source_ids == ("one", "two")

def test_same_state_stale_supplement_replays_raw_forecast_before_provider_outage(
    monkeypatch,
) -> None:
    persistence = MemoryPersistence()
    base = _league_state(as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    rules = base.league.rules.model_copy(
        update={"scoring": (ScoringRule(stat="fum_lost", points=-2.0),)}
    )
    state = base.model_copy(
        update={"league": base.league.model_copy(update={"rules": rules})}
    )
    stale = _with_replayable_raw_forecast(
        _stale_forecast_without_first_party_fumbles_lost(state),
        state,
    )
    stale_runtime = stale.runtime_result.model_copy(
        update={
            "fumbles_lost_supplement_authority_fingerprint": "legacy-authority",
            "fumbles_lost_supplement_model_version": "legacy-supplement-v0",
            "fumbles_lost_supplement_league_state_id": state.state_id,
        }
    )
    stale = replace(stale, runtime_result=stale_runtime)
    persist_runtime_snapshot(
        persistence,
        user_id="same-state-outage",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=stale,
        value_evidence=_empty_value(state),
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.set_league_state("same-state-outage", state)

    # Exact-State restore must reject the stale downstream supplement while the
    # governed raw provider evidence remains independently reusable.
    assert runtime.get("same-state-outage").forecast_evidence is None

    replay_calls: list[str] = []

    def replay(target_state, prior_evidence):
        replay_calls.append(target_state.state_id)
        replay_runtime = prior_evidence.runtime_result.model_copy(
            update={
                "fumbles_lost_supplement_authority_fingerprint": "current-authority",
                "fumbles_lost_supplement_model_version": (
                    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
                ),
                "fumbles_lost_supplement_league_state_id": target_state.state_id,
            }
        )
        return replace(prior_evidence, runtime_result=replay_runtime)

    monkeypatch.setattr(
        "fsffl.product.persistent_runtime.replay_live_forecast_evidence_for_state",
        replay,
    )

    provider_calls: list[str] = []

    def provider_outage(_state):
        provider_calls.append("forecast")
        raise RuntimeError("all live Forecast providers unavailable")

    restored = runtime.restore_exact_state_intelligence("same-state-outage")
    evidence = restored.forecast_evidence
    if evidence is None:
        evidence = provider_outage(state)

    assert replay_calls == [state.state_id]
    assert provider_calls == []
    assert evidence is not None
    assert evidence.raw_forecasts == stale.raw_forecasts
    assert restored.simulation_analytics is None
    assert restored.value_evidence is None
    assert restored.intelligence_reused is True

    decision = runtime.forecast_replay_decision("same-state-outage")
    assert decision is not None
    assert decision["selection"] == "raw_replay"
    assert decision["raw_compatibility"] == "compatible"
    assert decision["prior_state_id"] == state.state_id
    assert decision["target_state_id"] == state.state_id
    assert decision["fresh_acquisition_required"] is False
    assert decision["rejection_components"] == []

def test_restore_finds_older_simulation_with_exact_current_forecast_dependency() -> None:
    persistence = MemoryPersistence()
    state = _simulation_state()

    base = _with_replayable_raw_forecast(
        _stale_forecast_without_first_party_fumbles_lost(state),
        state,
    )
    current_a = replace(
        base,
        runtime_result=base.runtime_result.model_copy(
            update={
                "fumbles_lost_supplement_authority_fingerprint": "authority-a",
                "fumbles_lost_supplement_model_version": (
                    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
                ),
                "fumbles_lost_supplement_league_state_id": state.state_id,
            }
        ),
    )
    current_b = replace(
        base,
        runtime_result=base.runtime_result.model_copy(
            update={
                "fumbles_lost_supplement_authority_fingerprint": "authority-b",
                "fumbles_lost_supplement_model_version": (
                    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
                ),
                "fumbles_lost_supplement_league_state_id": state.state_id,
            }
        ),
    )
    simulation_a = build_live_simulation_analytics(
        state,
        forecasts=_simulation_forecasts(state),
        forecast_model_version="forecast-a",
        simulation_count=100,
        seed=7,
        generated_at=state.as_of,
    )
    simulation_b = build_live_simulation_analytics(
        state,
        forecasts=_simulation_forecasts(state),
        forecast_model_version="forecast-b",
        simulation_count=100,
        seed=11,
        generated_at=state.as_of,
    )

    # Persist a compatible A pair, then a newer B pair for the same canonical
    # State. Finally make Forecast A current again without rebuilding Simulation.
    # Exact dependency lookup must recover older Simulation A rather than consult
    # only the newest same-State Simulation B.
    persist_runtime_snapshot(
        persistence,
        user_id="exact-simulation-dependency",
        league_state=state,
        selected_team_id="a",
        forecast_evidence=current_a,
        simulation_analytics=simulation_a,
        value_evidence=_empty_value(state),
    )
    persist_runtime_snapshot(
        persistence,
        user_id="exact-simulation-dependency",
        league_state=state,
        selected_team_id="a",
        forecast_evidence=current_b,
        simulation_analytics=simulation_b,
        value_evidence=_empty_value(state),
    )
    persist_runtime_snapshot(
        persistence,
        user_id="exact-simulation-dependency",
        league_state=state,
        selected_team_id="a",
        forecast_evidence=current_a,
        value_evidence=_empty_value(state),
    )

    restored_forecast, restored_simulation, restored_value = (
        restore_state_bound_intelligence(
            persistence,
            league_state=state,
        )
    )

    assert restored_forecast is not None
    assert (
        restored_forecast.runtime_result.fumbles_lost_supplement_authority_fingerprint
        == "authority-a"
    )
    assert restored_simulation == simulation_a
    assert restored_simulation != simulation_b
    assert restored_value is not None


def test_same_state_forecast_replay_interruption_restart_rejects_stale_simulation(
    monkeypatch,
) -> None:
    persistence = MemoryPersistence()
    state = _simulation_state()
    stale = _with_replayable_raw_forecast(
        _stale_forecast_without_first_party_fumbles_lost(state),
        state,
    )
    stale_runtime = stale.runtime_result.model_copy(
        update={
            "fumbles_lost_supplement_authority_fingerprint": "legacy-authority",
            "fumbles_lost_supplement_model_version": "legacy-supplement-v0",
            "fumbles_lost_supplement_league_state_id": state.state_id,
        }
    )
    stale = replace(stale, runtime_result=stale_runtime)
    old_simulation = build_live_simulation_analytics(
        state,
        forecasts=_simulation_forecasts(state),
        forecast_model_version=stale.model_version,
        simulation_count=100,
        seed=7,
        generated_at=state.as_of,
    )
    persist_runtime_snapshot(
        persistence,
        user_id="same-state-restart",
        league_state=state,
        selected_team_id="a",
        forecast_evidence=stale,
        simulation_analytics=old_simulation,
        value_evidence=_empty_value(state),
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.set_league_state("same-state-restart", state)
    before_replay = runtime.get("same-state-restart")
    assert before_replay.forecast_evidence is None
    assert before_replay.simulation_analytics is None

    def replay(target_state, prior_evidence):
        return replace(
            prior_evidence,
            runtime_result=prior_evidence.runtime_result.model_copy(
                update={
                    "fumbles_lost_supplement_authority_fingerprint": (
                        "current-authority"
                    ),
                    "fumbles_lost_supplement_model_version": (
                        FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
                    ),
                    "fumbles_lost_supplement_league_state_id": target_state.state_id,
                }
            ),
        )

    monkeypatch.setattr(
        "fsffl.product.persistent_runtime.replay_live_forecast_evidence_for_state",
        replay,
    )
    replayed = runtime.restore_exact_state_intelligence("same-state-restart")
    assert replayed.forecast_evidence is not None
    assert replayed.simulation_analytics is None
    assert runtime.wait_for_checkpoint("same-state-restart", timeout=2.0)

    # Reproduce an interruption after Forecast replay was durably checkpointed but
    # before its dependent Simulation could be rebuilt.
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind="intelligence_job_lifecycle",
                scope_kind="user",
                scope_id="same-state-restart",
                input_fingerprint="same-state-replay-interrupted",
                model_version="intelligence-job-lifecycle-v1",
            ),
            payload={"status": "interrupted"},
            computed_at=datetime.now(UTC),
        )
    )

    restarted = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored_after_restart = restarted.restore_user("same-state-restart")

    assert restored_after_restart.league_state is not None
    assert restored_after_restart.league_state.state_id == state.state_id
    # The replayed Forecast belonged only to the interrupted working generation.
    # Restart restores the prior published generation, whose legacy Forecast is
    # rejected by the current supplement contract rather than promoting replay work.
    assert restored_after_restart.forecast_evidence is None
    assert restored_after_restart.simulation_analytics is None
    assert restored_after_restart.value_evidence is not None



def test_working_generation_checkpoint_never_moves_restart_authority() -> None:
    persistence = MemoryPersistence()
    published_state = _league_state(
        as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
    )
    published_forecast = _stale_forecast_without_first_party_fumbles_lost(
        published_state
    )
    published_value = _empty_value(published_state)
    persist_runtime_snapshot(
        persistence,
        user_id="atomic-restart",
        league_state=published_state,
        selected_team_id="t2",
        forecast_evidence=published_forecast,
        value_evidence=published_value,
    )
    published_pointer = persistence.user
    assert published_pointer is not None

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.restore_user("atomic-restart")
    assert restored.league_state is not None
    assert restored.league_state.state_id == published_state.state_id

    target_state = _league_state(
        as_of=datetime(2026, 9, 8, 12, 10, tzinfo=UTC)
    )
    runtime.begin_working_generation(
        "atomic-restart",
        league_state=target_state,
    )
    assert runtime.checkpoint_working_generation("atomic-restart")

    # Durable artifacts for the replacement may exist, but the session pointer
    # remains the prior published generation until atomic publication succeeds.
    assert persistence.user is not None
    assert persistence.user.state_hash == published_pointer.state_hash

    restarted = PersistentPrivateBetaRuntimeStore(
        persistence_store=persistence
    )
    after_restart = restarted.restore_user("atomic-restart")
    assert after_restart.league_state is not None
    assert after_restart.league_state.state_id == published_state.state_id
    assert after_restart.league_state.state_id != target_state.state_id


def test_same_state_working_artifacts_never_gain_restart_authority_before_manifest_publish() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    published_forecast = _stale_forecast_without_first_party_fumbles_lost(state)
    published_value = _empty_value(state)
    persist_runtime_snapshot(
        persistence,
        user_id="same-state-atomic-restart",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=published_forecast,
        value_evidence=published_value,
        publication_generation_id="published-generation-a",
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.restore_user("same-state-atomic-restart")
    assert restored.publication_generation_id == "published-generation-a"
    assert restored.forecast_evidence is not None
    assert restored.forecast_evidence.raw_forecasts == ()

    runtime.begin_working_generation(
        "same-state-atomic-restart",
        league_state=state,
    )
    working_forecast = _with_replayable_raw_forecast(published_forecast, state)
    runtime.set_forecast_evidence(
        "same-state-atomic-restart",
        working_forecast,
    )
    runtime.set_value_evidence(
        "same-state-atomic-restart",
        published_value,
    )
    assert runtime.checkpoint_working_generation("same-state-atomic-restart")

    # The reusable cache now contains a newer same-State Forecast artifact, but the
    # published-generation manifest still names generation A. A crash/restart must
    # therefore restore A rather than the unpublished working Forecast.
    restarted = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    after_restart = restarted.restore_user("same-state-atomic-restart")
    assert after_restart.publication_generation_id == "published-generation-a"
    assert after_restart.forecast_evidence is not None
    assert after_restart.forecast_evidence.raw_forecasts == ()
    assert after_restart.value_evidence is not None


class BlockingPublicationPersistence(MemoryPersistence):
    """Pause one named generation after its manifest write for race testing."""

    def __init__(self, blocked_generation_id: str) -> None:
        super().__init__()
        self.blocked_generation_id = blocked_generation_id
        self.publication_entered = Event()
        self.release_publication = Event()

    def put_artifact(self, record):
        super().put_artifact(record)
        if (
            record.key.artifact_kind == PUBLISHED_GENERATION_ARTIFACT_KIND
            and record.payload.get("publication_generation_id")
            == self.blocked_generation_id
        ):
            self.publication_entered.set()
            if not self.release_publication.wait(timeout=3.0):
                raise RuntimeError("test publication release timed out")


def test_team_switch_before_publish_interrupts_without_advancing_old_team_restart_authority() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    forecast = _stale_forecast_without_first_party_fumbles_lost(state)
    value = _empty_value(state)
    persist_runtime_snapshot(
        persistence,
        user_id="team-interrupt",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="generation-a",
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.restore_user("team-interrupt")
    assert restored.selected_team_id == "t2"
    assert restored.publication_generation_id == "generation-a"

    runtime.begin_working_generation("team-interrupt", league_state=state)
    runtime.select_team("team-interrupt", "t1")
    assert runtime.working_generation_active("team-interrupt") is False

    try:
        runtime.publish_working_generation(
            "team-interrupt",
            publication_generation_id="generation-b",
        )
    except ValueError as exc:
        assert "working intelligence generation" in str(exc)
    else:
        raise AssertionError("team switch must interrupt stale working publication")

    assert runtime.wait_for_checkpoint("team-interrupt", timeout=3.0)
    restarted = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    after_restart = restarted.restore_user("team-interrupt")
    assert after_restart.selected_team_id == "t1"

    stale_generation_b = [
        row
        for row in persistence.artifacts
        if row.key.artifact_kind == PUBLISHED_GENERATION_ARTIFACT_KIND
        and row.payload.get("publication_generation_id") == "generation-b"
    ]
    assert stale_generation_b == []


def test_team_switch_during_durable_publish_serializes_then_restart_restores_new_team() -> None:
    persistence = BlockingPublicationPersistence("generation-b")
    state = _league_state()
    forecast = _stale_forecast_without_first_party_fumbles_lost(state)
    value = _empty_value(state)
    persist_runtime_snapshot(
        persistence,
        user_id="team-race",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="generation-a",
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.restore_user("team-race")
    assert restored.selected_team_id == "t2"
    assert restored.publication_generation_id == "generation-a"
    runtime.begin_working_generation("team-race", league_state=state)

    publish_errors = []
    publish_finished = Event()

    def publish() -> None:
        try:
            runtime.publish_working_generation(
                "team-race",
                publication_generation_id="generation-b",
            )
        except Exception as exc:  # pragma: no cover - asserted below
            publish_errors.append(exc)
        finally:
            publish_finished.set()

    select_errors = []
    select_finished = Event()

    def switch_team() -> None:
        try:
            runtime.select_team("team-race", "t1")
        except Exception as exc:  # pragma: no cover - asserted below
            select_errors.append(exc)
        finally:
            select_finished.set()

    publish_thread = Thread(target=publish, name="test-publish")
    publish_thread.start()
    assert persistence.publication_entered.wait(timeout=2.0)

    # The durable generation-B manifest exists, but the runtime publication lock is
    # still held through pointer commit + in-memory swap. Team selection must wait.
    select_thread = Thread(target=switch_team, name="test-select-team")
    select_thread.start()
    assert select_finished.wait(timeout=0.05) is False

    persistence.release_publication.set()
    publish_thread.join(timeout=3.0)
    select_thread.join(timeout=3.0)
    assert publish_finished.is_set()
    assert select_finished.is_set()
    assert publish_errors == []
    assert select_errors == []

    # The queued team switch applies after the coherent generation-B commit/swap,
    # invalidates its team-specific presentation id, then durably checkpoints t1.
    current = runtime.get("team-race")
    assert current.selected_team_id == "t1"
    assert current.publication_generation_id is None
    assert runtime.wait_for_checkpoint("team-race", timeout=3.0)
    assert persistence.user is not None
    assert persistence.user.selected_team_id == "t1"

    restarted = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    after_restart = restarted.restore_user("team-race")
    assert after_restart.selected_team_id == "t1"

    latest_manifest = persistence.get_latest_reusable_artifact(
        artifact_kind=PUBLISHED_GENERATION_ARTIFACT_KIND,
        scope_kind="user_league_state",
        scope_id=f"team-race:{state.league.league_id}:{state.state_id}",
        model_version="runtime-published-intelligence-generation-v1",
    )
    assert latest_manifest is not None
    assert latest_manifest.payload["selected_team_id"] == "t1"


def test_cold_set_league_state_restores_published_team_and_generation_identity() -> None:
    """Hosted activate() must not clear a valid exact-State publication on cold use."""

    persistence = MemoryPersistence()
    state = _league_state()
    forecast = _stale_forecast_without_first_party_fumbles_lost(state)
    value = _empty_value(state)
    persist_runtime_snapshot(
        persistence,
        user_id="cold-published-identity",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="generation-restored",
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.set_league_state("cold-published-identity", state)

    assert restored.selected_team_id == "t2"
    assert restored.publication_generation_id == "generation-restored"
    assert restored.forecast_evidence is not None
    assert restored.value_evidence is not None

    # This is the exact hosted acceptance branch: because the durable managed team
    # is restored with its generation, activate() has no reason to call select_team()
    # and invalidate the coherent presentation identity.
    assert runtime.get("cold-published-identity").selected_team_id == "t2"
    assert (
        runtime.get("cold-published-identity").publication_generation_id
        == "generation-restored"
    )


def test_changed_state_restore_carries_only_team_matched_served_publication_generation() -> None:
    persistence = MemoryPersistence()
    last_good = _league_state(
        as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
    )
    forecast = _stale_forecast_without_first_party_fumbles_lost(last_good)
    value = _empty_value(last_good)
    persist_runtime_snapshot(
        persistence,
        user_id="served-generation-match",
        league_state=last_good,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="served-generation-a",
    )
    target = _league_state(
        as_of=datetime(2026, 9, 8, 12, 10, tzinfo=UTC)
    )
    persist_runtime_snapshot(
        persistence,
        user_id="served-generation-match",
        league_state=target,
        selected_team_id="t2",
    )

    restored = restore_runtime_snapshot(
        persistence,
        user_id="served-generation-match",
    )
    assert restored is not None
    assert restored.league_state.state_id == target.state_id
    assert restored.publication_generation_id is None
    assert restored.served_league_state_id == last_good.state_id
    assert restored.served_publication_generation_id == "served-generation-a"

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    active = runtime.restore_user("served-generation-match")
    assert active.publication_generation_id is None
    assert active.served_intelligence is not None
    assert (
        active.served_intelligence.publication_generation_id
        == "served-generation-a"
    )

    mismatch = MemoryPersistence()
    persist_runtime_snapshot(
        mismatch,
        user_id="served-generation-mismatch",
        league_state=last_good,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="served-generation-a",
    )
    persist_runtime_snapshot(
        mismatch,
        user_id="served-generation-mismatch",
        league_state=target,
        selected_team_id="t1",
    )
    mismatched = restore_runtime_snapshot(
        mismatch,
        user_id="served-generation-mismatch",
    )
    assert mismatched is not None
    assert mismatched.served_league_state_id == last_good.state_id
    assert mismatched.served_publication_generation_id is None


def test_cold_changed_state_activation_restores_target_team_before_served_generation() -> None:
    persistence = MemoryPersistence()
    last_good = _league_state(
        as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
    )
    forecast = _stale_forecast_without_first_party_fumbles_lost(last_good)
    value = _empty_value(last_good)
    persist_runtime_snapshot(
        persistence,
        user_id="cold-served-generation",
        league_state=last_good,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="served-generation-a",
    )
    target = _league_state(
        as_of=datetime(2026, 9, 8, 12, 10, tzinfo=UTC)
    )
    persist_runtime_snapshot(
        persistence,
        user_id="cold-served-generation",
        league_state=target,
        selected_team_id="t2",
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    activated = runtime.set_league_state("cold-served-generation", target)

    assert activated.selected_team_id == "t2"
    assert activated.publication_generation_id is None
    assert activated.served_intelligence is not None
    assert activated.served_intelligence.league_state_id == last_good.state_id
    assert (
        activated.served_intelligence.publication_generation_id
        == "served-generation-a"
    )


def test_team_selection_serializes_with_entire_publication_sequence() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    forecast = _stale_forecast_without_first_party_fumbles_lost(state)
    value = _empty_value(state)
    persist_runtime_snapshot(
        persistence,
        user_id="full-publication-sequence",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="generation-a",
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.restore_user("full-publication-sequence")
    assert restored.selected_team_id == "t2"
    runtime.begin_working_generation(
        "full-publication-sequence",
        league_state=state,
    )

    sequence_entered = Event()
    release_sequence = Event()
    select_finished = Event()
    select_errors = []

    def hold_publication_sequence() -> None:
        with runtime.publication_sequence("full-publication-sequence"):
            sequence_entered.set()
            if not release_sequence.wait(timeout=3.0):
                raise RuntimeError("test publication sequence release timed out")

    def switch_team() -> None:
        try:
            runtime.select_team("full-publication-sequence", "t1")
        except Exception as exc:  # pragma: no cover - asserted below
            select_errors.append(exc)
        finally:
            select_finished.set()

    publication_thread = Thread(
        target=hold_publication_sequence,
        name="test-full-publication-sequence",
    )
    publication_thread.start()
    assert sequence_entered.wait(timeout=2.0)

    select_thread = Thread(target=switch_team, name="test-sequence-team-select")
    select_thread.start()
    assert select_finished.wait(timeout=0.05) is False

    release_sequence.set()
    publication_thread.join(timeout=3.0)
    select_thread.join(timeout=3.0)
    assert select_finished.is_set()
    assert select_errors == []
    assert runtime.get("full-publication-sequence").selected_team_id == "t1"
    assert runtime.working_generation_active("full-publication-sequence") is False


def test_conditional_team_switch_requires_active_working_generation() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    forecast = _stale_forecast_without_first_party_fumbles_lost(state)
    value = _empty_value(state)
    persist_runtime_snapshot(
        persistence,
        user_id="conditional-team-switch",
        league_state=state,
        selected_team_id="t2",
        forecast_evidence=forecast,
        value_evidence=value,
        publication_generation_id="generation-a",
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.restore_user("conditional-team-switch")

    assert (
        runtime.select_team_if_working_generation_active(
            "conditional-team-switch",
            "t1",
        )
        is None
    )
    runtime.begin_working_generation(
        "conditional-team-switch",
        league_state=state,
    )
    switched = runtime.select_team_if_working_generation_active(
        "conditional-team-switch",
        "t1",
    )
    assert switched is not None
    working, selected = switched
    assert working.selected_team_id == "t2"
    assert selected.selected_team_id == "t1"
    assert runtime.working_generation_active("conditional-team-switch") is False


class MultiUserLifecyclePersistence(MemoryPersistence):
    """Thread-safe in-memory persistence with independent per-user runtime rows."""

    def __init__(self) -> None:
        super().__init__()
        self.users = {}
        self.leagues = {}
        self._io_lock = RLock()
        self.block_publication_user: str | None = None
        self.block_publication_generation: str | None = None
        self.publication_entered = Event()
        self.release_publication = Event()
        self.block_restore_user: str | None = None
        self.restore_entered = Event()
        self.release_restore = Event()
        self.block_checkpoint_user: str | None = None
        self.checkpoint_entered = Event()
        self.release_checkpoint = Event()

    def get_user_runtime_context(self, *, user_id):
        if user_id == self.block_restore_user:
            self.restore_entered.set()
            if not self.release_restore.wait(timeout=3.0):
                raise RuntimeError("test restore release timed out")
        with self._io_lock:
            return self.users.get(user_id)

    def put_user_runtime_context(self, record):
        if record.user_id == self.block_checkpoint_user:
            self.checkpoint_entered.set()
            if not self.release_checkpoint.wait(timeout=3.0):
                raise RuntimeError("test checkpoint release timed out")
        with self._io_lock:
            self.users[record.user_id] = record

    def get_league_snapshot(self, *, provider, league_id, season):
        with self._io_lock:
            return self.leagues.get((provider, league_id, season))

    def put_league_snapshot(self, record):
        with self._io_lock:
            self.leagues[(record.provider, record.league_id, record.season)] = record

    def get_team_snapshot(self, *, provider, league_id, team_id):
        with self._io_lock:
            return self.teams.get((provider, league_id, team_id))

    def put_team_snapshot(self, record):
        with self._io_lock:
            self.teams[(record.provider, record.league_id, record.team_id)] = record

    def get_reusable_artifact(self, key):
        with self._io_lock:
            return next(
                (row for row in self.artifacts if row.key == key and row.reusable),
                None,
            )

    def get_latest_reusable_artifact(
        self,
        *,
        artifact_kind,
        scope_kind,
        scope_id,
        model_version,
    ):
        with self._io_lock:
            rows = [
                row
                for row in self.artifacts
                if row.reusable
                and row.key.artifact_kind == artifact_kind
                and row.key.scope_kind == scope_kind
                and row.key.scope_id == scope_id
                and row.key.model_version == model_version
            ]
            return max(rows, key=lambda row: row.computed_at) if rows else None

    def put_artifact(self, record):
        with self._io_lock:
            self.artifacts.append(record)
        if (
            record.key.artifact_kind == PUBLISHED_GENERATION_ARTIFACT_KIND
            and self.block_publication_user is not None
            and record.key.scope_id.startswith(
                f"{self.block_publication_user}:"
            )
            and record.payload.get("publication_generation_id")
            == self.block_publication_generation
        ):
            self.publication_entered.set()
            if not self.release_publication.wait(timeout=3.0):
                raise RuntimeError("test publication release timed out")

    def append_market_value_snapshot(self, **kwargs):
        with self._io_lock:
            self.market.append(kwargs)


def _league_state_for(
    league_id: str,
    *,
    external_id: str,
    as_of: datetime | None = None,
) -> LeagueState:
    rules = LeagueRules(
        team_count=2,
        roster_size=1,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(),
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name=f"Test League {external_id}",
            season=2026,
            rules=rules,
            provider_refs=(
                ProviderRef(provider="sleeper", external_id=external_id),
            ),
        ),
        as_of=as_of or datetime(2026, 9, 8, 12, 0, tzinfo=UTC),
        teams=(
            Team(team_id="t1", league_id=league_id, display_name="One"),
            Team(team_id="t2", league_id=league_id, display_name="Two"),
        ),
        team_states=(
            TeamState(team_id="t1", roster=()),
            TeamState(team_id="t2", roster=()),
        ),
        players=(),
        player_states=(),
    )


def _seed_published_user(
    persistence: MultiUserLifecyclePersistence,
    *,
    user_id: str,
    state: LeagueState,
    generation_id: str,
    selected_team_id: str = "t2",
) -> None:
    persist_runtime_snapshot(
        persistence,
        user_id=user_id,
        league_state=state,
        selected_team_id=selected_team_id,
        forecast_evidence=_stale_forecast_without_first_party_fumbles_lost(state),
        value_evidence=_empty_value(state),
        publication_generation_id=generation_id,
    )


def _join_bounded(thread: Thread, *, timeout: float = 2.0) -> None:
    thread.join(timeout=timeout)
    assert not thread.is_alive(), f"thread {thread.name} exceeded bounded lifecycle timeout"


def test_two_user_final_publication_does_not_block_cold_restore() -> None:
    persistence = MultiUserLifecyclePersistence()
    state = _league_state()
    _seed_published_user(
        persistence,
        user_id="user-a",
        state=state,
        generation_id="a-generation-1",
    )
    _seed_published_user(
        persistence,
        user_id="user-b",
        state=state,
        generation_id="b-generation-1",
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.restore_user("user-a")
    runtime.begin_working_generation("user-a", league_state=state)

    persistence.block_publication_user = "user-a"
    persistence.block_publication_generation = "a-generation-2"
    publish_errors = []

    def publish_a() -> None:
        try:
            runtime.publish_working_generation(
                "user-a",
                publication_generation_id="a-generation-2",
            )
        except Exception as exc:
            publish_errors.append(exc)

    publish_thread = Thread(target=publish_a, name="publish-a")
    publish_thread.start()
    assert persistence.publication_entered.wait(timeout=1.0)

    restore_result = {}
    restore_errors = []

    def restore_b() -> None:
        try:
            restore_result["context"] = runtime.restore_user("user-b")
        except Exception as exc:
            restore_errors.append(exc)

    restore_thread = Thread(target=restore_b, name="restore-b")
    restore_thread.start()
    _join_bounded(restore_thread, timeout=1.0)
    assert restore_errors == []
    assert restore_result["context"].publication_generation_id == "b-generation-1"

    persistence.release_publication.set()
    _join_bounded(publish_thread)
    assert publish_errors == []
    assert runtime.get("user-a").publication_generation_id == "a-generation-2"


def test_user_a_checkpoint_wait_does_not_block_user_b_state_activation() -> None:
    persistence = MultiUserLifecyclePersistence()
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    state = _league_state()

    persistence.block_checkpoint_user = "user-a"
    runtime.set_league_state("user-a", state)
    assert persistence.checkpoint_entered.wait(timeout=1.0)

    wait_result = {}

    def wait_a() -> None:
        wait_result["ok"] = runtime.wait_for_checkpoint("user-a", timeout=2.5)

    wait_thread = Thread(target=wait_a, name="checkpoint-wait-a")
    wait_thread.start()

    activate_errors = []
    activate_done = Event()

    def activate_b() -> None:
        try:
            runtime.set_league_state("user-b", state)
        except Exception as exc:
            activate_errors.append(exc)
        finally:
            activate_done.set()

    activate_thread = Thread(target=activate_b, name="activate-b")
    activate_thread.start()
    assert activate_done.wait(timeout=0.5)
    assert activate_errors == []

    persistence.release_checkpoint.set()
    _join_bounded(wait_thread)
    _join_bounded(activate_thread)
    assert wait_result["ok"] is True


def test_simultaneous_cold_restore_is_per_user_isolated() -> None:
    persistence = MultiUserLifecyclePersistence()
    state = _league_state()
    _seed_published_user(
        persistence,
        user_id="user-a",
        state=state,
        generation_id="a-generation",
    )
    _seed_published_user(
        persistence,
        user_id="user-b",
        state=state,
        generation_id="b-generation",
    )
    persistence.block_restore_user = "user-a"
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)

    a_result = {}
    b_result = {}
    errors = []

    def restore_a() -> None:
        try:
            a_result["context"] = runtime.restore_user("user-a")
        except Exception as exc:
            errors.append(exc)

    def restore_b() -> None:
        try:
            b_result["context"] = runtime.restore_user("user-b")
        except Exception as exc:
            errors.append(exc)

    a_thread = Thread(target=restore_a, name="cold-restore-a")
    a_thread.start()
    assert persistence.restore_entered.wait(timeout=1.0)
    b_thread = Thread(target=restore_b, name="cold-restore-b")
    b_thread.start()
    _join_bounded(b_thread, timeout=1.0)
    assert b_result["context"].publication_generation_id == "b-generation"

    persistence.release_restore.set()
    _join_bounded(a_thread)
    assert errors == []
    assert a_result["context"].publication_generation_id == "a-generation"


def test_simultaneous_publication_is_per_user_isolated() -> None:
    persistence = MultiUserLifecyclePersistence()
    state = _league_state()
    for user_id in ("user-a", "user-b"):
        _seed_published_user(
            persistence,
            user_id=user_id,
            state=state,
            generation_id=f"{user_id}-generation-1",
        )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    for user_id in ("user-a", "user-b"):
        runtime.restore_user(user_id)
        runtime.begin_working_generation(user_id, league_state=state)

    persistence.block_publication_user = "user-a"
    persistence.block_publication_generation = "user-a-generation-2"
    errors = []

    def publish(user_id: str) -> None:
        try:
            runtime.publish_working_generation(
                user_id,
                publication_generation_id=f"{user_id}-generation-2",
            )
        except Exception as exc:
            errors.append(exc)

    a_thread = Thread(target=lambda: publish("user-a"), name="publish-a")
    a_thread.start()
    assert persistence.publication_entered.wait(timeout=1.0)

    b_thread = Thread(target=lambda: publish("user-b"), name="publish-b")
    b_thread.start()
    _join_bounded(b_thread, timeout=1.0)
    assert runtime.get("user-b").publication_generation_id == "user-b-generation-2"

    persistence.release_publication.set()
    _join_bounded(a_thread)
    assert errors == []
    assert runtime.get("user-a").publication_generation_id == "user-a-generation-2"


def test_user_a_team_switch_does_not_wait_for_user_b_publication() -> None:
    persistence = MultiUserLifecyclePersistence()
    state = _league_state()
    for user_id in ("user-a", "user-b"):
        _seed_published_user(
            persistence,
            user_id=user_id,
            state=state,
            generation_id=f"{user_id}-generation-1",
        )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    for user_id in ("user-a", "user-b"):
        runtime.restore_user(user_id)
    runtime.begin_working_generation("user-b", league_state=state)

    persistence.block_publication_user = "user-b"
    persistence.block_publication_generation = "user-b-generation-2"
    publish_errors = []

    def publish_b() -> None:
        try:
            runtime.publish_working_generation(
                "user-b",
                publication_generation_id="user-b-generation-2",
            )
        except Exception as exc:
            publish_errors.append(exc)

    publish_thread = Thread(target=publish_b, name="publish-b")
    publish_thread.start()
    assert persistence.publication_entered.wait(timeout=1.0)

    select_done = Event()
    select_errors = []

    def switch_a() -> None:
        try:
            runtime.select_team("user-a", "t1")
        except Exception as exc:
            select_errors.append(exc)
        finally:
            select_done.set()

    select_thread = Thread(target=switch_a, name="team-switch-a")
    select_thread.start()
    assert select_done.wait(timeout=0.5)
    assert select_errors == []
    assert runtime.get("user-a").selected_team_id == "t1"

    persistence.release_publication.set()
    _join_bounded(select_thread)
    _join_bounded(publish_thread)
    assert publish_errors == []


def test_user_a_league_switch_does_not_wait_for_user_b_cold_restore() -> None:
    persistence = MultiUserLifecyclePersistence()
    state_a = _league_state_for("sleeper:a", external_id="a")
    state_a2 = _league_state_for("sleeper:a2", external_id="a2")
    state_b = _league_state_for("sleeper:b", external_id="b")
    _seed_published_user(
        persistence,
        user_id="user-b",
        state=state_b,
        generation_id="b-generation",
    )

    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    runtime.set_league_state("user-a", state_a)
    assert runtime.wait_for_checkpoint("user-a", timeout=2.0)

    persistence.block_restore_user = "user-b"
    restore_errors = []

    def restore_b() -> None:
        try:
            runtime.restore_user("user-b")
        except Exception as exc:
            restore_errors.append(exc)

    restore_thread = Thread(target=restore_b, name="restore-b")
    restore_thread.start()
    assert persistence.restore_entered.wait(timeout=1.0)

    switch_done = Event()
    switch_errors = []

    def switch_a() -> None:
        try:
            runtime.set_league_state("user-a", state_a2)
        except Exception as exc:
            switch_errors.append(exc)
        finally:
            switch_done.set()

    switch_thread = Thread(target=switch_a, name="league-switch-a")
    switch_thread.start()
    assert switch_done.wait(timeout=0.5)
    assert switch_errors == []
    assert runtime.get("user-a").league_state.league.league_id == "sleeper:a2"

    persistence.release_restore.set()
    _join_bounded(switch_thread)
    _join_bounded(restore_thread)
    assert restore_errors == []


def test_interrupted_worker_cannot_attach_after_identity_change() -> None:
    persistence = MultiUserLifecyclePersistence()
    state = _league_state()
    _seed_published_user(
        persistence,
        user_id="stale-worker",
        state=state,
        generation_id="generation-a",
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    before = runtime.restore_user("stale-worker")
    runtime.begin_working_generation("stale-worker", league_state=state)
    runtime.select_team("stale-worker", "t1")

    try:
        runtime.set_forecast_evidence(
            "stale-worker",
            before.forecast_evidence,
            refreshed_league_state=state,
            require_working_generation=True,
        )
    except ValueError as exc:
        assert "no longer active" in str(exc)
    else:
        raise AssertionError("stale worker mutation must fail after identity change")

    current = runtime.get("stale-worker")
    assert current.selected_team_id == "t1"
    assert current.publication_generation_id is None
    assert runtime.wait_for_checkpoint("stale-worker", timeout=2.0)


def test_crash_after_presentation_build_before_durable_publication_restores_prior_generation() -> None:
    persistence = MultiUserLifecyclePersistence()
    state = _league_state()
    _seed_published_user(
        persistence,
        user_id="presentation-crash",
        state=state,
        generation_id="generation-a",
    )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = runtime.restore_user("presentation-crash")
    assert restored.publication_generation_id == "generation-a"
    runtime.begin_working_generation("presentation-crash", league_state=state)
    working = runtime.working_context("presentation-crash")

    continuity = PresentationContinuityStore(persistence)
    promoted = continuity.promote(
        user_id="presentation-crash",
        runtime=working,
        builders=tuple(
            (
                surface,
                lambda surface=surface: {
                    "surface": surface,
                    "league_state_id": state.state_id,
                },
            )
            for surface in REQUIRED_PRESENTATION_SURFACES
        ),
    )
    assert promoted is not None
    assert promoted.publication_generation_id != "generation-a"

    restarted = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    after_restart = restarted.restore_user("presentation-crash")
    assert after_restart.publication_generation_id == "generation-a"
    assert after_restart.league_state.state_id == state.state_id


def test_bounded_repeated_two_user_publication_stress() -> None:
    persistence = MultiUserLifecyclePersistence()
    state = _league_state()
    for user_id in ("stress-a", "stress-b"):
        _seed_published_user(
            persistence,
            user_id=user_id,
            state=state,
            generation_id=f"{user_id}-generation-0",
        )
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    for user_id in ("stress-a", "stress-b"):
        runtime.restore_user(user_id)

    for index in range(20):
        for user_id in ("stress-a", "stress-b"):
            runtime.begin_working_generation(user_id, league_state=state)

        start = Event()
        errors = []

        def publish(user_id: str) -> None:
            try:
                if not start.wait(timeout=1.0):
                    raise RuntimeError("stress start gate timed out")
                runtime.publish_working_generation(
                    user_id,
                    publication_generation_id=f"{user_id}-generation-{index + 1}",
                )
            except Exception as exc:
                errors.append(exc)

        a_thread = Thread(target=lambda: publish("stress-a"), name=f"stress-a-{index}")
        b_thread = Thread(target=lambda: publish("stress-b"), name=f"stress-b-{index}")
        a_thread.start()
        b_thread.start()
        start.set()
        _join_bounded(a_thread)
        _join_bounded(b_thread)
        assert errors == []
        assert (
            runtime.get("stress-a").publication_generation_id
            == f"stress-a-generation-{index + 1}"
        )
        assert (
            runtime.get("stress-b").publication_generation_id
            == f"stress-b-generation-{index + 1}"
        )

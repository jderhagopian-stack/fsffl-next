from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
)
from fsffl.forecast.supplemental_coordinate import league_consumes_fumbles_lost
from fsffl.state.models import LeagueState

from .contracts import (
    ArtifactKey,
    LeagueSnapshotRecord,
    canonical_fingerprint,
    PersistenceStore,
    ReusableArtifactRecord,
    TeamSnapshotRecord,
    UserRuntimeContextRecord,
    utc_now,
)
from .supplemental_coordinate import (
    first_party_fumbles_lost_supplement_artifact,
)
from .runtime_cache import (
    FORECAST_ARTIFACT_KIND,
    FORECAST_MODEL_VERSION,
    LEAGUE_SCOPE_KIND,
    SIMULATION_ARTIFACT_KIND,
    SIMULATION_MODEL_VERSION,
    VALUE_ARTIFACT_KIND,
    VALUE_MODEL_VERSION,
    decode_forecast_evidence,
    decode_simulation,
    decode_value_result,
    forecast_artifact,
    simulation_artifact,
    value_artifact,
)

if TYPE_CHECKING:
    from fsffl.product.runtime import LiveForecastEvidence
    from fsffl.product.simulation_runtime import LiveSimulationAnalyticsResult
    from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult


CURRENT_TEAM_ANALYTICS_VIEW_VERSION = "next7-team-view-v4:position-strength-age"
LAST_GOOD_ARTIFACT_KIND = "runtime_last_good_bundle"
LAST_GOOD_SCOPE_KIND = "user"
LAST_GOOD_MODEL_VERSION = "runtime-last-good-v1"
LEAGUE_LAST_GOOD_ARTIFACT_KIND = "runtime_last_good_league_bundle"
LEAGUE_LAST_GOOD_SCOPE_KIND = "user_league"
LEAGUE_LAST_GOOD_MODEL_VERSION = "runtime-last-good-league-v1"
JOB_LIFECYCLE_ARTIFACT_KIND = "intelligence_job_lifecycle"
JOB_LIFECYCLE_MODEL_VERSION = "intelligence-job-lifecycle-v1"
FORECAST_REPLAY_DECISION_ARTIFACT_KIND = "forecast_replay_decision"
FORECAST_REPLAY_DECISION_SCOPE_KIND = "user_league_state"
FORECAST_REPLAY_DECISION_MODEL_VERSION = "forecast-replay-decision-v1"
PUBLISHED_GENERATION_ARTIFACT_KIND = "runtime_published_intelligence_generation"
PUBLISHED_GENERATION_SCOPE_KIND = "user_league_state"
PUBLISHED_GENERATION_MODEL_VERSION = "runtime-published-intelligence-generation-v1"


def _forecast_replay_scope_id(
    user_id: str,
    league_state: LeagueState,
) -> str:
    return f"{user_id}:{league_state.league.league_id}:{league_state.state_id}"


def _published_generation_scope_id(
    user_id: str,
    league_state: LeagueState,
) -> str:
    return f"{user_id}:{league_state.league.league_id}:{league_state.state_id}"


def _published_generation_record(
    *,
    user_id: str,
    league_state: LeagueState,
    selected_team_id: str | None,
    publication_generation_id: str,
    forecast_record: ReusableArtifactRecord,
    simulation_record: ReusableArtifactRecord | None,
    value_record: ReusableArtifactRecord,
    computed_at: datetime,
) -> ReusableArtifactRecord:
    payload = {
        "publication_generation_id": publication_generation_id,
        "league_id": league_state.league.league_id,
        "league_state_id": league_state.state_id,
        "selected_team_id": selected_team_id,
        "forecast_input_fingerprint": forecast_record.key.input_fingerprint,
        "simulation_input_fingerprint": (
            simulation_record.key.input_fingerprint
            if simulation_record is not None
            else None
        ),
        "value_input_fingerprint": value_record.key.input_fingerprint,
    }
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=PUBLISHED_GENERATION_ARTIFACT_KIND,
            scope_kind=PUBLISHED_GENERATION_SCOPE_KIND,
            scope_id=_published_generation_scope_id(user_id, league_state),
            input_fingerprint=canonical_fingerprint(payload),
            model_version=PUBLISHED_GENERATION_MODEL_VERSION,
        ),
        payload=payload,
        computed_at=computed_at,
    )


def _published_generation_manifest(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
) -> ReusableArtifactRecord | None:
    record = store.get_latest_reusable_artifact(
        artifact_kind=PUBLISHED_GENERATION_ARTIFACT_KIND,
        scope_kind=PUBLISHED_GENERATION_SCOPE_KIND,
        scope_id=_published_generation_scope_id(user_id, league_state),
        model_version=PUBLISHED_GENERATION_MODEL_VERSION,
    )
    if record is None:
        return None
    payload = record.payload
    if (
        payload.get("league_id") != league_state.league.league_id
        or payload.get("league_state_id") != league_state.state_id
    ):
        return None
    return record


def restore_published_generation_identity(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
) -> tuple[str | None, str | None]:
    """Return the team-specific identity of the last published exact-State generation."""

    manifest = _published_generation_manifest(
        store,
        user_id=user_id,
        league_state=league_state,
    )
    if manifest is None:
        return None, None
    payload = manifest.payload
    generation_id = str(payload.get("publication_generation_id") or "").strip()
    selected_team_id = payload.get("selected_team_id")
    if selected_team_id not in {team.team_id for team in league_state.teams}:
        selected_team_id = None
    return generation_id or None, selected_team_id


def persist_forecast_replay_decision(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
    decision: dict[str, object],
) -> None:
    """Persist one exact-target replay decision as audit/acceptance evidence."""

    payload = dict(decision)
    payload["user_id"] = user_id
    payload["target_league_id"] = league_state.league.league_id
    payload["target_state_id"] = league_state.state_id
    store.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=FORECAST_REPLAY_DECISION_ARTIFACT_KIND,
                scope_kind=FORECAST_REPLAY_DECISION_SCOPE_KIND,
                scope_id=_forecast_replay_scope_id(user_id, league_state),
                input_fingerprint=canonical_fingerprint(payload),
                model_version=FORECAST_REPLAY_DECISION_MODEL_VERSION,
            ),
            payload=payload,
            computed_at=utc_now(),
        )
    )


def restore_forecast_replay_decision(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
) -> dict[str, object] | None:
    record = store.get_latest_reusable_artifact(
        artifact_kind=FORECAST_REPLAY_DECISION_ARTIFACT_KIND,
        scope_kind=FORECAST_REPLAY_DECISION_SCOPE_KIND,
        scope_id=_forecast_replay_scope_id(user_id, league_state),
        model_version=FORECAST_REPLAY_DECISION_MODEL_VERSION,
    )
    return dict(record.payload) if record is not None else None


@dataclass(frozen=True)
class DurableRuntimeSnapshot:
    league_state: LeagueState
    selected_team_id: str | None
    publication_generation_id: str | None = None
    forecast_evidence: LiveForecastEvidence | None = None
    simulation_analytics: LiveSimulationAnalyticsResult | None = None
    value_evidence: CurrentMarketValueRuntimeResult | None = None
    served_league_id: str | None = None
    served_league_state_id: str | None = None
    served_as_of: datetime | None = None
    served_team_ids: tuple[str, ...] = ()
    served_publication_generation_id: str | None = None
    restored_from_last_good: bool = False


def _provider_external_id(league_state: LeagueState) -> tuple[str, str]:
    sleeper = next((ref for ref in league_state.league.provider_refs if ref.provider == "sleeper"), None)
    if sleeper is not None:
        return sleeper.provider, sleeper.external_id
    if league_state.league.provider_refs:
        ref = league_state.league.provider_refs[0]
        return ref.provider, ref.external_id
    return "canonical", league_state.league.league_id


def _terminal_bundle(
    forecast_evidence: "LiveForecastEvidence | None",
    simulation_analytics: "LiveSimulationAnalyticsResult | None",
    value_evidence: "CurrentMarketValueRuntimeResult | None",
) -> bool:
    return bool(
        forecast_evidence is not None
        and value_evidence is not None
        and (
            simulation_analytics is not None
            or not forecast_evidence.uncertainty_ready
        )
    )


def _league_last_good_scope_id(user_id: str, league_id: str) -> str:
    return f"{user_id}:{league_id}"


def persist_league_last_good_identity(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
    selected_team_id: str | None,
) -> None:
    """Persist only the per-league presentation identity, never runtime context."""

    store.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=LEAGUE_LAST_GOOD_ARTIFACT_KIND,
                scope_kind=LEAGUE_LAST_GOOD_SCOPE_KIND,
                scope_id=_league_last_good_scope_id(
                    user_id,
                    league_state.league.league_id,
                ),
                input_fingerprint=league_state.state_id,
                model_version=LEAGUE_LAST_GOOD_MODEL_VERSION,
            ),
            payload={
                "league_state": league_state.model_dump(mode="json"),
                "selected_team_id": selected_team_id,
            },
            computed_at=utc_now(),
        )
    )


def persist_runtime_identity(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
    selected_team_id: str | None,
) -> None:
    """Advance only the durable current-State / managed-team pointer.

    This is intentionally lighter than persist_runtime_snapshot. Callers use it only
    after canonical State durability is ordered ahead on the same per-user checkpoint
    queue. A managed-team change must not republish Forecast / Simulation / Value
    artifacts or manufacture a new team-specific publication generation before
    reconciliation coherently promotes one.
    """

    provider, external_id = _provider_external_id(league_state)
    store.put_user_runtime_context(
        UserRuntimeContextRecord(
            user_id=user_id,
            provider=provider,
            league_external_id=external_id,
            league_id=league_state.league.league_id,
            season=league_state.league.season,
            selected_team_id=selected_team_id,
            state_hash=league_state.state_id,
            updated_at=utc_now(),
        )
    )

def persist_runtime_snapshot(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
    selected_team_id: str | None,
    forecast_evidence: LiveForecastEvidence | None = None,
    simulation_analytics: LiveSimulationAnalyticsResult | None = None,
    value_evidence: CurrentMarketValueRuntimeResult | None = None,
    publish_context: bool = True,
    publication_generation_id: str | None = None,
) -> None:
    """Checkpoint authoritative runtime outputs without changing their ownership.

    ``publish_context=False`` persists State-bound working artifacts without moving
    the durable user-runtime pointer or last-good publication identity. This lets a
    replacement generation become durable before its manifest-last atomic publish.
    """

    provider, external_id = _provider_external_id(league_state)
    now = utc_now()
    state_payload = league_state.model_dump(mode="json")
    store.put_league_snapshot(
        LeagueSnapshotRecord(
            provider=provider,
            league_id=league_state.league.league_id,
            season=league_state.league.season,
            state_hash=league_state.state_id,
            payload=state_payload,
            source_updated_at=league_state.as_of,
            recorded_at=now,
        )
    )
    team_states = {row.team_id: row for row in league_state.team_states}
    for team in league_state.teams:
        store.put_team_snapshot(
            TeamSnapshotRecord(
                provider=provider,
                league_id=league_state.league.league_id,
                team_id=team.team_id,
                state_hash=league_state.state_id,
                payload={
                    "team": team.model_dump(mode="json"),
                    "team_state": team_states[team.team_id].model_dump(mode="json"),
                },
                source_updated_at=league_state.as_of,
                recorded_at=now,
            )
        )
    terminal_bundle = _terminal_bundle(
        forecast_evidence,
        simulation_analytics,
        value_evidence,
    )
    # For terminal intelligence, the published-generation manifest is the durable
    # commit point. Non-terminal State activation still advances the user pointer
    # immediately while derived intelligence remains unavailable/last-good.
    if publish_context and not terminal_bundle:
        store.put_user_runtime_context(
            UserRuntimeContextRecord(
                user_id=user_id,
                provider=provider,
                league_external_id=external_id,
                league_id=league_state.league.league_id,
                season=league_state.league.season,
                selected_team_id=selected_team_id,
                state_hash=league_state.state_id,
                updated_at=now,
            )
        )

    forecast_record = None
    simulation_record = None
    value_record = None
    if forecast_evidence is not None:
        supplement = getattr(
            forecast_evidence.runtime_result,
            "first_party_fumbles_lost_supplement",
            None,
        )
        if supplement is not None:
            if supplement.league_state_id != league_state.state_id:
                raise ValueError(
                    "first-party FUMBLES_LOST supplement does not match persisted State"
                )
            store.put_artifact(
                first_party_fumbles_lost_supplement_artifact(supplement)
            )
        forecast_record = forecast_artifact(
            league_state_id=league_state.state_id,
            evidence=forecast_evidence,
        )
        store.put_artifact(forecast_record)
    if simulation_analytics is not None and forecast_record is not None:
        simulation_record = simulation_artifact(
            league_state_id=league_state.state_id,
            forecast_fingerprint=forecast_record.key.input_fingerprint,
            result=simulation_analytics,
        )
        store.put_artifact(simulation_record)
        if publish_context:
            # Automatic annual League Atlas baseline capture is a publication
            # side-effect only; unpublished working Simulation never advances it.
            from fsffl.product.league_atlas_preseason import (
                capture_preseason_baseline_if_eligible,
            )

            capture_preseason_baseline_if_eligible(
                store,
                state=league_state,
                forecast=forecast_evidence,
                simulation=simulation_analytics,
            )
    if value_evidence is not None:
        value_record = value_artifact(
            league_state_id=league_state.state_id,
            result=value_evidence,
        )
        store.put_artifact(value_record)
        if publish_context:
            for estimate in value_evidence.estimates:
                store.append_market_value_snapshot(
                    asset_ref=estimate.asset_id,
                    asset_kind=estimate.asset_kind.value,
                    scale_id=estimate.scale.scale_id,
                    market_context_id=estimate.market_context_id,
                    estimate_as_of=estimate.as_of,
                    value=float(estimate.distribution.mean),
                    source_lineage={
                        "model_version": estimate.model_version,
                        "evidence_sources": list(estimate.evidence_sources),
                    },
                    recorded_at=now,
                )

    # Stable governed terminal bundles get durable presentation identities.
    # Keep the legacy user-scoped record for compatibility and also retain one
    # league-scoped record so switching away and back cannot lose that league's
    # last-good presentation snapshot.
    if publish_context and terminal_bundle:
        if forecast_record is None or value_record is None:
            raise ValueError("terminal publication requires Forecast and Value artifacts")
        generation_id = str(publication_generation_id or "").strip() or canonical_fingerprint(
            league_state.state_id,
            selected_team_id,
            forecast_record.key.input_fingerprint,
            (
                simulation_record.key.input_fingerprint
                if simulation_record is not None
                else None
            ),
            value_record.key.input_fingerprint,
        )

        # Crash-safe publication order:
        # 1. Every State-bound output above is already durable.
        # 2. The generation manifest names that exact artifact set.
        # 3. The user State pointer advances only after the manifest exists.
        #
        # For same-State publication the pointer is unchanged and the manifest is
        # the atomic generation swap. For changed-State publication a crash before
        # step 3 still restores the prior State; a crash after step 3 can resolve
        # the complete new generation by its already-durable manifest.
        store.put_artifact(
            _published_generation_record(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=selected_team_id,
                publication_generation_id=generation_id,
                forecast_record=forecast_record,
                simulation_record=simulation_record,
                value_record=value_record,
                computed_at=now,
            )
        )
        store.put_user_runtime_context(
            UserRuntimeContextRecord(
                user_id=user_id,
                provider=provider,
                league_external_id=external_id,
                league_id=league_state.league.league_id,
                season=league_state.league.season,
                selected_team_id=selected_team_id,
                state_hash=league_state.state_id,
                updated_at=now,
            )
        )

        # Last-good identity follows the publication commit. It is presentation
        # fallback metadata, not authority for choosing a model artifact generation.
        payload = {
            "league_state": state_payload,
            "selected_team_id": selected_team_id,
        }
        store.put_artifact(
            ReusableArtifactRecord(
                key=ArtifactKey(
                    artifact_kind=LAST_GOOD_ARTIFACT_KIND,
                    scope_kind=LAST_GOOD_SCOPE_KIND,
                    scope_id=user_id,
                    input_fingerprint=league_state.state_id,
                    model_version=LAST_GOOD_MODEL_VERSION,
                ),
                payload=payload,
                computed_at=now,
            )
        )
        persist_league_last_good_identity(
            store,
            user_id=user_id,
            league_state=league_state,
            selected_team_id=selected_team_id,
        )


def restore_state_bound_raw_forecast_evidence(
    store: PersistenceStore,
    *,
    league_state: LeagueState,
) -> "LiveForecastEvidence | None":
    """Load persisted Forecast evidence for raw-ensemble replay without downstream gates.

    The artifact is still exact-State and current-contract. This helper intentionally
    does not require the prior State's scoring supplement to remain current, because
    replay rebuilds State-specific scoring/supplement layers for the target State.
    """

    forecast_record = store.get_latest_reusable_artifact(
        artifact_kind=FORECAST_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state.state_id,
        model_version=FORECAST_MODEL_VERSION,
    )
    if forecast_record is None:
        return None
    try:
        candidate = decode_forecast_evidence(dict(forecast_record.payload))
    except (TypeError, ValueError):
        return None
    if not candidate.raw_forecasts:
        return None
    minimum_sources = getattr(
        getattr(candidate, "runtime_result", None),
        "coverage",
        None,
    )
    minimum_sources = getattr(minimum_sources, "minimum_independent_sources", 2)
    if len(set(candidate.successful_source_ids)) < int(minimum_sources):
        return None
    return candidate


def restore_state_bound_forecast(
    store: PersistenceStore,
    *,
    league_state: LeagueState,
) -> "LiveForecastEvidence | None":
    """Load only current-contract Forecast evidence bound to one exact State."""

    forecast = None
    forecast_record = store.get_latest_reusable_artifact(
        artifact_kind=FORECAST_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state.state_id,
        model_version=FORECAST_MODEL_VERSION,
    )
    if forecast_record is not None:
        try:
            candidate_forecast = decode_forecast_evidence(
                dict(forecast_record.payload)
            )
            requires_first_party_fumbles_lost = league_consumes_fumbles_lost(
                league_state.league.rules
            )
            has_first_party_fumbles_lost = bool(
                getattr(
                    candidate_forecast.runtime_result,
                    "fumbles_lost_supplement_authority_fingerprint",
                    None,
                )
            )
            current_supplement_contract = (
                getattr(
                    candidate_forecast.runtime_result,
                    "fumbles_lost_supplement_model_version",
                    None,
                )
                == FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
            )
            supplement_matches_state = (
                getattr(
                    candidate_forecast.runtime_result,
                    "fumbles_lost_supplement_league_state_id",
                    None,
                )
                == league_state.state_id
            )
            if (
                not requires_first_party_fumbles_lost
                or (
                    has_first_party_fumbles_lost
                    and current_supplement_contract
                    and supplement_matches_state
                )
            ):
                forecast = candidate_forecast
        except (TypeError, ValueError):
            forecast = None
    return forecast


def restore_published_state_bound_intelligence(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
) -> tuple[
    "LiveForecastEvidence | None",
    "LiveSimulationAnalyticsResult | None",
    "CurrentMarketValueRuntimeResult | None",
    str | None,
]:
    """Restore only the exact artifact set named by the last published manifest.

    Newer same-State working artifacts may coexist in the reusable cache, but they
    have no restart authority until a manifest-last publication commit names them.
    """

    manifest = _published_generation_manifest(
        store,
        user_id=user_id,
        league_state=league_state,
    )
    if manifest is None:
        # Upgrade compatibility only. Once a generation manifest exists, restore
        # never consults newest-by-State artifacts for published authority.
        forecast, simulation, values = restore_state_bound_intelligence(
            store,
            league_state=league_state,
        )
        return forecast, simulation, values, None

    payload = manifest.payload
    forecast_fp = str(payload.get("forecast_input_fingerprint") or "").strip()
    value_fp = str(payload.get("value_input_fingerprint") or "").strip()
    simulation_fp = str(payload.get("simulation_input_fingerprint") or "").strip()
    if not forecast_fp or not value_fp:
        return None, None, None, None

    forecast = None
    forecast_record = store.get_reusable_artifact(
        ArtifactKey(
            artifact_kind=FORECAST_ARTIFACT_KIND,
            scope_kind=LEAGUE_SCOPE_KIND,
            scope_id=league_state.state_id,
            input_fingerprint=forecast_fp,
            model_version=FORECAST_MODEL_VERSION,
        )
    )
    if forecast_record is not None:
        try:
            candidate = decode_forecast_evidence(dict(forecast_record.payload))
            requires_supplement = league_consumes_fumbles_lost(
                league_state.league.rules
            )
            supplement_ok = bool(
                getattr(
                    candidate.runtime_result,
                    "fumbles_lost_supplement_authority_fingerprint",
                    None,
                )
                and getattr(
                    candidate.runtime_result,
                    "fumbles_lost_supplement_model_version",
                    None,
                )
                == FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
                and getattr(
                    candidate.runtime_result,
                    "fumbles_lost_supplement_league_state_id",
                    None,
                )
                == league_state.state_id
            )
            if not requires_supplement or supplement_ok:
                forecast = candidate
        except (TypeError, ValueError):
            forecast = None
    simulation = None
    if forecast is not None and simulation_fp:
        simulation_record = store.get_reusable_artifact(
            ArtifactKey(
                artifact_kind=SIMULATION_ARTIFACT_KIND,
                scope_kind=LEAGUE_SCOPE_KIND,
                scope_id=league_state.state_id,
                input_fingerprint=simulation_fp,
                model_version=SIMULATION_MODEL_VERSION,
            )
        )
        if simulation_record is not None:
            try:
                candidate_simulation = decode_simulation(
                    dict(simulation_record.payload)
                )
                if (
                    candidate_simulation.league_view.context.league_state_id
                    == league_state.state_id
                    and all(
                        view.view_model_version == CURRENT_TEAM_ANALYTICS_VIEW_VERSION
                        for view in candidate_simulation.team_views
                    )
                ):
                    simulation = candidate_simulation
            except (TypeError, ValueError):
                simulation = None

    values = None
    value_record = store.get_reusable_artifact(
        ArtifactKey(
            artifact_kind=VALUE_ARTIFACT_KIND,
            scope_kind=LEAGUE_SCOPE_KIND,
            scope_id=league_state.state_id,
            input_fingerprint=value_fp,
            model_version=VALUE_MODEL_VERSION,
        )
    )
    if value_record is not None:
        try:
            candidate_value = decode_value_result(dict(value_record.payload))
            if candidate_value.league_state_id == league_state.state_id:
                values = candidate_value
        except (TypeError, ValueError):
            values = None

    generation_id = str(payload.get("publication_generation_id") or "").strip()
    return forecast, simulation, values, generation_id or None


def restore_state_bound_intelligence(
    store: PersistenceStore,
    *,
    league_state: LeagueState,
) -> tuple[
    "LiveForecastEvidence | None",
    "LiveSimulationAnalyticsResult | None",
    "CurrentMarketValueRuntimeResult | None",
]:
    """Load only artifacts proven compatible with this exact canonical State."""

    forecast = restore_state_bound_forecast(
        store,
        league_state=league_state,
    )
    simulation = None
    values = None
    if forecast is not None:
        # Simulation is downstream of the exact persisted Forecast artifact,
        # not merely of the canonical State. Query the exact dependency key so a
        # newer mismatched Simulation row cannot hide an older compatible one.
        current_forecast_record = forecast_artifact(
            league_state_id=league_state.state_id,
            evidence=forecast,
        )
        expected_simulation_input_fingerprint = canonical_fingerprint(
            league_state.state_id,
            current_forecast_record.key.input_fingerprint,
        )
        simulation_record = store.get_reusable_artifact(
            ArtifactKey(
                artifact_kind=SIMULATION_ARTIFACT_KIND,
                scope_kind=LEAGUE_SCOPE_KIND,
                scope_id=league_state.state_id,
                input_fingerprint=expected_simulation_input_fingerprint,
                model_version=SIMULATION_MODEL_VERSION,
            )
        )
        if simulation_record is not None:
            try:
                candidate = decode_simulation(dict(simulation_record.payload))
                has_current_team_views = all(
                    view.view_model_version == CURRENT_TEAM_ANALYTICS_VIEW_VERSION
                    for view in candidate.team_views
                )
                if (
                    candidate.league_view.context.league_state_id
                    == league_state.state_id
                    and has_current_team_views
                ):
                    simulation = candidate
            except (TypeError, ValueError):
                simulation = None

    value_record = store.get_latest_reusable_artifact(
        artifact_kind=VALUE_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state.state_id,
        model_version=VALUE_MODEL_VERSION,
    )
    if value_record is not None:
        try:
            candidate = decode_value_result(dict(value_record.payload))
            if candidate.league_state_id == league_state.state_id:
                values = candidate
        except (TypeError, ValueError):
            values = None
    return forecast, simulation, values


def migrate_legacy_last_good_identity(
    store: PersistenceStore,
    *,
    user_id: str,
    league_id: str,
) -> bool:
    """Copy a validated legacy user-scoped last-good record into league scope.

    This is a compatibility migration only. It does not materialize Forecast,
    Simulation, or Value into memory and therefore preserves the lightweight
    served-identity runtime architecture.
    """

    existing = store.get_latest_reusable_artifact(
        artifact_kind=LEAGUE_LAST_GOOD_ARTIFACT_KIND,
        scope_kind=LEAGUE_LAST_GOOD_SCOPE_KIND,
        scope_id=_league_last_good_scope_id(user_id, league_id),
        model_version=LEAGUE_LAST_GOOD_MODEL_VERSION,
    )
    if existing is not None:
        return False

    legacy = store.get_latest_reusable_artifact(
        artifact_kind=LAST_GOOD_ARTIFACT_KIND,
        scope_kind=LAST_GOOD_SCOPE_KIND,
        scope_id=user_id,
        model_version=LAST_GOOD_MODEL_VERSION,
    )
    if legacy is None:
        return False
    try:
        state = LeagueState.model_validate(legacy.payload["league_state"])
    except (KeyError, TypeError, ValueError):
        return False
    if state.league.league_id != league_id:
        return False

    selected = legacy.payload.get("selected_team_id")
    if selected not in {team.team_id for team in state.teams}:
        selected = None
    persist_league_last_good_identity(
        store,
        user_id=user_id,
        league_state=state,
        selected_team_id=selected,
    )
    return True


def restore_last_good_state_identity(
    store: PersistenceStore,
    *,
    user_id: str,
    league_id: str,
) -> tuple[LeagueState, str | None] | None:
    """Restore only durable State identity; does not confer derived authority."""

    candidates = (
        store.get_latest_reusable_artifact(
            artifact_kind=LEAGUE_LAST_GOOD_ARTIFACT_KIND,
            scope_kind=LEAGUE_LAST_GOOD_SCOPE_KIND,
            scope_id=_league_last_good_scope_id(user_id, league_id),
            model_version=LEAGUE_LAST_GOOD_MODEL_VERSION,
        ),
        store.get_latest_reusable_artifact(
            artifact_kind=LAST_GOOD_ARTIFACT_KIND,
            scope_kind=LAST_GOOD_SCOPE_KIND,
            scope_id=user_id,
            model_version=LAST_GOOD_MODEL_VERSION,
        ),
    )
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            state = LeagueState.model_validate(candidate.payload["league_state"])
        except (KeyError, TypeError, ValueError):
            continue
        if state.league.league_id != league_id:
            continue
        selected = candidate.payload.get("selected_team_id")
        if selected not in {team.team_id for team in state.teams}:
            selected = None
        return state, selected
    return None


def restore_last_good_intelligence(
    store: PersistenceStore,
    *,
    user_id: str,
    league_id: str,
) -> DurableRuntimeSnapshot | None:
    """Restore presentation-only last-good intelligence for one selected league."""

    candidate = store.get_latest_reusable_artifact(
        artifact_kind=LEAGUE_LAST_GOOD_ARTIFACT_KIND,
        scope_kind=LEAGUE_LAST_GOOD_SCOPE_KIND,
        scope_id=_league_last_good_scope_id(user_id, league_id),
        model_version=LEAGUE_LAST_GOOD_MODEL_VERSION,
    )
    if candidate is None:
        # Backward-compatible migration path for deployments that only have the
        # historical user-scoped last-good record.
        legacy = store.get_latest_reusable_artifact(
            artifact_kind=LAST_GOOD_ARTIFACT_KIND,
            scope_kind=LAST_GOOD_SCOPE_KIND,
            scope_id=user_id,
            model_version=LAST_GOOD_MODEL_VERSION,
        )
        candidate = legacy

    if candidate is None:
        return None
    try:
        league_state = LeagueState.model_validate(candidate.payload["league_state"])
    except (KeyError, TypeError, ValueError):
        return None
    if league_state.league.league_id != league_id:
        return None

    forecast, simulation, values, publication_generation_id = (
        restore_published_state_bound_intelligence(
            store,
            user_id=user_id,
            league_state=league_state,
        )
    )
    if not _terminal_bundle(forecast, simulation, values):
        return None
    selected = candidate.payload.get("selected_team_id")
    if selected not in {team.team_id for team in league_state.teams}:
        selected = None
    return DurableRuntimeSnapshot(
        league_state=league_state,
        selected_team_id=selected,
        publication_generation_id=publication_generation_id,
        forecast_evidence=forecast,
        simulation_analytics=simulation,
        value_evidence=values,
        restored_from_last_good=True,
    )


def restore_runtime_snapshot(store: PersistenceStore, *, user_id: str) -> DurableRuntimeSnapshot | None:
    """Restore canonical target State plus an optional same-league served last-good."""

    context = store.get_user_runtime_context(user_id=user_id)
    if context is None:
        return None

    # The user-scoped context owns the current canonical target State identity.
    # Never replace it with older last-good intelligence merely because a refresh
    # was interrupted. Last-good is restored separately below for presentation.
    league_record = store.get_league_snapshot(
        provider=context.provider,
        league_id=context.league_id,
        season=context.season,
    )
    league_state = None
    selected = context.selected_team_id
    restored_from_last_good = False
    if (
        league_record is not None
        and league_record.state_hash == context.state_hash
    ):
        candidate_state = LeagueState.model_validate(league_record.payload)
        if candidate_state.state_id == context.state_hash:
            league_state = candidate_state

    if league_state is None:
        # Session-isolation fallback: a shared latest league row may have been
        # advanced by another isolated user/session. The exact user last-good may
        # still be the only durable copy of this user's canonical context State.
        fallback = restore_last_good_state_identity(
            store,
            user_id=user_id,
            league_id=context.league_id,
        )
        if fallback is None or fallback[0].state_id != context.state_hash:
            return None
        league_state = fallback[0]
        # The user runtime row is the current managed-team authority. Last-good is
        # only a State payload fallback when the shared league snapshot has advanced;
        # its older team identity must not overwrite a newer lightweight team pointer.
        restored_from_last_good = True

    forecast, simulation, values, publication_generation_id = (
        restore_published_state_bound_intelligence(
            store,
            user_id=user_id,
            league_state=league_state,
        )
    )

    if selected not in {team.team_id for team in league_state.teams}:
        selected = None

    # Forecast/Simulation/Value are league-wide exact-State authority, but the
    # publication generation is team-specific. A lightweight managed-team pointer
    # may legitimately be newer than the last presentation manifest.
    manifest_generation_id, manifest_team_id = restore_published_generation_identity(
        store,
        user_id=user_id,
        league_state=league_state,
    )
    if (
        publication_generation_id is not None
        and (
            manifest_generation_id != publication_generation_id
            or manifest_team_id != selected
        )
    ):
        publication_generation_id = None

    served_state = None
    served_publication_generation_id = None
    if not _terminal_bundle(forecast, simulation, values):
        candidate = restore_last_good_state_identity(
            store,
            user_id=user_id,
            league_id=league_state.league.league_id,
        )
        if candidate is not None and candidate[0].state_id != league_state.state_id:
            served_state = candidate[0]
            candidate_generation_id, candidate_team_id = (
                restore_published_generation_identity(
                    store,
                    user_id=user_id,
                    league_state=served_state,
                )
            )
            if candidate_team_id == selected:
                served_publication_generation_id = candidate_generation_id
    return DurableRuntimeSnapshot(
        league_state=league_state,
        selected_team_id=selected,
        publication_generation_id=publication_generation_id,
        forecast_evidence=forecast,
        simulation_analytics=simulation,
        value_evidence=values,
        served_league_id=(
            served_state.league.league_id if served_state is not None else None
        ),
        served_league_state_id=(
            served_state.state_id if served_state is not None else None
        ),
        served_as_of=(served_state.as_of if served_state is not None else None),
        served_team_ids=(
            tuple(sorted(team.team_id for team in served_state.teams))
            if served_state is not None
            else ()
        ),
        served_publication_generation_id=served_publication_generation_id,
        restored_from_last_good=restored_from_last_good,
    )


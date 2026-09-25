from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fsffl.state.models import LeagueState

from .contracts import (
    ArtifactKey,
    LeagueSnapshotRecord,
    PersistenceStore,
    ReusableArtifactRecord,
    TeamSnapshotRecord,
    UserRuntimeContextRecord,
    utc_now,
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
JOB_LIFECYCLE_ARTIFACT_KIND = "intelligence_job_lifecycle"
JOB_LIFECYCLE_MODEL_VERSION = "intelligence-job-lifecycle-v1"


@dataclass(frozen=True)
class DurableRuntimeSnapshot:
    league_state: LeagueState
    selected_team_id: str | None
    forecast_evidence: LiveForecastEvidence | None = None
    simulation_analytics: LiveSimulationAnalyticsResult | None = None
    value_evidence: CurrentMarketValueRuntimeResult | None = None
    restored_from_last_good: bool = False


def _provider_external_id(league_state: LeagueState) -> tuple[str, str]:
    sleeper = next((ref for ref in league_state.league.provider_refs if ref.provider == "sleeper"), None)
    if sleeper is not None:
        return sleeper.provider, sleeper.external_id
    if league_state.league.provider_refs:
        ref = league_state.league.provider_refs[0]
        return ref.provider, ref.external_id
    return "canonical", league_state.league.league_id


def persist_runtime_snapshot(
    store: PersistenceStore,
    *,
    user_id: str,
    league_state: LeagueState,
    selected_team_id: str | None,
    forecast_evidence: LiveForecastEvidence | None = None,
    simulation_analytics: LiveSimulationAnalyticsResult | None = None,
    value_evidence: CurrentMarketValueRuntimeResult | None = None,
) -> None:
    """Checkpoint authoritative runtime outputs without changing their ownership."""

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
    if forecast_evidence is not None:
        forecast_record = forecast_artifact(
            league_state_id=league_state.state_id,
            evidence=forecast_evidence,
        )
        store.put_artifact(forecast_record)
    if simulation_analytics is not None and forecast_record is not None:
        store.put_artifact(
            simulation_artifact(
                league_state_id=league_state.state_id,
                forecast_fingerprint=forecast_record.key.input_fingerprint,
                result=simulation_analytics,
            )
        )
        # Automatic annual League Atlas baseline capture is an orchestration
        # side-effect of persisting an already-authoritative 50,000-run runtime.
        # The helper fails closed outside a proven pre-opener coordinate.
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
        store.put_artifact(
            value_artifact(
                league_state_id=league_state.state_id,
                result=value_evidence,
            )
        )
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

    # Complete bundles get an independent durable identity. Partial refresh
    # checkpoints cannot displace this restart authority.
    if forecast_evidence is not None and simulation_analytics is not None and value_evidence is not None:
        store.put_artifact(
            ReusableArtifactRecord(
                key=ArtifactKey(
                    artifact_kind=LAST_GOOD_ARTIFACT_KIND,
                    scope_kind=LAST_GOOD_SCOPE_KIND,
                    scope_id=user_id,
                    input_fingerprint=league_state.state_id,
                    model_version=LAST_GOOD_MODEL_VERSION,
                ),
                payload={"league_state": state_payload, "selected_team_id": selected_team_id},
                computed_at=now,
            )
        )

def restore_runtime_snapshot(store: PersistenceStore, *, user_id: str) -> DurableRuntimeSnapshot | None:
    """Restore only an internally consistent, current-model runtime snapshot."""

    context = store.get_user_runtime_context(user_id=user_id)
    if context is None:
        return None
    # A queued/running refresh, a restart-interrupted refresh, or a failed refresh
    # must not make a newer state-only checkpoint displace an independently promoted
    # complete bundle. Cross-league switches remain authoritative: a last-good bundle
    # is eligible only when it belongs to the same currently selected league.
    lifecycle = store.get_latest_reusable_artifact(
        artifact_kind=JOB_LIFECYCLE_ARTIFACT_KIND,
        scope_kind=LAST_GOOD_SCOPE_KIND,
        scope_id=user_id,
        model_version=JOB_LIFECYCLE_MODEL_VERSION,
    )
    refresh_needs_last_good = (
        lifecycle is not None
        and lifecycle.payload.get("status") in {"queued", "running", "failed", "interrupted"}
    )
    last_good = None
    last_good_state = None
    if refresh_needs_last_good:
        candidate = store.get_latest_reusable_artifact(
            artifact_kind=LAST_GOOD_ARTIFACT_KIND,
            scope_kind=LAST_GOOD_SCOPE_KIND,
            scope_id=user_id,
            model_version=LAST_GOOD_MODEL_VERSION,
        )
        if candidate is not None:
            try:
                candidate_state = LeagueState.model_validate(candidate.payload["league_state"])
            except (KeyError, TypeError, ValueError):
                candidate_state = None
            if (
                candidate_state is not None
                and candidate_state.league.league_id == context.league_id
            ):
                last_good = candidate
                last_good_state = candidate_state

    if last_good is not None and last_good_state is not None:
        league_state = last_good_state
        selected = (
            context.selected_team_id
            if context.selected_team_id in {team.team_id for team in league_state.teams}
            else last_good.payload.get("selected_team_id")
        )
    else:
        league_record = store.get_league_snapshot(
            provider=context.provider,
            league_id=context.league_id,
            season=context.season,
        )
        if league_record is None or league_record.state_hash != context.state_hash:
            return None
        league_state = LeagueState.model_validate(league_record.payload)
        if league_state.state_id != context.state_hash:
            return None
        selected = context.selected_team_id

    forecast = None
    simulation = None
    values = None
    forecast_record = store.get_latest_reusable_artifact(
        artifact_kind=FORECAST_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state.state_id,
        model_version=FORECAST_MODEL_VERSION,
    )
    if forecast_record is not None:
        try:
            forecast = decode_forecast_evidence(dict(forecast_record.payload))
        except (TypeError, ValueError):
            forecast = None

    if forecast is not None:
        simulation_record = store.get_latest_reusable_artifact(
            artifact_kind=SIMULATION_ARTIFACT_KIND,
            scope_kind=LEAGUE_SCOPE_KIND,
            scope_id=league_state.state_id,
            model_version=SIMULATION_MODEL_VERSION,
        )
        if simulation_record is not None:
            try:
                candidate = decode_simulation(dict(simulation_record.payload))
                has_current_team_views = all(
                    view.view_model_version == CURRENT_TEAM_ANALYTICS_VIEW_VERSION
                    for view in candidate.team_views
                )
                if (
                    candidate.league_view.context.league_state_id == league_state.state_id
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

    if selected not in {team.team_id for team in league_state.teams}:
        selected = None
    return DurableRuntimeSnapshot(
        league_state=league_state,
        selected_team_id=selected,
        forecast_evidence=forecast,
        simulation_analytics=simulation,
        value_evidence=values,
        restored_from_last_good=(last_good is not None and last_good_state is not None),
    )

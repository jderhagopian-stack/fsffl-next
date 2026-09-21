from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.forecast.preseason_baseline import (
    PRESEASON_BASELINE_MODEL_VERSION,
    build_runtime_from_preseason_baseline,
    preseason_scope_id,
)
from fsffl.persistence.postgres import PostgresPersistenceStore
from fsffl.persistence.runtime_cache import (
    FORECAST_ARTIFACT_KIND,
    FORECAST_MODEL_VERSION,
    LEAGUE_SCOPE_KIND,
    LEAGUE_SEASON_SCOPE_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    decode_forecast_evidence,
    decode_preseason_forecast_baseline,
)
from fsffl.persistence.session import restore_runtime_snapshot
from fsffl.product.team_page import build_forecast_team_view


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/live_forecast_value_corrective_20260921"
TARGET_LEAGUE_EXTERNAL_ID = os.getenv(
    "FSFFL_DIAGNOSTIC_LEAGUE_ID",
    "1312071960615731200",
).strip()
REPRESENTATIVE_NAMES = (
    "Josh Allen",
    "Dak Prescott",
    "Jahmyr Gibbs",
    "CeeDee Lamb",
    "Puka Nacua",
    "Kyle Pitts",
)
QUARANTINE_DEPLOYED_AT = datetime(2026, 9, 21, 14, 6, 54, tzinfo=UTC)


def _latest_user(database_url: str) -> str:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            select user_id
              from fsffl.user_runtime_context
             where league_external_id = %s
                or league_id = %s
             order by updated_at desc
             limit 1
            """,
            (TARGET_LEAGUE_EXTERNAL_ID, f"sleeper:{TARGET_LEAGUE_EXTERNAL_ID}"),
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("No persisted runtime context found for target league")
    return str(row[0])


def _artifact_row(
    database_url: str,
    *,
    artifact_kind: str,
    scope_kind: str,
    scope_id: str,
    model_version: str,
) -> dict[str, object] | None:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            select artifact_kind, scope_kind, scope_id, input_fingerprint,
                   model_version, payload, computed_at, invalidated_at,
                   invalidation_reason
              from fsffl.derived_artifact
             where artifact_kind = %s
               and scope_kind = %s
               and scope_id = %s
               and model_version = %s
             order by computed_at desc
             limit 1
            """,
            (artifact_kind, scope_kind, scope_id, model_version),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [desc.name for desc in cursor.description]
    return dict(zip(cols, row))


def _season_observation(evidence, player_id: str):
    candidates = [
        item
        for item in evidence.league_scored_forecasts
        if item.player_id == player_id
        and item.metric == ForecastMetric.FANTASY_POINTS
        and item.horizon == ForecastHorizon.SEASON
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (item.as_of, item.model_version, item.source),
        reverse=True,
    )[0]


def _baseline_observation(runtime, player_id: str):
    candidates = [
        item
        for item in runtime.fantasy_point_forecasts
        if item.player_id == player_id
        and item.metric == ForecastMetric.FANTASY_POINTS
        and item.horizon == ForecastHorizon.SEASON
    ]
    return candidates[0] if candidates else None


def _player_owner(state, player_id: str) -> str | None:
    for team_state in state.team_states:
        if any(entry.player_id == player_id for entry in team_state.roster):
            return team_state.team_id
    return None


def _top_level_projection(state, evidence, player_id: str) -> float | None:
    owner = _player_owner(state, player_id)
    if owner is None:
        return None
    forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
    view = build_forecast_team_view(
        state,
        team_id=owner,
        forecasts=forecasts,
        forecast_model_version=evidence.model_version,
        generated_at=state.as_of,
    )
    row = next((item for item in view.players if item.player_id == player_id), None)
    return row.season_fantasy_points_projection if row is not None else None


def _find_key_paths(value, *, key_fragment: str, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key_fragment.lower() in str(key).lower():
                found.append(path)
            found.extend(_find_key_paths(child, key_fragment=key_fragment, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(
                _find_key_paths(
                    child,
                    key_fragment=key_fragment,
                    prefix=f"{prefix}[{index}]",
                )
            )
    return found


def main() -> None:
    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("FSFFL_DATABASE_URL is required")

    OUT.mkdir(parents=True, exist_ok=True)
    user_id = _latest_user(database_url)
    store = PostgresPersistenceStore(database_url)
    snapshot = restore_runtime_snapshot(store, user_id=user_id)
    if snapshot is None:
        raise RuntimeError("Persisted runtime snapshot could not be restored")
    state = snapshot.league_state

    current_row = _artifact_row(
        database_url,
        artifact_kind=FORECAST_ARTIFACT_KIND,
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=state.state_id,
        model_version=FORECAST_MODEL_VERSION,
    )
    if current_row is None:
        raise RuntimeError("No persisted current_forecast_evidence artifact found")
    current = decode_forecast_evidence(dict(current_row["payload"]))

    baseline_scope = preseason_scope_id(state)
    baseline_row = _artifact_row(
        database_url,
        artifact_kind=PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
        scope_kind=LEAGUE_SEASON_SCOPE_KIND,
        scope_id=baseline_scope,
        model_version=PRESEASON_BASELINE_MODEL_VERSION,
    )
    if baseline_row is None:
        raise RuntimeError("No preserved preseason baseline artifact found")
    baseline = decode_preseason_forecast_baseline(dict(baseline_row["payload"]))
    baseline_runtime = build_runtime_from_preseason_baseline(state, baseline)

    player_by_name = {
        player.full_name: player
        for player in state.players
        if player.full_name in REPRESENTATIVE_NAMES
    }
    trace: list[dict[str, object]] = []
    for name in REPRESENTATIVE_NAMES:
        player = player_by_name.get(name)
        if player is None:
            trace.append({"player": name, "present": False})
            continue
        obs = _season_observation(current, player.player_id)
        fallback = _baseline_observation(baseline_runtime, player.player_id)
        top_level = _top_level_projection(state, current, player.player_id)
        governed = (
            float(obs.distribution.mean)
            if obs is not None
            else None
        )
        # This reproduces current product_shell.js presentation precedence exactly:
        # top-level season_fantasy_points_projection first, then governed season obs.
        ui_displayed = top_level if top_level is not None else governed
        trace.append(
            {
                "player": name,
                "present": True,
                "player_id": player.player_id,
                "position": player.position.value,
                "owner_team_id": _player_owner(state, player.player_id),
                "ui_displayed_number_current_contract": ui_displayed,
                "top_level_season_fantasy_points_projection": top_level,
                "governed_current_season_observation": governed,
                "governed_observation_source": obs.source if obs is not None else None,
                "governed_observation_model_version": (
                    obs.model_version if obs is not None else None
                ),
                "governed_observation_as_of": (
                    obs.as_of.isoformat() if obs is not None else None
                ),
                "preseason_fallback_season_projection": (
                    float(fallback.distribution.mean)
                    if fallback is not None
                    else None
                ),
                "delta_current_vs_fallback": (
                    ui_displayed - float(fallback.distribution.mean)
                    if ui_displayed is not None and fallback is not None
                    else None
                ),
            }
        )

    payload = dict(current_row["payload"])
    fingerprint_paths = _find_key_paths(payload, key_fragment="fingerprint")
    sha_paths = _find_key_paths(payload, key_fragment="sha256")
    provider_content_provenance_present = bool(fingerprint_paths or sha_paths)
    computed_at = current_row["computed_at"]
    pre_quarantine_deploy = bool(
        computed_at is not None and computed_at.astimezone(UTC) < QUARANTINE_DEPLOYED_AT
    )

    report = {
        "schema_version": "fsffl-live-forecast-corrective-trace-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "league_id": state.league.league_id,
        "league_state_id": state.state_id,
        "current_artifact": {
            "artifact_kind": current_row["artifact_kind"],
            "model_version": current_row["model_version"],
            "artifact_input_fingerprint": current_row["input_fingerprint"],
            "computed_at": current_row["computed_at"].isoformat(),
            "invalidated_at": (
                current_row["invalidated_at"].isoformat()
                if current_row["invalidated_at"] is not None
                else None
            ),
            "invalidation_reason": current_row["invalidation_reason"],
            "evidence_basis": current.evidence_basis,
            "runtime_model_version": current.runtime_result.model_version,
            "evaluation_as_of": current.runtime_result.evaluation_as_of.isoformat(),
            "successful_source_ids": list(current.successful_source_ids),
            "failed_sources": list(current.failed_sources),
            "coverage_independent_source_ids": list(
                current.runtime_result.coverage.independent_source_ids
            ),
            "provider_content_fingerprint_paths": fingerprint_paths,
            "provider_content_sha256_paths": sha_paths,
            "provider_content_provenance_present": provider_content_provenance_present,
            "computed_before_content_quarantine_deployment": pre_quarantine_deploy,
        },
        "preseason_fallback": {
            "scope_id": baseline_scope,
            "artifact_input_fingerprint": baseline_row["input_fingerprint"],
            "computed_at": baseline_row["computed_at"].isoformat(),
            "model_version": baseline.model_version,
            "source_runtime_model_version": baseline.source_runtime_model_version,
            "evaluation_as_of": baseline.evaluation_as_of.isoformat(),
            "successful_source_ids": list(baseline.successful_source_ids),
            "source_artifact_id": baseline.source_artifact_id,
        },
        "presentation_contract": {
            "current_precedence": (
                "top_level_season_fantasy_points_projection_then_governed_season_observation"
            ),
            "top_level_is_rederived_from_same_restored_forecast_evidence_in_trace": True,
            "stale_top_level_can_shadow_a_newer_observation_if_the_two_diverge": True,
        },
        "artifact_health_decision": {
            "known_bad_razzball_incident_fingerprint": (
                "0545b6c585712165997dca191169596d000aa30435f4e2ccde6d3f55c6877e3d"
            ),
            "can_prove_current_provider_payload_health": provider_content_provenance_present,
            "contains_razzball_source_id": "razzball" in set(current.successful_source_ids),
            "decision": (
                "FAIL_CLOSED_UNKNOWN_PROVENANCE"
                if not provider_content_provenance_present
                else "PROVENANCE_PRESENT_REQUIRES_CONTENT_CHECK"
            ),
            "reason": (
                "Persisted current_forecast_evidence predates the content quarantine "
                "and retains source ids but not provider content fingerprints/health "
                "witnesses, so reusable/non-invalidated is insufficient to prove it "
                "healthy under the current contract."
                if not provider_content_provenance_present
                else "Provider content provenance exists and must be checked against the incident gate."
            ),
        },
        "representative_players": trace,
    }

    (OUT / "LIVE_FORECAST_LINEAGE_TRACE.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md = [
        "# Live Forecast lineage trace",
        "",
        f"- Current artifact computed: {report['current_artifact']['computed_at']}",
        f"- Evidence basis: {current.evidence_basis}",
        f"- Successful sources: {', '.join(current.successful_source_ids)}",
        (
            "- Provider content fingerprints retained in current artifact: "
            f"{provider_content_provenance_present}"
        ),
        (
            "- Artifact health decision: "
            f"**{report['artifact_health_decision']['decision']}**"
        ),
        "",
        "| Player | UI/current | Top-level | Governed obs | Sep-10 fallback | Delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in trace:
        if not row.get("present"):
            md.append(f"| {row['player']} | unavailable | unavailable | unavailable | unavailable | unavailable |")
            continue
        def fmt(value):
            return "—" if value is None else f"{float(value):.4f}"
        md.append(
            f"| {row['player']} | {fmt(row['ui_displayed_number_current_contract'])} | "
            f"{fmt(row['top_level_season_fantasy_points_projection'])} | "
            f"{fmt(row['governed_current_season_observation'])} | "
            f"{fmt(row['preseason_fallback_season_projection'])} | "
            f"{fmt(row['delta_current_vs_fallback'])} |"
        )
    (OUT / "LIVE_FORECAST_LINEAGE_TRACE.md").write_text(
        "\n".join(md) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

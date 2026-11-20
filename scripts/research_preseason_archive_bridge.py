"""Extract directly evidenced pre-kickoff membership and Forecast from archived Analytics.

Research-only, does not manufacture a complete canonical historical State.
The post-kickoff State can *corroborate* only; never replace roster slots.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any


class ArchiveBridgeError(ValueError):
    pass


def _clock(value: str, name: str, cutoff: datetime) -> None:
    if not isinstance(value, str):
        raise ArchiveBridgeError(f"{name} has no source clock")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ArchiveBridgeError(f"{name} invalid source clock") from exc
    if dt.tzinfo is None or dt.utcoffset() is None or dt.astimezone(timezone.utc) > cutoff:
        raise ArchiveBridgeError(f"{name} is not proven available before cutoff")


def extract_preseason_archive_evidence(
    row: dict[str, Any], *, cutoff: str, expected_league_id: str,
) -> dict[str, Any]:
    """Return a *partial* historical input package, not a publishable replay."""
    ts = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise ArchiveBridgeError("cutoff must carry timezone")
    if row.get("artifact_kind") != "live_simulation_analytics":
        raise ArchiveBridgeError("requires original simulation artifact")
    _clock(row.get("computed_at"), "artifact computed_at", ts)
    payload = row["payload"]
    views = payload["team_views"]
    if not isinstance(views, list) or not views:
        raise ArchiveBridgeError("original team views missing")
    players: dict[str, dict] = {}
    picks: dict[str, dict] = {}
    forecasts: list[dict] = []
    for team in views:
        tid = team["team_id"]
        if not tid.startswith(expected_league_id + ":team:"):
            raise ArchiveBridgeError("cross-league data is forbidden")
        _clock(team["context"]["as_of"], "team analytics as_of", ts)
        for player in team.get("players", []):
            pid = player.get("player_id")
            slot = player.get("roster_slot")
            if not pid or not slot or pid in players:
                raise ArchiveBridgeError(f"player ownership/slot conflict: {pid}")
            players[pid] = {
                "player_id": pid, "team_id": tid, "roster_slot": slot,
                "full_name": player.get("full_name"),
                "position": player.get("position"), "age_years": player.get("age_years"),
            }
            archived_forecasts = [f for f in player.get("forecasts", ())
                                  if f.get("horizon") == "season" and f.get("metric") == "fantasy_points"]
            if len(archived_forecasts) > 1:
                raise ArchiveBridgeError(f"duplicate preseason season-forecast identity: {pid}")
            for forecast in archived_forecasts:
                if forecast.get("player_id") != pid:
                    raise ArchiveBridgeError(f"forecast canonical ID mismatch: {pid}")
                _clock(forecast.get("as_of"), "Forecast as_of", ts)
                provenance = forecast.get("provenance") or {}
                for k in ("effective_at", "retrieved_at"):
                    _clock(provenance.get(k), "Forecast provenance " + k, ts)
                forecasts.append(forecast)
        for pick_entry in team.get("draft_picks", ()):
            pick = pick_entry.get("pick") or {}
            pid = pick.get("pick_id")
            if not pid or pid in picks:
                raise ArchiveBridgeError(f"pick ownership conflict: {pid}")
            picks[pid] = {"pick_id": pid, "owner_team_id": tid, "pick": pick}
    digest = row.get("input_fingerprint")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ArchiveBridgeError("original input fingerprint must be supplied")
    # The input fingerprint and artifact_id are provenance identifiers. Source
    # payload integrity must still be proven through trusted storage separately.
    return {
        "status": "partial_historical_evidence_extracted",
        "cutoff": ts.astimezone(timezone.utc).isoformat(),
        "archive_artifact_id": row.get("id"),
        "archive_input_fingerprint": digest,
        "archive_computed_at": row["computed_at"],
        "source_evidence_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "player_memberships": list(players.values()),
        "pick_ownership": list(picks.values()),
        "historical_forecasts": forecasts,
        "counts": {"rostered_players": len(players), "picks": len(picks),
                   "historical_season_forecasts": len(forecasts),
                   "rostered_without_season_forecast": len(players)-len(forecasts)},
        "not_yet_evidenced": [
            "full canonical point-in-time LeagueState",
            "source-qualified league rules, NFL-team identity and injury/status evidence",
            "full historical schedule / score-free matchup record",
            "source-qualified NFL bye and per-week availability",
            "modern Forecast training/feature inputs and 3-Year/Career Intrinsic",
            "modern simulation kernel result",
        ],
        "publication_ready": False,
    }


def extract_preseason_raw_forecast_evidence(
    row: dict[str, Any], *, cutoff: str,
) -> dict[str, Any]:
    """Recover pre-kickoff RAW metric ensemble; do not re-label as modern Forecast.

    Source: historical current_forecast_evidence artifact runtime_result,
    distinct from the final fantasy-point observations in Analytics. Downstream
    accepted Forecast authority must re-score it using PIT-eligible parameters.
    """
    ts = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ArchiveBridgeError("cutoff must carry timezone")
    if row.get("artifact_kind") != "current_forecast_evidence":
        raise ArchiveBridgeError("requires archived current Forecast evidence")
    _clock(row.get("computed_at"), "Forecast artifact computed_at", ts)
    payload = row["payload"]
    original = payload.get("runtime_result") or {}
    original_raw = original.get("raw_ensemble")
    if not isinstance(original_raw, list) or not original_raw:
        raise ArchiveBridgeError("original raw forecast ensemble missing")
    seen: set[tuple[str, str, str]] = set()
    players: set[str] = set()
    for entry in original_raw:
        _clock(entry.get("as_of"), "raw forecast as_of", ts)
        prov = entry.get("provenance") or {}
        _clock(prov.get("effective_at"), "raw forecast provenance effective_at", ts)
        _clock(prov.get("retrieved_at"), "raw forecast provenance retrieved_at", ts)
        key = (entry.get("player_id"), entry.get("metric"), entry.get("horizon"))
        if not all(key) or key in seen:
            raise ArchiveBridgeError("raw forecast metric/subject identity is missing or duplicated")
        if entry.get("horizon") != "season":
            raise ArchiveBridgeError("raw forecast must be original full-season vintage")
        seen.add(key)
        players.add(key[0])
    coverage = original.get("coverage") or {}
    independent = original.get("successful_source_ids")
    if not isinstance(independent, list) or len(set(independent)) < 2:
        raise ArchiveBridgeError("raw ensemble lacks two independent prior source identities")
    if coverage.get("minimum_independent_sources", 0) > len(set(independent)):
        raise ArchiveBridgeError("archived raw source coverage below accepted minimum")
    return {
        "status": "raw_preseason_forecast_evidence_recovered_not_rescored",
        "archive_artifact_id": row.get("id"),
        "archive_computed_at": row["computed_at"],
        "cutoff": ts.astimezone(timezone.utc).isoformat(),
        "original_forecast_version": original.get("model_version"),
        "original_successful_source_ids": independent,
        "raw_ensemble": original_raw,
        "coverage": coverage,
        "counts": {"raw_observations": len(original_raw), "unique_subjects": len(players)},
        "modern_forecast_status": "unavailable_requires_PIT_rescoring_and_fumbles_lost_eligibility",
        "publication_ready": False,
    }

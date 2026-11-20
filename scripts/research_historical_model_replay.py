"""Read-only, model-authority-preserving historical simulation recovery.

This is NOT a new Forecast/Simulation engine. It validates and presents an
already-computed, archived FSFFL NEXT artifact at an explicit cutoff.

Inputs are externally obtained JSON documents. No database access or writes.
Retrospective anchors corroborate ownership but cannot establish that their
later-captured football state was known at the historical cutoff.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReplayValidationError(ValueError):
    """An archived output is ineligible for publication at the cutoff."""


def _when(raw: str, name: str) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ReplayValidationError(f"{name}: missing timestamp")
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReplayValidationError(f"{name}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ReplayValidationError(f"{name}: timestamp must have timezone")
    return ts.astimezone(timezone.utc)


def _not_late(raw: str, cutoff: datetime, field: str) -> None:
    if _when(raw, field) > cutoff:
        raise ReplayValidationError(f"future-information leak: {field} is after cutoff")


def _prob(value: Any, name: str) -> float:
    try:
        out = float(value)
    except (ValueError, TypeError) as exc:
        raise ReplayValidationError(f"{name}: missing probability") from exc
    if not math.isfinite(out) or not 0 <= out <= 1:
        raise ReplayValidationError(f"{name}: invalid probability")
    return out


def _roster_and_pick_owners_from_artifact(views: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    players: dict[str, str] = {}
    picks: dict[str, str] = {}
    for team in views:
        tid = team["team_id"]
        for player in team.get("players", []):
            pid = player.get("player_id")
            if not pid or pid in players:
                raise ReplayValidationError(f"missing or duplicate player: {pid}")
            players[pid] = tid
        for entry in team.get("draft_picks", []):
            pid = entry.get("pick", {}).get("pick_id")
            if not pid or pid in picks:
                raise ReplayValidationError(f"missing or duplicate pick: {pid}")
            picks[pid] = tid
    return players, picks


def _anchor_comparison(anchor: dict[str, Any], owner_players: dict[str, str], owner_picks: dict[str, str]) -> dict:
    p: dict[str, str] = {}
    for team in anchor["team_states"]:
        tid = team["team_id"]
        for member in team["roster"]:
            pid = member["player_id"]
            if pid in p:
                raise ReplayValidationError(f"duplicate anchor roster player: {pid}")
            p[pid] = tid
    picks = {entry["pick_id"]: entry["owner_team_id"] for entry in anchor["pick_ownership"]}
    if len(picks) != len(anchor["pick_ownership"]):
        raise ReplayValidationError("duplicate anchor pick identity")
    bad_players = sorted(pid for pid in set(p) | set(owner_players) if p.get(pid) != owner_players.get(pid))
    bad_picks = sorted(pid for pid in set(picks) | set(owner_picks) if picks.get(pid) != owner_picks.get(pid))
    return {
        "status": "exact_membership_match" if not bad_players and not bad_picks else "membership_conflict",
        "players_compared": len(owner_players), "picks_compared": len(owner_picks),
        "player_discrepancies": bad_players, "pick_discrepancies": bad_picks,
        "authority": "retrospective_corrob_only_not_at_cutoff_source_evidence",
    }


def recover_archived_preseason_simulation(
    artifact: dict[str, Any], *, cutoff_iso: str, expected_league_id: str | None = None,
    retrospective_anchor: dict[str, Any] | None = None,
    expected_wins_total: float | None = None,
    expected_playoff_berths: int | None = None,
) -> dict[str, Any]:
    """Recover a historical original-vintage result, rejecting future evidence.

    artifact is a row-like {id, artifact_kind, computed_at, scope_id,
    input_fingerprint, model_version, payload} object. retrospective_anchor
    is the payload of a later captured canonical State snapshot.
    """
    cutoff = _when(cutoff_iso, "cutoff")
    if artifact.get("artifact_kind") != "live_simulation_analytics":
        raise ReplayValidationError("wrong artifact kind")
    _not_late(artifact.get("computed_at"), cutoff, "artifact.computed_at")
    payload = artifact["payload"]
    sim = payload["simulation_result"]
    views = payload["team_views"]
    league = payload["league_view"]
    _not_late(league["context"]["as_of"], cutoff, "league.context.as_of")
    if not isinstance(views, list) or not views:
        raise ReplayValidationError("no archived team views")
    lnames = {t["team_id"]: t for t in league["teams"]}
    team_ids = [t["team_id"] for t in views]
    if len(team_ids) != len(set(team_ids)) or set(team_ids) != set(lnames):
        raise ReplayValidationError("team-view/league identities disagree")
    if expected_league_id and any(not tid.startswith(expected_league_id + ":team:") for tid in team_ids):
        raise ReplayValidationError("unexpected league identity")
    outcomes = {t["team_id"]: t for t in sim["outcomes"]}
    if len(outcomes) != len(sim["outcomes"]) or set(outcomes) != set(team_ids):
        raise ReplayValidationError("simulation outcome/team identities disagree")
    trials = sim["simulation_count"]
    if type(trials) is not int or trials < 1:
        raise ReplayValidationError("simulation trial count invalid")
    if any(o.get("simulation_count") != trials for o in outcomes.values()):
        raise ReplayValidationError("per-team simulation counts disagree")

    source_forecasts = 0
    for team in views:
        _not_late(team["context"]["as_of"], cutoff, "team.context.as_of")
        for player in team.get("players", []):
            for forecast in player.get("forecasts", []):
                source_forecasts += 1
                for field in ("as_of",):
                    _not_late(forecast.get(field), cutoff, f"forecast.{field}")
                provenance = forecast.get("provenance") or {}
                for field in ("effective_at", "retrieved_at"):
                    _not_late(provenance.get(field), cutoff, f"forecast.provenance.{field}")
    if source_forecasts == 0:
        raise ReplayValidationError("missing archived forecast evidence")
    owner_players, owner_picks = _roster_and_pick_owners_from_artifact(views)

    rows = []
    for tid in team_ids:
        t, outcome = lnames[tid], outcomes[tid]
        try:
            wins = float(outcome["expected_wins"])
        except (ValueError, TypeError, KeyError) as exc:
            raise ReplayValidationError("missing or invalid expected wins") from exc
        if not math.isfinite(wins) or wins < 0:
            raise ReplayValidationError("invalid expected wins")
        rows.append({
            "team_id": tid, "historical_username": t["display_name"],
            "expected_wins": wins,
            "playoff_probability": _prob(outcome["playoff_probability"], "playoffs"),
            "championship_probability": _prob(outcome["championship_probability"], "championship"),
            "first_place_probability": _prob(outcome["first_place_probability"], "first_place"),
            "optimized_expected_points": t.get("optimized_expected_points"),
            "player_count": t.get("player_count"), "draft_pick_count": t.get("draft_pick_count"),
        })
    rows.sort(key=lambda row: (-row["expected_wins"], row["team_id"]))
    totals = {
        "expected_wins": sum(row["expected_wins"] for row in rows),
        "playoff_berths": sum(row["playoff_probability"] for row in rows),
        "championship_probability": sum(row["championship_probability"] for row in rows),
        "first_place_probability": sum(row["first_place_probability"] for row in rows),
    }
    if not math.isclose(totals["championship_probability"], 1, abs_tol=1e-6):
        raise ReplayValidationError("championship probability mass does not sum to one")
    if not math.isclose(totals["first_place_probability"], 1, abs_tol=1e-6):
        raise ReplayValidationError("first-place probability mass does not sum to one")
    if expected_wins_total is not None and not math.isclose(totals["expected_wins"], expected_wins_total, abs_tol=0.05):
        raise ReplayValidationError("win-sum invariant failed")
    if expected_playoff_berths is not None and not math.isclose(totals["playoff_berths"], expected_playoff_berths, abs_tol=0.01):
        raise ReplayValidationError("playoff-slot invariant failed")
    corroboration = (_anchor_comparison(retrospective_anchor, owner_players, owner_picks)
                     if retrospective_anchor is not None else {"status": "not_checked"})
    if corroboration["status"] == "membership_conflict":
        raise ReplayValidationError("retrospective anchor ownership disagrees with archived artifact")
    return {
        "status": "original_historical_simulation_recovered_not_rerun",
        "cutoff": cutoff.isoformat(), "artifact_id": artifact.get("id"),
        "artifact_computed_at": artifact["computed_at"],
        "source_scope_id": artifact.get("scope_id"),
        "source_input_fingerprint": artifact.get("input_fingerprint"),
        "artifact_model_version": artifact.get("model_version"),
        "simulation_model_version": sim.get("model_version"),
        "seed": sim.get("seed"), "simulation_count": trials,
        "teams": rows, "checks": {"team_count": len(rows), "player_memberships": len(owner_players),
                                      "pick_memberships": len(owner_picks), "forecast_records_checked": source_forecasts,
                                      "aggregates": totals, "anchor": corroboration},
        "original_warnings": views[0]["context"].get("warnings", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_json", type=Path, help="Input JSON with artifact metadata and retained payload")
    parser.add_argument("--anchor-json", type=Path, help="Optional retrospective canonical State payload")
    parser.add_argument("--cutoff", required=True, help="Kickoff cutoff (timezone-aware ISO 8601)")
    parser.add_argument("--league-id", help="Expected canonical league ID")
    parser.add_argument("--expected-wins", type=float)
    parser.add_argument("--playoff-slots", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    artifact = json.loads(args.artifact_json.read_text())
    anchor = json.loads(args.anchor_json.read_text()) if args.anchor_json else None
    result = recover_archived_preseason_simulation(artifact, cutoff_iso=args.cutoff,
        expected_league_id=args.league_id, retrospective_anchor=anchor,
        expected_wins_total=args.expected_wins,
        expected_playoff_berths=args.playoff_slots)
    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out: args.out.write_text(output)
    else: print(output, end="")


if __name__ == "__main__":
    main()

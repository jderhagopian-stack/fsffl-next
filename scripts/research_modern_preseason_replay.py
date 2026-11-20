"""Strict research-only admission + offline modern Simulation replay for an historical season.

No provider calls, DB writes, new model, or shortcut from a later State.
The runtime consumes canonical FSFFL NEXT State, Forecast and Simulation
authorities and refuses to run when point-in-time evidence is incomplete.

This first lane is CURRENT Simulation 2.0 on retained PRESEASON Forecast,
NOT yet a modern Forecast/3-Year/Career re-estimation. The latter has a
separate acceptance gate and cannot be represented by these outputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

DEFAULT_CUTOFF = "2026-09-10T00:20:00Z"
REQUIRED_STATE_RECEIPTS = frozenset({
    "league_rules", "rosters", "player_identity", "player_status",
    "draft_picks", "pick_ownership", "schedule", "nfl_byes",
    "weekly_availability",
})
REQUIRED_MODEL_RECEIPTS = frozenset({"simulation", "weekly_volatility", "forecast"})
RUN_KIND = "modern_simulation_on_historical_preseason_forecast"


def _ts(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field}: dated evidence is missing")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field}: invalid timestamp")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{field}: timezone missing")
        return None
    return parsed.astimezone(timezone.utc)


def _by_cutoff(value: Any, field: str, cutoff: datetime, errors: list[str]) -> None:
    when = _ts(value, field, errors)
    if when is not None and when > cutoff:
        errors.append(f"{field}: later than historical cutoff")


def _nonblank(row: dict, key: str, field: str, errors: list[str]) -> None:
    if not isinstance(row.get(key), str) or not row[key].strip():
        errors.append(f"{field}.{key}: required identity missing")


def _receipts(
    items: Any, *, required: frozenset[str], cutoff: datetime, errors: list[str],
    model: bool,
) -> None:
    if not isinstance(items, list):
        errors.append("model receipts missing" if model else "state receipts missing")
        return
    seen: set[str] = set()
    for ix, receipt in enumerate(items):
        if not isinstance(receipt, dict):
            errors.append(f"receipt {ix}: invalid structure")
            continue
        role = receipt.get("role")
        if not role or role in seen:
            errors.append(f"receipt {ix}: blank or duplicate role")
            continue
        seen.add(role)
        label = f"{'model' if model else 'state'} receipt {role}"
        _nonblank(receipt, "source_id", label, errors)
        _nonblank(receipt, "source_sha256", label, errors)
        if model:
            # Modern executable code may be created after the cutoff;
            # the learning data behind its parameters may not.
            _by_cutoff(receipt.get("training_through"), f"{label}.training_through", cutoff, errors)
            _nonblank(receipt, "model_version", label, errors)
        else:
            if receipt.get("authority") not in ("historical_snapshot", "independently_reconstructed"):
                errors.append(f"{label}: missing historical evidence authority")
            _by_cutoff(receipt.get("effective_at"), f"{label}.effective_at", cutoff, errors)
            _by_cutoff(receipt.get("available_at"), f"{label}.available_at", cutoff, errors)
            if receipt.get("source_only_from_later_snapshot") is True:
                errors.append(f"{label}: later retrospective source cannot become an input")
    for role in sorted(required - seen):
        errors.append(f"missing {'model' if model else 'state'} receipt: {role}")


def admit_historical_modern_simulation(bundle: dict[str, Any]) -> dict[str, Any]:
    """Pure, fail-closed evidence assessment; uses only the supplied bundle.

    Passing admission means only that required *declared* evidence is internally
    coherent. Independently verify receipt hashes/sources in a private source
    environment before any results receive publication authority.
    """
    errors: list[str] = []
    cutoff = _ts(bundle.get("cutoff"), "cutoff", errors)
    if cutoff is None:
        return {"eligible_to_run": False, "eligible_to_publish": False, "blockers": errors}
    if bundle.get("run_kind") != RUN_KIND:
        errors.append("run_kind must identify modern Simulation on historical Forecast")
    state = bundle.get("historical_state")
    if not isinstance(state, dict):
        errors.append("historical_state missing; a post-cutoff snapshot cannot substitute")
        state = {}
    _by_cutoff(state.get("as_of"), "historical_state.as_of", cutoff, errors)
    league = state.get("league") or {}
    if league.get("season") != 2026:
        errors.append("historical league season must be 2026 for this prototype")
    if not isinstance(league.get("league_id"), str) or not league["league_id"].strip():
        errors.append("canonical league id is missing")
    if state.get("completed_through_week") not in (None, 0):
        errors.append("preseason state contains completed fantasy weeks")
    matchups = state.get("matchups")
    if not isinstance(matchups, list) or not matchups:
        errors.append("complete preseason fantasy schedule is missing")
    else:
        for ix, m in enumerate(matchups):
            if m.get("team_a_points") is not None or m.get("team_b_points") is not None:
                errors.append(f"matchup {ix}: scored/post-kickoff data cannot enter preseason State")
                break
    if not state.get("nfl_team_byes"):
        errors.append("canonical NFL bye evidence is missing")
    if not state.get("teams") or not state.get("team_states"):
        errors.append("canonical team and roster set is missing")
    if not state.get("players") or not state.get("player_states"):
        errors.append("canonical player/state set is missing")
    if not state.get("pick_ownership") or not state.get("draft_picks"):
        errors.append("draft-pick universe and ownership must be evidenced")

    _receipts(bundle.get("state_receipts"), required=REQUIRED_STATE_RECEIPTS,
              cutoff=cutoff, errors=errors, model=False)
    _receipts(bundle.get("model_receipts"), required=REQUIRED_MODEL_RECEIPTS,
              cutoff=cutoff, errors=errors, model=True)

    forecasts = bundle.get("historical_forecasts")
    if not isinstance(forecasts, list) or not forecasts:
        errors.append("preseason Forecast evidence is missing")
    else:
        seen: set[tuple[str, str, str]] = set()
        for i, f in enumerate(forecasts):
            for name in ("as_of",):
                _by_cutoff(f.get(name), f"forecast {i}.{name}", cutoff, errors)
            provenance = f.get("provenance") or {}
            for name in ("effective_at", "retrieved_at"):
                _by_cutoff(provenance.get(name), f"forecast {i}.provenance.{name}", cutoff, errors)
            if f.get("metric") != "fantasy_points" or f.get("horizon") != "season":
                errors.append(f"forecast {i}: requires season fantasy-points authority")
            if f.get("period_start", "")[:4] != "2026":
                errors.append(f"forecast {i}: incorrect forecast season")
            key = (f.get("player_id"), f.get("metric"), f.get("horizon"))
            if key in seen:
                errors.append(f"forecast {i}: duplicate canonical player/metric/horizon")
            seen.add(key)
    code_id = bundle.get("model_git_sha")
    if not isinstance(code_id, str) or len(code_id) != 40 or any(c not in "0123456789abcdef" for c in code_id):
        errors.append("exact 40-hex modern model commit SHA is required")
    return {
        "eligible_to_run": not errors,
        # Publication of the complete modern-model almanac also needs modern
        # PIT Forecast and Value/Intrinsic outputs with separate evidence gates.
        "eligible_to_publish": False,
        "run_kind": RUN_KIND,
        "cutoff": cutoff.isoformat(),
        "blockers": errors,
        "limitations": [
            "Receipt content hashes and claimed source clocks require external independent verification.",
            "Modern Forecast and 3-Year/Career Intrinsic have not yet been PIT re-estimated.",
            "This lane does not authorize the full modern-model almanac for publication.",
        ],
    }


def run_offline_replay(bundle: dict[str, Any]) -> dict[str, Any]:
    preflight = admit_historical_modern_simulation(bundle)
    if not preflight["eligible_to_run"]:
        raise ValueError("historical replay admission failed: " + "; ".join(preflight["blockers"]))

    # Import existing authorities only after evidence has passed preflight.
    from fsffl.forecast.models import ForecastObservation
    from fsffl.state.models import LeagueState
    from fsffl.product.simulation_runtime import build_live_simulation_analytics
    from fsffl.team_utility.simulation import NUMPY_PCG64_BATCHED_GAUSS_V1

    state = LeagueState.model_validate(bundle["historical_state"])
    forecasts = tuple(ForecastObservation.model_validate(f) for f in bundle["historical_forecasts"])
    cutoff = datetime.fromisoformat(bundle["cutoff"].replace("Z", "+00:00"))
    # Current Simulation 2.0, original 2026 forecasts; no new model or
    # historical data acquisition, no live product publication or DB writes.
    result = build_live_simulation_analytics(
        state, forecasts=forecasts,
        forecast_model_version="historical-preseason-forecast-evidence:held-at-2026-cutoff",
        forecast_as_of=cutoff,
        simulation_count=50_000, seed=20260905,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1, rng_batch_size=500,
    )
    content = result.model_dump(mode="json")
    league_teams = content["league_view"]["teams"]
    outcome_rows = content["simulation_result"]["outcomes"]
    if len(outcome_rows) != len(league_teams):
        raise ValueError("Simulation result team membership mismatch")
    by_id = {x["team_id"]: x for x in outcome_rows}
    teams = []
    for item in league_teams:
        o = by_id[item["team_id"]]
        teams.append({
            "team_id": item["team_id"],
            "historical_display_name": item["display_name"],
            "expected_wins": o["expected_wins"],
            "playoff_probability": o["playoff_probability"],
            "championship_probability": o["championship_probability"],
            "expected_points": item.get("optimized_expected_points"),
        })
    teams.sort(key=lambda t: (-t["expected_wins"], t["team_id"]))
    canonical_input = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    return {
        "status": "modern_simulation_preseason_forecast_research_not_publish_approved",
        "run_kind": RUN_KIND, "cutoff": preflight["cutoff"],
        "model_git_sha": bundle["model_git_sha"],
        "source_bundle_sha256": hashlib.sha256(canonical_input).hexdigest(),
        "simulation_count": content["simulation_result"]["simulation_count"],
        "simulation_model_version": content["simulation_result"]["model_version"],
        "teams": teams,
        "model_warnings": content["league_view"]["context"].get("warnings", []),
        "publication_ready": False,
        "next_gates": [
            "independent pre-cutoff State and source-receipt hash verification",
            "modern Forecast with no post-cutoff training/feature data",
            "modern 3-Year/Career Intrinsic and native pick-economics PIT validation",
            "complete downstream publication contract and model-output comparison",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=str, help="PRIVATE 2026 historical data bundle JSON")
    parser.add_argument("--run", action="store_true", help="Execute bounded current Simulation after admission")
    parser.add_argument("--out", type=str, help="Write a local JSON result")
    args = parser.parse_args()
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    report = run_offline_replay(bundle) if args.run else admit_historical_modern_simulation(bundle)
    result = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()

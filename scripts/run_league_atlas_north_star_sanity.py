from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from fsffl.product.league_atlas import build_league_atlas_payload
from fsffl.product.runtime import UserRuntimeContext, default_sleeper_state_loader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/league_atlas_north_star_20260922"
LEAGUE_ID = "1312071960615731200"
JS = ROOT / "src/fsffl/product/static/league_comparison.js"
CSS = ROOT / "src/fsffl/product/static/league_atlas.css"


def elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    state = default_sleeper_state_loader(LEAGUE_ID)
    state_load_ms = elapsed_ms(started)
    runtime = UserRuntimeContext(
        user_id="league-atlas-sanity",
        league_state=state,
        selected_team_id=state.teams[0].team_id if state.teams else None,
    )

    started = time.perf_counter()
    payload = build_league_atlas_payload(runtime)
    cold_compose_ms = elapsed_ms(started)

    warm_samples: list[float] = []
    for _ in range(25):
        started = time.perf_counter()
        repeated = build_league_atlas_payload(runtime)
        warm_samples.append(elapsed_ms(started))
        if repeated["league_state_id"] != payload["league_state_id"]:
            raise RuntimeError("repeat Atlas composition changed canonical State identity")

    warm_median_ms = statistics.median(warm_samples)
    warm_p95_ms = sorted(warm_samples)[max(0, int(len(warm_samples) * 0.95) - 1)]

    if len(state.teams) != 12:
        raise RuntimeError(f"expected real 12-team league, found {len(state.teams)}")
    if len(payload["standings"]) != 12:
        raise RuntimeError("Atlas standings do not cover every real league team")
    if state.completed_through_week is None:
        raise RuntimeError("real live State is missing matchup completion authority")
    if payload["last_completed_week"] != state.completed_through_week:
        raise RuntimeError("Atlas last-completed-week diverges from canonical State")
    false_future_scores = [
        matchup
        for matchup in state.matchups
        if matchup.week > state.completed_through_week
        and (
            matchup.team_a_points is not None
            or matchup.team_b_points is not None
        )
    ]
    if false_future_scores:
        raise RuntimeError(
            "future matchup rows still contain scored/completed evidence after canonical normalization"
        )
    if len(state.draft_picks) != len(state.pick_ownership):
        raise RuntimeError("canonical pick ownership coverage is incomplete")
    if not payload["pick_map"]["teams"]:
        raise RuntimeError("real league produced no Pick Map rows")

    per_team_pick_counts = [row["total_owned_picks"] for row in payload["pick_map"]["teams"]]
    if len(set(per_team_pick_counts)) < 2:
        raise RuntimeError("real league Pick Map does not expose ownership concentration")

    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    for token in (
        "Overview",
        "Position & Depth",
        "Value Map",
        "Pick Map",
        "Outlook",
        "data-room-team",
        "data-room-position",
        "data-player-intelligence-id",
        "data-pick-team",
        "api('/api/league/atlas')",
        "api('/api/league/team-views')",
        "api('/api/league/value-lenses')",
    ):
        if token not in js:
            raise RuntimeError(f"Atlas source missing required interaction/evidence token: {token}")

    for forbidden in (
        "api('/api/values')",
        "team_cardinal_portfolios",
        "acceptance_probability",
    ):
        if forbidden in js:
            raise RuntimeError(f"Atlas source contains forbidden authority token: {forbidden}")

    for token in (
        "@media(max-width:720px)",
        "env(safe-area-inset-top)",
        "env(safe-area-inset-bottom)",
        "-webkit-overflow-scrolling:touch",
        ".atlas-drawer{inset:0",
    ):
        if token not in css:
            raise RuntimeError(f"Atlas mobile CSS missing required token: {token}")

    if cold_compose_ms > 500.0 or warm_p95_ms > 500.0:
        raise RuntimeError(
            "Atlas presentation composition exceeded the bounded 500 ms sanity threshold; "
            f"cold={cold_compose_ms:.2f} ms warm_p95={warm_p95_ms:.2f} ms"
        )

    manifest = {
        "schema_version": "fsffl-league-atlas-north-star-sanity-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "league_id": state.league.league_id,
        "league_name": state.league.name,
        "league_state_id": state.state_id,
        "team_count": len(state.teams),
        "draft_pick_count": len(state.draft_picks),
        "pick_ownership_count": len(state.pick_ownership),
        "pick_years": payload["pick_map"]["seasons"],
        "distinct_team_pick_counts": sorted(set(per_team_pick_counts)),
        "last_completed_week": payload["last_completed_week"],
        "future_scored_matchup_rows": len(false_future_scores),
        "simulation_status_in_ci_runtime": payload["simulation"]["status"],
        "preseason_status_in_ci_runtime": payload["preseason_expectation"]["status"],
        "latency_ms": {
            "real_sleeper_state_load": round(state_load_ms, 2),
            "atlas_compose_cold": round(cold_compose_ms, 3),
            "atlas_compose_warm_median": round(warm_median_ms, 3),
            "atlas_compose_warm_p95": round(warm_p95_ms, 3),
        },
        "authority": payload["authority"],
        "notes": [
            "This CI sanity uses the real league State and exercises the production Atlas composition builder.",
            "It intentionally does not recompute the 50,000-run Simulation or Shapley Intrinsic in CI.",
            "Persisted production evidence for Simulation, position strength, resilience, Market and A2+Burr-backed Intrinsic is recorded separately in the implementation checkpoint.",
            "Authenticated hosted iPhone/Safari latency remains a management acceptance item after exact-SHA deployment.",
        ],
        "status": "PASS",
    }
    (OUT / "LEAGUE_ATLAS_NORTH_STAR_SANITY.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUT / "LEAGUE_ATLAS_NORTH_STAR_SANITY.md").write_text(
        "\n".join(
            [
                "# League Atlas North Star real-league sanity",
                "",
                f"- Status: **{manifest['status']}**",
                f"- League: {manifest['league_name']} ({manifest['team_count']} teams)",
                f"- State: {manifest['league_state_id']}",
                f"- Picks: {manifest['draft_pick_count']} canonical picks / {manifest['pick_ownership_count']} ownership rows",
                f"- Pick years: {', '.join(str(x) for x in manifest['pick_years'])}",
                f"- State load: {state_load_ms:.2f} ms",
                f"- Atlas composition cold: {cold_compose_ms:.3f} ms",
                f"- Atlas composition warm median: {warm_median_ms:.3f} ms",
                f"- Atlas composition warm p95: {warm_p95_ms:.3f} ms",
                "",
                "The UI contract exposes the five North Star surfaces and required drilldowns without creating prohibited model authority.",
                "",
                "Authenticated hosted/mobile latency is not claimed by this CI run.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

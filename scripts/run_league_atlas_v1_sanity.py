from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from fsffl.product.league_value_lenses import build_league_value_lenses
from fsffl.product.runtime import UserRuntimeContext, default_sleeper_state_loader
from fsffl.product.team_page import build_state_only_team_view
from fsffl.value.current_runtime import build_current_market_values
from scripts.run_league_value_lens_real_roster_audit import (
    LEAGUE_ID,
    _intrinsic_contract,
    _load_rows,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/league_atlas_v1_20260921"
ATLAS_SOURCE = ROOT / "src/fsffl/product/static/league_atlas_v1.js"


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 2)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    state = default_sleeper_state_loader(LEAGUE_ID)
    state_load_ms = _elapsed_ms(started)

    started = time.perf_counter()
    market = build_current_market_values(state)
    market_load_ms = _elapsed_ms(started)

    started = time.perf_counter()
    intrinsic = _intrinsic_contract(_load_rows(), state.league.rules)
    intrinsic_build_ms = _elapsed_ms(started)

    runtime = UserRuntimeContext(
        user_id="league-atlas-sanity",
        league_state=state,
        value_evidence=market,
    )
    started = time.perf_counter()
    lenses = build_league_value_lenses(runtime, intrinsic)
    value_lens_build_ms = _elapsed_ms(started)

    started = time.perf_counter()
    team_views = tuple(
        build_state_only_team_view(state, team_id=team.team_id)
        for team in sorted(state.teams, key=lambda item: item.team_id)
    )
    state_team_views_ms = _elapsed_ms(started)

    ages = [
        float(view.roster_average_age)
        for view in team_views
        if view.roster_average_age is not None
    ]
    pick_counts = [len(view.draft_picks) for view in team_views]
    comparable = [
        row
        for row in lenses["players"]
        if row["comparison_available"] is True
    ]
    disagreement = sorted(
        comparable,
        key=lambda row: (
            -abs(float(row["percentile_gap"])),
            str(row["full_name"]),
        ),
    )[:12]

    atlas_source = ATLAS_SOURCE.read_text(encoding="utf-8")
    forbidden_source_tokens = {
        "legacy_values_endpoint": "api('/api/values')" in atlas_source,
        "team_cardinal_portfolios": "team_cardinal_portfolios" in atlas_source,
        "raw_intrinsic_value": "raw_intrinsic_value" in atlas_source,
    }
    if any(forbidden_source_tokens.values()):
        raise RuntimeError(
            f"Atlas source contains forbidden legacy/team-value wiring: {forbidden_source_tokens}"
        )
    if "api('/api/league/team-views')" not in atlas_source:
        raise RuntimeError("Atlas does not consume governed team-view contract")
    if "api('/api/league/value-lenses')" not in atlas_source:
        raise RuntimeError("Atlas does not consume governed value-lens contract")

    if len(state.teams) < 2:
        raise RuntimeError("real league sanity requires multiple teams")
    if len(set(pick_counts)) < 2:
        raise RuntimeError("real league did not expose a meaningful pick-inventory difference")
    if ages and max(ages) - min(ages) < 0.5:
        raise RuntimeError("real league did not expose a meaningful roster-age difference")
    if not comparable:
        raise RuntimeError("real league produced no comparable Broad Market / Intrinsic players")
    if max(abs(float(row["percentile_gap"])) for row in comparable) <= 0:
        raise RuntimeError("real league produced no player-level Market / Intrinsic disagreement")

    manifest = {
        "schema_version": "fsffl-league-atlas-v1-sanity-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "sleeper_league_id": LEAGUE_ID,
        "league_name": state.league.name,
        "team_count": len(state.teams),
        "rostered_player_rows": len(lenses["players"]),
        "comparable_value_lens_rows": len(comparable),
        "broad_market_status": lenses["broad_market"]["status"],
        "intrinsic_status": lenses["fsffl_intrinsic"]["status"],
        "state_only_team_view_count": len(team_views),
        "age_evidence": {
            "teams_with_roster_average_age": len(ages),
            "youngest_roster_average_age": min(ages) if ages else None,
            "oldest_roster_average_age": max(ages) if ages else None,
            "spread_years": (max(ages) - min(ages)) if ages else None,
        },
        "pick_inventory_evidence": {
            "minimum_owned_pick_count": min(pick_counts) if pick_counts else None,
            "maximum_owned_pick_count": max(pick_counts) if pick_counts else None,
            "distinct_pick_counts": sorted(set(pick_counts)),
        },
        "largest_player_value_disagreements": [
            {
                "team": row["owner_team_name"],
                "player": row["full_name"],
                "position": row["position"],
                "broad_market_percentile": row["broad_market_percentile"],
                "intrinsic_percentile": row["intrinsic_percentile"],
                "percentile_gap": row["percentile_gap"],
            }
            for row in disagreement
        ],
        "latency_ms": {
            "sleeper_state_load": state_load_ms,
            "current_market_load": market_load_ms,
            "intrinsic_contract_build": intrinsic_build_ms,
            "league_value_lens_build": value_lens_build_ms,
            "state_team_views_build": state_team_views_ms,
        },
        "authority": lenses["authority"],
        "presentation_source_checks": {
            **forbidden_source_tokens,
            "team_views_route_present": "api('/api/league/team-views')" in atlas_source,
            "value_lenses_route_present": "api('/api/league/value-lenses')" in atlas_source,
            "mobile_900_rule_present": "@media(max-width:900px)" in atlas_source,
            "mobile_560_rule_present": "@media(max-width:560px)" in atlas_source,
            "latency_measurement_present": "performance.now" in atlas_source,
        },
        "availability_note": (
            "This real-state audit validates State/age/picks and player Value-lens "
            "differences. Position strength, competitive lanes, and fragility remain "
            "conditional on the already-governed enriched team-view runtime evidence; "
            "the Atlas does not manufacture substitutes when those layers are absent."
        ),
        "status": "PASS",
    }

    (OUT / "LEAGUE_ATLAS_V1_SANITY.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = [
        "# League Atlas v1 real-league sanity",
        "",
        f"- Status: **{manifest['status']}**",
        f"- League: {manifest['league_name']} ({manifest['team_count']} teams)",
        f"- Comparable player value-lens rows: {len(comparable)}",
        f"- Roster-age spread: {manifest['age_evidence']['spread_years']:.2f} years"
        if ages
        else "- Roster-age evidence unavailable",
        (
            "- Owned-pick count range: "
            f"{manifest['pick_inventory_evidence']['minimum_owned_pick_count']}–"
            f"{manifest['pick_inventory_evidence']['maximum_owned_pick_count']}"
        ),
        f"- State load: {state_load_ms:.2f} ms",
        f"- Market load: {market_load_ms:.2f} ms",
        f"- Value-lens composition: {value_lens_build_ms:.2f} ms",
        "",
        "The persisted/live league evidence exposes meaningful age, pick-inventory, "
        "and player-level Market-vs-Intrinsic differences without a team master score.",
        "",
        manifest["availability_note"],
    ]
    (OUT / "LEAGUE_ATLAS_V1_SANITY.md").write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

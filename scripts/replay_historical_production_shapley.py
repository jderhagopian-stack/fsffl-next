"""Reproducible historical observed-year replay through the *production* Shapley engine.

HINDSIGHT DIAGNOSTIC ONLY: not point-in-time forecasts, 3-Year or Career
Intrinsic; no Y8+ terminal. No missing-season zero fill. Run explicitly with
a governed input panel; this script neither downloads nor changes production.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import LeagueRules, LineupRequirement, RosterSlot
from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS, FROZEN_SHAPLEY_SEED,
    monte_carlo_shapley_scenarios, subset_caps_from_rules,
)

STARTS = (2003, 2006, 2009, 2012, 2015)


def fixture(superflex: bool = True) -> LeagueRules:
    positions = [("QB", 1), ("RB", 2), ("WR", 2), ("TE", 1), ("FLEX", 1)]
    if superflex:
        positions.append(("SUPERFLEX", 1))
    return LeagueRules(
        team_count=12, roster_size=24,
        lineup=tuple(LineupRequirement(slot=RosterSlot(slot), count=count)
                     for slot, count in positions),
        scoring=(),
    )


def read_observed_panel(path: Path) -> dict[int, list[tuple[str, str, float]]]:
    seasons: dict[int, list[tuple[str, str, float]]] = defaultdict(list)
    seen: set[tuple[int, str]] = set()
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            season, pid, position = int(row["season"]), row["player_id"], row["position"]
            if position not in {"QB", "RB", "WR", "TE"}:
                continue
            if (season, pid) in seen:
                raise ValueError("duplicate historical player season")
            seen.add((season, pid))
            seasons[season].append((pid, position, max(0.0, float(row["fantasy_points"]))))
    return {year: sorted(players) for year, players in seasons.items()}


def replay(
    panel: dict[int, list[tuple[str, str, float]]],
    *,
    starts: tuple[int, ...] = STARTS,
    rules: LeagueRules | None = None,
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS,
) -> dict[str, object]:
    if permutations < 1:
        raise ValueError("permutations must be positive")
    rules = rules or fixture()
    caps = subset_caps_from_rules(rules)
    needed = sorted({s + i for s in starts for i in range(8)})
    annual: dict[int, dict[str, float]] = {}
    for year in needed:
        players = panel.get(year)
        if not players:
            raise ValueError(f"missing complete observed year {year}")
        result = monte_carlo_shapley_scenarios(
            players, {pid: (pts,) for pid, _, pts in players}, caps,
            permutations=permutations, seed=FROZEN_SHAPLEY_SEED,
        )
        annual[year] = {pid: values[0] for pid, values in result.estimates.items()}
    cohorts = []
    for start in starts:
        rows = []
        for pid in sorted(annual[start]):
            values = [annual[start + offset].get(pid) for offset in range(8)]
            rows.append({
                "player_id": pid,
                "annual_observed_shapley": values,
                "three_year_hindsight": (
                    sum(v * (.85 ** i) for i, v in enumerate(values[:3]))
                    if all(v is not None for v in values[:3]) else None
                ),
                "seven_year_hindsight": (
                    sum(values[:7]) if all(v is not None for v in values[:7]) else None
                ),
            })
        cohorts.append({"start_season": start, "player_count": len(rows),
                        "three_year_complete": sum(x["three_year_hindsight"] is not None for x in rows),
                        "seven_year_complete": sum(x["seven_year_hindsight"] is not None for x in rows),
                        "max_three_year": max((x["three_year_hindsight"] for x in rows
                                               if x["three_year_hindsight"] is not None), default=None),
                        "max_seven_year": max((x["seven_year_hindsight"] for x in rows
                                               if x["seven_year_hindsight"] is not None), default=None),
                        "players": rows})
    return {
        "evidence_kind": "hindsight_production_shapley_not_career_intrinsic",
        "rules": rules.model_dump(mode="json"),
        "permutations": permutations,
        "seed": FROZEN_SHAPLEY_SEED,
        "years": needed,
        "cohorts": cohorts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--permutations", type=int, default=FROZEN_SHAPLEY_PERMUTATIONS)
    parser.add_argument("--single-qb", action="store_true")
    args = parser.parse_args()
    data = replay(read_observed_panel(args.panel), rules=fixture(not args.single_qb),
                  permutations=args.permutations)
    data["panel_sha256"] = hashlib.sha256(args.panel.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()

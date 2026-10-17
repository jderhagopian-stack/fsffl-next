"""Historical hindsight Y1–Y3 *real frozen Shapley* replay; NOT a Career contract.

Consumes prepared historical outcome CSV from external evidence package.
Uses full historical player pool per year, a chosen fixed league-rule fixture,
and FSFFL's actual frozen Shapley Monte Carlo implementation. No predictions
are inferred and missing future seasons are never silently set to zero.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from fsffl.state.models import LeagueRules, LineupRequirement, RosterSlot
from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS, FROZEN_SHAPLEY_SEED,
    monte_carlo_shapley_scenarios, subset_caps_from_rules,
)


def example_rules() -> LeagueRules:
    return LeagueRules(
        team_count=12, roster_size=24,
        lineup=tuple(LineupRequirement(slot=RosterSlot(s), count=n) for s, n in (
            ("QB", 1), ("RB", 2), ("WR", 2), ("TE", 1),
            ("FLEX", 1), ("SUPERFLEX", 1),
        )),
        scoring=(),
    )


def replay_observed_three_year(path: Path, *, seasons: tuple[int, ...],
                               rules: LeagueRules, permutations: int = FROZEN_SHAPLEY_PERMUTATIONS) -> list[dict]:
    observed = defaultdict(dict)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["data_role"] != "hindsight_observed_outcome_not_forecast":
                raise ValueError("input cannot be treated as contemporaneous forecasts")
            season = int(row["season"])
            key = (int(row["evaluation_season"]), season)
            pid = row["player_id"]
            if pid in observed[key]:
                raise ValueError("duplicate historical player-season record")
            observed[key][pid] = (row["position"], max(0.0, float(row["recorded_fantasy_points"])))
    caps = subset_caps_from_rules(rules)
    results = []
    for start in seasons:
        contributions = defaultdict(dict)
        cohort = set(observed[start, start])
        if not cohort:
            raise ValueError(f"historical cohort absent: {start}")
        for offset in range(3):
            year = start + offset
            year_pool = observed.get((start, year), {})
            missing = cohort - set(year_pool)
            if missing:
                # Retirement and nonappearance require governed evidence;
                # survivorship must not be manufactured into zero projections.
                raise ValueError(f"{start} +{offset}: {len(missing)} missing future player seasons")
            players = sorted((pid, pos, points) for pid, (pos, points) in year_pool.items())
            game = monte_carlo_shapley_scenarios(
                players, {pid: (points,) for pid, _, points in players}, caps,
                permutations=permutations, seed=FROZEN_SHAPLEY_SEED+offset,
            )
            for pid in cohort:
                contributions[pid][offset] = game.estimates[pid][0]
        for pid in sorted(cohort):
            y = contributions[pid]
            results.append({"evaluation_season": start, "player_id": pid,
                            "observed_shapley_y1": y[0], "observed_shapley_y2": y[1],
                            "observed_shapley_y3": y[2],
                            "hindsight_three_year": y[0]+0.85*y[1]+0.7225*y[2],
                            "evidence": "hindsight_shapley_not_career_intrinsic"})
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("historical_csv", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--seasons", nargs="+", type=int, default=[2003,2006,2009,2012,2015])
    parser.add_argument("--permutations", type=int, default=FROZEN_SHAPLEY_PERMUTATIONS)
    args = parser.parse_args()
    rows = replay_observed_three_year(args.historical_csv, seasons=tuple(args.seasons),
                                      rules=example_rules(), permutations=args.permutations)
    args.output_json.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()

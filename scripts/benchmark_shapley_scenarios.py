"""Isolated synthetic Shapley execution benchmark; no acquisition or persistence.

Run the same script with PYTHONPATH pointing at each checkout's src directory.
Compare result_sha256 before comparing runtime. This is a kernel measurement,
not a production refresh or forecast-accuracy evaluation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import random
import resource
import sys
from time import perf_counter, process_time

from fsffl.state.models import LeagueRules, LineupRequirement
from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS, FROZEN_SHAPLEY_SEED,
    clear_shapley_execution_caches, monte_carlo_shapley_scenarios,
    subset_caps_from_rules,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", type=int, default=366)
    parser.add_argument("--format", choices=("superflex", "1qb"), default="superflex")
    args = parser.parse_args()
    if args.players < 1:
        parser.error("--players must be positive")
    lineup = [("QB", 1), ("RB", 2), ("WR", 3), ("TE", 1), ("FLEX", 1)]
    if args.format == "superflex":
        lineup.append(("SUPERFLEX", 1))
    rules = LeagueRules(team_count=12, roster_size=30, scoring=(),
        lineup=tuple(LineupRequirement(slot=slot, count=count) for slot, count in lineup))
    rng = random.Random(817)
    players = [(f"p{i:03}", ("QB", "RB", "WR", "TE")[i % 4], rng.uniform(0, 350))
               for i in range(args.players)]
    scenarios = {pid: tuple(weight * factor for factor in (1, 0, .1, .4, .75, 1.2, 1.7))
                 for pid, _, weight in players}
    caps = subset_caps_from_rules(rules)
    clear_shapley_execution_caches()
    wall, cpu = perf_counter(), process_time()
    result = monte_carlo_shapley_scenarios(players, scenarios, caps)
    elapsed, cpu_elapsed = perf_counter() - wall, process_time() - cpu
    digest = hashlib.sha256(json.dumps(asdict(result), sort_keys=True).encode()).hexdigest()
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({
        "format": args.format, "players": args.players, "scenarios": 7,
        "permutations": FROZEN_SHAPLEY_PERMUTATIONS, "seed": FROZEN_SHAPLEY_SEED,
        "wall_seconds": elapsed, "cpu_seconds": cpu_elapsed,
        "process_peak_rss_bytes": peak if sys.platform == "darwin" else peak * 1024,
        "result_sha256": digest,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

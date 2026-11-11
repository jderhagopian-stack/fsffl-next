"""Independent permutation/basis parity test against production Shapley.

Catches RNG carry-forward or replacement-planning drift on a deterministic fixture.
This is a numerical *fixture* test, not proof of full-history replay parity.
"""
from __future__ import annotations

import bisect
import random

from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_SEED, monte_carlo_shapley_scenarios, subset_caps_from_rules,
)
from scripts.replay_historical_production_shapley import fixture


def independent_reference(players, caps, permutations, seed):
    rng = random.Random(seed)
    players = sorted(players)
    totals = {pid: 0.0 for pid, _, _ in players}
    for _ in range(permutations):
        order = list(range(len(players)))  # fresh canonical order every draw
        rng.shuffle(order)
        counts = [0] * 4
        held = [[] for _ in range(4)]
        for i in order:
            pid, pos, weight = players[i]
            incoming = ("QB", "RB", "WR", "TE").index(pos)
            add = counts[:]
            add[incoming] += 1
            feasible = all(sum(add[j] for j in subset) <= cap for subset, cap in caps)
            outgoing = None
            if not feasible:
                choices = []
                for j in range(4):
                    if not counts[j]:
                        continue
                    replacement = counts[:]
                    replacement[j] -= 1
                    replacement[incoming] += 1
                    if all(sum(replacement[k] for k in subset) <= cap for subset, cap in caps):
                        if held[j]:
                            w, old_id = held[j][0]
                            choices.append((w, old_id, j))
                outgoing = min(choices) if choices else None
                if outgoing is None or weight <= outgoing[0] + 1e-12:
                    continue
                _, _, old_pos = outgoing
                held[old_pos].pop(0)
                counts[old_pos] -= 1
            bisect.insort(held[incoming], (weight, pid))
            counts[incoming] += 1
            totals[pid] += weight - (outgoing[0] if outgoing else 0.0)
    return {pid: total / permutations for pid, total in totals.items()}


def test_production_matches_independent_reference_on_oversubscribed_fixture():
    players = sorted([
        (f"qb{i}", "QB", float(340-i*11)) for i in range(18)
    ] + [
        (f"rb{i}", "RB", float(280-i*5)) for i in range(45)
    ] + [
        (f"wr{i}", "WR", float(275-i*4)) for i in range(50)
    ] + [
        (f"te{i}", "TE", float(220-i*7)) for i in range(23)
    ])
    for superflex in (False, True):
        caps = subset_caps_from_rules(fixture(superflex))
        expected = independent_reference(players, caps, 128, FROZEN_SHAPLEY_SEED)
        result = monte_carlo_shapley_scenarios(
            players, {pid: (value,) for pid, _, value in players}, caps,
            permutations=128, seed=FROZEN_SHAPLEY_SEED,
        )
        for pid, amount in expected.items():
            assert abs(result.estimates[pid][0] - amount) < 1e-8, (superflex, pid)

from __future__ import annotations

import bisect
import random
from dataclasses import dataclass
from typing import Mapping, Sequence

POSITIONS = ("QB", "RB", "WR", "TE")
POS_INDEX = {p: i for i, p in enumerate(POSITIONS)}
FROZEN_DISCOUNT = 0.85
FROZEN_PERMUTATIONS = 2048
FROZEN_SEED = 20260914


@dataclass(frozen=True)
class LeagueDeploymentRules:
    team_count: int = 12
    direct_qb: int = 1
    direct_rb: int = 2
    direct_wr: int = 3
    direct_te: int = 1
    flex: int = 1
    superflex: int = 1

    def subset_caps(self) -> tuple[tuple[tuple[int, ...], int], ...]:
        direct = {"QB": self.direct_qb, "RB": self.direct_rb, "WR": self.direct_wr, "TE": self.direct_te}
        caps = []
        for mask in range(1, 1 << 4):
            cap = self.team_count * sum(direct[POSITIONS[i]] for i in range(4) if mask & (1 << i))
            if any(mask & (1 << POS_INDEX[p]) for p in ("RB", "WR", "TE")):
                cap += self.team_count * self.flex
            cap += self.team_count * self.superflex
            caps.append((tuple(i for i in range(4) if mask & (1 << i)), cap))
        return tuple(caps)


@dataclass(frozen=True)
class PlayerDeployment:
    player_id: str
    position: str
    production: float


class _Basis:
    def __init__(self, caps):
        self.caps = caps; self.counts = [0, 0, 0, 0]; self.by_pos = [[] for _ in range(4)]; self.total = 0.0
    def _ok(self, counts): return all(sum(counts[i] for i in idxs) <= cap for idxs, cap in self.caps)
    def _can_add(self, pi):
        c = self.counts.copy(); c[pi] += 1; return self._ok(c)
    def _can_swap(self, out_pos, in_pos):
        if self.counts[out_pos] <= 0: return False
        c = self.counts.copy(); c[out_pos] -= 1; c[in_pos] += 1; return self._ok(c)
    def marginal(self, pos, weight):
        w = max(0.0, float(weight)); pi = POS_INDEX[pos]
        if w <= 0: return 0.0, None
        if self._can_add(pi): return w, (None, None, None)
        best = None
        for opi in range(4):
            if not self.by_pos[opi] or not self._can_swap(opi, pi): continue
            ow, opid = self.by_pos[opi][0]
            if best is None or (ow, opid, opi) < best: best = (ow, opid, opi)
        if best is None or w <= best[0] + 1e-12: return 0.0, None
        return w - best[0], (best[2], best[0], best[1])
    def add(self, pid, pos, weight):
        delta, replace = self.marginal(pos, weight); w = max(0.0, float(weight)); pi = POS_INDEX[pos]
        if replace is None: return 0.0
        if replace[0] is None:
            bisect.insort(self.by_pos[pi], (w, pid)); self.counts[pi] += 1; self.total += w; return w
        opi, ow, _ = replace
        self.by_pos[opi].pop(0); self.counts[opi] -= 1; self.total -= ow
        bisect.insort(self.by_pos[pi], (w, pid)); self.counts[pi] += 1; self.total += w
        return delta


def deployment_shapley(players: Sequence[PlayerDeployment], rules: LeagueDeploymentRules = LeagueDeploymentRules(), *, permutations: int = FROZEN_PERMUTATIONS, seed: int = FROZEN_SEED) -> dict[str, float]:
    """Frozen roster-neutral deployment Shapley estimator. Holding/B4 effects are zero."""
    if permutations <= 0: raise ValueError("permutations must be positive")
    caps = rules.subset_caps(); ids = [p.player_id for p in players]
    if len(ids) != len(set(ids)): raise ValueError("player ids must be unique")
    by_id = {p.player_id: p for p in players}; sums = {pid: 0.0 for pid in ids}; rng = random.Random(seed)
    for _ in range(permutations):
        order = ids[:]; rng.shuffle(order); basis = _Basis(caps)
        for pid in order:
            p = by_id[pid]; sums[pid] += basis.add(pid, p.position, p.production)
    return {pid: sums[pid] / permutations for pid in ids}


def scenario_shapley(players: Sequence[PlayerDeployment], scenario_values: Mapping[str, Sequence[float]], rules: LeagueDeploymentRules = LeagueDeploymentRules(), *, permutations: int = FROZEN_PERMUTATIONS, seed: int = FROZEN_SEED) -> dict[str, tuple[float, ...]]:
    caps = rules.subset_caps(); ids = [p.player_id for p in players]; by_id = {p.player_id: p for p in players}; rng = random.Random(seed)
    sums = {pid: [0.0] * len(scenario_values[pid]) for pid in ids}
    for _ in range(permutations):
        order = ids[:]; rng.shuffle(order); basis = _Basis(caps)
        for pid in order:
            p = by_id[pid]
            for j, value in enumerate(scenario_values[pid]): sums[pid][j] += basis.marginal(p.position, value)[0]
            basis.add(pid, p.position, p.production)
    return {pid: tuple(v / permutations for v in vals) for pid, vals in sums.items()}


def career_intrinsic_value(y1_phi: float, future_expected_phi: Sequence[float], *, discount: float = FROZEN_DISCOUNT) -> float:
    """Frozen career integration: Y1 plus discounted Y2/Y3 expected deployment contribution."""
    if discount != FROZEN_DISCOUNT:
        raise ValueError("frozen Intrinsic discount must remain 0.85")
    return max(0.0, float(y1_phi)) + sum((discount ** h) * max(0.0, float(phi)) for h, phi in enumerate(future_expected_phi, start=1))

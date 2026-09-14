from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load():
    path = Path(__file__).with_name("run_intrinsic_marginal_franchise_challenge.py")
    spec = importlib.util.spec_from_file_location("intrinsic_marginal_challenge_impl", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


m = _load()


def _synthetic(latest_baselines, latest_pools, latest_econ, tapers, marginal_parents, marginal_cells, v5c):
    profiles = [
        ("elite_young_qb", "QB", 24, (360, 380, 390)),
        ("solid_starting_qb", "QB", 29, (285, 270, 255)),
        ("elite_young_rb", "RB", 23, (330, 305, 275)),
        ("elite_young_wr", "WR", 23, (285, 305, 315)),
        ("elite_young_te", "TE", 23, (235, 250, 260)),
        ("aging_productive_rb", "RB", 31, (260, 195, 125)),
        ("developmental_wr", "WR", 22, (105, 155, 205)),
        ("fringe_player", "WR", 27, (45, 35, 25)),
    ]
    rows = []
    for name, pos, age, means in profiles:
        p = m.Position(pos)
        demand = latest_econ[p].selected_starters
        pool = latest_pools[p]
        cf = tapers["aging_cells"].get(f"{pos}:{v5c.age_band(pos, age)}", tapers["parent"][pos])
        inc = sum((m.DISCOUNT ** i) * value * m.relevance(value, pool, demand) for i, value in enumerate(means))
        inc += (m.DISCOUNT ** 3) * means[2] * m.relevance(means[2], pool, demand) * cf
        mcf = marginal_cells.get((pos, m.age_band(pos, age)), marginal_parents[pos])
        chal = sum((m.DISCOUNT ** i) * m.marginal_at_x(value, latest_baselines[pos]) for i, value in enumerate(means))
        chal += (m.DISCOUNT ** 3) * m.marginal_at_x(means[2], latest_baselines[pos]) * mcf
        rows.append({"profile": name, "position": pos, "incumbent_raw_no_pedigree": inc, "challenger_raw_no_pedigree": chal})
    return rows


m.synthetic = _synthetic
m.main()

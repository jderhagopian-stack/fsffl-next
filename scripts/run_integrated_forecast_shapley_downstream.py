from __future__ import annotations

import argparse, importlib.util, json, math, sys
from collections import defaultdict
from pathlib import Path

PERMS = 2048
DISCOUNT = 0.85
SEED = 20260915
TEST_SEASONS = (2021, 2022)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def quantile(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo = int(math.floor(z)); hi = int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    f = z - lo
    return xs[lo] * (1 - f) + xs[hi] * f


def corr(xs, ys):
    xs = list(xs); ys = list(ys)
    if len(xs) < 2:
        return 0.0
    mx = mean(xs); my = mean(ys)
    dx = [x - mx for x in xs]; dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return sum(a*b for a,b in zip(dx,dy)) / den if den > 1e-12 else 0.0


def rankdata(vals):
    order = sorted(range(len(vals)), key=lambda i: (vals[i], i))
    out = [0.0] * len(vals); i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and vals[order[j]] == vals[order[i]]:
            j += 1
        r = (i + j - 1) / 2 + 1
        for k in order[i:j]:
            out[k] = r
        i = j
    return out


def spearman(xs, ys):
    return corr(rankdata(list(xs)), rankdata(list(ys))) if len(xs) >= 2 else 0.0


def age_band(pos, age):
    if age is None:
        return "unknown"
    if pos == "QB":
        return "young" if age <= 25 else ("prime" if age <= 31 else "aging")
    return "young" if age <= 23 else ("prime" if age <= 27 else "aging")


def metric(rows, key, ref="realized_h3"):
    xs = [float(r[key]) for r in rows]
    ys = [float(r[ref]) for r in rows]
    ds = [x-y for x,y in zip(xs,ys)]
    return {
        "n": len(rows),
        "mae": mean(abs(d) for d in ds),
        "bias": mean(ds),
        "pearson": corr(xs, ys),
        "spearman": spearman(xs, ys),
    }


def summarize_groups(rows):
    positives = [float(r["realized_h3"]) for r in rows if float(r["realized_h3"]) > 1e-12]
    p25 = quantile(positives, .25); p75 = quantile(positives, .75); p90 = quantile(positives, .90)
    groups = {p: [r for r in rows if r["position"] == p] for p in ("QB","RB","WR","TE")}
    groups.update({
        "no_use": [r for r in rows if float(r["realized_h3"]) <= 1e-12],
        "replacement_useful": [r for r in rows if 0 < float(r["realized_h3"]) <= p25],
        "ordinary_useful": [r for r in rows if p25 < float(r["realized_h3"]) <= p75],
        "premium": [r for r in rows if float(r["realized_h3"]) > p75],
        "elite": [r for r in rows if float(r["realized_h3"]) >= p90],
        "young": [r for r in rows if age_band(r["position"], r.get("age")) == "young"],
        "prime": [r for r in rows if age_band(r["position"], r.get("age")) == "prime"],
        "aging": [r for r in rows if age_band(r["position"], r.get("age")) == "aging"],
    })
    out = {}
    for name, g in groups.items():
        if not g:
            continue
        out[name] = {
            "n": len(g),
            "integrated_mean": mean(float(r["integrated_shapley"]) for r in g),
            "prior_forecast_mean": mean(float(r["prior_forecast_shapley"]) for r in g),
            "realized_h3_mean": mean(float(r["realized_h3"]) for r in g),
            "integrated_mae": mean(abs(float(r["integrated_shapley"])-float(r["realized_h3"])) for r in g),
            "prior_mae": mean(abs(float(r["prior_forecast_shapley"])-float(r["realized_h3"])) for r in g),
            "target_mean": mean(float(r["target"]) for r in g),
        }
    return {"positive_thresholds": {"p25": p25, "p75": p75, "p90": p90}, "groups": out}


def deciles(rows):
    ordered = sorted(rows, key=lambda r: float(r["realized_h3"]))
    n = len(ordered); out = []
    for d in range(10):
        a = int(d*n/10); b = int((d+1)*n/10); g = ordered[a:b]
        if not g:
            continue
        out.append({
            "decile": d+1,
            "n": len(g),
            "realized_h3_mean": mean(float(r["realized_h3"]) for r in g),
            "integrated_mean": mean(float(r["integrated_shapley"]) for r in g),
            "prior_mean": mean(float(r["prior_forecast_shapley"]) for r in g),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--usage-panel", type=Path, required=True)
    ap.add_argument("--model-a-rows", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--prior-forecast-json", type=Path, required=True)
    ap.add_argument("--prior-event-json", type=Path, required=True)
    ap.add_argument("--prior-persistence-json", type=Path, required=True)
    ap.add_argument("--integrated-results", type=Path, required=True)
    ap.add_argument("--prior-decomp-rows", type=Path, required=True)
    ap.add_argument("--constitution-json", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    here = Path(__file__).parent
    im = load(here / "run_integrated_multivariate_forecast.py", "down_im")
    dep = load(here / "run_deployment_shapley_intrinsic_research.py", "down_dep")
    pf = load(here / "run_persistence_first_forecast_calibration.py", "down_pf")
    prior = load(here / "run_forecast_low_end_career_calibration.py", "down_prior")
    legacy = load(here / "run_fundamental_intrinsic_residual_calibration.py", "down_legacy")
    parity = load(here / "run_fundamental_intrinsic_production_parity.py", "down_parity")
    base = load(here / "run_intrinsic_explicit_state_challenge.py", "down_base")
    evt = load(here / "reconstruct_event_time_absence_cause_evidence.py", "down_evt")

    selected = json.loads(args.integrated_results.read_text())
    if selected["holdout"]["status"] != "PROMOTABLE FOR MANAGEMENT REVIEW" or selected["holdout"]["selected"] != "I1":
        raise RuntimeError("downstream Shapley is authorized only for frozen promotable I1")
    C = float(selected["C"]["I1"])

    F = json.loads(args.prior_forecast_json.read_text())
    E = json.loads(args.prior_event_json.read_text())
    P = json.loads(args.prior_persistence_json.read_text())
    parity_checks = {
        "c0": abs(F["summaries"]["low_end"]["c0_"]["state_brier"] - .17558645736306655) < 1e-10,
        "resolution": abs(E["overall_resolution"]["resolved_share"] - 685/925) < 1e-10,
        "p145": P["conclusion"] == "P4. TWO-STAGE PERSISTENCE-FIRST DECOMPOSITION DOES NOT IMPROVE THE PROBLEM",
    }
    if not all(parity_checks.values()):
        raise RuntimeError("frozen evidence parity failed: " + json.dumps(parity_checks))

    examples, _ = parity.build_examples(panel_path=args.career_panel, model_rows_path=args.model_a_rows, qb_results_path=args.qb_results, legacy=legacy)
    panel = legacy.load_rows(args.career_panel)
    by = {(r.player_id, r.season): r for r in panel}
    usage = pf.load_usage(args.usage_panel)
    qb = parity.load_qb_probabilities(args.qb_results)
    ev = pf.source_evidence_map(evt, list(range(2012, 2025)))
    caps = dep.subset_caps()

    prior_rows = json.loads(args.prior_decomp_rows.read_text())
    prior_by = {(int(r["season"]), r["player_id"]): r for r in prior_rows}
    all_rows = []
    season_diag = {}

    for season in TEST_SEASONS:
        supply = [e for e in examples if e.season == season and (e.player_id, season) in by]
        bounds = base.fit_state_boundaries(panel, season)
        c0 = base.fit_transition_counts(panel, season, bounds)
        R = im.records(pf, base, panel, by, season, bounds, usage, ev)
        B = im.fitmodel(R, C, "I1")
        forecast = {}
        for e in supply:
            x = by[(e.player_id, season)]
            cur = base.state_for_points(x.points, bounds[e.position])
            age = base.age_band(e.position, e.age)
            u = usage.get((e.player_id, season))
            evidence = ev["source"].get((e.player_id, season))
            prevrow = by.get((e.player_id, season-1)); prev = None if prevrow is None else float(prevrow.points)
            for h in (1,2):
                _, p0 = prior.probs(base, c0, e, bounds, qb, h)
                inp = {"position": e.position, "age": age, "current": cur, "h": h, "srcpts": float(x.points), "prev": prev, "exp": e.experience, "u": u, "e": evidence}
                probs, path = im.pred(B, inp, p0)
                means = {s: max(0.0, float(B["means"].g(e.position, h, s))) for s in im.STATES}
                forecast[(e.player_id,h)] = {"probs": probs, "path": path, "means": means, "expected": max(0.0, float(B["means"].exp(probs, e.position, h)))}

        est_by_h = {}; se_by_h = {}; diag_by_h = {}
        for h in (0,1,2):
            if h == 0:
                players = [(e.player_id, e.position, max(0.0, float(e.means[0]))) for e in supply]
                scenarios = {pid: [w] for pid,_,w in players}
            else:
                players = [(e.player_id, e.position, forecast[(e.player_id,h)]["expected"]) for e in supply]
                scenarios = {}
                for e in supply:
                    f = forecast[(e.player_id,h)]
                    scenarios[e.player_id] = [f["expected"]] + [f["means"][s] for s in im.STATES]
            est, se, _, diag = dep.mc_scenarios(players, scenarios, caps, perms=PERMS, seed=SEED + season*10 + h)
            est_by_h[h] = est; se_by_h[h] = se; diag_by_h[h] = diag

        abs_se = []
        for h in (0,1,2):
            for e in supply:
                abs_se.extend(float(v) for v in se_by_h[h][e.player_id])
        season_diag[str(season)] = {
            "supply_n": len(supply),
            "permutations": PERMS,
            "scenario_se_p50": quantile(abs_se, .50),
            "scenario_se_p95": quantile(abs_se, .95),
            "max_efficiency_residual": max(abs(float(diag_by_h[h]["efficiency_residual"])) for h in (0,1,2)),
        }

        for e in supply:
            old = prior_by.get((season, e.player_id))
            if old is None:
                continue
            phi0 = float(est_by_h[0][e.player_id][0])
            total = phi0; horizon = []
            for h in (1,2):
                f = forecast[(e.player_id,h)]
                vals = est_by_h[h][e.player_id]
                expected_phi = sum(float(f["probs"][s]) * float(vals[1 + im.STATES.index(s)]) for s in im.STATES)
                total += (DISCOUNT ** h) * expected_phi
                horizon.append({"horizon": h+1, "expected_points": f["expected"], "expected_shapley": expected_phi, "path": f["path"], "probs": f["probs"], "state_means": f["means"]})
            all_rows.append({
                "season": season,
                "player_id": e.player_id,
                "position": e.position,
                "age": e.age,
                "experience": e.experience,
                "integrated_shapley": total,
                "phi_y1": phi0,
                "future": horizon,
                "prior_forecast_shapley": float(old["forecast_shapley"]),
                "realized_h3": float(old["realized_h3"]),
                "realized_h6": float(old["realized_h6"]),
                "target": float(old["target"]),
                "A": float(old["A"]),
            })

    if not all_rows:
        raise RuntimeError("no joined downstream rows")

    overall = {
        "integrated_vs_realized_h3": metric(all_rows, "integrated_shapley"),
        "prior_forecast_vs_realized_h3": metric(all_rows, "prior_forecast_shapley"),
        "A_vs_established_target": metric(all_rows, "A", "target"),
        "integrated_vs_established_target_secondary": metric(all_rows, "integrated_shapley", "target"),
    }
    folds = {}
    for season in TEST_SEASONS:
        g = [r for r in all_rows if r["season"] == season]
        folds[str(season)] = {
            "integrated": metric(g, "integrated_shapley"),
            "prior": metric(g, "prior_forecast_shapley"),
        }
    groups = summarize_groups(all_rows)
    d10 = deciles(all_rows)
    positive_total = sum(max(0.0, float(r["integrated_shapley"])) for r in all_rows)
    low_cut = quantile([float(r["realized_h3"]) for r in all_rows], .20)
    low_total = sum(max(0.0, float(r["integrated_shapley"])) for r in all_rows if float(r["realized_h3"]) <= low_cut)

    constitution = json.loads(args.constitution_json.read_text())
    constitution_pass = constitution.get("conclusion", "").startswith("A1.") and all(constitution.get("principles", {}).values())
    improvement = overall["prior_forecast_vs_realized_h3"]["mae"] - overall["integrated_vs_realized_h3"]["mae"]

    result = {
        "study": "integrated-forecast-shapley-downstream-v1",
        "frozen_forecast": {"candidate": "I1", "C": C, "source_artifact_status": selected["holdout"]["status"], "holdout_seasons": list(TEST_SEASONS)},
        "frozen_shapley": {"permutations": PERMS, "discount": DISCOUNT, "economic_definition_changed": False, "W_changed": False, "holding_B4_changed": False},
        "evidence_parity": parity_checks,
        "rows_n": len(all_rows),
        "season_diagnostics": season_diag,
        "metrics": overall,
        "folds": folds,
        "groups": groups,
        "realized_h3_deciles": d10,
        "low_realized_bottom20_integrated_share": low_total / positive_total if positive_total else 0.0,
        "mae_improvement_vs_prior_forecast_shapley": improvement,
        "constitution": {"conclusion": constitution.get("conclusion"), "principles": constitution.get("principles"), "pass": constitution_pass, "harness_revision": constitution.get("harness_revision")},
        "current_sanity": {"status": "NOT_RUN_WITH_NAMED_PLAYERS", "reason": "The frozen integrated research model is not yet wired to a governed 2026 current-season football-state adapter. The directive prohibits named-player tuning; no market or owner data were substituted. Historical holdout and temporary-absence safety cohorts remain the governed sanity evidence."},
        "governance": {"market_inputs": False, "owner_inputs": False, "team_utility_inputs": False, "named_player_tuning": False, "production_authority_changed": False},
    }
    (args.output_dir / "integrated_forecast_shapley_downstream_results.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output_dir / "integrated_forecast_shapley_rows.json").write_text(json.dumps(all_rows, indent=2, sort_keys=True))
    print(json.dumps({"rows": len(all_rows), "integrated": overall["integrated_vs_realized_h3"], "prior": overall["prior_forecast_vs_realized_h3"], "improvement": improvement, "constitution": result["constitution"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

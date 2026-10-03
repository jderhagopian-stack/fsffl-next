from __future__ import annotations

"""Deployment-shape verification for the already-frozen QB career-state challenger.

The initial challenger used source-season role statistics, which is correct for an
end-of-season forecast but not for Intrinsic v1 during the active/preseason year.
Production will know the authoritative Y1 Forecast now, while full current-season
role totals do not yet exist.  This check therefore preserves the exact same
binary state, logistic form, features, holdouts and frozen gates, but makes the
role-history fields strictly deployment-shaped: they come from the most recently
completed prior season.  Current source-season production percentile remains the
PIT proxy for the authoritative Y1 Forecast rank used by production.
"""

import argparse
import json
import time
from pathlib import Path

import run_career_persistence_feature_layer_research as study
import run_qb_career_state_intrinsic_v1_research as qb

ROLE_FIELDS = (
    "games_pct",
    "opportunity_pct",
    "role_mean_2",
    "role_vol_2",
    "qb_established_starter_seasons",
)


def features_for(row: study.Row, prior: study.Row | None, horizon: int) -> tuple[float, ...]:
    old = prior.features if prior is not None else {}
    return (
        float(row.age) if row.age is not None else 27.0,
        float(row.experience),
        float(row.features.get("draft_pick_pct", 0.0)),
        float(old.get("games_pct", 0.0)),
        float(old.get("opportunity_pct", 0.0)),
        float(old.get("role_mean_2", 0.0)),
        float(old.get("role_vol_2", 0.0)),
        float(old.get("qb_established_starter_seasons", 0.0)),
        float(row.percentile),
        float(horizon),
    )


def build_examples(rows: list[study.Row], stats: dict[tuple[str, int], dict[str, float]]) -> list[qb.QBExample]:
    qbs = [r for r in rows if r.position == "QB" and r.current > 0]
    row_by_key = {(r.player_id, r.season): r for r in qbs}
    by_season: dict[int, list[study.Row]] = {}
    for row in qbs:
        by_season.setdefault(row.season, []).append(row)
    realized = study.realized_map(rows)
    out: list[qb.QBExample] = []
    for season, season_rows in sorted(by_season.items()):
        elite_cut = qb.percentile([r.current for r in season_rows], 0.75)
        for row in season_rows:
            prior = row_by_key.get((row.player_id, season - 1))
            for horizon in (1, 2):
                target_season = season + horizon
                attempts = study.safe_float(stats.get((row.player_id, target_season), {}).get("attempts"), 0.0)
                out.append(qb.QBExample(
                    player_id=row.player_id,
                    source_season=season,
                    target_season=target_season,
                    horizon=horizon,
                    current_points=row.current,
                    target_points=realized.get((row.player_id, target_season), 0.0),
                    target_starter=1 if attempts >= qb.MEANINGFUL_STARTER_ATTEMPTS else 0,
                    features=features_for(row, prior, horizon),
                    elite=row.current >= elite_cut,
                ))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache = args.output_dir / "cache"
    t0 = time.perf_counter()
    rows = study.build_features(args.career_panel, cache, args.output_dir)
    seasons = sorted({r.season for r in rows})
    stats = study.load_season_stats(list(range(min(seasons), max(seasons) + 3)), cache)
    examples = build_examples(rows, stats)
    result = qb.evaluate(rows, examples)
    result["deployment_shape"] = {
        "role_fields": "most recently completed prior-season values",
        "production_percentile": "current source-season production percentile as PIT proxy for live authoritative Y1 Forecast percentile",
        "age_experience": "current source-season",
        "reason": "match Intrinsic v1 live-time evidence availability; prevents relying on uncompleted current-season role totals",
    }
    result["deployment_operations"] = {
        "derived_rows": len(rows),
        "qb_examples": len(examples),
        "deployment_check_seconds": time.perf_counter() - t0,
    }
    (args.output_dir / "qb_career_state_deployment_results.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "gates", "overall", "elite", "state", "folds", "trajectory", "deployment_operations")}, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

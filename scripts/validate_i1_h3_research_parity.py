from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from fsffl.forecast.integrated_i1 import I1ForecastInput, IntegratedI1Model, STATE_NAMES
from fsffl.state.models import Position

PROB_TOL = 1e-8
PERSISTENCE_TOL = 1e-8
POINT_TOL = 1e-6
RESEARCH_FREEZE_COMMIT = "744952af01140daa0cbdbff9b0683018d4db0e0d"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--usage-panel", type=Path, required=True)
    parser.add_argument("--forecast-freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    here = Path(__file__).parent
    bridge = _load(here / "validate_i1_production_parity_v2.py", "h3_parity_bridge")
    bridge._append_research_only_package_paths(args.research_root)
    validator = _load(here / "validate_i1_production_parity.py", "h3_parity_validator")

    scripts = args.research_root / "scripts"
    ltc = _load(scripts / "run_live_forecast_horizon_research.py", "h3_ltc")
    im = _load(scripts / "run_integrated_multivariate_forecast.py", "h3_im")
    pf = _load(scripts / "run_persistence_first_forecast_calibration.py", "h3_pf")
    prior = _load(scripts / "run_forecast_low_end_career_calibration.py", "h3_prior")
    legacy = _load(scripts / "run_fundamental_intrinsic_residual_calibration.py", "h3_legacy")
    base = _load(scripts / "run_intrinsic_explicit_state_challenge.py", "h3_base")
    evt = _load(scripts / "reconstruct_event_time_absence_cause_evidence.py", "h3_evt")

    freeze = json.loads(args.forecast_freeze.read_text(encoding="utf-8"))
    if freeze.get("disposition") != "LIVE THREE-YEAR COORDINATE VALIDATED":
        raise RuntimeError("frozen research disposition is not the management-selected live coordinate")
    if freeze.get("architecture") != "I1" or abs(float(freeze.get("global_C")) - 0.25) > 1e-15:
        raise RuntimeError("frozen h3 research architecture/C does not match production governance")
    direct = freeze.get("direct_h3", {})
    if not isinstance(direct, dict) or direct.get("recursive") is not False:
        raise RuntimeError("frozen h3 research does not declare direct non-recursive semantics")

    panel = legacy.load_rows(args.career_panel)
    by = {(row.player_id, row.season): row for row in panel}
    usage = pf.load_usage(args.usage_panel)
    ev = pf.source_evidence_map(evt, list(range(2012, 2025)))

    max_probability_diff = 0.0
    max_persistence_diff = 0.0
    max_anticipated_diff = 0.0
    path_mismatches = 0
    evaluated_rows = 0
    fold_rows: list[dict[str, object]] = []

    seasons = tuple(ltc.SELECTION_SEASONS) + (int(ltc.CONFIRMATION_SEASON),)
    for season in seasons:
        bounds = base.fit_state_boundaries(panel, season)
        train = ltc.training_records(im, pf, base, panel, by, season, 3, bounds, usage, ev)
        research_model = im.fitmodel(train, 0.25, "I1")
        direct_prior = im.Prior(train, False)
        production_rows = validator.training_rows_from_research(train, Position)
        if any(row.horizon != 3 for row in production_rows):
            raise AssertionError("direct h3 parity training set contains a non-h3 row")
        production_model = IntegratedI1Model(production_rows)

        fold_count = 0
        for source in panel:
            if source.position not in ltc.POSITIONS or int(source.season) != int(season):
                continue
            truth = pf.target_truth(
                base,
                by,
                ev["roster_year"],
                ev["injury_map"],
                source.player_id,
                season,
                source.position,
                3,
                bounds,
            )
            if not truth["resolved"]:
                continue

            band = base.age_band(source.position, source.age)
            current_state = base.state_for_points(source.points, bounds[source.position])
            previous = by.get((source.player_id, season - 1))
            prior_points = None if previous is None else float(previous.points)
            role = usage.get((source.player_id, season))
            raw_evidence = ev["source"].get((source.player_id, season))
            research_input = {
                "position": source.position,
                "age": band,
                "current": current_state,
                "h": 3,
                "srcpts": float(source.points),
                "prev": prior_points,
                "exp": source.experience,
                "u": role,
                "e": raw_evidence,
            }
            p0 = direct_prior.p(source.position, band, current_state, 3)
            if p0 is None:
                p0 = ltc.empirical_fallback(train, source.position, 3)
            research_probabilities, research_path = im.pred(research_model, research_input, p0)
            research_expected = max(
                0.0,
                float(research_model["means"].exp(research_probabilities, source.position, 3)),
            )

            position = Position(source.position)
            canonical = validator.canonical_evidence(
                source.player_id,
                position,
                source.age,
                source.experience,
                float(source.points),
                prior_points,
                role,
                raw_evidence,
            )
            production = production_model.predict(
                I1ForecastInput(
                    position=position,
                    age_band=band,
                    current_state=current_state,
                    horizon=3,
                    current_points=max(0.0, float(source.points)),
                    prior_points=prior_points,
                    experience_years=(int(source.experience) if source.experience is not None else None),
                    evidence=canonical,
                ),
                fallback_probabilities=p0,
            )

            probability_diff = max(
                abs(float(production.probabilities[state]) - float(research_probabilities[state]))
                for state in STATE_NAMES
            )
            persistence_diff = abs(
                production.persistence_probability - (1.0 - float(research_probabilities["out"]))
            )
            anticipated_diff = abs(production.anticipated_points - research_expected)
            max_probability_diff = max(max_probability_diff, probability_diff)
            max_persistence_diff = max(max_persistence_diff, persistence_diff)
            max_anticipated_diff = max(max_anticipated_diff, anticipated_diff)

            expected_path = (
                "rich" if research_path == "full" else
                "reduced" if research_path == "red" else
                "legacy_fallback"
            )
            if production.evidence_path != expected_path:
                path_mismatches += 1

            evaluated_rows += 1
            fold_count += 1

        fold_rows.append(
            {
                "source_season": int(season),
                "target_season": int(season) + 3,
                "horizon": 3,
                "training_rows": len(train),
                "evaluated_rows": fold_count,
            }
        )

    passed = (
        evaluated_rows > 0
        and max_probability_diff <= PROB_TOL
        and max_persistence_diff <= PERSISTENCE_TOL
        and max_anticipated_diff <= POINT_TOL
        and path_mismatches == 0
    )
    output = {
        "status": "PASS" if passed else "FAIL",
        "research_freeze_commit": RESEARCH_FREEZE_COMMIT,
        "research_disposition": freeze.get("disposition"),
        "architecture": "I1-direct-h3",
        "global_C": 0.25,
        "recursive": False,
        "evaluated_rows": evaluated_rows,
        "max_probability_diff": max_probability_diff,
        "max_persistence_diff": max_persistence_diff,
        "max_anticipated_points_diff": max_anticipated_diff,
        "path_mismatches": path_mismatches,
        "tolerances": {
            "probability": PROB_TOL,
            "persistence": PERSISTENCE_TOL,
            "anticipated_points": POINT_TOL,
        },
        "folds": fold_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

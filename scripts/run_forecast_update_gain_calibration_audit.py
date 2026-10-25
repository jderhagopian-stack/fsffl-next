from __future__ import annotations

import csv
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

MIN_CELL_ROWS = 100
_GAIN_CACHE: dict[tuple[int, int, str, int], dict[str, object]] = {}


def _load_registered(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
_load_registered(HERE / "run_career_calibration.py", "pr131_career_calibration")
audit = _load_registered(
    HERE / "run_forecast_update_reliability_audit.py",
    "pr131_forecast_update_gain_base",
)


def _fit_gain(rows, *, position: str | None = None, horizon: int | None = None):
    subset = [
        r for r in rows
        if (position is None or r["position"] == position)
        and (horizon is None or int(r["horizon_overlap"]) == horizon)
        and abs(float(r["raw_revision"])) > 1e-9
    ]
    denom = sum(float(r["raw_revision"]) ** 2 for r in subset)
    raw = (
        sum(float(r["raw_revision"]) * float(r["needed_revision"]) for r in subset) / denom
        if denom > 0 else 1.0
    )
    # Preserve the Forecast update's direction. Magnitude is empirically estimated;
    # there is deliberately no arbitrary upper cap because the audit may identify
    # underreaction (gain > 1) as well as overreaction (gain < 1).
    return {"n": len(subset), "raw_alpha": raw, "alpha": max(0.0, raw)}


def _rolling_gain(audit_rows, new_fold: int, position_name: str, horizon: int):
    cache_key = (id(audit_rows), new_fold, position_name, horizon)
    cached = _GAIN_CACHE.get(cache_key)
    if cached is not None:
        return cached
    training = [
        r for r in audit_rows
        if int(r["new_fold"]) < new_fold and int(r["target_season"]) <= new_fold - 1
    ]
    cell = _fit_gain(training, position=position_name, horizon=horizon)
    position_fit = _fit_gain(training, position=position_name)
    horizon_fit = _fit_gain(training, horizon=horizon)
    pooled = _fit_gain(training)
    if int(cell["n"]) >= MIN_CELL_ROWS:
        chosen, scope = cell, "position_horizon"
    elif int(position_fit["n"]) >= MIN_CELL_ROWS:
        chosen, scope = position_fit, "position"
    elif int(horizon_fit["n"]) >= MIN_CELL_ROWS:
        chosen, scope = horizon_fit, "horizon"
    else:
        chosen, scope = pooled, "global"
    result = {
        "alpha": float(chosen["alpha"]),
        "raw_alpha": float(chosen["raw_alpha"]),
        "n": int(chosen["n"]),
        "scope": scope,
    }
    _GAIN_CACHE[cache_key] = result
    return result


def _annotate(audit_rows):
    for row in audit_rows:
        fit = _rolling_gain(
            audit_rows,
            int(row["new_fold"]),
            str(row["position"]),
            int(row["horizon_overlap"]),
        )
        repaired = fit["alpha"] * float(row["raw_revision"])
        row["repair_alpha"] = fit["alpha"]
        row["repair_alpha_raw_estimate"] = fit["raw_alpha"]
        row["repair_training_n"] = fit["n"]
        row["repair_scope"] = fit["scope"]
        row["repaired_revision"] = repaired
        row["repaired_forecast_mean"] = float(row["old_forecast_mean"]) + repaired
        row["repaired_revision_magnitude_error"] = abs(repaired - float(row["needed_revision"]))
        row["repaired_revision_direction_correct"] = (
            audit.sign(repaired) == audit.sign(float(row["needed_revision"]))
            and audit.sign(repaired) != 0
        )


def _repaired_paths(base, seasons, raw_paths, audit_rows):
    result = {}
    for season in seasons:
        season_paths = {offset: list(states) for offset, states in raw_paths[season].items()}
        prior = season - 1
        if prior not in raw_paths:
            result[season] = season_paths
            continue
        for offset in (0, 1):
            prior_offset = offset + 1
            if offset not in season_paths or prior_offset not in raw_paths[prior]:
                continue
            anchors = {s.player_id: s for s in raw_paths[prior][prior_offset]}
            adjusted = []
            for state in season_paths[offset]:
                anchor = anchors.get(state.player_id)
                if anchor is None:
                    adjusted.append(state)
                    continue
                fit = _rolling_gain(audit_rows, season, state.position, offset)
                adjusted_mean = anchor.mean + fit["alpha"] * (state.mean - anchor.mean)
                adjusted.append(replace(state, mean=max(0.0, adjusted_mean)))
            season_paths[offset] = base.assign_percentiles(adjusted)
        result[season] = season_paths
    return result


def _tier(percentile: float) -> str:
    # The source panel carries quartile-midpoint percentiles for observed states,
    # while recursively forecast states carry continuous within-position ranks.
    # Quartile-aligned bands keep the classification comparable across both.
    if percentile >= 0.75:
        return "elite_tail"
    if percentile >= 0.25:
        return "middle"
    return "replacement_tail"


def _report_gains(output_dir: Path):
    rows_path = output_dir / "forecast_update_reliability_rows.csv"
    results_path = output_dir / "forecast_update_reliability_results.json"
    report_path = output_dir / "forecast_update_reliability_report.md"
    with rows_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("new_fold", "target_season", "horizon_overlap", "repair_training_n"):
            row[key] = int(float(row[key]))
        for key in ("raw_revision", "needed_revision", "repair_alpha", "repair_alpha_raw_estimate"):
            row[key] = float(row[key])
    final_fold = max(int(r["new_fold"]) for r in rows)
    table = {}
    for position_name in ("QB", "RB", "WR", "TE"):
        table[position_name] = {
            str(h): _rolling_gain(rows, final_fold, position_name, h)
            for h in (0, 1)
        }
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    payload["forecast_update_audit"]["rolling_gain_by_position_horizon_at_final_fold"] = table
    payload["forecast_update_audit"]["repair_interpretation"] = (
        "PIT position-by-shared-horizon gain calibration; gain may exceed 1 when prior resolved evidence supports underreaction."
    )
    results_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["", "## Final-fold position × shared-horizon gain calibration", ""]
    for position_name in ("QB", "RB", "WR", "TE"):
        for h in (0, 1):
            fit = table[position_name][str(h)]
            lines.append(
                f"- {position_name}, shared horizon {h}: gain={fit['alpha']:.3f} "
                f"(raw={fit['raw_alpha']:.3f}, n={fit['n']}, scope={fit['scope']})"
            )
    report_path.write_text(report_path.read_text(encoding="utf-8") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


# Replace only the research-audit calibration hooks. Production Forecast is untouched.
audit.tier = _tier
audit.annotate_repaired_revisions = _annotate
audit.repaired_paths = _repaired_paths


if __name__ == "__main__":
    audit.main()
    # argparse is owned by the imported audit; retrieve its required output path
    # directly from argv without changing its CLI contract.
    output_dir = None
    for i, arg in enumerate(sys.argv[:-1]):
        if arg == "--output-dir":
            output_dir = Path(sys.argv[i + 1])
            break
    if output_dir is not None:
        _report_gains(output_dir)

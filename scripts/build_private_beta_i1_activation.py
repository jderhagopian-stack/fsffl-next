from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import urllib.request
from datetime import date
from pathlib import Path

import nflreadpy as nfl
import pandas as pd

from fsffl.forecast.i1_artifact import FrozenI1Artifact, freeze_i1_model
from fsffl.forecast.i1_current_facts import I1_CURRENT_FACTS_SCHEMA_VERSION
from fsffl.forecast.integrated_i1 import I1ForecastInput, IntegratedI1Model
from fsffl.state.models import Position

POSITIONS = ("QB", "RB", "WR", "TE")
FROZEN_SOURCE_MAX = 2022
H3_SOURCE_MAX = 2021
CURRENT_SOURCE_URL = "nflverse:nflreadpy+Sleeper"
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _pandas(frame):
    if hasattr(frame, "to_pandas"):
        return frame.to_pandas()
    if isinstance(frame, pd.DataFrame):
        return frame
    return pd.DataFrame(frame)


def _col(frame: pd.DataFrame, *names: str, required: bool = True) -> str | None:
    for name in names:
        if name in frame.columns:
            return name
    if required:
        raise RuntimeError(f"missing expected column {names}; available={list(frame.columns)}")
    return None


def _final_records(*, panel, by, usage, ev, base, pf, bounds, horizons, source_max):
    rows = []
    for x in panel:
        if x.position not in POSITIONS or x.season < 2012 or x.season > source_max:
            continue
        current = base.state_for_points(x.points, bounds[x.position])
        band = base.age_band(x.position, x.age)
        previous = by.get((x.player_id, x.season - 1))
        prior_points = None if previous is None else float(previous.points)
        source_ev = ev["source"].get((x.player_id, x.season))
        for horizon in horizons:
            target_season = x.season + horizon
            if target_season > 2024:
                continue
            truth = pf.target_truth(
                base, by, ev["roster_year"], ev["injury_map"], x.player_id,
                x.season, x.position, horizon, bounds,
            )
            if not truth["resolved"]:
                continue
            target = by.get((x.player_id, target_season))
            rows.append({
                "position": x.position,
                "age": band,
                "current": current,
                "h": horizon,
                "points": max(0.0, float(target.points)) if target is not None else 0.0,
                "srcpts": max(0.0, float(x.points)),
                "prev": prior_points,
                "exp": x.experience,
                "u": usage.get((x.player_id, x.season)),
                "e": source_ev,
                "cov": bool(source_ev and float(source_ev.get("roster_weeks", 0) or 0) > 0),
                "persist": int(truth["persist"]),
                "state": truth["state"],
            })
    return rows


def _roundtrip_check(model: IntegratedI1Model, artifact: FrozenI1Artifact, training_rows) -> dict[str, float | int]:
    max_prob = 0.0
    max_points = 0.0
    sampled = 0
    stride = max(1, len(training_rows) // 500)
    for row in training_rows[::stride]:
        item = I1ForecastInput(
            position=row.position,
            age_band=row.age_band,
            current_state=row.current_state,
            horizon=row.horizon,
            current_points=row.current_points,
            prior_points=row.prior_points,
            experience_years=row.experience_years,
            evidence=row.evidence,
        )
        try:
            expected = model.predict(item)
            actual = artifact.predict(item)
        except ValueError:
            continue
        max_prob = max(max_prob, max(
            abs(float(expected.probabilities[k]) - float(actual.probabilities[k]))
            for k in expected.probabilities
        ))
        max_points = max(max_points, abs(expected.anticipated_points - actual.anticipated_points))
        sampled += 1
    if sampled < 1 or max_prob > 1e-10 or max_points > 1e-8:
        raise RuntimeError(
            f"frozen artifact roundtrip failed: sampled={sampled} max_prob={max_prob} max_points={max_points}"
        )
    return {"sampled": sampled, "max_probability_diff": max_prob, "max_anticipated_points_diff": max_points}


def _sleepers() -> dict[str, dict]:
    request = urllib.request.Request(
        SLEEPER_PLAYERS_URL,
        headers={"User-Agent": "fsffl-next-private-beta-activation/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = json.loads(response.read().decode("utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("Sleeper current player universe was not a mapping")
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _source_age(birth_date, source_season: int):
    if birth_date is None or pd.isna(birth_date):
        return None
    try:
        born = pd.to_datetime(birth_date).date()
    except Exception:
        return None
    return max(0.0, (date(source_season, 9, 1) - born).days / 365.2425)


def _build_current_facts(*, career_csv: Path, base, bounds, evaluation_season: int):
    source_season = evaluation_season - 1
    prior_season = source_season - 1

    reg = _pandas(nfl.load_player_stats([2020, 2021, 2022, prior_season, source_season], summary_level="reg"))
    weekly = _pandas(nfl.load_player_stats([source_season], summary_level="week"))
    players = _pandas(nfl.load_players())
    rosters = _pandas(nfl.load_rosters([source_season]))
    sleeper = _sleepers()

    pid = _col(reg, "player_id", "gsis_id")
    season_col = _col(reg, "season")
    points_col = _col(reg, "fantasy_points", "fantasyPoints")
    position_col = _col(reg, "position_group", "position")
    reg = reg[reg[position_col].astype(str).isin(POSITIONS)].copy()

    career = pd.read_csv(career_csv)
    frozen = career[career["season"].isin([2020, 2021, 2022])][["player_id", "season", "fantasy_points"]].copy()
    current = reg[reg[season_col].isin([2020, 2021, 2022])][[pid, season_col, points_col]].copy()
    current.columns = ["player_id", "season", "candidate_points"]
    compare = frozen.merge(current, on=["player_id", "season"], how="inner")
    if compare.empty:
        raise RuntimeError("no overlapping rows to validate completed-source fantasy-points coordinate")
    compare["abs_diff"] = (compare["fantasy_points"] - compare["candidate_points"]).abs()
    max_diff = float(compare["abs_diff"].max())
    mean_diff = float(compare["abs_diff"].mean())
    if max_diff > 1e-6:
        raise RuntimeError(
            f"nflreadpy fantasy_points does not reproduce frozen research coordinate: max_diff={max_diff}"
        )

    source_rows = reg[reg[season_col] == source_season].copy()
    prior_rows = reg[reg[season_col] == prior_season].copy()
    source_by = {str(r[pid]): r for _, r in source_rows.iterrows() if pd.notna(r[pid])}
    prior_by = {str(r[pid]): float(r[points_col]) for _, r in prior_rows.iterrows() if pd.notna(r[pid])}

    w_pid = _col(weekly, "player_id", "gsis_id")
    w_pos = _col(weekly, "position_group", "position")
    w_attempts = _col(weekly, "attempts", "passing_attempts", required=False)
    w_carries = _col(weekly, "carries", "rushing_attempts", required=False)
    w_targets = _col(weekly, "targets", required=False)
    weekly = weekly[weekly[w_pos].astype(str).isin(POSITIONS)].copy()
    role: dict[str, tuple[float, float]] = {}
    for player_id, group in weekly.groupby(w_pid):
        position = str(group.iloc[0][w_pos])
        games = float(len(group))
        if position == "QB":
            total = float(group[w_attempts].fillna(0).sum()) if w_attempts else 0.0
        elif position == "RB":
            total = (
                (float(group[w_carries].fillna(0).sum()) if w_carries else 0.0)
                + (float(group[w_targets].fillna(0).sum()) if w_targets else 0.0)
            )
        else:
            total = float(group[w_targets].fillna(0).sum()) if w_targets else 0.0
        role[str(player_id)] = (games, total / games if games > 0 else 0.0)

    median_by_pos: dict[str, float] = {}
    for pos in POSITIONS:
        vals = []
        for player_id, (games, opg) in role.items():
            row = source_by.get(player_id)
            if games > 0 and row is not None and str(row[position_col]) == pos:
                vals.append(opg)
        median_by_pos[pos] = float(pd.Series(vals).median()) if vals else 0.0

    p_id = _col(players, "gsis_id", "player_id")
    p_birth = _col(players, "birth_date", "birthdate", required=False)
    p_rookie = _col(players, "rookie_season", "entry_year", "draft_year", required=False)
    player_by = {str(r[p_id]): r for _, r in players.iterrows() if pd.notna(r[p_id])}

    r_id = _col(rosters, "gsis_id", "gsis_it", "player_id")
    roster_ids = {str(v) for v in rosters[r_id].dropna().astype(str)}

    rows = []
    counts = {"stats": 0, "roster_zero": 0, "rookie_zero": 0, "unsupported": 0}
    for sleeper_id, raw in sorted(sleeper.items()):
        position = str(raw.get("position") or "").upper()
        team = raw.get("team")
        if position not in POSITIONS or not team:
            continue
        gsis = str(raw.get("gsis_id") or "").strip()
        display_name = str(
            raw.get("full_name")
            or " ".join(filter(None, (raw.get("first_name"), raw.get("last_name"))))
            or sleeper_id
        ).strip()
        source = source_by.get(gsis) if gsis else None
        identity = player_by.get(gsis) if gsis else None
        rookie_season = None
        if identity is not None and p_rookie and pd.notna(identity[p_rookie]):
            try:
                rookie_season = int(identity[p_rookie])
            except (TypeError, ValueError):
                rookie_season = None
        if rookie_season is None and raw.get("years_exp") == 0:
            rookie_season = evaluation_season

        games = opportunity = None
        role_band = None
        if source is not None:
            points = max(0.0, float(source[points_col]))
            counts["stats"] += 1
            if gsis in role:
                games, opportunity = role[gsis]
                role_band = "weak" if opportunity < median_by_pos.get(position, 0.0) else "established"
        elif gsis and gsis in roster_ids:
            points = 0.0
            games, opportunity, role_band = 0.0, 0.0, "weak"
            counts["roster_zero"] += 1
        elif rookie_season is not None and rookie_season >= evaluation_season:
            points = 0.0
            counts["rookie_zero"] += 1
        else:
            counts["unsupported"] += 1
            continue

        birth = identity[p_birth] if identity is not None and p_birth else None
        age = _source_age(birth, source_season)
        experience = max(0, source_season - rookie_season) if rookie_season is not None else None
        prior = prior_by.get(gsis) if gsis else None
        current_state = base.state_for_points(points, bounds[position])
        rows.append({
            "source_player_id": f"sleeper:{sleeper_id}",
            "display_name": display_name,
            "position": position,
            "source_season": source_season,
            "current_fantasy_points": points,
            "prior_fantasy_points": prior,
            "age_years": age,
            "experience_years": experience,
            "current_state": current_state,
            "games": games,
            "opportunity_per_game": opportunity,
            "role_band": role_band,
            "source_version": f"private-beta-completed-source-{source_season}-v1",
            "identity_provider": "sleeper",
            "identity_external_id": sleeper_id,
        })

    artifact = {
        "schema_version": I1_CURRENT_FACTS_SCHEMA_VERSION,
        "evaluation_season": evaluation_season,
        "completed_source_season": source_season,
        "source_season_complete": True,
        "state_boundary_version": "i1-final-boundaries-source-2012-2022-v1",
        "source_version": f"private-beta-completed-source-{source_season}-v1",
        "rows": rows,
        "metadata": {
            "providers": ["nflverse/nflreadpy", "Sleeper"],
            "provider_neutral_contract": True,
            "research_coordinate_validation": {
                "overlap_rows": int(len(compare)),
                "max_abs_fantasy_points_diff": max_diff,
                "mean_abs_fantasy_points_diff": mean_diff,
                "seasons": [2020, 2021, 2022],
            },
            "coverage_policy": {
                "roster_continuity": False,
                "injury_practice": False,
                "participation_snaps": False,
                "role_opportunity": True,
                "rich_path_authorized": False,
                "reduced_path_authorized": True,
            },
            "zero_fact_basis_counts": counts,
            "rights_classification": "acceptable_for_beta_but_must_be_replaced_or_cleared_before_commercial_launch",
            "source_note": CURRENT_SOURCE_URL,
        },
    }
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--usage-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evaluation-season", type=int, default=2026)
    args = parser.parse_args()

    root = Path(__file__).parent
    bridge = _load(root / "validate_i1_production_parity_v2.py", "activation_bridge")
    bridge._append_research_only_package_paths(args.research_root)
    validator = _load(root / "validate_i1_production_parity.py", "activation_validator")

    rs = args.research_root / "scripts"
    pf = _load(rs / "run_persistence_first_forecast_calibration.py", "activation_pf")
    legacy = _load(rs / "run_fundamental_intrinsic_residual_calibration.py", "activation_legacy")
    base = _load(rs / "run_intrinsic_explicit_state_challenge.py", "activation_base")
    evt = _load(rs / "reconstruct_event_time_absence_cause_evidence.py", "activation_evt")

    panel = legacy.load_rows(args.career_panel)
    by = {(row.player_id, row.season): row for row in panel}
    usage = pf.load_usage(args.usage_panel)
    ev = pf.source_evidence_map(evt, list(range(2012, 2025)))
    bounds = base.fit_state_boundaries(panel, FROZEN_SOURCE_MAX + 1)

    records_h12 = _final_records(
        panel=panel, by=by, usage=usage, ev=ev, base=base, pf=pf,
        bounds=bounds, horizons=(1, 2), source_max=FROZEN_SOURCE_MAX,
    )
    records_h3 = _final_records(
        panel=panel, by=by, usage=usage, ev=ev, base=base, pf=pf,
        bounds=bounds, horizons=(3,), source_max=H3_SOURCE_MAX,
    )
    rows_h12 = validator.training_rows_from_research(records_h12, Position)
    rows_h3 = validator.training_rows_from_research(records_h3, Position)
    model_h12 = IntegratedI1Model(rows_h12)
    model_h3 = IntegratedI1Model(rows_h3)
    artifact_h12 = freeze_i1_model(
        model_h12,
        metadata={"fit": "final-h1-h2", "source_season_max": FROZEN_SOURCE_MAX, "training_rows": len(rows_h12)},
    )
    artifact_h3 = freeze_i1_model(
        model_h3,
        metadata={"fit": "final-direct-h3", "source_season_max": H3_SOURCE_MAX, "training_rows": len(rows_h3), "recursive": False},
    )
    checks = {
        "h1_h2": _roundtrip_check(model_h12, artifact_h12, rows_h12),
        "h3": _roundtrip_check(model_h3, artifact_h3, rows_h3),
    }
    current = _build_current_facts(
        career_csv=args.career_panel,
        base=base,
        bounds=bounds,
        evaluation_season=args.evaluation_season,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_h12.dump(args.output_dir / "frozen_i1_h12.json")
    artifact_h3.dump(args.output_dir / "frozen_i1_h3.json")
    (args.output_dir / "current_i1_facts_2026.json").write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = {
        "status": "PASS",
        "evaluation_season": args.evaluation_season,
        "completed_source_season": args.evaluation_season - 1,
        "training_rows": {"h1_h2": len(rows_h12), "h3": len(rows_h3)},
        "artifact_roundtrip": checks,
        "current_fact_rows": len(current["rows"]),
        "current_fact_metadata": current["metadata"],
        "model_changes": False,
        "reduced_path_authorized": True,
    }
    (args.output_dir / "private_beta_activation_build_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
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
CURRENT_SOURCE_COORDINATE = (
    "Fantasy-Football-Analytics-Textbook/player_stats_seasonal.RData"
    "+nflverse/nflreadpy+Sleeper"
)
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


def _normalize_name(value: object) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", "", str(value or "").lower()).split())


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
                base,
                by,
                ev["roster_year"],
                ev["injury_map"],
                x.player_id,
                x.season,
                x.position,
                horizon,
                bounds,
            )
            if not truth["resolved"]:
                continue
            target = by.get((x.player_id, target_season))
            rows.append(
                {
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
                }
            )
    return rows


def _roundtrip_check(
    model: IntegratedI1Model,
    artifact: FrozenI1Artifact,
    training_rows,
) -> dict[str, float | int]:
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
        max_prob = max(
            max_prob,
            max(
                abs(float(expected.probabilities[k]) - float(actual.probabilities[k]))
                for k in expected.probabilities
            ),
        )
        max_points = max(
            max_points,
            abs(expected.anticipated_points - actual.anticipated_points),
        )
        sampled += 1
    if sampled < 1 or max_prob > 1e-10 or max_points > 1e-8:
        raise RuntimeError(
            "frozen artifact roundtrip failed: "
            f"sampled={sampled} max_prob={max_prob} max_points={max_points}"
        )
    return {
        "sampled": sampled,
        "max_probability_diff": max_prob,
        "max_anticipated_points_diff": max_points,
    }


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


def _load_frozen_coordinate_points(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"player_id", "season", "position", "fantasy_points"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"frozen-coordinate source is missing columns: {missing}")
    columns = ["player_id", "season", "position", "fantasy_points"]
    if "display_name" in frame.columns:
        columns.insert(1, "display_name")
    frame = frame[columns].copy()
    if "display_name" not in frame.columns:
        frame["display_name"] = ""
    frame["player_id"] = frame["player_id"].astype(str).str.strip()
    frame["display_name"] = frame["display_name"].fillna("").astype(str).str.strip()
    frame["season"] = pd.to_numeric(frame["season"], errors="raise").astype(int)
    frame["position"] = frame["position"].astype(str).str.upper()
    frame["fantasy_points"] = pd.to_numeric(frame["fantasy_points"], errors="raise")
    frame = frame[
        frame["player_id"].ne("")
        & frame["position"].isin(POSITIONS)
        & frame["fantasy_points"].notna()
    ].copy()
    duplicate = frame.duplicated(["player_id", "season"], keep=False)
    if duplicate.any():
        sample = frame.loc[duplicate, ["player_id", "season"]].head(10).to_dict("records")
        raise RuntimeError(f"duplicate frozen-coordinate player-season rows: {sample}")
    return frame


def _coordinate_validation(
    *,
    career_csv: Path,
    source_points: pd.DataFrame,
    runtime_stats: pd.DataFrame,
) -> tuple[dict[str, object], dict[str, object]]:
    seasons = [2020, 2021, 2022]
    career = pd.read_csv(career_csv)
    frozen = career[career["season"].isin(seasons)][
        ["player_id", "season", "position", "fantasy_points"]
    ].copy()
    candidate = source_points[source_points["season"].isin(seasons)][
        ["player_id", "season", "position", "fantasy_points"]
    ].copy()
    frozen["player_id"] = frozen["player_id"].astype(str)
    candidate["player_id"] = candidate["player_id"].astype(str)
    frozen_keys = set(zip(frozen["player_id"], frozen["season"], frozen["position"]))
    candidate_keys = set(zip(candidate["player_id"], candidate["season"], candidate["position"]))
    if frozen_keys != candidate_keys:
        missing = sorted(frozen_keys - candidate_keys)[:10]
        extra = sorted(candidate_keys - frozen_keys)[:10]
        raise RuntimeError(
            "frozen completed-source coordinate does not reproduce research row coverage: "
            f"missing={missing}; extra={extra}"
        )
    compare = frozen.merge(
        candidate,
        on=["player_id", "season", "position"],
        how="inner",
        suffixes=("_research", "_source"),
    )
    compare["abs_diff"] = (
        compare["fantasy_points_research"] - compare["fantasy_points_source"]
    ).abs()
    max_diff = float(compare["abs_diff"].max()) if not compare.empty else math.inf
    mean_diff = float(compare["abs_diff"].mean()) if not compare.empty else math.inf
    if len(compare) != len(frozen) or max_diff > 1e-12:
        raise RuntimeError(
            "frozen completed-source scoring coordinate failed exact research parity: "
            f"rows={len(compare)}/{len(frozen)} max_diff={max_diff}"
        )
    exact = {
        "source": "Fantasy-Football-Analytics-Textbook/player_stats_seasonal.RData",
        "rows": int(len(compare)),
        "expected_rows": int(len(frozen)),
        "max_abs_fantasy_points_diff": max_diff,
        "mean_abs_fantasy_points_diff": mean_diff,
        "seasons": seasons,
        "acceptance_tolerance": 1e-12,
        "status": "PASS",
    }

    pid = _col(runtime_stats, "player_id", "gsis_id")
    season_col = _col(runtime_stats, "season")
    points_col = _col(runtime_stats, "fantasy_points", "fantasyPoints")
    runtime = runtime_stats[runtime_stats[season_col].isin(seasons)][
        [pid, season_col, points_col]
    ].copy()
    runtime.columns = ["player_id", "season", "runtime_points"]
    runtime["player_id"] = runtime["player_id"].astype(str)
    audit = candidate[["player_id", "season", "fantasy_points"]].merge(
        runtime,
        on=["player_id", "season"],
        how="inner",
    )
    if audit.empty:
        drift = {
            "source": "current nflverse/nflreadpy",
            "overlap_rows": 0,
            "max_abs_fantasy_points_diff": None,
            "mean_abs_fantasy_points_diff": None,
            "acceptance_gate": False,
        }
    else:
        audit["abs_diff"] = (audit["fantasy_points"] - audit["runtime_points"]).abs()
        drift = {
            "source": "current nflverse/nflreadpy",
            "overlap_rows": int(len(audit)),
            "max_abs_fantasy_points_diff": float(audit["abs_diff"].max()),
            "mean_abs_fantasy_points_diff": float(audit["abs_diff"].mean()),
            "acceptance_gate": False,
            "note": (
                "Audit only. Current nflverse stat corrections may differ from the frozen "
                "research data vintage and are not substituted for the governed research coordinate."
            ),
        }
    return exact, drift


def _build_current_facts(
    *,
    career_csv: Path,
    source_points_csv: Path,
    base,
    bounds,
    evaluation_season: int,
):
    source_season = evaluation_season - 1
    prior_season = source_season - 1

    source_points = _load_frozen_coordinate_points(source_points_csv)
    if not (source_points["season"] == source_season).any():
        raise RuntimeError(
            f"frozen completed-source coordinate has no rows for completed season {source_season}"
        )

    reg = _pandas(
        nfl.load_player_stats(
            [2020, 2021, 2022, prior_season, source_season],
            summary_level="reg",
        )
    )
    weekly = _pandas(nfl.load_player_stats([source_season], summary_level="week"))
    players = _pandas(nfl.load_players())
    rosters = _pandas(nfl.load_rosters([source_season]))
    sleeper = _sleepers()

    position_col = _col(reg, "position_group", "position")
    reg = reg[reg[position_col].astype(str).isin(POSITIONS)].copy()
    coordinate_validation, runtime_drift_audit = _coordinate_validation(
        career_csv=career_csv,
        source_points=source_points,
        runtime_stats=reg,
    )

    source_rows = source_points[source_points["season"] == source_season].copy()
    prior_rows = source_points[source_points["season"] == prior_season].copy()
    source_by = {
        str(row["player_id"]): row
        for _, row in source_rows.iterrows()
        if pd.notna(row["player_id"])
    }
    prior_by = {
        str(row["player_id"]): float(row["fantasy_points"])
        for _, row in prior_rows.iterrows()
        if pd.notna(row["player_id"])
    }
    source_by_name_position: dict[tuple[str, str], list[pd.Series]] = {}
    for _, row in source_rows.iterrows():
        normalized = _normalize_name(row.get("display_name", ""))
        position = str(row["position"])
        if normalized:
            source_by_name_position.setdefault((normalized, position), []).append(row)

    current_sleeper_rows: list[tuple[str, dict, str, str, str]] = []
    current_name_counts: dict[tuple[str, str], int] = {}
    current_gsis_counts: dict[str, int] = {}
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
        normalized = _normalize_name(display_name)
        current_sleeper_rows.append((sleeper_id, raw, position, gsis, display_name))
        if normalized:
            key = (normalized, position)
            current_name_counts[key] = current_name_counts.get(key, 0) + 1
        if gsis:
            current_gsis_counts[gsis] = current_gsis_counts.get(gsis, 0) + 1

    w_pid = _col(weekly, "player_id", "gsis_id")
    w_pos = _col(weekly, "position_group", "position")
    w_attempts = _col(weekly, "attempts", "passing_attempts", required=False)
    w_carries = _col(weekly, "carries", "rushing_attempts", required=False)
    w_targets = _col(weekly, "targets", required=False)
    weekly = weekly[weekly[w_pos].astype(str).isin(POSITIONS)].copy()
    role: dict[str, tuple[str, float, float]] = {}
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
        role[str(player_id)] = (position, games, total / games if games > 0 else 0.0)

    median_by_pos: dict[str, float] = {}
    for pos in POSITIONS:
        vals = []
        for player_id, (role_position, games, opg) in role.items():
            row = source_by.get(player_id)
            if (
                games > 0
                and row is not None
                and str(row["position"]) == pos
                and role_position == pos
            ):
                vals.append(opg)
        median_by_pos[pos] = float(pd.Series(vals).median()) if vals else 0.0

    p_id = _col(players, "gsis_id", "player_id")
    p_birth = _col(players, "birth_date", "birthdate", required=False)
    p_rookie = _col(
        players,
        "rookie_season",
        "entry_year",
        "draft_year",
        required=False,
    )
    player_by = {
        str(row[p_id]): row
        for _, row in players.iterrows()
        if pd.notna(row[p_id])
    }

    r_id = _col(rosters, "gsis_id", "gsis_it", "player_id")
    roster_ids = {str(value) for value in rosters[r_id].dropna().astype(str)}

    rows = []
    counts = {
        "frozen_coordinate_stats": 0,
        "roster_zero": 0,
        "rookie_zero": 0,
        "unsupported": 0,
    }
    identity_resolution = {
        "direct_unique_gsis": 0,
        "unique_name_position_fallback": 0,
        "ambiguous_name_position": 0,
        "ambiguous_gsis": 0,
        "source_stat_rows": int(len(source_rows)),
        "source_stat_rows_with_display_name": int(source_rows["display_name"].astype(str).str.strip().ne("").sum()),
    }
    used_source_ids: set[str] = set()
    source_version = f"private-beta-completed-source-{source_season}-frozen-coordinate-v3"
    for sleeper_id, raw, position, gsis, display_name in current_sleeper_rows:
        normalized = _normalize_name(display_name)
        source = None
        resolution = None
        if gsis and current_gsis_counts.get(gsis, 0) == 1:
            direct = source_by.get(gsis)
            if direct is not None and str(direct["position"]) == position:
                source = direct
                resolution = "direct_unique_gsis"
        elif gsis and current_gsis_counts.get(gsis, 0) > 1:
            identity_resolution["ambiguous_gsis"] += 1

        if source is None and normalized:
            key = (normalized, position)
            candidates = source_by_name_position.get(key, [])
            if current_name_counts.get(key, 0) == 1 and len(candidates) == 1:
                source = candidates[0]
                resolution = "unique_name_position_fallback"
            elif candidates and (current_name_counts.get(key, 0) != 1 or len(candidates) != 1):
                identity_resolution["ambiguous_name_position"] += 1

        source_key = str(source["player_id"]) if source is not None else None
        if source_key and source_key in used_source_ids:
            source = None
            source_key = None
            resolution = None
            identity_resolution["ambiguous_name_position"] += 1

        identity = player_by.get(gsis) if gsis else None
        if identity is None and source_key:
            identity = player_by.get(source_key)
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
            points = max(0.0, float(source["fantasy_points"]))
            counts["frozen_coordinate_stats"] += 1
            if resolution:
                identity_resolution[resolution] += 1
            if source_key:
                used_source_ids.add(source_key)
            role_id = None
            if gsis and gsis in role:
                role_id = gsis
            elif source_key and source_key in role:
                role_id = source_key
            if role_id is not None:
                role_position, games, opportunity = role[role_id]
                if role_position == position:
                    role_band = (
                        "weak"
                        if opportunity < median_by_pos.get(position, 0.0)
                        else "established"
                    )
                else:
                    games = opportunity = None
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
        experience = (
            max(0, source_season - rookie_season)
            if rookie_season is not None
            else None
        )
        prior_raw = prior_by.get(source_key) if source_key else None
        prior = None if prior_raw is None else max(0.0, float(prior_raw))
        current_state = base.state_for_points(points, bounds[position])
        rows.append(
            {
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
                "source_version": source_version,
                "identity_provider": "sleeper",
                "identity_external_id": sleeper_id,
            }
        )

    identity_resolution["unique_source_stat_rows_used"] = len(used_source_ids)
    identity_resolution["source_stat_rows_not_in_current_universe"] = max(0, len(source_rows) - len(used_source_ids))
    identity_resolution["current_team_assigned_skill_players"] = len(current_sleeper_rows)

    artifact = {
        "schema_version": I1_CURRENT_FACTS_SCHEMA_VERSION,
        "evaluation_season": evaluation_season,
        "completed_source_season": source_season,
        "source_season_complete": True,
        "state_boundary_version": "i1-final-boundaries-source-2012-2022-v1",
        "source_version": source_version,
        "rows": rows,
        "metadata": {
            "providers": [
                "Fantasy-Football-Analytics-Textbook/player_stats_seasonal.RData",
                "nflverse/nflreadpy",
                "Sleeper",
            ],
            "provider_neutral_contract": True,
            "research_coordinate_validation": coordinate_validation,
            "secondary_source_drift_audit": runtime_drift_audit,
            "identity_resolution": identity_resolution,
            "scoring_coordinate": (
                "frozen research fantasyPoints coordinate; standard/non-PPR semantics; "
                "current nflverse revisions retained only as a non-authoritative drift audit"
            ),
            "coverage_policy": {
                "roster_continuity": False,
                "injury_practice": False,
                "participation_snaps": False,
                "role_opportunity": True,
                "rich_path_authorized": False,
                "reduced_path_authorized": True,
            },
            "zero_fact_basis_counts": counts,
            "rights_classification": (
                "acceptable_for_beta_but_must_be_replaced_or_cleared_before_commercial_launch"
            ),
            "source_note": CURRENT_SOURCE_COORDINATE,
        },
    }
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--usage-panel", type=Path, required=True)
    parser.add_argument("--source-points-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evaluation-season", type=int, default=2026)
    args = parser.parse_args()

    root = Path(__file__).parent
    bridge = _load(root / "validate_i1_production_parity_v2.py", "activation_bridge")
    bridge._append_research_only_package_paths(args.research_root)
    validator = _load(root / "validate_i1_production_parity.py", "activation_validator")

    rs = args.research_root / "scripts"
    pf = _load(
        rs / "run_persistence_first_forecast_calibration.py",
        "activation_pf",
    )
    legacy = _load(
        rs / "run_fundamental_intrinsic_residual_calibration.py",
        "activation_legacy",
    )
    base = _load(
        rs / "run_intrinsic_explicit_state_challenge.py",
        "activation_base",
    )
    evt = _load(
        rs / "reconstruct_event_time_absence_cause_evidence.py",
        "activation_evt",
    )

    panel = legacy.load_rows(args.career_panel)
    by = {(row.player_id, row.season): row for row in panel}
    usage = pf.load_usage(args.usage_panel)
    ev = pf.source_evidence_map(evt, list(range(2012, 2025)))
    bounds = base.fit_state_boundaries(panel, FROZEN_SOURCE_MAX + 1)

    records_h12 = _final_records(
        panel=panel,
        by=by,
        usage=usage,
        ev=ev,
        base=base,
        pf=pf,
        bounds=bounds,
        horizons=(1, 2),
        source_max=FROZEN_SOURCE_MAX,
    )
    records_h3 = _final_records(
        panel=panel,
        by=by,
        usage=usage,
        ev=ev,
        base=base,
        pf=pf,
        bounds=bounds,
        horizons=(3,),
        source_max=H3_SOURCE_MAX,
    )
    rows_h12 = validator.training_rows_from_research(records_h12, Position)
    rows_h3 = validator.training_rows_from_research(records_h3, Position)
    model_h12 = IntegratedI1Model(rows_h12)
    model_h3 = IntegratedI1Model(rows_h3)
    artifact_h12 = freeze_i1_model(
        model_h12,
        metadata={
            "fit": "final-h1-h2",
            "source_season_max": FROZEN_SOURCE_MAX,
            "training_rows": len(rows_h12),
        },
    )
    artifact_h3 = freeze_i1_model(
        model_h3,
        metadata={
            "fit": "final-direct-h3",
            "source_season_max": H3_SOURCE_MAX,
            "training_rows": len(rows_h3),
            "recursive": False,
        },
    )
    checks = {
        "h1_h2": _roundtrip_check(model_h12, artifact_h12, rows_h12),
        "h3": _roundtrip_check(model_h3, artifact_h3, rows_h3),
    }
    current = _build_current_facts(
        career_csv=args.career_panel,
        source_points_csv=args.source_points_csv,
        base=base,
        bounds=bounds,
        evaluation_season=args.evaluation_season,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_h12.dump(args.output_dir / "frozen_i1_h12.json")
    artifact_h3.dump(args.output_dir / "frozen_i1_h3.json")
    (args.output_dir / "current_i1_facts_2026.json").write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
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
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

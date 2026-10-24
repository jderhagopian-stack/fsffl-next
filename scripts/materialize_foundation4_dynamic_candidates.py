"""Batch materialization adapter for out-of-reference Career candidates.

Consumes complete, already-governed candidate P0 rows. It does not acquire data,
fit a new model family, or change the frozen 335 reference board.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from fsffl.product.resource_coordinator import release_unused_process_memory
from fsffl.product.foundation4_matrix import bounded_feature_matrix
from fsffl.product.foundation4_history import BoundedHorizonHistory

REQUIRED = {
    "player_id", "position", "historical_gsis_id", "age", "experience",
    "league_y1_points", "y2_player_league_expected_points",
    "y3_player_league_expected_points", "state_hash", "state_as_of",
    "evaluation_as_of", "forecast_as_of", "evidence_source",
    "evidence_version", "scoring_coordinate", "team_id", "roster_slot",
    "identity_as_of",
}
POSITIONS = {"QB", "RB", "WR", "TE"}
RAW_HISTORY_COLUMNS = (
    "player_id", "season", "position", "team", "games", "attempts", "carries",
    "targets", "fantasy_points", "fantasy_points_ppr", "receptions",
    "passing_interceptions", "sack_fumbles_lost", "rushing_fumbles_lost",
    "receiving_fumbles_lost", "passing_yards", "passing_tds", "passing_epa",
    "passing_cpoe", "rushing_yards", "rushing_tds", "rushing_epa",
    "receiving_yards", "receiving_tds", "receiving_epa", "target_share",
    "air_yards_share", "wopr", "fumbles", "sacks_suffered",
)
MODEL_A_COLUMNS = (
    "fold_id", "target_season", "asset_id", "position", "season_offset",
    "player_forecast_mean", "player_forecast_stddev",
)
PLAYER_METADATA_COLUMNS = (
    "gsis_id", "birth_date", "height", "weight", "college_name",
    "college_conference", "rookie_season", "draft_year", "draft_round",
    "draft_pick", "draft_team",
)
RESIDUAL_COLUMNS = (
    "forecast_fold", "player_id", "career_stage", "production_tier",
    "prior_direction", "history_n", "reliability", "residual_mean",
    "residual_sd", "residual_last", "production_history_n", "production_slope",
    "production_volatility", "production_pattern", "career_high_recency",
    "player_residual_component", "trajectory_state",
)
INNOVATION_COLUMNS = (
    "forecast_fold", "player_id", "history_n", "stable_level_baseline",
    "latest_residual", "latest_innovation", "innovation_slope",
    "innovation_acceleration", "innovation_autocorrelation",
    "innovation_volatility", "innovation_z", "same_sign_count",
    "signed_same_sign_count", "innovation_state", "volatility_ratio",
    "volatility_band", "level_component",
)


def read_raw_history(path: str | Path) -> pd.DataFrame:
    """Read only columns consumed by the accepted F4 feature pipeline."""
    header = pd.read_csv(path, nrows=0).columns
    required_scoring = {
        "fantasy_points", "fantasy_points_ppr", "receptions",
        "passing_interceptions", "sack_fumbles_lost", "rushing_fumbles_lost",
        "receiving_fumbles_lost",
    }
    missing = sorted(required_scoring - set(header))
    if missing:
        raise ValueError(f"raw scoring evidence missing required columns: {missing}")
    return pd.read_csv(path, usecols=[column for column in RAW_HISTORY_COLUMNS if column in header])


def stage_projected_csv(path: str, destination: Path, columns: tuple[str, ...]) -> Path:
    """Stage a temporary, contract-scoped view of a governed input CSV."""
    header = pd.read_csv(path, nrows=0).columns
    selected = [column for column in columns if column in header]
    if not selected:
        raise ValueError(f"accepted Foundation 4 input has no expected feature columns: {path}")
    pd.read_csv(path, usecols=selected).to_csv(destination, index=False)
    return destination


def compact_history_categories(frame: pd.DataFrame, dev, *, copy: bool = True) -> pd.DataFrame:
    """Dictionary-encode repeated route labels without changing model inputs."""
    categorical = set(getattr(dev, "CATEGORICAL", ())) | {"position"}
    out = frame.copy() if copy else frame
    for column in sorted(categorical & set(out.columns)):
        values = out[column].astype("category")
        if "MISSING" not in values.cat.categories:
            values = values.cat.add_categories(["MISSING"])
        out[column] = values
    return out


def validate_candidates(frame: pd.DataFrame, reference_ids: set[str], season: int,
                        exact_roster: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED - set(frame.columns))
    if missing:
        raise ValueError(f"candidate evidence is missing required fields: {missing}")
    frame = frame.copy()
    for field in ("player_id", "position", "state_hash", "evidence_source", "evidence_version", "scoring_coordinate", "team_id", "roster_slot"):
        frame[field] = frame[field].astype(str).str.strip()
        if frame[field].eq("").any():
            raise ValueError(f"candidate evidence has blank {field}")
    if frame.player_id.duplicated().any():
        raise ValueError("candidate evidence has duplicate canonical IDs")
    if set(frame.player_id) & reference_ids:
        raise ValueError("dynamic candidate overlaps frozen reference cohort")
    if not frame.position.isin(POSITIONS).all():
        raise ValueError("unsupported candidate position")
    # The accepted feature pipeline represents absent historical crosswalks as
    # missing lags/metadata. Keep the canonical State ID as the model row key in
    # that case; do not drop the player or fabricate historical production.
    frame["historical_gsis_id"] = frame["historical_gsis_id"].where(
        frame["historical_gsis_id"].notna(), ""
    ).astype(str).str.strip()
    for field in ("age", "experience", "league_y1_points", "y2_player_league_expected_points", "y3_player_league_expected_points"):
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
        if not np.isfinite(frame[field]).all() or (frame[field] < 0).any():
            raise ValueError(f"invalid candidate {field}")
    for field in ("state_as_of", "evaluation_as_of", "forecast_as_of", "identity_as_of"):
        frame[field] = pd.to_datetime(frame[field], utc=True, errors="coerce")
        if frame[field].isna().any():
            raise ValueError(f"invalid timezone-aware {field}")
    if (frame.state_as_of > frame.evaluation_as_of).any():
        raise ValueError("State is later than evaluation cutoff")
    if (frame.forecast_as_of > frame.evaluation_as_of).any():
        raise ValueError("Forecast is later than evaluation cutoff")
    if (frame.identity_as_of > frame.evaluation_as_of).any():
        raise ValueError("canonical identity evidence is later than evaluation cutoff")
    if (frame.evaluation_as_of.dt.year != season).any():
        raise ValueError("evaluation cutoff does not match model season")
    for field in ("state_hash", "evidence_version", "scoring_coordinate"):
        if frame[field].nunique() != 1:
            raise ValueError(f"candidate batch must share one {field}")
    required_roster = {"state_hash", "player_id", "position", "team_id", "roster_slot", "age", "state_as_of"}
    if required_roster - set(exact_roster.columns):
        raise ValueError("exact State roster evidence is incomplete")
    roster = exact_roster.copy()
    roster["age"] = pd.to_numeric(roster.age, errors="coerce")
    roster["state_as_of"] = pd.to_datetime(roster.state_as_of, utc=True, errors="coerce")
    if roster.player_id.duplicated().any():
        raise ValueError("exact State roster has duplicate canonical subjects")
    matched = frame.merge(roster, on="player_id", how="left", suffixes=("", "_state"), validate="one_to_one")
    if "state_hash_state" not in matched or matched.state_hash_state.isna().any():
        raise ValueError("candidate is not present in exact State")
    for field in ("state_hash", "position", "team_id", "roster_slot"):
        state_field = field + "_state"
        if state_field not in matched or not (matched[field].astype(str) == matched[state_field].astype(str)).all():
            raise ValueError(f"candidate {field} differs from exact State")
    if not np.allclose(matched.age.to_numpy(float), matched.age_state.to_numpy(float), rtol=0, atol=1e-9):
        raise ValueError("candidate age differs from exact State age")
    candidate_state_as_of = pd.to_datetime(matched.state_as_of, utc=True, errors="coerce")
    if not candidate_state_as_of.equals(matched.state_as_of_state):
        raise ValueError("candidate State timestamp differs from exact State")
    return frame.sort_values("player_id").reset_index(drop=True)



def validate_candidates_per_player(
    frame: pd.DataFrame,
    reference_ids: set[str],
    season: int,
    exact_roster: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, dict[str, object]]]:
    """Validate rows independently; one malformed candidate cannot abort its cohort."""
    if "player_id" not in frame.columns:
        raise ValueError("candidate evidence has no player_id column")
    player_ids = frame.player_id.astype(str).str.strip()
    if player_ids.eq("").any():
        raise ValueError("candidate evidence contains a row without a canonical player_id")
    duplicate_ids = set(player_ids[player_ids.duplicated(keep=False)])
    valid: list[pd.DataFrame] = []
    failures: dict[str, dict[str, object]] = {}

    def provenance_for(index: int) -> dict[str, str]:
        row = frame.iloc[index]
        fields = (
            "state_hash", "state_as_of", "evaluation_as_of", "forecast_as_of",
            "identity_as_of", "evidence_source", "evidence_version",
            "scoring_coordinate",
        )
        return {
            field: str(row[field])
            for field in fields
            if field in frame.columns and pd.notna(row[field])
        }

    for index, player_id in enumerate(player_ids):
        if player_id in duplicate_ids:
            failures[player_id] = {
                "failure_code": "duplicate_candidate_input",
                "failure_detail": "Candidate evidence contains more than one row for this canonical player ID.",
                "evidence_checked": ["candidate_input_validation", "exact_state_roster"],
                "provenance": provenance_for(index),
            }
            continue
        try:
            validated = validate_candidates(
                frame.iloc[[index]].copy(), reference_ids, season, exact_roster
            )
        except (TypeError, ValueError, KeyError, OverflowError) as exc:
            failures[player_id] = {
                "failure_code": "candidate_input_invalid",
                "failure_detail": f"{type(exc).__name__}: {exc}",
                "evidence_checked": ["candidate_input_validation", "exact_state_roster"],
                "provenance": provenance_for(index),
            }
            continue
        valid.append(validated)

    candidates = (
        pd.concat(valid, ignore_index=True).sort_values("player_id").reset_index(drop=True)
        if valid else frame.iloc[0:0].copy().reset_index(drop=True)
    )
    if set(candidates.player_id.astype(str)) & set(failures):
        raise ValueError("candidate validation accounted for one player as both success and failure")
    return candidates, failures

def build_candidate_features(dev, candidates, reference, raw, players, residual, innovation):
    x = candidates.copy()
    x["output_player_id"] = x.player_id.astype(str)
    history_ids = x.historical_gsis_id.astype(str).str.strip()
    x["player_id"] = history_ids.where(history_ids.ne(""), x.output_player_id)
    x["base_season"] = 2026
    x["y1"] = x.league_y1_points.astype(float)
    x["y2"] = x.y2_player_league_expected_points.astype(float)
    x["y3"] = x.y3_player_league_expected_points.astype(float)
    x["sd1"] = np.nan
    x["sd2"] = np.nan
    x["sd3"] = np.nan
    age, exp = x.age.to_numpy(dtype=float), x.experience.to_numpy(dtype=float)
    x = dev.merge_lags(x, raw)
    x = dev.add_engineered_features(x, players)
    # Preserve the accepted 335 percentile coordinate without making reference
    # values depend on the size or order of this new candidate batch.
    for idx, row in x.iterrows():
        values = pd.to_numeric(reference.loc[reference.position == row.position, "y1"], errors="coerce").dropna().to_numpy()
        if not len(values):
            raise ValueError(f"frozen percentile reference missing {row.position}")
        x.at[idx, "y1_pct"] = (int(np.sum(values < row.y1)) + 0.5 * int(np.sum(values == row.y1))) / len(values)
    x["age"], x["experience"] = age, exp
    return dev.merge_trajectory(x, residual, innovation)


def write_durable_roster_checkpoint(
    path: str | Path,
    *,
    state_hash: str,
    state_as_of: str,
    evaluation_as_of: str,
    roster_rows: list[dict],
    candidate_inputs: pd.DataFrame,
    y4_y7_rows: pd.DataFrame,
    y8_plus_rows: pd.DataFrame,
    failures: dict[str, dict],
) -> str:
    """Atomically persist sanitized roster-only derived outputs with mode 0600."""
    if not state_hash.strip():
        raise ValueError("durable roster checkpoint requires exact State hash")
    state_time = pd.to_datetime(state_as_of, utc=True, errors="coerce")
    evaluation_time = pd.to_datetime(evaluation_as_of, utc=True, errors="coerce")
    if pd.isna(state_time) or pd.isna(evaluation_time) or state_time > evaluation_time:
        raise ValueError("invalid State/evaluation timestamps for durable checkpoint")

    roster_by_id = {str(row["player_id"]): row for row in roster_rows}
    if len(roster_by_id) != len(roster_rows) or not roster_by_id:
        raise ValueError("durable roster checkpoint requires unique roster player IDs")
    candidate_by_id = {
        str(row["player_id"]): row
        for row in json.loads(candidate_inputs.to_json(orient="records", date_format="iso", date_unit="ns"))
    }
    failure_ids = set(failures)
    candidate_ids = set(candidate_by_id)
    roster_ids = set(roster_by_id)
    if candidate_ids & failure_ids or candidate_ids | failure_ids != roster_ids:
        raise ValueError("durable checkpoint must account for every roster player exactly once")
    if candidate_inputs.empty and not failures:
        raise ValueError("durable checkpoint cannot be empty")
    for player_id in roster_ids:
        row = roster_by_id[player_id]
        if str(row.get("state_hash", state_hash)) != state_hash:
            raise ValueError("roster row State mismatch in durable checkpoint")
    for player_id, row in candidate_by_id.items():
        roster = roster_by_id[player_id]
        if str(row.get("state_hash", "")) != state_hash:
            raise ValueError(f"candidate State mismatch for {player_id}")
        for field in ("position", "team_id", "roster_slot"):
            if str(row.get(field, "")) != str(roster.get(field, "")):
                raise ValueError(f"candidate {field} differs from exact State for {player_id}")
        row_state_time = pd.to_datetime(row.get("state_as_of"), utc=True, errors="coerce")
        if pd.isna(row_state_time) or row_state_time != state_time:
            raise ValueError(f"candidate State timestamp mismatch for {player_id}")
        row_evaluation = pd.to_datetime(row.get("evaluation_as_of"), utc=True, errors="coerce")
        if pd.isna(row_evaluation) or row_evaluation != evaluation_time:
            raise ValueError(f"candidate evaluation cutoff mismatch for {player_id}")
        for field in ("forecast_as_of", "identity_as_of"):
            evidence_time = pd.to_datetime(row.get(field), utc=True, errors="coerce")
            if pd.isna(evidence_time) or evidence_time > evaluation_time:
                raise ValueError(f"candidate {field} is invalid or after cutoff for {player_id}")
        if not str(row.get("evidence_source", "")).strip() or not str(row.get("evidence_version", "")).strip():
            raise ValueError(f"candidate provenance is incomplete for {player_id}")

    y4_by_id = {
        player_id: rows
        for player_id, rows in y4_y7_rows.groupby("player_id", sort=False)
    } if not y4_y7_rows.empty else {}
    tail_by_id = {
        str(row["player_id"]): row
        for row in json.loads(y8_plus_rows.to_json(orient="records"))
    } if not y8_plus_rows.empty else {}
    if candidate_ids and (
        set(y4_by_id) != candidate_ids or set(tail_by_id) != candidate_ids
    ):
        raise ValueError("durable Career component player sets differ from successful P0 inputs")
    records = []
    for player_id in sorted(roster_ids):
        roster = roster_by_id[player_id]
        if player_id in failure_ids:
            failure = failures[player_id]
            code, detail = str(failure.get("failure_code", "")).strip(), str(
                failure.get("failure_detail", "")
            ).strip()
            if not code or not detail or "evidence_checked" not in failure or "provenance" not in failure:
                raise ValueError(f"failure record is incomplete for {player_id}")
            records.append({
                "player_id": player_id,
                "position": str(roster["position"]),
                "team_id": str(roster["team_id"]),
                "roster_slot": str(roster["roster_slot"]),
                "state_hash": state_hash,
                "state_as_of": state_time.isoformat(),
                "evaluation_as_of": evaluation_time.isoformat(),
                "status": "p0_failure",
                "failure": failure,
            })
            continue

        annual = y4_by_id.get(player_id)
        tail = tail_by_id.get(player_id)
        if annual is None or len(annual) != 16 or tail is None:
            raise ValueError(f"partial Career outputs incomplete for {player_id}")
        records.append({
            "player_id": player_id,
            "position": str(roster["position"]),
            "team_id": str(roster["team_id"]),
            "roster_slot": str(roster["roster_slot"]),
            "state_hash": state_hash,
            "state_as_of": state_time.isoformat(),
            "evaluation_as_of": evaluation_time.isoformat(),
            "status": "p0_inputs_available_career_partial",
            "career_failure_reason": "exact_Current_Y1_Y3_Shapley_contract_absent",
            "p0_input": candidate_by_id[player_id],
            "y4_y7": json.loads(annual.to_json(orient="records", date_format="iso")),
            "y8_plus": tail,
            "provenance": {
                "evidence_source": candidate_by_id[player_id]["evidence_source"],
                "evidence_version": candidate_by_id[player_id]["evidence_version"],
                "forecast_as_of": candidate_by_id[player_id]["forecast_as_of"],
                "identity_as_of": candidate_by_id[player_id]["identity_as_of"],
            },
        })

    payload = {
        "schema_version": "fsffl-career-roster-p0-checkpoint-v1",
        "state_hash": state_hash,
        "state_as_of": state_time.isoformat(),
        "evaluation_as_of": evaluation_time.isoformat(),
        "player_count": len(records),
        "success_count": len(candidate_ids),
        "failure_count": len(failure_ids),
        "players": records,
    }
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    target = Path(path).expanduser().resolve()
    repository_root = Path(__file__).resolve().parents[1]
    if target == repository_root or repository_root in target.parents:
        raise ValueError("durable roster checkpoint must be outside the public repository")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False) as handle:
            temporary_path = Path(handle.name)
            os.chmod(temporary_path, 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
        os.chmod(target, 0o600)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return hashlib.sha256(encoded).hexdigest()


def build_roster_authority_status(
    roster,
    reference_ids: set[str],
    candidate_ids: set[str],
    candidate_failures: dict[str, dict[str, object]] | None = None,
):
    """Account for every exact-State QB/RB/WR/TE without hiding missing subjects."""
    rows = []
    candidate_failures = candidate_failures or {}
    for row in roster.sort_values("player_id").itertuples():
        player_id = str(row.player_id)
        if player_id in reference_ids:
            status, components, failure = "reference_estimate_available", "accepted_335_career", ""
        elif player_id in candidate_ids:
            status, components = "partial_authority", "accepted_y4_y7_and_y8_plus"
            failure = "exact_Current_Y1_Y3_Shapley_contract_absent"
        else:
            status, components = "unavailable", "none"
            failure = str(candidate_failures.get(player_id, {}).get(
                "failure_detail",
                "governed_dynamic_P0_candidate_packet_absent_for_this_exact_State",
            ))
        rows.append({
            "player_id": player_id, "position": str(row.position),
            "team_id": str(row.team_id), "roster_slot": str(row.roster_slot),
            "state_hash": str(row.state_hash), "coverage_status": status,
            "available_components": components, "full_career_failure": failure,
        })
    return pd.DataFrame(rows)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser()
    for name in ("development-module", "route-module", "model-a-rows", "qb-results", "raw-seasons", "players", "residual-states", "innovation-states", "reference-board", "current-route", "cell-metrics", "policy-freeze", "connected-rules", "candidate-input", "state-roster", "out-dir"):
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--state-player-universe", help="exact-State JSON with the complete canonical players list")
    ap.add_argument("--durable-roster-checkpoint", help="absolute private path for atomic roster-only derived output")
    ap.add_argument("--evaluation-as-of", help="timezone-aware evaluation timestamp required for a durable roster checkpoint")
    ap.add_argument("--candidate-failures", help="CSV of explicit per-player P0 failure details and provenance")
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    dev = load_module("dynamic_career_dev", a.development_module)
    accepted_matrix = dev.matrix
    dev.matrix = lambda train, evaluation, features, architecture: bounded_feature_matrix(
        accepted_matrix, dev.CATEGORICAL, train, evaluation, features, architecture)
    route = load_module("dynamic_career_route", a.route_module)
    from fsffl.product.foundation4_matrix import bounded_candidate_fit
    accepted_fit = route.fit_candidate
    route.fit_candidate = lambda dev, long, candidate, origin, horizon, position, evaluation: bounded_candidate_fit(
        accepted_fit, dev, long, candidate, origin, horizon, position, evaluation)
    source = load_module("foundation4_source", str(Path(__file__).with_name("materialize_foundation4_fsffl_coordinate.py")))
    from fsffl.product.career_coverage import (
        build_career_position_depth_refresh,
        select_career_coverage,
    )
    roster_frame = pd.read_csv(a.state_roster)
    if a.state_player_universe:
        state_payload = json.loads(Path(a.state_player_universe).read_text())
        state_players = state_payload.get("players", [])
    else:
        # Roster-only mode remains useful for bounded replay. Production should
        # supply the exact State universe to preselect the full waiver pool.
        state_players = roster_frame[["player_id", "position"]].to_dict("records")
    if roster_frame.state_hash.nunique() != 1:
        raise ValueError("roster input must represent one exact State")
    exact_state_hash = str(roster_frame.state_hash.iloc[0])
    coverage_subjects = select_career_coverage(
        state_players=state_players, roster_rows=roster_frame.to_dict("records"),
        state_hash=exact_state_hash,
    )
    pd.DataFrame([subject.__dict__ for subject in coverage_subjects]).to_csv(
        out / "CAREER_EXACT_STATE_COVERAGE_SELECTION.csv", index=False
    )
    connected = source.scored_raw_frame(read_raw_history(a.raw_seasons))
    previous = {(str(row.player_id), int(row.season)): float(row.fantasyPoints)
                for row in connected.itertuples() if int(row.season) == 2025}
    scoped_history_path = out.parent / "accepted_raw_history.csv"
    connected.to_csv(scoped_history_path, index=False)
    # Current's accepted lag join uses only 2026 minus lags 1, 2 and 3.
    # Rankings and team shares in prep_raw are season-local, so keep all
    # players in those seasons and release older rows before current joins.
    raw = dev.prep_raw(connected.loc[connected.season.isin((2023, 2024, 2025))])
    del connected
    release_unused_process_memory(label="foundation4-current-lag-history-scoped")
    players_header = pd.read_csv(a.players, nrows=0).columns
    players = pd.read_csv(a.players, usecols=[c for c in PLAYER_METADATA_COLUMNS if c in players_header])
    residual_header = pd.read_csv(a.residual_states, nrows=0).columns
    residual = pd.read_csv(a.residual_states, usecols=[c for c in RESIDUAL_COLUMNS if c in residual_header])
    innovation_header = pd.read_csv(a.innovation_states, nrows=0).columns
    innovation = pd.read_csv(a.innovation_states, usecols=[c for c in INNOVATION_COLUMNS if c in innovation_header])
    reference_board = pd.read_csv(a.reference_board)
    reference = source.build_current(dev, reference_board, raw, players, residual, innovation)
    reference_player_count = int(reference.output_player_id.nunique())
    reference_ids = set(reference.output_player_id.astype(str))
    candidates, candidate_input_failures = validate_candidates_per_player(
        pd.read_csv(a.candidate_input),
        set(reference.output_player_id.astype(str)),
        2026,
        roster_frame,
    )
    current = build_candidate_features(dev, candidates, reference, raw, players, residual, innovation)
    # Release current-board joins before the full accepted history panel is built.
    del raw, players, residual, innovation, reference_board, reference
    release_unused_process_memory(label="foundation4-current-inputs-released")
    class Args: pass
    history = Args()
    history.model_a_rows = str(stage_projected_csv(
        a.model_a_rows, out.parent / "accepted_model_a_rows.csv", MODEL_A_COLUMNS
    ))
    history.qb_results = a.qb_results
    history.raw_seasons = str(scoped_history_path)
    history.players = str(stage_projected_csv(
        a.players, out.parent / "accepted_player_metadata.csv", PLAYER_METADATA_COLUMNS
    ))
    history.residual_states = str(stage_projected_csv(
        a.residual_states, out.parent / "accepted_residual_states.csv", RESIDUAL_COLUMNS
    ))
    history.innovation_states = str(stage_projected_csv(
        a.innovation_states, out.parent / "accepted_innovation_states.csv", INNOVATION_COLUMNS
    ))
    model_a = pd.read_csv(history.model_a_rows)
    qb_results = json.loads(Path(history.qb_results).read_text())
    model_a = dev.add_qb_governed_path(model_a, qb_results)
    del qb_results
    history_base = dev.build_forecast_base(model_a)
    del model_a
    release_unused_process_memory(label="foundation4-model-a-released")
    history_raw = dev.prep_raw(read_raw_history(history.raw_seasons))
    history_base = dev.merge_lags(history_base, history_raw)
    history_players = pd.read_csv(history.players)
    history_base = dev.add_engineered_features(history_base, history_players)
    del history_players
    model_features = {column for features in dev.FEATURE_SETS.values() for column in features}
    base_columns = {"player_id", "base_season", "position"} | model_features
    history_base = history_base.loc[:, [column for column in history_base if column in base_columns]]
    history_base = compact_history_categories(history_base, dev, copy=False)
    release_unused_process_memory(label="foundation4-unused-engineered-columns-released")
    history_residual = pd.read_csv(history.residual_states)
    history_innovation = pd.read_csv(history.innovation_states)
    history_base = dev.merge_trajectory(history_base, history_residual, history_innovation)
    del history_residual, history_innovation
    model_features = {
        column for feature_set in dev.FEATURE_SETS.values() for column in feature_set
    }
    base_columns = {"player_id", "base_season", "position"} | model_features
    history_base = history_base.loc[:, [column for column in history_base.columns if column in base_columns]]
    history_base = compact_history_categories(history_base, dev, copy=False)
    release_unused_process_memory(label="foundation4-before-horizon-expansion")
    staged_history_base = BoundedHorizonHistory.stage_base(
        history_base, out.parent / 'accepted_feature_columns'
    )
    del history_base
    release_unused_process_memory(label="foundation4-base-features-staged")
    # Preserve the existing runtime projection exactly: generated horizon_sq
    # was not part of that projection unless explicitly owned by a feature set.
    # Exposing it now would change global-continuous model inputs.
    long = BoundedHorizonHistory.from_staged(
        dev, staged_history_base, history_raw,
        columns=model_features | {'position', 'horizon', 'target_season', 'actual'},
    )
    del staged_history_base, history_raw
    release_unused_process_memory(label="foundation4-history-base-released")
    release_unused_process_memory(label="foundation4-before-policy-materialization")
    # This admitted materializer already owns the heavy phase. Bound native
    # fit workers to avoid one scratch workspace per available host core;
    # restore the caller's thread limits afterward. Model parameters and
    # accepted row/feature calculations remain unchanged.
    with threadpool_limits(limits=1):
        result = source.current_policy_rows(
            route, dev, long, current, pd.read_csv(a.current_route),
            pd.read_csv(a.cell_metrics), json.loads(Path(a.policy_freeze).read_text()),
        )
    if set(result.player_id) != set(candidates.player_id) or not (result.groupby("player_id").size() == 16).all():
        raise ValueError("each candidate must receive all 16 accepted Y4-Y7 policy rows")
    evidence_digest = hashlib.sha256(json.dumps(candidates.to_dict("records"), sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    mapped = candidates.set_index("player_id")
    for field in ("state_hash", "team_id", "roster_slot", "evidence_source", "evidence_version", "evaluation_as_of"):
        result[field] = result.player_id.map(mapped[field])
    result["candidate_evidence_sha256"] = evidence_digest
    result.to_csv(out / "FOUNDATION4_DYNAMIC_CANDIDATE_Y4_Y7.csv", index=False)

    from fsffl.state.models import LeagueRules, Position
    from fsffl.value.career_tail import CAREER_TAIL_SCORING_COORDINATE, CareerTailFeatures, build_career_tail_authority
    rules = LeagueRules.model_validate(json.loads(Path(a.connected_rules).read_text()))
    tails = []
    tail_authorities = []
    for row in candidates.itertuples():
        features = CareerTailFeatures(
            player_id=str(row.player_id), position=Position(str(row.position)),
            age_years=float(row.age), experience_years=float(row.experience),
            current_points=float(row.league_y1_points),
            prior_points=previous.get((str(row.historical_gsis_id), 2025)),
            current_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
            prior_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
            live_feature_transport_limitation="Governed P0 Y1 and completed 2025 FSFFL production; absent prior remains missing.",
        )
        authority = build_career_tail_authority(features, rules=rules)
        tail_authorities.append(authority.model_dump(mode="json"))
        tails.append({"player_id": authority.player_id, "position": authority.position.value,
                      "prior_points": features.prior_points, "model_authority_low": authority.model_authority_low,
                      "reference_center": authority.reference_center, "model_authority_high": authority.model_authority_high,
                      "outcome_outer_80": authority.outcome_outer_80, "outcome_outer_90": authority.outcome_outer_90,
                      "model_version": authority.model_version})
    pd.DataFrame(tails).to_csv(out / "FOUNDATION4_DYNAMIC_CANDIDATE_Y8_PLUS.csv", index=False)
    (out / "FOUNDATION4_DYNAMIC_CANDIDATE_Y8_PLUS_AUTHORITY.json").write_text(
        json.dumps(tail_authorities, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    roster_status = build_roster_authority_status(
        roster_frame,
        reference_ids,
        set(candidates.player_id.astype(str)),
        candidate_input_failures,
    )
    roster_status.to_csv(out / "CAREER_EXACT_STATE_ROSTER_AUTHORITY.csv", index=False)
    authority_by_id = {
        player_id: "reference" for player_id in set(roster_frame.player_id.astype(str)) & reference_ids
    }
    partial_by_id = {player_id: "partial" for player_id in set(candidates.player_id.astype(str))}
    failure_by_id = {
        str(row.player_id): str(row.full_career_failure)
        for row in roster_status.itertuples()
        if str(row.coverage_status) == "unavailable"
    }
    depth_refresh = build_career_position_depth_refresh(
        state_hash=exact_state_hash, roster_rows=roster_frame.to_dict("records"),
        subjects=coverage_subjects, authority=authority_by_id,
        partial_authority=partial_by_id, failures=failure_by_id,
    )
    pd.DataFrame(depth_refresh).to_csv(out / "CAREER_POSITION_DEPTH_EXACT_STATE.csv", index=False)
    if not a.state_player_universe and not a.durable_roster_checkpoint:
        raise ValueError("roster-only mode requires --durable-roster-checkpoint")
    if a.durable_roster_checkpoint:
        if not a.evaluation_as_of or not a.candidate_failures:
            raise ValueError("durable roster output requires evaluation cutoff and explicit failure CSV")
        failure_frame = pd.read_csv(a.candidate_failures)
        failure_fields = {"player_id", "failure_code", "failure_detail", "evidence_checked", "provenance"}
        if failure_fields - set(failure_frame.columns):
            raise ValueError("candidate failure CSV is missing required player-level detail")
        failure_records = {}
        for row in failure_frame.to_dict("records"):
            player_id = str(row["player_id"])
            failure_records[player_id] = {
                "failure_code": str(row["failure_code"]),
                "failure_detail": str(row["failure_detail"]),
                "evidence_checked": json.loads(row["evidence_checked"]),
                "provenance": json.loads(row["provenance"]),
            }
        for player_id, failure in candidate_input_failures.items():
            if player_id in failure_records:
                failure_records[player_id] = {
                    "failure_code": "conflicting_candidate_input_records",
                    "failure_detail": "Candidate input validation failure conflicts with a separate source failure record.",
                    "evidence_checked": ["candidate_input_validation", "candidate_failure_record"],
                    "provenance": failure.get("provenance", {}),
                }
            else:
                failure_records[player_id] = failure
        state_times = pd.to_datetime(roster_frame.state_as_of, utc=True, errors="coerce").dropna().unique()
        if len(state_times) != 1:
            raise ValueError("durable roster output requires one exact State timestamp")
        dynamic_roster_rows = roster_frame[
            ~roster_frame.player_id.astype(str).isin(reference_ids)
        ].to_dict("records")
        checkpoint_sha256 = write_durable_roster_checkpoint(
            a.durable_roster_checkpoint,
            state_hash=exact_state_hash,
            state_as_of=str(state_times[0]),
            evaluation_as_of=a.evaluation_as_of,
            roster_rows=dynamic_roster_rows,
            candidate_inputs=candidates,
            y4_y7_rows=result,
            y8_plus_rows=pd.DataFrame(tails),
            failures=failure_records,
        )
    (out / "FOUNDATION4_DYNAMIC_CANDIDATE_SUMMARY.json").write_text(json.dumps({
        "evaluation_season": 2026, "reference_player_count": reference_player_count,
        "candidate_count": int(candidates.player_id.nunique()), "y4_y7_policy_rows": int(len(result)),
        "y8_plus_authorities": len(tails), "candidate_evidence_sha256": evidence_digest,
        "exact_state_roster_subjects": int(len(roster_status)),
        "exact_state_reference_estimates": int((roster_status.coverage_status == "reference_estimate_available").sum()),
        "exact_state_partial_authorities": int((roster_status.coverage_status == "partial_authority").sum()),
        "exact_state_player_specific_failures": int((roster_status.coverage_status == "unavailable").sum()),
        "exact_state_coverage_selection_subjects": len(coverage_subjects),
        "exact_state_waiver_pool_subjects": sum(subject.source == "waiver_pool" for subject in coverage_subjects),
        "full_state_universe_supplied": bool(a.state_player_universe),
        "accepted_model_authority": "Foundation4 frozen route / policy / uncertainty cells + Career Tail v1",
        "reference_board_modified": False, "full_career_composed": False,
        "full_career_gate": "exact Current Y1-Y3 Shapley contract required for full Career Forward aggregation",
        "durable_roster_checkpoint_sha256": checkpoint_sha256 if a.durable_roster_checkpoint else None,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()

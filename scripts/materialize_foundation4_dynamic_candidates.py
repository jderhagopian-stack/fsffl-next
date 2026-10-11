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
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = {
    "player_id", "position", "historical_gsis_id", "age", "experience",
    "league_y1_points", "y2_player_league_expected_points",
    "y3_player_league_expected_points", "state_hash", "state_as_of",
    "evaluation_as_of", "forecast_as_of", "evidence_source",
    "evidence_version", "scoring_coordinate", "team_id", "roster_slot",
    "identity_as_of",
}
POSITIONS = {"QB", "RB", "WR", "TE"}


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
    if frame.historical_gsis_id.isna().any() or frame.historical_gsis_id.astype(str).str.strip().eq("").any():
        raise ValueError("accepted historical identity mapping is required")
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


def build_candidate_features(dev, candidates, reference, raw, players, residual, innovation):
    x = candidates.copy()
    x["output_player_id"] = x.player_id.astype(str)
    x["player_id"] = x.historical_gsis_id.astype(str)
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


def build_roster_authority_status(roster, reference_ids: set[str], candidate_ids: set[str]):
    """Account for every exact-State QB/RB/WR/TE without hiding missing subjects."""
    rows = []
    for row in roster.sort_values("player_id").itertuples():
        player_id = str(row.player_id)
        if player_id in reference_ids:
            status, components, failure = "reference_estimate_available", "accepted_335_career", ""
        elif player_id in candidate_ids:
            status, components = "partial_authority", "accepted_y4_y7_and_y8_plus"
            failure = "exact_Current_Y1_Y3_Shapley_contract_absent"
        else:
            status, components = "unavailable", "none"
            failure = "governed_dynamic_P0_candidate_packet_absent_for_this_exact_State"
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
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    dev = load_module("dynamic_career_dev", a.development_module)
    route = load_module("dynamic_career_route", a.route_module)
    source = load_module("foundation4_source", str(Path(__file__).with_name("materialize_foundation4_fsffl_coordinate.py")))
    connected = source.scored_raw_frame(pd.read_csv(a.raw_seasons))
    previous = {(str(row.player_id), int(row.season)): float(row.fantasyPoints)
                for row in connected.itertuples() if int(row.season) == 2025}
    raw = dev.prep_raw(connected.copy())
    players = pd.read_csv(a.players)
    residual, innovation = pd.read_csv(a.residual_states), pd.read_csv(a.innovation_states)
    reference_board = pd.read_csv(a.reference_board)
    reference = source.build_current(dev, reference_board, raw, players, residual, innovation)
    reference_player_count = int(reference.output_player_id.nunique())
    reference_ids = set(reference.output_player_id.astype(str))
    candidates = validate_candidates(pd.read_csv(a.candidate_input), set(reference.output_player_id.astype(str)), 2026, pd.read_csv(a.state_roster))
    current = build_candidate_features(dev, candidates, reference, raw, players, residual, innovation)
    # Drop materialization-only wide tables before loading/using the accepted
    # route-training panel; this bounds the scorer phase to one historical panel.
    del connected, raw, players, residual, innovation, reference_board, reference
    gc.collect()
    class Args: pass
    history = Args()
    history.model_a_rows, history.qb_results, history.raw_seasons = a.model_a_rows, a.qb_results, a.raw_seasons
    history.players, history.residual_states, history.innovation_states = a.players, a.residual_states, a.innovation_states
    long = route.build_inputs(dev, history)
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
        tails.append({"player_id": authority.player_id, "position": authority.position.value,
                      "prior_points": features.prior_points, "model_authority_low": authority.model_authority_low,
                      "reference_center": authority.reference_center, "model_authority_high": authority.model_authority_high,
                      "outcome_outer_80": authority.outcome_outer_80, "outcome_outer_90": authority.outcome_outer_90,
                      "model_version": authority.model_version})
    pd.DataFrame(tails).to_csv(out / "FOUNDATION4_DYNAMIC_CANDIDATE_Y8_PLUS.csv", index=False)
    roster_status = build_roster_authority_status(
        pd.read_csv(a.state_roster),
        reference_ids,
        set(candidates.player_id.astype(str)),
    )
    roster_status.to_csv(out / "CAREER_EXACT_STATE_ROSTER_AUTHORITY.csv", index=False)
    (out / "FOUNDATION4_DYNAMIC_CANDIDATE_SUMMARY.json").write_text(json.dumps({
        "evaluation_season": 2026, "reference_player_count": reference_player_count,
        "candidate_count": int(candidates.player_id.nunique()), "y4_y7_policy_rows": int(len(result)),
        "y8_plus_authorities": len(tails), "candidate_evidence_sha256": evidence_digest,
        "exact_state_roster_subjects": int(len(roster_status)),
        "exact_state_reference_estimates": int((roster_status.coverage_status == "reference_estimate_available").sum()),
        "exact_state_partial_authorities": int((roster_status.coverage_status == "partial_authority").sum()),
        "exact_state_player_specific_failures": int((roster_status.coverage_status == "unavailable").sum()),
        "accepted_model_authority": "Foundation4 frozen route / policy / uncertainty cells + Career Tail v1",
        "reference_board_modified": False, "full_career_composed": False,
        "full_career_gate": "exact Current Y1-Y3 Shapley contract required for full Career Forward aggregation",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()

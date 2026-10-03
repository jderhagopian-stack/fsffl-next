from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


POSITIONS = ("QB", "RB", "WR", "TE")
HORIZONS = (4, 5, 6, 7)
POLICIES = ("baseline", "hard_router", "soft_stack", "blanket_75_25")
SCORING_COORDINATE = "connected_league_fantasy_points"
MODEL_VERSION = "y4-y7-frozen-policy-fsffl-direct-materialization-v1"
SOURCE = "fsffl:frozen_cell_routing_fsffl_scoring_recalibration"
EXPECTED_FSFFL_SCORING = {
    "pass_yd": 0.04,
    "pass_td": 4.0,
    "pass_int": -1.0,
    "rush_yd": 0.1,
    "rush_td": 6.0,
    "rec": 0.5,
    "rec_yd": 0.1,
    "rec_td": 6.0,
    "fum_lost": -1.0,
    "pass_2pt": 2.0,
    "rush_2pt": 2.0,
    "rec_2pt": 2.0,
}


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_connected_rules(path: str) -> None:
    payload = json.loads(Path(path).read_text())
    scoring = {
        str(row["stat"]): float(row["points"])
        for row in payload["scoring"]
    }
    mismatches = {
        stat: (scoring.get(stat), expected)
        for stat, expected in EXPECTED_FSFFL_SCORING.items()
        if scoring.get(stat) != expected
    }
    if mismatches:
        raise SystemExit(f"connected FSFFL scoring rules drifted: {mismatches}")


def fsffl_half_ppr_points(raw: pd.DataFrame) -> pd.Series:
    """Exact transform from nflverse standard points for rules that differ in FSFFL.

    nflverse fantasy_points already carries the unchanged yardage/TD/two-point
    scoring. FSFFL changes reception credit from 0 to 0.5, passing INT from -2
    to -1, and fumble lost from -2 to -1. The rich source carries each required
    count, so no position multiplier is used.
    """

    required = {
        "fantasy_points",
        "fantasy_points_ppr",
        "receptions",
        "passing_interceptions",
        "sack_fumbles_lost",
        "rushing_fumbles_lost",
        "receiving_fumbles_lost",
    }
    missing = sorted(required - set(raw.columns))
    if missing:
        raise SystemExit(f"raw scoring evidence missing required columns: {missing}")

    standard = pd.to_numeric(raw["fantasy_points"], errors="coerce").fillna(0.0)
    ppr = pd.to_numeric(raw["fantasy_points_ppr"], errors="coerce").fillna(0.0)
    receptions = pd.to_numeric(raw["receptions"], errors="coerce").fillna(0.0)
    if float((ppr - standard - receptions).abs().max()) > 1e-8:
        raise SystemExit("historical PPR evidence no longer differs from standard by receptions")

    interceptions = pd.to_numeric(
        raw["passing_interceptions"], errors="coerce"
    ).fillna(0.0)
    fumbles_lost = sum(
        pd.to_numeric(raw[column], errors="coerce").fillna(0.0)
        for column in (
            "sack_fumbles_lost",
            "rushing_fumbles_lost",
            "receiving_fumbles_lost",
        )
    )
    return (
        standard
        + 0.5 * receptions
        + interceptions
        + fumbles_lost
    ).clip(lower=0.0)


def scored_raw_frame(raw: pd.DataFrame) -> pd.DataFrame:
    scored = raw.copy()
    connected = fsffl_half_ppr_points(scored)
    # The frozen development program prefers fantasyPoints when present.
    scored["fantasyPoints"] = connected
    scored["fantasy_points"] = connected
    scored["fantasy_points_ppr"] = connected
    return scored


def build_current(
    dev,
    board: pd.DataFrame,
    raw: pd.DataFrame,
    players: pd.DataFrame,
    residual: pd.DataFrame,
    innovation: pd.DataFrame,
) -> pd.DataFrame:
    x = board[board.position.isin(POSITIONS)].copy()
    if len(x) != 335:
        raise SystemExit(f"expected governed 335-player board, got {len(x)}")
    required = {
        "league_y1_points",
        "y2_player_league_expected_points",
        "y3_player_league_expected_points",
    }
    missing = sorted(required - set(x.columns))
    if missing:
        raise SystemExit(f"connected current board missing columns: {missing}")

    x["output_player_id"] = x["player_id"].astype(str)
    historical = x["historical_gsis_id"].astype(str)
    historical = historical.replace({"nan": np.nan, "None": np.nan, "": np.nan})
    x["player_id"] = historical.fillna(x["output_player_id"])
    x["base_season"] = 2026
    x["y1"] = pd.to_numeric(x["league_y1_points"], errors="coerce").fillna(0).clip(lower=0)
    x["y2"] = pd.to_numeric(
        x["y2_player_league_expected_points"], errors="coerce"
    ).fillna(0).clip(lower=0)
    x["y3"] = pd.to_numeric(
        x["y3_player_league_expected_points"], errors="coerce"
    ).fillna(0).clip(lower=0)
    x["sd1"] = np.nan
    x["sd2"] = np.nan
    x["sd3"] = np.nan
    frozen_age = pd.to_numeric(x["age"], errors="coerce")
    frozen_experience = pd.to_numeric(x["experience"], errors="coerce")

    x = dev.merge_lags(x, raw)
    x = dev.add_engineered_features(x, players)
    x = dev.merge_trajectory(x, residual, innovation)
    x["age"] = frozen_age.to_numpy()
    x["experience"] = frozen_experience.to_numpy()
    return x


def candidate_prediction(route, dev, long, candidate: str, h: int, pos: str,
                         ev: pd.DataFrame) -> np.ndarray:
    (pred, _p_active), _train_n = route.fit_candidate(
        dev, long, candidate, 2026, h, pos, ev
    )
    return np.asarray(pred, dtype=float).clip(min=0.0)


def generate_fixed_candidate_bank(route, dev, long, freeze):
    outer_n = int(freeze["rolling_contract"]["outer_origins_per_horizon_max"])
    min_outer = int(freeze["rolling_contract"]["minimum_outer_origins"])
    inner_w = int(freeze["rolling_contract"]["inner_origin_window"])
    min_inner = int(freeze["rolling_contract"]["minimum_inner_origins"])
    baseline = str(freeze["incumbent_comparator"])
    shared = str(freeze["shared_anchor"])
    rows = []
    plan = {}
    for h in HORIZONS:
        eligible = route.eligible_origins(long, h, dev.MIN_TRAIN_ROWS)
        outer_eligible = [
            T for i, T in enumerate(eligible) if i >= min_inner
        ]
        outer = outer_eligible[-outer_n:]
        if len(outer) < min_outer:
            raise SystemExit(f"insufficient FSFFL rolling origins Y{h}: {outer}")
        needed = set(outer)
        for T in outer:
            prior = [x for x in eligible if x < T][-inner_w:]
            if len(prior) < min_inner:
                raise SystemExit(f"insufficient FSFFL inner origins Y{h} T{T}")
            needed.update(prior)
        bank_origins = sorted(needed)
        plan[str(h)] = {"bank": bank_origins, "outer": outer}
        for T in bank_origins:
            evh = long[(long.horizon == h) & (long.base_season == T)]
            for pos in POSITIONS:
                ev = evh[evh.position == pos]
                if ev.empty:
                    continue
                key = f"{pos}|Y{h}"
                candidates = list(
                    dict.fromkeys(
                        freeze["specialist_shortlists"][key] + [baseline, shared]
                    )
                )
                for candidate in candidates:
                    (pred, pa), train_n = route.fit_candidate(
                        dev, long, candidate, T, h, pos, ev
                    )
                    for i, row in enumerate(ev.itertuples()):
                        rows.append(
                            {
                                "row_id": row.row_id,
                                "base_season": T,
                                "horizon": h,
                                "position": pos,
                                "player_id": row.player_id,
                                "actual": float(row.actual),
                                "candidate": candidate,
                                "pred": float(pred[i]),
                                "p_active": (
                                    float(pa[i])
                                    if np.isfinite(pa[i])
                                    else np.nan
                                ),
                                "train_n": int(train_n),
                            }
                        )
    return pd.DataFrame(rows), plan


def fixed_policy_calibration(route, dev, bank, plan, freeze, current_route):
    inner_w = int(freeze["rolling_contract"]["inner_origin_window"])
    min_inner = int(freeze["rolling_contract"]["minimum_inner_origins"])
    baseline = str(freeze["incumbent_comparator"])
    shared = str(freeze["shared_anchor"])
    predictions = []
    for h in HORIZONS:
        for pos in POSITIONS:
            rr = current_route[
                (current_route.position == pos) & (current_route.horizon == h)
            ]
            if len(rr) != 1:
                raise SystemExit(f"missing frozen current route {pos} Y{h}")
            route_row = rr.iloc[0]
            hard = str(route_row.hard_candidate)
            soft = json.loads(str(route_row.soft_weights))
            blanket = str(route_row.prior_blanket_specialist_candidate)
            weights_by_policy = {
                "baseline": {baseline: 1.0},
                "hard_router": {hard: 1.0},
                "soft_stack": {str(k): float(v) for k, v in soft.items()},
                "blanket_75_25": {blanket: 0.75, shared: 0.25},
            }
            for T in plan[str(h)]["outer"]:
                prior = [
                    x for x in plan[str(h)]["bank"] if x < T
                ][-inner_w:]
                if len(prior) < min_inner:
                    raise SystemExit(f"insufficient fixed-policy calibration {pos} Y{h} T{T}")
                for policy, weights in weights_by_policy.items():
                    candidates = set(weights)
                    inner = bank[
                        (bank.horizon == h)
                        & (bank.position == pos)
                        & (bank.base_season.isin(prior))
                        & (bank.candidate.isin(candidates))
                    ]
                    outer = bank[
                        (bank.horizon == h)
                        & (bank.position == pos)
                        & (bank.base_season == T)
                        & (bank.candidate.isin(candidates))
                    ]
                    inner_combo = route.combine(inner, weights)
                    outer_combo = route.combine(outer, weights)
                    if inner_combo.empty or outer_combo.empty:
                        raise SystemExit(
                            f"missing fixed-policy combination {policy} {pos} Y{h} T{T}"
                        )
                    q80, q90 = route.calibrate(inner_combo)
                    predictions.append(
                        route.annotate_outer(
                            outer_combo, policy, q80, q90
                        )
                    )
    pred = pd.concat(predictions, ignore_index=True)
    metrics = route.policy_metric_rows(dev, pred)
    return pred, metrics


def current_policy_rows(route, dev, long, current, current_route, metrics, freeze):
    baseline = str(freeze["incumbent_comparator"])
    shared = str(freeze["shared_anchor"])
    rows = []
    for h in HORIZONS:
        for pos in POSITIONS:
            ev = current[current.position == pos].copy()
            ev["horizon"] = h
            ev["horizon_sq"] = float(h * h)
            ev["target_season"] = 2026 + h - 1
            rr = current_route[
                (current_route.position == pos) & (current_route.horizon == h)
            ]
            if len(rr) != 1:
                raise SystemExit(f"missing frozen route for {pos} Y{h}")
            route_row = rr.iloc[0]
            hard = str(route_row.hard_candidate)
            soft = json.loads(str(route_row.soft_weights))
            blanket = str(route_row.prior_blanket_specialist_candidate)
            needed = {baseline, shared, hard, blanket, *soft.keys()}
            cache = {
                candidate: candidate_prediction(
                    route, dev, long, candidate, h, pos, ev
                )
                for candidate in sorted(needed)
            }
            policy_predictions = {
                "baseline": cache[baseline],
                "hard_router": cache[hard],
                "soft_stack": sum(
                    float(weight) * cache[candidate]
                    for candidate, weight in soft.items()
                ),
                "blanket_75_25": 0.75 * cache[blanket] + 0.25 * cache[shared],
            }
            for policy in POLICIES:
                m = metrics[
                    (metrics.position == pos)
                    & (metrics.horizon == h)
                    & (metrics.policy == policy)
                ]
                if len(m) != 1:
                    raise SystemExit(
                        f"missing FSFFL uncertainty {policy} {pos} Y{h}"
                    )
                q80 = float(m.iloc[0].mean_q80)
                q90 = float(m.iloc[0].mean_q90)
                if q90 < q80:
                    raise SystemExit("FSFFL 90 band narrower than 80 band")
                pred = policy_predictions[policy]
                for source_row, central in zip(ev.itertuples(), pred, strict=True):
                    rows.append(
                        {
                            "player_id": str(source_row.output_player_id),
                            "position": pos,
                            "evaluation_season": 2026,
                            "year_index": h,
                            "target_season": 2026 + h - 1,
                            "policy_id": policy,
                            "central_expectation": max(0.0, float(central)),
                            "absolute_error_80": q80,
                            "absolute_error_90": q90,
                            "scoring_coordinate": SCORING_COORDINATE,
                            "model_version": MODEL_VERSION,
                            "source": SOURCE,
                            "evidence_path": (
                                "foundation4-fsffl-scoring-recalibration/"
                                f"{policy}/{pos}/Y{h}"
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def terminal_player_seasons(scored_raw: pd.DataFrame) -> pd.DataFrame:
    out = scored_raw[
        scored_raw.position.isin(POSITIONS)
    ].copy()
    return pd.DataFrame(
        {
            "player_id": out.player_id.astype(str),
            "season": pd.to_numeric(out.season, errors="raise").astype(int),
            "position": out.position.astype(str),
            "fantasy_points": pd.to_numeric(
                out.fantasyPoints, errors="coerce"
            ).fillna(0.0),
            "age_years": pd.to_numeric(out.age, errors="coerce"),
            "experience_years": pd.to_numeric(
                out.years_of_experience, errors="coerce"
            ),
        }
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--development-module", required=True)
    ap.add_argument("--route-module", required=True)
    ap.add_argument("--model-a-rows", required=True)
    ap.add_argument("--qb-results", required=True)
    ap.add_argument("--raw-seasons", required=True)
    ap.add_argument("--players", required=True)
    ap.add_argument("--residual-states", required=True)
    ap.add_argument("--innovation-states", required=True)
    ap.add_argument("--board", required=True)
    ap.add_argument("--current-route", required=True)
    ap.add_argument("--policy-freeze", required=True)
    ap.add_argument("--connected-rules", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    validate_connected_rules(args.connected_rules)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dev = load_module("foundation4_dev", args.development_module)
    route = load_module("foundation4_route", args.route_module)

    source_raw = pd.read_csv(args.raw_seasons)
    connected_raw = scored_raw_frame(source_raw)
    scored_path = out / "FOUNDATION4_FSFFL_PLAYER_SEASONS_RICH.csv"
    connected_raw.to_csv(scored_path, index=False)

    raw = dev.prep_raw(connected_raw.copy())
    players = pd.read_csv(args.players)
    residual = pd.read_csv(args.residual_states)
    innovation = pd.read_csv(args.innovation_states)
    board = pd.read_csv(args.board)
    current = build_current(
        dev, board, raw, players, residual, innovation
    )

    class Args:
        pass

    history_args = Args()
    history_args.model_a_rows = args.model_a_rows
    history_args.qb_results = args.qb_results
    history_args.raw_seasons = str(scored_path)
    history_args.players = args.players
    history_args.residual_states = args.residual_states
    history_args.innovation_states = args.innovation_states
    long = route.build_inputs(dev, history_args)

    freeze = json.loads(Path(args.policy_freeze).read_text())
    current_route = pd.read_csv(args.current_route)
    bank, plan = generate_fixed_candidate_bank(
        route, dev, long, freeze
    )
    calibration_rows, metrics = fixed_policy_calibration(
        route, dev, bank, plan, freeze, current_route
    )
    result = current_policy_rows(
        route, dev, long, current, current_route, metrics, freeze
    ).sort_values(
        ["player_id", "year_index", "policy_id"]
    ).reset_index(drop=True)

    if len(result) != 335 * 4 * 4:
        raise SystemExit(f"expected 5360 FSFFL rows, got {len(result)}")
    if result.player_id.nunique() != 335:
        raise SystemExit("FSFFL long-horizon board must cover 335 players")
    if set(result.scoring_coordinate) != {SCORING_COORDINATE}:
        raise SystemExit("FSFFL long-horizon scoring coordinate drifted")

    connected_points = {
        (str(row.player_id), int(row.season)): float(row.fantasyPoints)
        for row in connected_raw.itertuples()
    }
    terminal_rows = []
    for row in board.itertuples():
        historical_id = (
            None if pd.isna(row.historical_gsis_id)
            else str(row.historical_gsis_id)
        )
        prior = (
            connected_points.get((historical_id, 2025))
            if historical_id is not None else None
        )
        terminal_rows.append(
            {
                "player_id": str(row.player_id),
                "position": str(row.position),
                "age_years": float(row.age),
                "experience_years": float(row.experience),
                "current_points": max(0.0, float(row.league_y1_points)),
                "prior_points": prior,
                "prior_missing": prior is None,
                "current_points_coordinate": SCORING_COORDINATE,
                "prior_points_coordinate": SCORING_COORDINATE,
                "live_feature_transport_limitation": (
                    "terminal calibration uses the exact FSFFL scoring transform "
                    "of frozen historical standard production; 2026 uses the "
                    "governed connected-league full-season Y1 expectation"
                ),
            }
        )
    terminal = pd.DataFrame(terminal_rows).sort_values(
        "player_id"
    ).reset_index(drop=True)
    if len(terminal) != 335 or terminal.player_id.nunique() != 335:
        raise SystemExit("FSFFL terminal feature board must cover 335 players")

    terminal_training = terminal_player_seasons(connected_raw)
    terminal_training.to_csv(
        out / "FOUNDATION4_FSFFL_TERMINAL_PLAYER_SEASONS.csv",
        index=False,
    )
    calibration_rows.to_csv(
        out / "FOUNDATION4_FSFFL_ROLLING_POLICY_PREDICTIONS.csv",
        index=False,
    )
    metrics.to_csv(
        out / "FOUNDATION4_FSFFL_ROLLING_POLICY_CELL_METRICS.csv",
        index=False,
    )
    result.to_csv(
        out / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv",
        index=False,
    )
    terminal.to_csv(
        out / "FOUNDATION4_CURRENT_TERMINAL_FEATURES_335.csv",
        index=False,
    )
    long_rows = result.where(pd.notna(result), None).to_dict(
        orient="records"
    )
    terminal_json = terminal.where(pd.notna(terminal), None).to_dict(
        orient="records"
    )
    with gzip.open(
        out / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.json.gz",
        "wt",
        encoding="utf-8",
        compresslevel=9,
    ) as handle:
        json.dump(long_rows, handle, sort_keys=True, separators=(",", ":"))
    with gzip.open(
        out / "FOUNDATION4_CURRENT_TERMINAL_FEATURES_335.json.gz",
        "wt",
        encoding="utf-8",
        compresslevel=9,
    ) as handle:
        json.dump(terminal_json, handle, sort_keys=True, separators=(",", ":"))

    summary = {
        "authority": "frozen_policy_fsffl_scoring_direct_recalibration",
        "player_count": 335,
        "row_count": int(len(result)),
        "policies": list(POLICIES),
        "horizons": list(HORIZONS),
        "evaluation_season": 2026,
        "scoring_coordinate": SCORING_COORDINATE,
        "historical_scoring_transform": (
            "nflverse_standard + 0.5*receptions + passing_interceptions "
            "+ fumbles_lost"
        ),
        "model_family_search_reopened": False,
        "route_policy_search_reopened": False,
        "current_source": "FINAL_CONNECTED_LEAGUE_BOARD_335.csv",
        "terminal_feature_player_count": int(len(terminal)),
        "terminal_current_points_coordinate": SCORING_COORDINATE,
        "terminal_prior_points_coordinate": SCORING_COORDINATE,
        "uncertainty_recalibrated_on_fsffl_target": True,
    }
    (out / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


POSITIONS = ("QB", "RB", "WR", "TE")
HORIZONS = (4, 5, 6, 7)
POLICIES = ("baseline", "hard_router", "soft_stack", "blanket_75_25")


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_current(dev, board: pd.DataFrame, raw: pd.DataFrame, players: pd.DataFrame,
                  residual: pd.DataFrame, innovation: pd.DataFrame) -> pd.DataFrame:
    x = board[board.position.isin(POSITIONS)].copy()
    if len(x) != 335:
        raise SystemExit(f"expected governed 335-player board, got {len(x)}")
    x["output_player_id"] = x["player_id"].astype(str)
    historical = x["historical_gsis_id"].astype(str)
    historical = historical.replace({"nan": np.nan, "None": np.nan, "": np.nan})
    x["player_id"] = historical.fillna(x["output_player_id"])
    x["base_season"] = 2026
    x["y1"] = pd.to_numeric(x["standard_y1_points"], errors="coerce").fillna(0).clip(lower=0)
    x["y2"] = pd.to_numeric(x["y2_standard_expected_points"], errors="coerce").fillna(0).clip(lower=0)
    x["y3"] = pd.to_numeric(x["y3_standard_expected_points"], errors="coerce").fillna(0).clip(lower=0)
    x["sd1"] = np.nan
    x["sd2"] = np.nan
    x["sd3"] = np.nan
    frozen_age = pd.to_numeric(x["age"], errors="coerce")
    frozen_experience = pd.to_numeric(x["experience"], errors="coerce")

    x = dev.merge_lags(x, raw)
    x = dev.add_engineered_features(x, players)
    x = dev.merge_trajectory(x, residual, innovation)
    # The 335 source board is the governed 2026 current coordinate for these fields.
    x["age"] = frozen_age.to_numpy()
    x["experience"] = frozen_experience.to_numpy()
    return x


def candidate_prediction(route, dev, long, candidate: str, h: int, pos: str,
                         ev: pd.DataFrame) -> np.ndarray:
    (pred, _p_active), _train_n = route.fit_candidate(
        dev, long, candidate, 2026, h, pos, ev
    )
    return np.asarray(pred, dtype=float).clip(min=0.0)


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
    ap.add_argument("--cell-metrics", required=True)
    ap.add_argument("--policy-freeze", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dev = load_module("foundation4_dev", args.development_module)
    route = load_module("foundation4_route", args.route_module)

    raw = dev.prep_raw(pd.read_csv(args.raw_seasons))
    players = pd.read_csv(args.players)
    residual = pd.read_csv(args.residual_states)
    innovation = pd.read_csv(args.innovation_states)
    board = pd.read_csv(args.board)
    current = build_current(dev, board, raw, players, residual, innovation)

    class Args:
        pass
    history_args = Args()
    history_args.model_a_rows = args.model_a_rows
    history_args.qb_results = args.qb_results
    history_args.raw_seasons = args.raw_seasons
    history_args.players = args.players
    history_args.residual_states = args.residual_states
    history_args.innovation_states = args.innovation_states
    long = route.build_inputs(dev, history_args)

    current_route = pd.read_csv(args.current_route)
    metrics = pd.read_csv(args.cell_metrics)
    freeze = json.loads(Path(args.policy_freeze).read_text())
    baseline = str(freeze["incumbent_comparator"])
    shared = str(freeze["shared_anchor"])

    rows: list[dict[str, object]] = []
    candidate_cache: dict[tuple[int, str, str], np.ndarray] = {}

    for h in HORIZONS:
        for pos in POSITIONS:
            ev = current[current.position == pos].copy()
            ev["horizon"] = h
            ev["horizon_sq"] = float(h * h)
            ev["target_season"] = 2026 + h - 1
            route_row = current_route[
                (current_route.position == pos) & (current_route.horizon == h)
            ]
            if len(route_row) != 1:
                raise SystemExit(f"missing frozen route for {pos} Y{h}")
            rr = route_row.iloc[0]
            hard = str(rr.hard_candidate)
            soft = json.loads(str(rr.soft_weights))
            blanket_specialist = str(rr.prior_blanket_specialist_candidate)

            needed = {baseline, shared, hard, blanket_specialist, *soft.keys()}
            for candidate in sorted(needed):
                candidate_cache[(h, pos, candidate)] = candidate_prediction(
                    route, dev, long, candidate, h, pos, ev
                )

            policy_predictions = {
                "baseline": candidate_cache[(h, pos, baseline)],
                "hard_router": candidate_cache[(h, pos, hard)],
                "soft_stack": sum(
                    float(weight) * candidate_cache[(h, pos, candidate)]
                    for candidate, weight in soft.items()
                ),
                "blanket_75_25": (
                    0.75 * candidate_cache[(h, pos, blanket_specialist)]
                    + 0.25 * candidate_cache[(h, pos, shared)]
                ),
            }

            for policy in POLICIES:
                m = metrics[
                    (metrics.position == pos)
                    & (metrics.horizon == h)
                    & (metrics.policy == policy)
                ]
                if len(m) != 1:
                    raise SystemExit(f"missing frozen uncertainty for {policy} {pos} Y{h}")
                q80 = float(m.iloc[0].mean_q80)
                q90 = float(m.iloc[0].mean_q90)
                if q90 < q80:
                    raise SystemExit("frozen 90 band narrower than 80 band")
                pred = policy_predictions[policy]
                if len(pred) != len(ev):
                    raise SystemExit("current policy prediction length mismatch")
                for source_row, central in zip(ev.itertuples(), pred, strict=True):
                    rows.append({
                        "player_id": str(source_row.output_player_id),
                        "position": pos,
                        "evaluation_season": 2026,
                        "year_index": h,
                        "target_season": 2026 + h - 1,
                        "policy_id": policy,
                        "central_expectation": max(0.0, float(central)),
                        "absolute_error_80": q80,
                        "absolute_error_90": q90,
                        "model_version": "y4-y7-frozen-policy-materialization-v1",
                        "source": "fsffl:frozen_cell_routing_current_coordinate",
                        "evidence_path": (
                            "run:36271080037/artifact:10916355135/"
                            f"{policy}/{pos}/Y{h}"
                        ),
                    })

    result = pd.DataFrame(rows).sort_values(
        ["player_id", "year_index", "policy_id"]
    ).reset_index(drop=True)

    # Freeze the scale-compatible terminal feature coordinate in the same evidence
    # job. The retrospective terminal study used full-season base-year production;
    # during the 2026 season we therefore use the governed full-season Y1 point
    # coordinate as an explicitly labeled live proxy rather than annualizing YTD.
    prior_2025 = {
        str(row.player_id): float(row.fantasy_target)
        for row in raw[raw.season == 2025].itertuples()
    }
    terminal_rows = []
    for row in board.itertuples():
        historical_id = (
            None
            if pd.isna(row.historical_gsis_id)
            else str(row.historical_gsis_id)
        )
        prior = prior_2025.get(historical_id) if historical_id is not None else None
        terminal_rows.append({
            "player_id": str(row.player_id),
            "position": str(row.position),
            "age_years": float(row.age),
            "experience_years": float(row.experience),
            "current_points": max(0.0, float(row.standard_y1_points)),
            "prior_points": prior,
            "prior_missing": prior is None,
            "current_points_coordinate": (
                "governed_2026_standard_y1_full_season_expectation_proxy"
            ),
            "prior_points_coordinate": "completed_2025_fantasy_production",
            "live_feature_transport_limitation": (
                "terminal calibration used retrospective completed base-season production; "
                "2026 shadow uses the governed full-season Y1 point coordinate to preserve "
                "the training scale without inventing a YTD annualization multiplier"
            ),
        })
    terminal = pd.DataFrame(terminal_rows).sort_values("player_id").reset_index(drop=True)
    if len(terminal) != 335 or terminal.player_id.nunique() != 335:
        raise SystemExit("terminal feature snapshot must cover the governed 335-player cohort")
    if len(result) != 335 * 4 * 4:
        raise SystemExit(f"expected 5360 rows, got {len(result)}")
    counts = result.groupby("player_id").size()
    if not (counts == 16).all():
        raise SystemExit("every governed player must have 16 Y4-Y7 policy rows")
    if result.central_expectation.isna().any() or (result.central_expectation < 0).any():
        raise SystemExit("invalid current long-horizon central predictions")

    csv_path = out / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv"
    result.to_csv(csv_path, index=False)
    terminal.to_csv(
        out / "FOUNDATION4_CURRENT_TERMINAL_FEATURES_335.csv",
        index=False,
    )
    summary = {
        "authority": "frozen_accepted_y4_y7_policy_materialization",
        "player_count": 335,
        "row_count": int(len(result)),
        "policies": list(POLICIES),
        "horizons": list(HORIZONS),
        "evaluation_season": 2026,
        "rolling_route_run_id": 36271080037,
        "rolling_route_artifact_id": 10916355135,
        "authority_map_sha256": "487555fac2e5fd0823c6a70d29b1c1e60fbf2adc0e1bb8140f9f43e6ee0e9e00",
        "current_source": "FINAL_STANDARD_COORDINATE_BOARD_335.csv",
        "model_refit_at_runtime": False,
        "terminal_feature_player_count": int(len(terminal)),
        "terminal_current_points_coordinate": (
            "governed_2026_standard_y1_full_season_expectation_proxy"
        ),
        "terminal_prior_points_coordinate": "completed_2025_fantasy_production",
        "terminal_ytd_annualization_multiplier_used": False,
        "materialization_semantics": (
            "one-time application of frozen research candidates/routes to the governed "
            "2026 current coordinate; runtime consumes the frozen resulting board only"
        ),
    }
    (out / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

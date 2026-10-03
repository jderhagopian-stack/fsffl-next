from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fsffl.forecast.long_horizon_contract import (
    LongHorizonForecastAuthorityContract,
    LongHorizonPolicyForecast,
)
from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.long_term_intrinsic import build_long_term_intrinsic_shadow

CURRENT_SEASON = 2026
POSITIONS = ("QB", "RB", "WR", "TE")
HORIZONS = (4, 5, 6, 7)
POLICIES = ("baseline", "hard_router", "soft_stack", "blanket_75_25")
BASELINE = "specialist|forecast10|two_part_ridge"
SHARED = "global_continuous|football_plus|two_part_ridge"
BOARD = Path(
    "artifacts/implementation/final_forecast_route_implementation_20260920/"
    "FINAL_STANDARD_COORDINATE_BOARD_335.csv"
)
OUT = Path("/tmp/foundation4_current_long_horizon")


def _load_module(path: str):
    spec = importlib.util.spec_from_file_location("foundation4_dev", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(),
    )


def _history(dev, args):
    model = pd.read_csv(args.model_a_rows)
    qb = json.loads(Path(args.qb_results).read_text())
    raw = dev.prep_raw(pd.read_csv(args.raw_seasons))
    players = pd.read_csv(args.players)
    residual = pd.read_csv(args.residual_states)
    innovation = pd.read_csv(args.innovation_states)
    model = dev.add_qb_governed_path(model, qb)
    base = dev.build_forecast_base(model)
    base = dev.merge_lags(base, raw)
    base = dev.add_engineered_features(base, players)
    base = dev.merge_trajectory(base, residual, innovation)
    return dev.build_long(base, raw), raw, players, residual, innovation


def _current(dev, raw, players, residual, innovation):
    board = pd.read_csv(BOARD)
    board = board[board["position"].isin(POSITIONS)].copy()
    if len(board) != 335:
        raise SystemExit(f"expected 335 current players, got {len(board)}")
    board["source_player_id"] = board["player_id"].astype(str)
    historical = board["historical_gsis_id"].astype(str)
    historical = historical.replace({"nan": np.nan, "None": np.nan, "": np.nan})
    board["player_id"] = historical.fillna(
        "unmapped:" + board["source_player_id"]
    )
    board["base_season"] = CURRENT_SEASON
    board["board_age"] = pd.to_numeric(board["age"], errors="coerce")
    board["board_experience"] = pd.to_numeric(
        board["experience"], errors="coerce"
    )
    board["y1"] = pd.to_numeric(
        board["standard_y1_points"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0)
    board["y2"] = pd.to_numeric(
        board["y2_standard_expected_points"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0)
    board["y3"] = pd.to_numeric(
        board["y3_standard_expected_points"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0)
    # The preserved 335 board does not carry the richer research forecast
    # uncertainty features. Keep them missing; the frozen research matrix
    # imputes missing numeric evidence from training medians.
    board["sd1"] = np.nan
    board["sd2"] = np.nan
    board["sd3"] = np.nan
    board["scoring_multiplier"] = pd.to_numeric(
        board["player_specific_scoring_multiplier"], errors="coerce"
    ).fillna(1.0)
    out = dev.merge_lags(board, raw)
    out = dev.add_engineered_features(out, players)
    out = dev.merge_trajectory(out, residual, innovation)
    out["age"] = out["board_age"].combine_first(out["age"])
    out["experience"] = out["board_experience"].combine_first(
        out["experience"]
    )
    return out


def _fit_candidate(dev, long, candidate: str, h: int, pos: str, ev):
    arch, feature_set, model = candidate.split("|")
    if arch == "specialist":
        train = long[
            (long.horizon == h)
            & (long.position == pos)
            & (long.target_season < CURRENT_SEASON)
        ]
    elif arch == "global_continuous":
        train = long[long.target_season < CURRENT_SEASON]
    elif arch == "position_continuous":
        train = long[
            (long.position == pos)
            & (long.target_season < CURRENT_SEASON)
        ]
    elif arch == "shared_horizon":
        train = long[
            (long.horizon == h)
            & (long.target_season < CURRENT_SEASON)
        ]
    else:
        raise ValueError(f"unsupported frozen candidate architecture: {arch}")
    current = ev.copy()
    current["horizon"] = h
    current["horizon_sq"] = float(h * h)
    prediction, _ = dev.fit_predict(
        train, current, feature_set, model, arch
    )
    return np.asarray(prediction, dtype=float)


def _combine(predictions: dict[str, np.ndarray], weights: dict[str, float]):
    missing = sorted(set(weights) - set(predictions))
    if missing:
        raise ValueError(f"missing current candidate predictions: {missing}")
    total = sum(float(v) for v in weights.values())
    if not np.isclose(total, 1.0, atol=1e-9):
        raise ValueError(f"policy weights must sum to one, got {total}")
    result = None
    for candidate, weight in weights.items():
        part = predictions[candidate] * float(weight)
        result = part if result is None else result + part
    return np.asarray(result, dtype=float)


def _error_bands(rolling):
    output = {}
    for (pos, h, policy), rows in rolling.groupby(
        ["position", "horizon", "policy"]
    ):
        errors = (
            pd.to_numeric(rows["pred"], errors="coerce")
            - pd.to_numeric(rows["actual"], errors="coerce")
        ).abs().dropna()
        output[(str(pos), int(h), str(policy))] = (
            float(errors.quantile(0.80)),
            float(errors.quantile(0.90)),
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--development-module",
        default="scripts/_foundation4_frozen_long_horizon_research_dev.py",
    )
    parser.add_argument("--model-a-rows", required=True)
    parser.add_argument("--qb-results", required=True)
    parser.add_argument("--raw-seasons", required=True)
    parser.add_argument("--players", required=True)
    parser.add_argument("--residual-states", required=True)
    parser.add_argument("--innovation-states", required=True)
    parser.add_argument("--current-route", required=True)
    parser.add_argument("--rolling-policy-predictions", required=True)
    args = parser.parse_args()

    dev = _load_module(args.development_module)
    long, raw, players, residual, innovation = _history(dev, args)
    current = _current(dev, raw, players, residual, innovation)
    route = pd.read_csv(args.current_route)
    rolling = pd.read_csv(args.rolling_policy_predictions)
    bands = _error_bands(rolling)

    rows: list[LongHorizonPolicyForecast] = []
    audit: list[dict[str, object]] = []
    for h in HORIZONS:
        for pos in POSITIONS:
            cell = route[
                (route.position == pos) & (route.horizon == h)
            ]
            if len(cell) != 1:
                raise SystemExit(f"missing frozen route for {pos} Y{h}")
            cell = cell.iloc[0]
            soft = json.loads(str(cell.soft_weights))
            policy_weights = {
                "baseline": {BASELINE: 1.0},
                "hard_router": {str(cell.hard_candidate): 1.0},
                "soft_stack": {
                    str(k): float(v) for k, v in soft.items()
                },
                "blanket_75_25": {
                    str(cell.prior_blanket_specialist_candidate): 0.75,
                    SHARED: 0.25,
                },
            }
            candidates = sorted(
                {
                    candidate
                    for weights in policy_weights.values()
                    for candidate in weights
                }
            )
            mask = current.position == pos
            ev = current.loc[mask].copy()
            candidate_predictions = {
                candidate: _fit_candidate(
                    dev, long, candidate, h, pos, ev
                )
                for candidate in candidates
            }
            multiplier = ev["scoring_multiplier"].to_numpy(float)
            for policy in POLICIES:
                standard = _combine(
                    candidate_predictions, policy_weights[policy]
                )
                connected = np.clip(standard * multiplier, 0.0, None)
                q80, q90 = bands[(pos, h, policy)]
                for index, (_, player) in enumerate(ev.iterrows()):
                    player_id = str(player.source_player_id)
                    scale = max(0.0, float(player.scoring_multiplier))
                    rows.append(
                        LongHorizonPolicyForecast(
                            player_id=player_id,
                            position=Position(pos),
                            evaluation_season=CURRENT_SEASON,
                            year_index=h,
                            target_season=CURRENT_SEASON + h - 1,
                            policy_id=policy,
                            central_expectation=float(connected[index]),
                            absolute_error_80=q80 * scale,
                            absolute_error_90=q90 * scale,
                            model_version=(
                                "foundation4-frozen-current-y4-y7-policy-v1"
                            ),
                            source=(
                                "accepted_rolling_policy_routing_"
                                "artifact_10916355135"
                            ),
                            evidence_path=(
                                "CURRENT_RESEARCH_ROUTE.csv + "
                                "ROLLING_POLICY_PREDICTIONS.csv"
                            ),
                        )
                    )
                audit.append(
                    {
                        "position": pos,
                        "year_index": h,
                        "policy_id": policy,
                        "candidate_weights": policy_weights[policy],
                        "standard_mean": float(np.mean(standard)),
                        "connected_mean": float(np.mean(connected)),
                        "absolute_error_80_standard": q80,
                        "absolute_error_90_standard": q90,
                    }
                )

    contract = LongHorizonForecastAuthorityContract(
        evaluation_season=CURRENT_SEASON,
        forecast_model_version=(
            "foundation4-frozen-current-y4-y7-policy-v1"
        ),
        forecast_source=(
            "accepted_intrinsic_cell_routing_rolling_validation"
        ),
        forecasts=tuple(rows),
        provenance={
            "routing_artifact_id": 10916355135,
            "historical_panel_artifact_id": 10912862252,
            "historical_term_artifact_id": 10899387479,
            "current_player_count": 335,
            "current_missing_rich_features_use_frozen_training_imputation": True,
            "market_inputs_used": False,
        },
    )
    shadow = build_long_term_intrinsic_shadow(
        contract,
        rules=_rules(),
    )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "LONG_HORIZON_FORECAST_AUTHORITY.json").write_text(
        json.dumps(contract.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUT / "LONG_TERM_INTRINSIC_Y4_Y7_SHADOW.json").write_text(
        json.dumps(shadow.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(audit).to_json(
        OUT / "POLICY_MATERIALIZATION_AUDIT.json",
        orient="records",
        indent=2,
    )
    summary = {
        "player_count": len(shadow.estimates),
        "forecast_rows": len(contract.forecasts),
        "long_term_input_fingerprint": shadow.input_fingerprint,
        "contract_version": shadow.contract_version,
        "forecast_contract_version": contract.contract_version,
        "market_inputs_used": False,
        "display_scaling_applied": False,
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

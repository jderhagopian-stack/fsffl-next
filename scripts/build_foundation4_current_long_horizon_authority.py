from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path

# Foundation 4 replay must be reproducible across Actions runners. Set numerical
# thread controls before importing NumPy/scikit-learn so BLAS reductions cannot
# change routed/stacked current-cohort predictions across otherwise identical runs.
for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = "1"

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

    terminal_features: list[dict[str, object]] = []
    seen_terminal_ids: set[str] = set()
    for _, player in current.iterrows():
        player_id = str(player.source_player_id)
        if player_id in seen_terminal_ids:
            raise SystemExit(f"duplicate current terminal feature player: {player_id}")
        seen_terminal_ids.add(player_id)
        age = pd.to_numeric(player.age, errors="coerce")
        experience = pd.to_numeric(player.experience, errors="coerce")
        current_points = pd.to_numeric(player.y1, errors="coerce")
        prior_points = pd.to_numeric(player.prior_points, errors="coerce")
        if pd.isna(age) or pd.isna(experience) or pd.isna(current_points):
            raise SystemExit(
                "Foundation 4 terminal features require age, experience and current "
                f"production for every governed player; missing={player_id}"
            )
        terminal_features.append(
            {
                "player_id": player_id,
                "position": str(player.position),
                "age_years": max(0.0, float(age)),
                "experience_years": max(0.0, float(experience)),
                "current_points": max(0.0, float(current_points)),
                "prior_points": (
                    None if pd.isna(prior_points) else max(0.0, float(prior_points))
                ),
            }
        )
    terminal_features.sort(key=lambda item: str(item["player_id"]))
    if len(terminal_features) != len(shadow.estimates):
        raise SystemExit(
            "Foundation 4 terminal/current-cohort coverage mismatch: "
            f"{len(terminal_features)} != {len(shadow.estimates)}"
        )
    if {str(item["player_id"]) for item in terminal_features} != {
        item.player_id for item in shadow.estimates
    }:
        raise SystemExit(
            "Foundation 4 terminal feature subjects do not match Y4-Y7 authority"
        )

    production_bundle = {
        "bundle_version": "foundation4-current-cohort-production-bundle-v1",
        "evaluation_season": CURRENT_SEASON,
        "y4_y7_shadow": shadow.model_dump(mode="json"),
        "terminal_features": terminal_features,
        "provenance": {
            "routing_artifact_id": 10916355135,
            "historical_panel_artifact_id": 10912862252,
            "historical_term_artifact_id": 10899387479,
            "current_player_count": len(terminal_features),
            "market_inputs_used": False,
            "display_index_inputs_used": False,
            "historical_fitting_runs_in_web_process": False,
        },
    }
    production_bytes = json.dumps(
        production_bundle,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    production_sha256 = hashlib.sha256(production_bytes).hexdigest()
    production_b64 = base64.b64encode(
        gzip.compress(production_bytes, compresslevel=9, mtime=0)
    ).decode("ascii")

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
    (OUT / "TERMINAL_FEATURES.json").write_text(
        json.dumps(terminal_features, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUT / "CURRENT_COHORT_PRODUCTION_BUNDLE.json.gz.b64").write_text(
        production_b64 + "\n",
        encoding="utf-8",
    )
    (OUT / "CURRENT_COHORT_PRODUCTION_BUNDLE.sha256").write_text(
        production_sha256 + "\n",
        encoding="utf-8",
    )
    summary = {
        "player_count": len(shadow.estimates),
        "terminal_feature_count": len(terminal_features),
        "forecast_rows": len(contract.forecasts),
        "long_term_input_fingerprint": shadow.input_fingerprint,
        "contract_version": shadow.contract_version,
        "forecast_contract_version": contract.contract_version,
        "production_bundle_version": production_bundle["bundle_version"],
        "production_bundle_sha256": production_sha256,
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

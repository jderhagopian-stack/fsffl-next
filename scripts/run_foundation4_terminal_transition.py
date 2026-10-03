from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fsffl.value.shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_SEED,
)

OUT = Path("artifacts/research/foundation4_terminal_transition_20261002")
BOOTSTRAP_SEED = 20261002
BOOTSTRAP_REPS = 500
POSITIONS = ("QB", "RB", "WR", "TE")
DEVELOPMENT_BASE_SEASONS = (2013, 2014)
HOLDOUT_BASE_SEASON = 2015
ANCHOR_HORIZON = 7
HOLDOUT_MAX_HORIZON = 11


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rho_through_origin(x: np.ndarray, y: np.ndarray) -> float:
    denom = float(np.dot(x, x))
    if denom <= 0:
        return float("nan")
    return max(0.0, float(np.dot(x, y) / denom))


def transition_rows(
    *,
    predicted: pd.DataFrame,
    actual_phi: dict[int, dict[str, float]],
    source_max_season: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for anchor in predicted.itertuples():
        base = int(anchor.base_season)
        start = base + ANCHOR_HORIZON - 1
        for season in range(start, source_max_season):
            h = season - base + 1
            x = float(actual_phi.get(season, {}).get(str(anchor.player_id), 0.0))
            y = float(actual_phi.get(season + 1, {}).get(str(anchor.player_id), 0.0))
            rows.append(
                {
                    "base_season": base,
                    "player_id": str(anchor.player_id),
                    "position": anchor.position,
                    "season": season,
                    "relative_horizon": h,
                    "phi_now": x,
                    "phi_next": y,
                    "reactivation": bool(x <= 0 and y > 0),
                }
            )
    return pd.DataFrame(rows)


def fit_rho_authority(transitions: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    records: list[dict[str, object]] = []
    for position in POSITIONS:
        z = transitions[transitions.position == position].copy()
        # Main fit is deduplicated by player/calendar transition because the same
        # player can appear in both development base cohorts.
        z = z.sort_values(["player_id", "season", "base_season"]).drop_duplicates(
            ["player_id", "season"]
        )
        positive = z[z.phi_now > 0].copy()
        x = positive.phi_now.to_numpy(float)
        y = positive.phi_next.to_numpy(float)
        rho = rho_through_origin(x, y)
        players = positive.player_id.unique()
        boot = []
        if len(players) >= 2:
            grouped = {pid: positive[positive.player_id == pid] for pid in players}
            for _ in range(BOOTSTRAP_REPS):
                sampled = rng.choice(players, size=len(players), replace=True)
                pieces = [grouped[pid] for pid in sampled]
                sample = pd.concat(pieces, ignore_index=True)
                value = rho_through_origin(
                    sample.phi_now.to_numpy(float),
                    sample.phi_next.to_numpy(float),
                )
                if np.isfinite(value):
                    boot.append(value)
        q10 = float(np.quantile(boot, 0.10)) if boot else float("nan")
        q50 = float(np.quantile(boot, 0.50)) if boot else float("nan")
        q90 = float(np.quantile(boot, 0.90)) if boot else float("nan")
        zero_rows = z[z.phi_now <= 0]
        reactivation_rate = (
            float(zero_rows.reactivation.mean()) if len(zero_rows) else 0.0
        )
        records.append(
            {
                "position": position,
                "transition_n": int(len(z)),
                "positive_anchor_transition_n": int(len(positive)),
                "unique_players": int(len(players)),
                "rho_reference": rho,
                "rho_q10": q10,
                "rho_q50": q50,
                "rho_q90": q90,
                "discount_times_rho_reference": FROZEN_INTRINSIC_DISCOUNT * rho,
                "discount_times_rho_q90": FROZEN_INTRINSIC_DISCOUNT * q90,
                "reactivation_n": int(z.reactivation.sum()),
                "zero_anchor_n": int(len(zero_rows)),
                "reactivation_rate_after_zero": reactivation_rate,
            }
        )
    return pd.DataFrame(records)


def horizon_stability(transitions: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (position, base_season, horizon), z in transitions.groupby(
        ["position", "base_season", "relative_horizon"]
    ):
        positive = z[z.phi_now > 0]
        rho = rho_through_origin(
            positive.phi_now.to_numpy(float),
            positive.phi_next.to_numpy(float),
        )
        records.append(
            {
                "position": position,
                "base_season": int(base_season),
                "relative_horizon": int(horizon),
                "n": int(len(z)),
                "positive_anchor_n": int(len(positive)),
                "rho": rho,
                "reactivation_rate_after_zero": (
                    float(z.loc[z.phi_now <= 0, "reactivation"].mean())
                    if (z.phi_now <= 0).any()
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(records)


def restricted_tail_prediction(anchor: float, rho: float, max_horizon: int) -> float:
    return float(
        sum(
            (FROZEN_INTRINSIC_DISCOUNT ** (h - 1))
            * anchor
            * (rho ** (h - ANCHOR_HORIZON))
            for h in range(ANCHOR_HORIZON + 1, max_horizon + 1)
        )
    )


def infinite_tail(anchor: float, rho: float) -> float | None:
    product = FROZEN_INTRINSIC_DISCOUNT * rho
    if not np.isfinite(rho) or product >= 1:
        return None
    return float(
        (FROZEN_INTRINSIC_DISCOUNT ** ANCHOR_HORIZON)
        * anchor
        * rho
        / (1.0 - product)
    )


def metric(rows: pd.DataFrame, pred_col: str) -> dict[str, float | int]:
    z = rows[rows[pred_col].notna()].copy()
    if z.empty:
        return {"n": 0, "mae": float("nan"), "rmse": float("nan"), "spearman": float("nan")}
    error = z[pred_col].to_numpy(float) - z.actual_restricted_tail.to_numpy(float)
    return {
        "n": int(len(z)),
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error * error))),
        "spearman": float(
            z[pred_col].corr(z.actual_restricted_tail, method="spearman")
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--helpers-module", required=True)
    parser.add_argument("--development-module", required=True)
    parser.add_argument("--model-a-rows", required=True)
    parser.add_argument("--qb-results", required=True)
    parser.add_argument("--raw-seasons", required=True)
    parser.add_argument("--players", required=True)
    parser.add_argument("--residual-states", required=True)
    parser.add_argument("--innovation-states", required=True)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    helpers = load_module(args.helpers_module, "career_helpers")
    dev = helpers.load_module(args.development_module)
    _base, long, raw, _players = helpers.build_inputs(dev, args)
    source_max_season = int(raw.season.max())
    if source_max_season < HOLDOUT_BASE_SEASON + HOLDOUT_MAX_HORIZON - 1:
        raise SystemExit("holdout Y8-Y11 window is not fully observed")

    base_seasons = DEVELOPMENT_BASE_SEASONS + (HOLDOUT_BASE_SEASON,)
    predicted = helpers.terminal_anchor_predictions(dev, long, base_seasons)
    predicted["predicted_anchor_shapley"] = np.nan
    for base_season in base_seasons:
        board = predicted[predicted.base_season == base_season][
            ["player_id", "position", "predicted_anchor_points"]
        ].copy()
        values = helpers.shapley_board(
            board,
            weight_column="predicted_anchor_points",
            season_seed=(
                FROZEN_SHAPLEY_SEED + base_season + ANCHOR_HORIZON - 1
            ),
        )
        idx = predicted.base_season == base_season
        predicted.loc[idx, "predicted_anchor_shapley"] = predicted.loc[
            idx, "player_id"
        ].map(values)

    needed_seasons = range(
        min(base_seasons) + ANCHOR_HORIZON - 1,
        source_max_season + 1,
    )
    actual_phi: dict[int, dict[str, float]] = {}
    for season in needed_seasons:
        board = raw[raw.season == season][
            ["player_id", "position", "fantasy_target"]
        ].copy()
        actual_phi[season] = helpers.shapley_board(
            board,
            weight_column="fantasy_target",
            season_seed=FROZEN_SHAPLEY_SEED + season,
        )

    development_pred = predicted[
        predicted.base_season.isin(DEVELOPMENT_BASE_SEASONS)
    ].copy()
    transitions = transition_rows(
        predicted=development_pred,
        actual_phi=actual_phi,
        source_max_season=source_max_season,
    )
    authority = fit_rho_authority(transitions)
    stability = horizon_stability(transitions)

    holdout = predicted[predicted.base_season == HOLDOUT_BASE_SEASON].copy()
    holdout["actual_restricted_tail"] = 0.0
    for idx, row in holdout.iterrows():
        player_id = str(row.player_id)
        base = int(row.base_season)
        actual = 0.0
        for h in range(ANCHOR_HORIZON + 1, HOLDOUT_MAX_HORIZON + 1):
            season = base + h - 1
            actual += (
                FROZEN_INTRINSIC_DISCOUNT ** (h - 1)
            ) * float(actual_phi.get(season, {}).get(player_id, 0.0))
        holdout.loc[idx, "actual_restricted_tail"] = actual

    auth_by_position = authority.set_index("position")
    holdout["pred_zero_tail"] = 0.0
    holdout["pred_restricted_tail"] = np.nan
    holdout["terminal_tail_low"] = np.nan
    holdout["terminal_tail_reference"] = np.nan
    holdout["terminal_tail_high"] = np.nan
    holdout["terminal_convergent"] = False
    for idx, row in holdout.iterrows():
        pos = row.position
        if pos not in auth_by_position.index:
            continue
        auth = auth_by_position.loc[pos]
        anchor = float(row.predicted_anchor_shapley)
        rho = float(auth.rho_reference)
        holdout.loc[idx, "pred_restricted_tail"] = restricted_tail_prediction(
            anchor,
            rho,
            HOLDOUT_MAX_HORIZON,
        )
        low = infinite_tail(anchor, float(auth.rho_q10))
        ref = infinite_tail(anchor, rho)
        high = infinite_tail(anchor, float(auth.rho_q90))
        holdout.loc[idx, "terminal_tail_low"] = np.nan if low is None else low
        holdout.loc[idx, "terminal_tail_reference"] = np.nan if ref is None else ref
        holdout.loc[idx, "terminal_tail_high"] = np.nan if high is None else high
        holdout.loc[idx, "terminal_convergent"] = all(
            value is not None for value in (low, ref, high)
        )

    metrics = []
    for candidate, column in (
        ("zero_tail", "pred_zero_tail"),
        ("geometric_transition_tail", "pred_restricted_tail"),
    ):
        metrics.append({"candidate": candidate, **metric(holdout, column)})
    metric_frame = pd.DataFrame(metrics)

    per_position = []
    for position in POSITIONS:
        z = holdout[holdout.position == position]
        for candidate, column in (
            ("zero_tail", "pred_zero_tail"),
            ("geometric_transition_tail", "pred_restricted_tail"),
        ):
            per_position.append(
                {"position": position, "candidate": candidate, **metric(z, column)}
            )
    per_position_frame = pd.DataFrame(per_position)

    authority.to_csv(OUT / "TRANSITION_AUTHORITY.csv", index=False)
    stability.to_csv(OUT / "TRANSITION_STABILITY.csv", index=False)
    transitions.to_csv(OUT / "DEVELOPMENT_TRANSITIONS.csv", index=False)
    holdout.to_csv(OUT / "HOLDOUT_TAIL_ROWS.csv", index=False)
    metric_frame.to_csv(OUT / "HOLDOUT_TAIL_METRICS.csv", index=False)
    per_position_frame.to_csv(OUT / "HOLDOUT_TAIL_METRICS_BY_POSITION.csv", index=False)

    zero = next(row for row in metrics if row["candidate"] == "zero_tail")
    geometric = next(
        row for row in metrics if row["candidate"] == "geometric_transition_tail"
    )
    convergent_positions = authority[
        authority.discount_times_rho_q90 < 1.0
    ].position.tolist()
    result = {
        "state": "FOUNDATION4_TERMINAL_TRANSITION_HISTORICAL_FREEZE",
        "authority": "research_only_no_product_promotion",
        "aggregation_candidate": {
            "name": "stationary_continuation_of_current_intrinsic_kernel",
            "discount": FROZEN_INTRINSIC_DISCOUNT,
            "discount_search": False,
        },
        "tail_candidate": {
            "name": "position_specific_geometric_shapley_transition",
            "development_base_seasons": DEVELOPMENT_BASE_SEASONS,
            "untouched_holdout_base_season": HOLDOUT_BASE_SEASON,
            "holdout_observed_horizons": [
                ANCHOR_HORIZON + 1,
                HOLDOUT_MAX_HORIZON,
            ],
            "bootstrap_reps": BOOTSTRAP_REPS,
            "convergent_positions_at_q90": convergent_positions,
            "transition_authority": authority.to_dict("records"),
            "holdout_metrics": metrics,
            "holdout_metrics_by_position": per_position,
        },
        "guards": {
            "current_players_inspected": False,
            "named_player_tuning": False,
            "age_or_youth_multiplier": False,
            "hand_set_survival_coefficient": False,
            "terminal_multiplier_hand_set": False,
            "market_owner_team_utility_inputs": False,
            "cross_horizon_covariance_validated": False,
        },
        "interpretation": {
            "holdout_validation_scope": "restricted fully observed Y8-Y11 tail only",
            "infinite_tail_scope": (
                "research terminal extrapolation; promotable only if transition stability "
                "and convergence are accepted in governance review"
            ),
            "zero_tail_promotable": False,
        },
    }
    if geometric["n"] and geometric["mae"] < zero["mae"] and geometric["rmse"] < zero["rmse"]:
        result["evidence_direction"] = "geometric_tail_improves_restricted_holdout"
    else:
        result["evidence_direction"] = "geometric_tail_not_better_than_zero_baseline"

    (OUT / "RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Foundation 4 Terminal Transition Research",
        "",
        f"Evidence direction: **{result['evidence_direction']}**",
        "",
        "## Position transition authority",
        "",
        authority.to_markdown(index=False),
        "",
        "## Untouched 2015 restricted Y8-Y11 holdout",
        "",
        metric_frame.to_markdown(index=False),
        "",
        "## Governance",
        "",
        "- rho is learned from realized lineup-capacity Shapley transitions; it is not hand-set.",
        "- 0.85 is the existing Current Intrinsic kernel; no alternate discount search occurs.",
        "- the holdout validates only the fully observed Y8-Y11 portion; infinite Y8+ remains a terminal extrapolation subject to convergence/stability review.",
        "- returns after zero-value seasons are reported separately through the reactivation diagnostic rather than erased.",
        "- no current-player inspection occurred.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

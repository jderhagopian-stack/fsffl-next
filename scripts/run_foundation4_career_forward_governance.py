from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from fsffl.state.models import LeagueRules, LineupRequirement, RosterSlot
from fsffl.value.shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    monte_carlo_shapley_scenarios,
    subset_caps_from_rules,
)

OUT = Path("artifacts/research/foundation4_career_forward_20261002")
POSITIONS = ("QB", "RB", "WR", "TE")
FROZEN_TERMINAL_ANCHOR_CANDIDATE = "specialist|forecast10|two_part_ridge"
TERMINAL_ANCHOR_HORIZON = 7
FROZEN_ELIGIBLE_BASE_SEASONS = (2013, 2014, 2015)
FROZEN_DEVELOPMENT_BASE_SEASONS = (2013, 2014)
FROZEN_HOLDOUT_BASE_SEASONS = (2015,)
MIN_POST_Y8_OBSERVED_SEASONS = 3


def load_module(path: str):
    spec = importlib.util.spec_from_file_location("intrinsic_comprehensive_dev", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def research_rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        taxi_size=0,
        ir_size=0,
        rookie_draft_rounds=3,
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


def build_inputs(dev, args):
    model_a = pd.read_csv(args.model_a_rows)
    qb = json.loads(Path(args.qb_results).read_text())
    raw = dev.prep_raw(pd.read_csv(args.raw_seasons))
    players = pd.read_csv(args.players)
    residual = pd.read_csv(args.residual_states)
    innovation = pd.read_csv(args.innovation_states)
    model_a = dev.add_qb_governed_path(model_a, qb)
    base = dev.build_forecast_base(model_a)
    base = dev.merge_lags(base, raw)
    base = dev.add_engineered_features(base, players)
    base = dev.merge_trajectory(base, residual, innovation)
    long = dev.build_long(base, raw)
    return base, long, raw, players


def terminal_anchor_predictions(
    dev,
    long: pd.DataFrame,
    base_seasons: tuple[int, ...],
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for base_season in base_seasons:
        evaluation = long[
            (long.horizon == TERMINAL_ANCHOR_HORIZON)
            & (long.base_season == base_season)
        ]
        for position in POSITIONS:
            ev = evaluation[evaluation.position == position]
            if ev.empty:
                continue
            train = long[
                (long.horizon == TERMINAL_ANCHOR_HORIZON)
                & (long.position == position)
                & (long.target_season < base_season)
            ]
            if len(train) < dev.MIN_TRAIN_ROWS or train.base_season.nunique() < 2:
                raise RuntimeError(
                    "insufficient frozen terminal-anchor training evidence "
                    f"for {position} base {base_season}"
                )
            pred, p_active = dev.fit_predict(
                train,
                ev,
                "forecast10",
                "two_part_ridge",
                "specialist",
            )
            for index, row in enumerate(ev.itertuples()):
                records.append(
                    {
                        "base_season": int(base_season),
                        "anchor_target_season": int(
                            base_season + TERMINAL_ANCHOR_HORIZON - 1
                        ),
                        "target_y8_season": int(base_season + 7),
                        "player_id": str(row.player_id),
                        "position": position,
                        "predicted_anchor_points": float(pred[index]),
                        "predicted_anchor_p_active": (
                            float(p_active[index])
                            if np.isfinite(p_active[index])
                            else np.nan
                        ),
                    }
                )
    return pd.DataFrame(records)


def shapley_board(
    rows: pd.DataFrame,
    *,
    weight_column: str,
    season_seed: int,
) -> dict[str, float]:
    clean = rows[
        rows.player_id.notna()
        & rows.position.isin(POSITIONS)
        & pd.to_numeric(rows[weight_column], errors="coerce").notna()
    ].copy()
    clean["player_id"] = clean.player_id.astype(str)
    clean[weight_column] = (
        pd.to_numeric(clean[weight_column], errors="coerce").fillna(0.0).clip(lower=0.0)
    )
    clean = clean.sort_values(["position", "player_id"]).drop_duplicates("player_id")
    players = tuple(
        (row.player_id, row.position, float(getattr(row, weight_column)))
        for row in clean.itertuples()
    )
    scenarios = {player_id: (weight,) for player_id, _position, weight in players}
    result = monte_carlo_shapley_scenarios(
        players,
        scenarios,
        subset_caps_from_rules(research_rules()),
        permutations=FROZEN_SHAPLEY_PERMUTATIONS,
        seed=season_seed,
    )
    return {
        player_id: float(values[0])
        for player_id, values in result.estimates.items()
    }


def player_status_map(players: pd.DataFrame) -> tuple[dict[str, str], str | None]:
    player_id_column = "gsis_id" if "gsis_id" in players.columns else (
        "player_id" if "player_id" in players.columns else None
    )
    if player_id_column is None:
        return {}, None
    status_column = next(
        (
            column
            for column in ("status", "current_status", "roster_status")
            if column in players.columns
        ),
        None,
    )
    if status_column is None:
        return {}, None
    status = {}
    for row in players[[player_id_column, status_column]].itertuples(index=False):
        player_id = str(row[0])
        value = "" if pd.isna(row[1]) else str(row[1]).strip().upper()
        if player_id and player_id != "nan":
            status[player_id] = value
    return status, status_column


def explicitly_retired(status: str | None) -> bool:
    if not status:
        return False
    value = status.upper()
    return value in {"RET", "RETIRED"} or "RETIRED" in value


def metrics(rows: pd.DataFrame, pred: str, actual: str = "actual_tail") -> dict[str, float | int]:
    if rows.empty:
        return {"n": 0, "mae": float("nan"), "rmse": float("nan"), "spearman": float("nan")}
    error = rows[pred].to_numpy(float) - rows[actual].to_numpy(float)
    spearman = float(rows[pred].corr(rows[actual], method="spearman")) if len(rows) > 1 else float("nan")
    return {
        "n": int(len(rows)),
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error * error))),
        "spearman": spearman,
    }


def fit_tail_models(train: pd.DataFrame, evaluation: pd.DataFrame) -> pd.DataFrame:
    output = evaluation.copy()
    output["pred_zero_tail"] = 0.0
    for position in POSITIONS:
        tr = train[(train.position == position) & train.explicit_retired].copy()
        ev = evaluation[evaluation.position == position]
        if tr.empty or ev.empty:
            continue
        candidate_features = {
            "anchor": ["predicted_anchor_shapley"],
            "anchor_plus_pactive": [
                "predicted_anchor_shapley",
                "predicted_anchor_p_active",
            ],
        }
        for candidate, features in candidate_features.items():
            tr_fit = tr.dropna(subset=features + ["actual_tail"])
            if len(tr_fit) < max(8, len(features) + 3):
                continue
            model = LinearRegression(positive=True)
            model.fit(tr_fit[features].to_numpy(float), tr_fit.actual_tail.to_numpy(float))
            ev_fit = ev.dropna(subset=features)
            output.loc[ev_fit.index, f"pred_{candidate}"] = model.predict(
                ev_fit[features].to_numpy(float)
            )
            output.loc[ev.index, f"{candidate}_training_n"] = int(len(tr_fit))
            output.loc[ev.index, f"{candidate}_intercept"] = float(model.intercept_)
            for feature, coefficient in zip(features, model.coef_, strict=True):
                output.loc[ev.index, f"{candidate}_coef_{feature}"] = float(coefficient)
            residual = np.abs(
                model.predict(tr_fit[features].to_numpy(float))
                - tr_fit.actual_tail.to_numpy(float)
            )
            output.loc[ev.index, f"{candidate}_q80"] = float(np.quantile(residual, 0.80))
            output.loc[ev.index, f"{candidate}_q90"] = float(np.quantile(residual, 0.90))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-module", required=True)
    parser.add_argument("--model-a-rows", required=True)
    parser.add_argument("--qb-results", required=True)
    parser.add_argument("--raw-seasons", required=True)
    parser.add_argument("--players", required=True)
    parser.add_argument("--residual-states", required=True)
    parser.add_argument("--innovation-states", required=True)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    dev = load_module(args.development_module)
    _base, long, raw, players = build_inputs(dev, args)
    source_max_season = int(raw.season.max())

    eligible = list(FROZEN_ELIGIBLE_BASE_SEASONS)
    development_seasons = FROZEN_DEVELOPMENT_BASE_SEASONS
    holdout_seasons = FROZEN_HOLDOUT_BASE_SEASONS

    source = long[long.horizon == TERMINAL_ANCHOR_HORIZON]
    available = set(int(x) for x in source.base_season.unique())
    if not set(eligible).issubset(available):
        raise SystemExit(
            "frozen terminal-anchor seasons are no longer present in the source panel"
        )
    for season in eligible:
        if season + 7 > source_max_season - MIN_POST_Y8_OBSERVED_SEASONS:
            raise SystemExit(
                f"frozen terminal base {season} lacks required post-Y8 follow-up"
            )

    pred = terminal_anchor_predictions(dev, long, tuple(eligible))

    needed_actual_seasons = range(min(eligible) + 7, source_max_season + 1)
    actual_phi: dict[int, dict[str, float]] = {}
    for season in needed_actual_seasons:
        board = raw[raw.season == season][
            ["player_id", "position", "fantasy_target"]
        ].copy()
        actual_phi[season] = shapley_board(
            board,
            weight_column="fantasy_target",
            season_seed=FROZEN_SHAPLEY_SEED + season,
        )

    pred["predicted_anchor_shapley"] = np.nan
    for base_season in eligible:
        board = pred[pred.base_season == base_season][
            ["player_id", "position", "predicted_anchor_points"]
        ].copy()
        values = shapley_board(
            board,
            weight_column="predicted_anchor_points",
            season_seed=(
                FROZEN_SHAPLEY_SEED
                + base_season
                + TERMINAL_ANCHOR_HORIZON
                - 1
            ),
        )
        idx = pred.base_season == base_season
        pred.loc[idx, "predicted_anchor_shapley"] = pred.loc[
            idx, "player_id"
        ].map(values)

    status_map, status_column = player_status_map(players)
    records: list[dict[str, object]] = []
    for row in pred.itertuples():
        base = int(row.base_season)
        target_y8 = int(row.target_y8_season)
        player_id = str(row.player_id)
        total = 0.0
        observed_years = 0
        active_years = 0
        for season in range(target_y8, source_max_season + 1):
            relative_horizon = season - base + 1
            phi = float(actual_phi.get(season, {}).get(player_id, 0.0))
            total += (FROZEN_INTRINSIC_DISCOUNT ** (relative_horizon - 1)) * phi
            observed_years += 1
            if phi > 0:
                active_years += 1
        status = status_map.get(player_id)
        retired = explicitly_retired(status)
        records.append(
            {
                "base_season": base,
                "target_y8_season": target_y8,
                "player_id": player_id,
                "position": row.position,
                "predicted_anchor_points": float(row.predicted_anchor_points),
                "predicted_anchor_p_active": float(row.predicted_anchor_p_active),
                "predicted_anchor_shapley": float(row.predicted_anchor_shapley),
                "actual_tail": total,
                "tail_observed_seasons": observed_years,
                "tail_active_seasons": active_years,
                "player_status": status,
                "explicit_retired": retired,
                "right_censored": not retired,
                "split": "holdout" if base in holdout_seasons else "development",
            }
        )
    rows = pd.DataFrame(records)

    development = rows[rows.split == "development"].copy()
    holdout = rows[rows.split == "holdout"].copy()
    scored = fit_tail_models(development, holdout)

    metric_rows = []
    for candidate in ("zero_tail", "anchor", "anchor_plus_pactive"):
        column = f"pred_{candidate}"
        available = scored[scored.explicit_retired & scored[column].notna()] if column in scored else scored.iloc[0:0]
        result = metrics(available, column) if column in scored else metrics(available, "pred_zero_tail")
        metric_rows.append({"candidate": candidate, **result})
    metric_frame = pd.DataFrame(metric_rows)

    coverage_rows = []
    for candidate in ("anchor", "anchor_plus_pactive"):
        pred_col = f"pred_{candidate}"
        for level in (80, 90):
            q_col = f"{candidate}_q{level}"
            if pred_col not in scored or q_col not in scored:
                continue
            z = scored[
                scored.explicit_retired
                & scored[pred_col].notna()
                & scored[q_col].notna()
            ].copy()
            if z.empty:
                continue
            lower = np.maximum(0.0, z[pred_col] - z[q_col])
            upper = z[pred_col] + z[q_col]
            coverage_rows.append(
                {
                    "candidate": candidate,
                    "nominal": level / 100.0,
                    "n": int(len(z)),
                    "coverage": float(
                        ((z.actual_tail >= lower) & (z.actual_tail <= upper)).mean()
                    ),
                }
            )
    coverage = pd.DataFrame(coverage_rows)

    censoring = (
        rows.groupby(["split", "position"], dropna=False)
        .agg(
            n=("player_id", "size"),
            explicit_retired=("explicit_retired", "sum"),
            right_censored=("right_censored", "sum"),
            mean_observed_tail=("actual_tail", "mean"),
        )
        .reset_index()
    )
    censoring["right_censored_rate"] = censoring.right_censored / censoring.n

    metric_frame.to_csv(OUT / "TAIL_HOLDOUT_METRICS.csv", index=False)
    coverage.to_csv(OUT / "TAIL_HOLDOUT_COVERAGE.csv", index=False)
    censoring.to_csv(OUT / "TAIL_CENSORING.csv", index=False)
    rows.to_csv(OUT / "TAIL_RESEARCH_ROWS.csv", index=False)
    scored.to_csv(OUT / "TAIL_HOLDOUT_ROWS.csv", index=False)

    baseline = next(
        (row for row in metric_rows if row["candidate"] == "zero_tail"),
        {"n": 0, "mae": float("nan"), "rmse": float("nan")},
    )
    candidates = [
        row
        for row in metric_rows
        if row["candidate"] != "zero_tail" and row["n"] > 0
    ]
    best = min(candidates, key=lambda row: (row["mae"], row["rmse"])) if candidates else None

    if status_column is None or best is None:
        disposition = "INSUFFICIENT_EVIDENCE"
    elif (
        best["mae"] < baseline["mae"]
        and best["rmse"] < baseline["rmse"]
        and best["n"] >= 20
    ):
        disposition = "TAIL_AND_STATIONARY_AGGREGATION_RESEARCH_SUPPORTED"
    else:
        disposition = "TAIL_BAND_ONLY"

    result = {
        "state": "FOUNDATION4_CAREER_FORWARD_RESEARCH_HISTORICAL_FREEZE",
        "authority": "research_only_no_product_promotion",
        "disposition": disposition,
        "aggregation_candidate": {
            "name": "stationary_continuation_of_current_intrinsic_kernel",
            "discount": FROZEN_INTRINSIC_DISCOUNT,
            "interpretation": (
                "continuity hypothesis only; football outcomes do not identify a normative "
                "discount rate and no discount search was performed"
            ),
            "null_candidate": "term_structure_only_no_holistic_scalar",
        },
        "tail": {
            "anchor_horizon": "Y7",
            "tail_horizon": "Y8+",
            "frozen_forecast_candidate": FROZEN_TERMINAL_ANCHOR_CANDIDATE,
            "candidate_models": ["zero_tail_baseline", "anchor", "anchor_plus_pactive"],
            "source_max_season": source_max_season,
            "minimum_post_y8_observed_seasons": MIN_POST_Y8_OBSERVED_SEASONS,
            "development_base_seasons": development_seasons,
            "untouched_holdout_base_seasons": holdout_seasons,
            "status_column": status_column,
            "best_holdout_candidate": None if best is None else best["candidate"],
            "holdout_metrics": metric_rows,
            "coverage": coverage_rows,
        },
        "uncertainty": {
            "model_authority_separate_from_outcome_uncertainty": True,
            "cross_horizon_covariance_validated": False,
            "cumulative_standard_deviation_authorized": False,
            "right_censoring_reported": True,
        },
        "guards": {
            "current_player_inspection": False,
            "discount_search": False,
            "market_owner_team_utility_inputs": False,
            "unobserved_future_filled_with_zero": False,
            "zero_tail_promotable": False,
        },
    }
    (OUT / "RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Foundation 4 Career-Forward Tail / Aggregation Research",
        "",
        f"Disposition: **{disposition}**",
        "",
        f"Source max season: {source_max_season}",
        f"Terminal anchor: Y{TERMINAL_ANCHOR_HORIZON}",
        f"Development base seasons: {development_seasons}",
        f"Untouched terminal holdout base seasons: {holdout_seasons}",
        f"Explicit player status column: {status_column or 'UNAVAILABLE'}",
        "",
        "## Tail holdout metrics",
        "",
        metric_frame.to_markdown(index=False),
        "",
        "## Censoring",
        "",
        censoring.to_markdown(index=False),
        "",
        "## Governance",
        "",
        "- 0.85 is the existing Current Intrinsic kernel, tested only as a stationary continuation candidate.",
        "- No alternate discount or horizon-weight search was performed.",
        "- Zero tail is a diagnostic baseline and can never be promoted.",
        "- Players without explicit retired status remain right-censored; their unobserved future is never set to zero.",
        "- Any supported tail remains a coarse Research envelope until live-cohort shadow implementation and separate promotion.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    monte_carlo_shapley_scenarios,
    subset_caps_from_rules,
)

OUT = Path("artifacts/research/foundation4_career_tail_20261002")
TARGET_VERSION = "career-tail-y8plus-shapley-v1"
MODEL_VERSION = "career-tail-two-family-v1"
FEATURES = (
    "age_years",
    "experience_years",
    "log_current_points",
    "log_prior_points",
    "prior_missing",
)
CANDIDATES = ("direct_ridge", "two_part_state")
ROLLING_ORIGINS = tuple(range(2006, 2011))
FINAL_HOLDOUT_ORIGIN = 2011
RIGHT_CENSOR_BOUNDARY = 2024
RIDGE_ALPHA = 10.0
LOGIT_C = 1.0
POSITION_CATASTROPHE_RATIO = 1.15
MIN_POSITIVE_TERMINAL_ROWS = 1


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


def _lineup_capacity_signature(rules: LeagueRules) -> str:
    payload = {
        "team_count": rules.team_count,
        "caps": subset_caps_from_rules(rules),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _spearman(a: pd.Series, b: pd.Series) -> float:
    if len(a) < 2 or a.nunique() < 2 or b.nunique() < 2:
        return float("nan")
    return float(a.corr(b, method="spearman"))


def _metrics(rows: pd.DataFrame, pred_col: str) -> dict[str, float | int]:
    if rows.empty:
        return {"n": 0}
    actual = rows["tail_target"].to_numpy(float)
    pred = rows[pred_col].to_numpy(float)
    err = pred - actual
    return {
        "n": int(len(rows)),
        "rmse": float(np.sqrt(np.mean(err * err))),
        "mae": float(np.mean(np.abs(err))),
        "bias": float(np.mean(err)),
        "spearman": _spearman(rows[pred_col], rows["tail_target"]),
        "positive_actual_rate": float(np.mean(actual > 0)),
        "positive_prediction_rate": float(np.mean(pred > 0)),
    }


def _annual_shapley(
    player_seasons: pd.DataFrame,
    rules: LeagueRules,
) -> dict[tuple[int, str], float]:
    caps = subset_caps_from_rules(rules)
    output: dict[tuple[int, str], float] = {}
    for season, group in player_seasons.groupby("season", sort=True):
        players = [
            (
                str(row.player_id),
                str(row.position),
                max(0.0, float(row.fantasy_points)),
            )
            for row in group.itertuples()
            if str(row.position) in {"QB", "RB", "WR", "TE"}
        ]
        scenario_values = {
            player_id: (weight,)
            for player_id, _position, weight in players
        }
        result = monte_carlo_shapley_scenarios(
            players,
            scenario_values,
            caps,
            permutations=FROZEN_SHAPLEY_PERMUTATIONS,
            seed=FROZEN_SHAPLEY_SEED + int(season),
        )
        for player_id, values in result.estimates.items():
            output[(int(season), player_id)] = float(values[0])
    return output


def _build_rows(
    player_seasons: pd.DataFrame,
    annual_phi: dict[tuple[int, str], float],
) -> pd.DataFrame:
    source = player_seasons.copy()
    source["player_id"] = source["player_id"].astype(str)
    source["season"] = source["season"].astype(int)
    source = source[source["position"].isin(["QB", "RB", "WR", "TE"])].copy()
    last_observed = source.groupby("player_id")["season"].max().to_dict()
    point_map = {
        (str(row.player_id), int(row.season)): float(row.fantasy_points)
        for row in source.itertuples()
    }
    max_season = int(source["season"].max())

    rows: list[dict[str, object]] = []
    for row in source.itertuples():
        base = int(row.season)
        if base > FINAL_HOLDOUT_ORIGIN:
            continue
        age = None if pd.isna(row.age_years) else float(row.age_years)
        experience = (
            None
            if pd.isna(row.experience_years)
            else int(row.experience_years)
        )
        if age is None or experience is None:
            continue
        prior = point_map.get((str(row.player_id), base - 1))
        tail = sum(
            annual_phi.get((season, str(row.player_id)), 0.0)
            for season in range(base + 7, max_season + 1)
        )
        censored = int(last_observed[str(row.player_id)]) >= RIGHT_CENSOR_BOUNDARY
        rows.append(
            {
                "base_season": base,
                "player_id": str(row.player_id),
                "position": str(row.position),
                "age_years": age,
                "experience_years": float(experience),
                "log_current_points": math.log1p(
                    max(0.0, float(row.fantasy_points))
                ),
                "log_prior_points": math.log1p(
                    max(0.0, 0.0 if prior is None else float(prior))
                ),
                "prior_missing": 1.0 if prior is None else 0.0,
                "tail_target": float(tail),
                "right_censored": bool(censored),
                "last_observed_season": int(
                    last_observed[str(row.player_id)]
                ),
            }
        )
    return pd.DataFrame(rows)


def _fit_one(
    train: pd.DataFrame,
    position: str,
    model: str,
) -> dict[str, object]:
    data = train[train["position"] == position].copy()
    if len(data) < 50:
        raise ValueError(
            f"insufficient terminal training rows for {position}: {len(data)}"
        )
    x = data[list(FEATURES)].to_numpy(float)
    scaler = StandardScaler().fit(x)
    z = scaler.transform(x)
    y = data["tail_target"].to_numpy(float)

    if model == "direct_ridge":
        log_y = np.log1p(y)
        ridge = Ridge(alpha=RIDGE_ALPHA).fit(z, log_y)
        log_residual = log_y - ridge.predict(z)
        smearing_factor = float(np.mean(np.exp(log_residual)))
        return {
            "kind": model,
            "position": position,
            "feature_names": list(FEATURES),
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_scale": scaler.scale_.tolist(),
            "ridge_intercept": float(ridge.intercept_),
            "ridge_coefficients": ridge.coef_.tolist(),
            "smearing_factor": smearing_factor,
            "retransformation": "duan_smearing_training_only_v1",
        }

    positive = (y > 0).astype(int)
    if len(set(positive)) < 2 or int(positive.sum()) < MIN_POSITIVE_TERMINAL_ROWS:
        raise ValueError(
            "two-part terminal state is not identifiable for "
            f"{position}: positive_rows={int(positive.sum())} "
            f"total_rows={len(data)}"
        )
    logit = LogisticRegression(
        C=LOGIT_C,
        solver="lbfgs",
        max_iter=2000,
        random_state=20261002,
    ).fit(z, positive)
    positive_mask = positive == 1
    positive_log_y = np.log1p(y[positive_mask])
    ridge = Ridge(alpha=RIDGE_ALPHA).fit(
        z[positive_mask],
        positive_log_y,
    )
    positive_log_residual = positive_log_y - ridge.predict(z[positive_mask])
    positive_smearing_factor = float(
        np.mean(np.exp(positive_log_residual))
    )
    return {
        "kind": model,
        "position": position,
        "feature_names": list(FEATURES),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "logit_intercept": float(logit.intercept_[0]),
        "logit_coefficients": logit.coef_[0].tolist(),
        "positive_ridge_intercept": float(ridge.intercept_),
        "positive_ridge_coefficients": ridge.coef_.tolist(),
        "positive_smearing_factor": positive_smearing_factor,
        "retransformation": "duan_smearing_training_only_v1",
    }


def _linear(
    intercept: float,
    coefficients: list[float],
    x: np.ndarray,
) -> np.ndarray:
    return intercept + x @ np.asarray(coefficients, dtype=float)


def _predict_model(
    model: dict[str, object],
    rows: pd.DataFrame,
) -> np.ndarray:
    x = rows[list(FEATURES)].to_numpy(float)
    mean = np.asarray(model["scaler_mean"], dtype=float)
    scale = np.asarray(model["scaler_scale"], dtype=float)
    scale = np.where(scale == 0, 1.0, scale)
    z = (x - mean) / scale
    kind = str(model["kind"])
    if kind == "direct_ridge":
        log_tail = _linear(
            float(model["ridge_intercept"]),
            list(model["ridge_coefficients"]),
            z,
        )
        smearing_factor = float(model["smearing_factor"])
        return np.maximum(
            0.0,
            np.exp(log_tail) * smearing_factor - 1.0,
        )

    logits = _linear(
        float(model["logit_intercept"]),
        list(model["logit_coefficients"]),
        z,
    )
    probability = 1.0 / (
        1.0 + np.exp(-np.clip(logits, -40, 40))
    )
    positive_log_tail = _linear(
        float(model["positive_ridge_intercept"]),
        list(model["positive_ridge_coefficients"]),
        z,
    )
    conditional = np.maximum(
        0.0,
        np.exp(positive_log_tail)
        * float(model["positive_smearing_factor"])
        - 1.0,
    )
    return probability * conditional


def _fit_models(
    train: pd.DataFrame,
) -> dict[tuple[str, str], dict[str, object]]:
    return {
        (position, model): _fit_one(train, position, model)
        for position in ("QB", "RB", "WR", "TE")
        for model in CANDIDATES
    }


def _predict(
    rows: pd.DataFrame,
    fitted: dict[tuple[str, str], dict[str, object]],
) -> pd.DataFrame:
    out = rows.copy()
    out["zero_tail"] = 0.0
    for model in CANDIDATES:
        out[model] = 0.0
        for position in ("QB", "RB", "WR", "TE"):
            mask = out["position"] == position
            if mask.any():
                out.loc[mask, model] = _predict_model(
                    fitted[(position, model)],
                    out.loc[mask],
                )
    return out


def _rolling_validation(rows: pd.DataFrame) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    scored = rows[~rows["right_censored"]].copy()
    for origin in ROLLING_ORIGINS:
        test = scored[scored["base_season"] == origin].copy()
        if test.empty:
            continue
        test_player_ids = set(test["player_id"].astype(str))
        train = scored[
            (scored["base_season"] < origin)
            & (~scored["player_id"].astype(str).isin(test_player_ids))
        ].copy()
        if train.empty:
            continue
        if set(train["player_id"].astype(str)) & test_player_ids:
            raise AssertionError(
                "rolling validation player groups must be disjoint"
            )
        fitted = _fit_models(train)
        predicted = _predict(test, fitted)
        predicted["validation_origin"] = origin
        predicted["validation_train_rows"] = len(train)
        predicted["validation_train_players"] = train["player_id"].nunique()
        predicted["validation_test_players"] = len(test_player_ids)
        predicted["validation_player_overlap"] = 0
        records.append(predicted)
    if not records:
        raise ValueError(
            "terminal research produced no rolling validation rows"
        )
    return pd.concat(records, ignore_index=True)


def _candidate_disposition(
    rolling: pd.DataFrame,
) -> tuple[list[str], list[dict[str, object]]]:
    disposition: list[dict[str, object]] = []
    zero_all = _metrics(rolling, "zero_tail")
    supported: list[str] = []
    for model in CANDIDATES:
        overall = _metrics(rolling, model)
        position_rows = []
        catastrophe = False
        for position in ("QB", "RB", "WR", "TE"):
            sub = rolling[rolling["position"] == position]
            candidate = _metrics(sub, model)
            zero = _metrics(sub, "zero_tail")
            ratio = (
                float(candidate["rmse"])
                / max(1e-12, float(zero["rmse"]))
                if int(candidate["n"]) > 0
                and float(zero["rmse"]) > 0
                else float("inf")
            )
            catastrophe = (
                catastrophe
                or ratio > POSITION_CATASTROPHE_RATIO
            )
            position_rows.append(
                {
                    "position": position,
                    "candidate": candidate,
                    "zero_tail": zero,
                    "rmse_ratio_vs_zero": ratio,
                }
            )
        passes = (
            float(overall["rmse"]) < float(zero_all["rmse"])
            and math.isfinite(float(overall["spearman"]))
            and float(overall["spearman"]) > 0
            and not catastrophe
            and bool(
                np.isfinite(
                    rolling[model].to_numpy(float)
                ).all()
            )
            and bool((rolling[model] >= 0).all())
        )
        if passes:
            supported.append(model)
        disposition.append(
            {
                "model": model,
                "passes": passes,
                "overall": overall,
                "zero_tail_overall": zero_all,
                "positions": position_rows,
            }
        )
    if not supported:
        raise ValueError(
            "no terminal candidate cleared the frozen promotion gates"
        )
    return supported, disposition


def _residual_bands(
    rolling: pd.DataFrame,
    supported: list[str],
) -> dict[str, dict[str, dict[str, float]]]:
    output: dict[str, dict[str, dict[str, float]]] = {}
    for model in supported:
        output[model] = {}
        for position in ("QB", "RB", "WR", "TE"):
            sub = rolling[rolling["position"] == position]
            residual = np.abs(
                sub["tail_target"].to_numpy(float)
                - sub[model].to_numpy(float)
            )
            output[model][position] = {
                "q80": float(np.quantile(residual, 0.80)),
                "q90": float(np.quantile(residual, 0.90)),
                "n": int(len(residual)),
            }
    return output


def _holdout_summary(
    holdout: pd.DataFrame,
    supported: list[str],
    residuals: dict[str, dict[str, dict[str, float]]],
) -> dict[str, object]:
    output: dict[str, object] = {
        "base_season": FINAL_HOLDOUT_ORIGIN,
        "scored_rows": int(len(holdout)),
        "models": {},
    }
    for model in supported:
        output["models"][model] = {
            "overall": _metrics(holdout, model),
            "positions": {
                position: _metrics(
                    holdout[
                        holdout["position"] == position
                    ],
                    model,
                )
                for position in ("QB", "RB", "WR", "TE")
            },
        }

    central_low = holdout[supported].min(axis=1).to_numpy(float)
    central_high = holdout[supported].max(axis=1).to_numpy(float)
    actual = holdout["tail_target"].to_numpy(float)
    output["model_authority_envelope_coverage"] = float(
        np.mean(
            (actual >= central_low)
            & (actual <= central_high)
        )
    )

    for level in ("q80", "q90"):
        lows = []
        highs = []
        for row in holdout.itertuples():
            model_lows = []
            model_highs = []
            for model in supported:
                band = residuals[model][str(row.position)][level]
                prediction = float(getattr(row, model))
                model_lows.append(
                    max(0.0, prediction - band)
                )
                model_highs.append(prediction + band)
            lows.append(min(model_lows))
            highs.append(max(model_highs))
        output[f"combined_outer_{level[1:]}_coverage"] = float(
            np.mean(
                (actual >= np.asarray(lows))
                & (actual <= np.asarray(highs))
            )
        )
    return output


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-seasons", required=True)
    parser.add_argument("--out-dir", default=str(OUT))
    parser.add_argument(
        "--scoring-coordinate",
        default="frozen_standard_non_ppr_fantasy_points",
    )
    args = parser.parse_args()

    OUT = Path(args.out_dir)
    OUT.mkdir(parents=True, exist_ok=True)
    player_seasons = pd.read_csv(args.player_seasons)
    rules = _rules()
    signature = _lineup_capacity_signature(rules)

    annual_phi = _annual_shapley(player_seasons, rules)
    rows = _build_rows(player_seasons, annual_phi)
    rows.to_csv(OUT / "TAIL_RESEARCH_ROWS.csv", index=False)

    rolling = _rolling_validation(rows)
    rolling.to_csv(
        OUT / "ROLLING_VALIDATION.csv",
        index=False,
    )
    supported, disposition = _candidate_disposition(rolling)
    residuals = _residual_bands(rolling, supported)

    scored = rows[~rows["right_censored"]].copy()
    holdout = scored[
        scored["base_season"] == FINAL_HOLDOUT_ORIGIN
    ].copy()
    holdout_player_ids = set(holdout["player_id"].astype(str))
    train = scored[
        (scored["base_season"] <= 2010)
        & (~scored["player_id"].astype(str).isin(holdout_player_ids))
    ].copy()
    if set(train["player_id"].astype(str)) & holdout_player_ids:
        raise AssertionError(
            "final holdout player groups must be disjoint"
        )
    fitted_pre_holdout = _fit_models(train)
    holdout = _predict(holdout, fitted_pre_holdout)
    holdout.to_csv(
        OUT / "FINAL_HOLDOUT_PREDICTIONS.csv",
        index=False,
    )
    holdout_summary = _holdout_summary(
        holdout,
        supported,
        residuals,
    )

    final_train = scored[
        scored["base_season"]
        <= FINAL_HOLDOUT_ORIGIN
    ].copy()
    final_fitted = _fit_models(final_train)
    final_supported = {
        model: {
            position: final_fitted[(position, model)]
            for position in ("QB", "RB", "WR", "TE")
        }
        for model in supported
    }

    holdout_all = rows[
        rows["base_season"] == FINAL_HOLDOUT_ORIGIN
    ]
    censoring = {
        "overall_rows": int(len(rows)),
        "censored_rows": int(
            rows["right_censored"].sum()
        ),
        "censored_rate": float(
            rows["right_censored"].mean()
        ),
        "holdout_total_rows": int(
            len(holdout_all)
        ),
        "holdout_censored_rows": int(
            holdout_all["right_censored"].sum()
        ),
        "holdout_by_position": {
            position: {
                "total": int(
                    len(
                        holdout_all[
                            holdout_all["position"]
                            == position
                        ]
                    )
                ),
                "censored": int(
                    holdout_all[
                        (
                            holdout_all["position"]
                            == position
                        )
                        & holdout_all[
                            "right_censored"
                        ]
                    ].shape[0]
                ),
            }
            for position in ("QB", "RB", "WR", "TE")
        },
    }

    evidence = {
        "target_version": TARGET_VERSION,
        "model_version": MODEL_VERSION,
        "scoring_coordinate": args.scoring_coordinate,
        "authority": "coarse_set_valued_terminal",
        "raw_quantity": (
            "cumulative_governed_shapley_"
            "marginal_fantasy_points_y8_plus"
        ),
        "supported_models": supported,
        "features": list(FEATURES),
        "candidate_disposition": disposition,
        "rolling_origins": list(ROLLING_ORIGINS),
        "fit_identifiability": {
            "minimum_positive_rows": MIN_POSITIVE_TERMINAL_ROWS,
            "semantics": (
                "solver identifiability guard only; model adequacy is governed "
                "by frozen out-of-sample promotion gates"
            ),
        },
        "final_holdout_origin": FINAL_HOLDOUT_ORIGIN,
        "right_censor_boundary": RIGHT_CENSOR_BOUNDARY,
        "censoring": censoring,
        "residual_bands": residuals,
        "final_holdout": holdout_summary,
        "validation_governance": {
            "split_unit": "player_id",
            "rolling_training_excludes_validation_player_ids": True,
            "final_holdout_training_excludes_holdout_player_ids": True,
            "rolling_validation_player_overlap": int(
                rolling["validation_player_overlap"].max()
            ),
            "final_holdout_player_overlap": 0,
        },
        "retransformation": {
            "method": "duan_smearing_training_only_v1",
            "direct_ridge_target": "expected_original_scale_tail",
            "two_part_positive_magnitude_target": (
                "expected_original_scale_positive_tail"
            ),
        },
        "lineup_capacity_signature": signature,
        "league_rules": rules.model_dump(mode="json"),
        "shapley_permutations": (
            FROZEN_SHAPLEY_PERMUTATIONS
        ),
        "shapley_seed": FROZEN_SHAPLEY_SEED,
        "fitted_models": final_supported,
        "aggregation_semantics": {
            "career_forward_raw": (
                "sum annual raw Shapley Y1-Y7 "
                "+ direct cumulative tail Y8+"
            ),
            "discounting": "none",
            "display_indexes_combined": False,
            "current_intrinsic_replaced": False,
            "cumulative_outcome_sd_authorized": False,
        },
        "limitations": [
            (
                "terminal labels are retrospective "
                "completed-career outcomes, not "
                "historically real-time available labels"
            ),
            (
                "right-censored rows are excluded "
                "rather than treated as zero"
            ),
            (
                "terminal artifact is valid only for "
                "the matching lineup-capacity signature"
            ),
            (
                "terminal artifact is valid only for its declared scoring "
                "coordinate; cross-coordinate aggregation is forbidden"
            ),
            (
                "model-family spread is model-authority "
                "uncertainty, not an outcome confidence interval"
            ),
            (
                "rolling and final-holdout validation are grouped by player "
                "to prevent overlapping-career target leakage"
            ),
            (
                "log-scale terminal magnitude models use training-only Duan "
                "smearing to target expected original-scale cumulative tail"
            ),
        ],
    }
    (OUT / "TERMINAL_TAIL_EVIDENCE.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report = [
        "# Foundation 4 Career-Tail Research",
        "",
        (
            "Supported terminal models: **"
            + ", ".join(supported)
            + "**."
        ),
        (
            "Lineup-capacity signature: "
            + signature
            + "."
        ),
        (
            "Scoring coordinate: **"
            + str(args.scoring_coordinate)
            + "**."
        ),
        (
            "Rolling validation rows: **"
            + str(len(rolling))
            + "** with zero train/test player overlap."
        ),
        (
            "Untouched 2011 holdout scored rows: **"
            + str(len(holdout))
            + "**."
        ),
        (
            "Holdout censored rows excluded: **"
            + str(censoring["holdout_censored_rows"])
            + " / "
            + str(censoring["holdout_total_rows"])
            + "**."
        ),
        "",
        "## Candidate disposition",
        "",
    ]
    for row in disposition:
        overall = row["overall"]
        report.append(
            "- "
            + str(row["model"])
            + ": "
            + ("PASS" if row["passes"] else "FAIL")
            + "; RMSE "
            + f"{overall['rmse']:.3f}"
            + "; MAE "
            + f"{overall['mae']:.3f}"
            + "; Spearman "
            + f"{overall['spearman']:.3f}."
        )
    report += [
        "",
        "## Untouched final holdout",
        "",
    ]
    for model in supported:
        metric = holdout_summary["models"][model]["overall"]
        report.append(
            "- "
            + model
            + ": RMSE "
            + f"{metric['rmse']:.3f}"
            + "; MAE "
            + f"{metric['mae']:.3f}"
            + "; Spearman "
            + f"{metric['spearman']:.3f}."
        )
    report += [
        (
            "- central model-envelope coverage: "
            + f"{holdout_summary['model_authority_envelope_coverage']:.1%}"
        ),
        (
            "- combined outer 80 coverage: "
            + f"{holdout_summary['combined_outer_80_coverage']:.1%}"
        ),
        (
            "- combined outer 90 coverage: "
            + f"{holdout_summary['combined_outer_90_coverage']:.1%}"
        ),
        "",
        "## Governed interpretation",
        "",
        (
            "The Y8+ tail is a direct cumulative career Shapley "
            "quantity. It is not a perpetuity, carried Y8 value, "
            "discount extrapolation, or terminal multiplier."
        ),
        (
            "Rolling and final-holdout validation are grouped by player; "
            "no evaluated player's overlapping career rows enter that "
            "split's training set."
        ),
        (
            "Log-target models use training-only Duan smearing so the "
            "terminal prediction targets expected original-scale Y8+ mass."
        ),
        (
            "Supported-model spread is retained as model-authority "
            "uncertainty. Empirical residual bands remain separate "
            "ordinary outcome uncertainty."
        ),
        (
            "The holistic career-forward raw coordinate may sum "
            "annual Y1-Y7 raw Shapley contributions plus this tail "
            "because all terms share the same marginal-lineup "
            "fantasy-point unit."
        ),
        (
            "Current Intrinsic remains the separate discounted "
            "Y1-Y3 product lens."
        ),
    ]
    (OUT / "RESEARCH_CLOSEOUT.md").write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )
    print("\n".join(report))


if __name__ == "__main__":
    main()

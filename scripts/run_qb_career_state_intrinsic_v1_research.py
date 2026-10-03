from __future__ import annotations

"""Bounded QB career-state challenger for the final Intrinsic v1 release check.

This study asks one question only: does separating QB meaningful-starting-role
probability from conditional fantasy production beat Intrinsic v1's conservative
QB carry-forward policy?  It deliberately reuses the existing PR #131 point-in-
time feature pipeline, uses one transparent pooled logistic model, and does not
fit a second conditional-production model.

Final holdout seasons (2017-2022), model definition, label, features and gates
below are frozen before final holdout scoring.  For a test source season T,
training examples are eligible only when their target season is < T, so every
label was resolved before the test season began.
"""

import argparse
import csv
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

import run_career_persistence_feature_layer_research as study
import run_career_persistence_feature_layer_research_v2  # noqa: F401; installs governed Calibration

DEV_START = 2005
HOLDOUT_SEASONS = tuple(range(2017, 2023))
MEANINGFUL_STARTER_ATTEMPTS = 200.0

# Small, predeclared football-state set.  These fields are all known at the
# source-season cutoff and come from the already governed/offline feature layer.
FEATURES = (
    "age",
    "experience",
    "draft_pick_pct",
    "games_pct",
    "opportunity_pct",
    "role_mean_2",
    "role_vol_2",
    "qb_established_starter_seasons",
    "production_percentile",
    "horizon",
)

# Frozen acceptance gates.  They intentionally demand material improvement over
# PR #133's QB carry-forward rather than mere calibration-model significance.
Y2_MAE_GAIN = 0.02
Y3_MAE_GAIN = 0.02
CUMULATIVE_MAE_GAIN = 0.03
ELITE_CUMULATIVE_GAIN = 0.05
FOLD_WIN_RATE = 0.60
MAX_FOLD_HARM = 0.10
BRIER_GAIN_VS_BASE_RATE = 0.05
MIN_AUC = 0.70
MAX_ECE = 0.10
MAX_RANK_HARM = 0.01
MAX_UPWARD_STATE_RATE = 0.05


@dataclass(frozen=True)
class QBExample:
    player_id: str
    source_season: int
    target_season: int
    horizon: int
    current_points: float
    target_points: float
    target_starter: int
    features: tuple[float, ...]
    elite: bool


@dataclass(frozen=True)
class LogisticModel:
    means: np.ndarray
    scales: np.ndarray
    beta: np.ndarray

    def predict(self, raw: np.ndarray) -> np.ndarray:
        z = (raw - self.means) / self.scales
        design = np.column_stack([np.ones(len(z)), z])
        linear = np.clip(design @ self.beta, -35.0, 35.0)
        return 1.0 / (1.0 + np.exp(-linear))


def safe_age(row: study.Row) -> float:
    return float(row.age) if row.age is not None else 27.0


def raw_features(row: study.Row, horizon: int) -> tuple[float, ...]:
    f = row.features
    return (
        safe_age(row),
        float(row.experience),
        float(f.get("draft_pick_pct", 0.0)),
        float(f.get("games_pct", 0.0)),
        float(f.get("opportunity_pct", 0.0)),
        float(f.get("role_mean_2", 0.0)),
        float(f.get("role_vol_2", 0.0)),
        float(f.get("qb_established_starter_seasons", 0.0)),
        float(row.percentile),
        float(horizon),
    )


def fit_logistic(examples: list[QBExample]) -> LogisticModel:
    if not examples:
        raise RuntimeError("QB career-state model has no training examples")
    X = np.asarray([e.features for e in examples], dtype=float)
    y = np.asarray([e.target_starter for e in examples], dtype=float)
    means = X.mean(axis=0)
    scales = X.std(axis=0)
    scales[scales < 1e-9] = 1.0
    Z = (X - means) / scales
    D = np.column_stack([np.ones(len(Z)), Z])
    beta = np.zeros(D.shape[1], dtype=float)

    # Standard maximum-likelihood logistic regression.  The tiny diagonal term
    # is numerical stabilization only, not a tuned regularization coefficient.
    for _ in range(100):
        linear = np.clip(D @ beta, -35.0, 35.0)
        p = 1.0 / (1.0 + np.exp(-linear))
        w = np.clip(p * (1.0 - p), 1e-8, None)
        gradient = D.T @ (y - p)
        hessian = (D.T * w) @ D
        hessian[1:, 1:] += np.eye(D.shape[1] - 1) * 1e-8
        try:
            delta = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            delta = np.linalg.pinv(hessian) @ gradient
        beta += delta
        if float(np.max(np.abs(delta))) < 1e-8:
            break
    return LogisticModel(means=means, scales=scales, beta=beta)


def percentile(values: list[float], q: float) -> float:
    return study.percentile(values, q)


def build_examples(
    rows: list[study.Row],
    stats: dict[tuple[str, int], dict[str, float]],
) -> list[QBExample]:
    qbs = [r for r in rows if r.position == "QB" and r.current > 0]
    by_season: dict[int, list[study.Row]] = {}
    for row in qbs:
        by_season.setdefault(row.season, []).append(row)

    out: list[QBExample] = []
    realized = study.realized_map(rows)
    for season, season_rows in sorted(by_season.items()):
        elite_cut = percentile([r.current for r in season_rows], 0.75)
        for row in season_rows:
            for horizon in (1, 2):
                target_season = season + horizon
                target_stat = stats.get((row.player_id, target_season), {})
                attempts = study.safe_float(target_stat.get("attempts"), 0.0)
                out.append(
                    QBExample(
                        player_id=row.player_id,
                        source_season=season,
                        target_season=target_season,
                        horizon=horizon,
                        current_points=row.current,
                        target_points=realized.get((row.player_id, target_season), 0.0),
                        target_starter=1 if attempts >= MEANINGFUL_STARTER_ATTEMPTS else 0,
                        features=raw_features(row, horizon),
                        elite=row.current >= elite_cut,
                    )
                )
    return out


def rankdata(values: list[float]) -> list[float]:
    if not values:
        return []
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def pearson(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(a) != len(b):
        return math.nan
    aa = np.asarray(a, dtype=float)
    bb = np.asarray(b, dtype=float)
    if float(aa.std()) < 1e-12 or float(bb.std()) < 1e-12:
        return math.nan
    return float(np.corrcoef(aa, bb)[0, 1])


def spearman(a: list[float], b: list[float]) -> float:
    return pearson(rankdata(a), rankdata(b))


def mae(pred: Iterable[float], actual: Iterable[float]) -> float:
    pairs = list(zip(pred, actual))
    return statistics.mean(abs(p - a) for p, a in pairs) if pairs else math.nan


def brier(prob: list[float], actual: list[int]) -> float:
    return statistics.mean((p - y) ** 2 for p, y in zip(prob, actual)) if prob else math.nan


def auc(prob: list[float], actual: list[int]) -> float:
    pos = [p for p, y in zip(prob, actual) if y == 1]
    neg = [p for p, y in zip(prob, actual) if y == 0]
    if not pos or not neg:
        return math.nan
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def ece(prob: list[float], actual: list[int], bins: int = 10) -> float:
    if not prob:
        return math.nan
    total = len(prob)
    acc = 0.0
    for idx in range(bins):
        lo = idx / bins
        hi = (idx + 1) / bins
        members = [(p, y) for p, y in zip(prob, actual) if lo <= p < hi or (idx == bins - 1 and p == 1.0)]
        if not members:
            continue
        mean_p = statistics.mean(p for p, _ in members)
        mean_y = statistics.mean(y for _, y in members)
        acc += len(members) / total * abs(mean_p - mean_y)
    return acc


def rel_gain(base: float, challenger: float) -> float:
    return (base - challenger) / base if base and math.isfinite(base) else math.nan


def bounded_for_fold(rows: list[study.Row], source_season: int) -> dict[str, tuple[float, float]]:
    # Importing the v2 runner above replaces study.Calibration with the governed
    # empirical-Bayes control used by the authoritative materializer research.
    _cal, _source, y2, y3 = study.fold_predictions(rows, source_season, (), False)
    d2 = {s.player_id: s.mean for s in y2 if s.position == "QB"}
    d3 = {s.player_id: s.mean for s in y3 if s.position == "QB"}
    return {pid: (d2.get(pid, math.nan), d3.get(pid, math.nan)) for pid in set(d2) | set(d3)}


def evaluate(rows: list[study.Row], examples: list[QBExample]) -> dict:
    by_source: dict[int, dict[int, dict[str, QBExample]]] = {}
    for e in examples:
        by_source.setdefault(e.source_season, {}).setdefault(e.horizon, {})[e.player_id] = e

    all_records: list[dict] = []
    fold_results: list[dict] = []
    coefficient_snapshots: list[dict] = []
    inference_times: list[float] = []

    for source_season in HOLDOUT_SEASONS:
        # Strict PIT: a training label's target season must be completed before
        # the test source season.  No future role outcome enters model fitting.
        train = [
            e for e in examples
            if e.source_season >= DEV_START and e.target_season < source_season
        ]
        model = fit_logistic(train)
        coefficient_snapshots.append({
            "source_season": source_season,
            "training_examples": len(train),
            "means": model.means.tolist(),
            "scales": model.scales.tolist(),
            "beta": model.beta.tolist(),
        })

        y2 = by_source.get(source_season, {}).get(1, {})
        y3 = by_source.get(source_season, {}).get(2, {})
        common = sorted(set(y2) & set(y3))
        if not common:
            continue
        X = np.asarray([y2[pid].features for pid in common] + [y3[pid].features for pid in common], dtype=float)
        t0 = time.perf_counter()
        probabilities = model.predict(X)
        inference_times.append(time.perf_counter() - t0)
        p2 = probabilities[: len(common)]
        p3 = probabilities[len(common) :]
        bounded = bounded_for_fold(rows, source_season)

        fold_carry_pred: list[float] = []
        fold_challenger_pred: list[float] = []
        fold_actual: list[float] = []
        for idx, pid in enumerate(common):
            e2, e3 = y2[pid], y3[pid]
            current = e2.current_points
            pred2 = float(p2[idx]) * current
            pred3 = float(p3[idx]) * current
            b2, b3 = bounded.get(pid, (math.nan, math.nan))
            record = {
                "player_id": pid,
                "source_season": source_season,
                "elite": e2.elite,
                "current_points": current,
                "actual_y2": e2.target_points,
                "actual_y3": e3.target_points,
                "starter_y2": e2.target_starter,
                "starter_y3": e3.target_starter,
                "prob_y2": float(p2[idx]),
                "prob_y3": float(p3[idx]),
                "challenger_y2": pred2,
                "challenger_y3": pred3,
                "carry_y2": current,
                "carry_y3": current,
                "bounded_y2": b2,
                "bounded_y3": b3,
            }
            all_records.append(record)
            fold_carry_pred.append(2.0 * current)
            fold_challenger_pred.append(pred2 + pred3)
            fold_actual.append(e2.target_points + e3.target_points)

        carry_mae = mae(fold_carry_pred, fold_actual)
        challenger_mae = mae(fold_challenger_pred, fold_actual)
        fold_results.append({
            "source_season": source_season,
            "n": len(common),
            "carry_cumulative_mae": carry_mae,
            "challenger_cumulative_mae": challenger_mae,
            "relative_improvement": rel_gain(carry_mae, challenger_mae),
        })

    def subset(records: list[dict]) -> dict:
        carry2 = [r["carry_y2"] for r in records]
        carry3 = [r["carry_y3"] for r in records]
        chall2 = [r["challenger_y2"] for r in records]
        chall3 = [r["challenger_y3"] for r in records]
        bounded2 = [r["bounded_y2"] for r in records if math.isfinite(r["bounded_y2"])]
        bounded3 = [r["bounded_y3"] for r in records if math.isfinite(r["bounded_y3"])]
        bounded_records = [r for r in records if math.isfinite(r["bounded_y2"]) and math.isfinite(r["bounded_y3"])]
        actual2 = [r["actual_y2"] for r in records]
        actual3 = [r["actual_y3"] for r in records]
        return {
            "n": len(records),
            "carry": {
                "y2_mae": mae(carry2, actual2),
                "y3_mae": mae(carry3, actual3),
                "cumulative_mae": mae([a + b for a, b in zip(carry2, carry3)], [a + b for a, b in zip(actual2, actual3)]),
                "y2_spearman": spearman(carry2, actual2),
                "y3_spearman": spearman(carry3, actual3),
                "cumulative_spearman": spearman([a + b for a, b in zip(carry2, carry3)], [a + b for a, b in zip(actual2, actual3)]),
            },
            "challenger": {
                "y2_mae": mae(chall2, actual2),
                "y3_mae": mae(chall3, actual3),
                "cumulative_mae": mae([a + b for a, b in zip(chall2, chall3)], [a + b for a, b in zip(actual2, actual3)]),
                "y2_spearman": spearman(chall2, actual2),
                "y3_spearman": spearman(chall3, actual3),
                "cumulative_spearman": spearman([a + b for a, b in zip(chall2, chall3)], [a + b for a, b in zip(actual2, actual3)]),
            },
            "bounded": {
                "n": len(bounded_records),
                "y2_mae": mae(bounded2, [r["actual_y2"] for r in bounded_records]),
                "y3_mae": mae(bounded3, [r["actual_y3"] for r in bounded_records]),
                "cumulative_mae": mae(
                    [r["bounded_y2"] + r["bounded_y3"] for r in bounded_records],
                    [r["actual_y2"] + r["actual_y3"] for r in bounded_records],
                ),
            },
        }

    overall = subset(all_records)
    elite = subset([r for r in all_records if r["elite"]])

    state: dict[str, dict] = {}
    for key, suffix in (("y2", "y2"), ("y3", "y3")):
        probs = [r[f"prob_{suffix}"] for r in all_records]
        actual = [r[f"starter_{suffix}"] for r in all_records]
        # Fold-specific base-rate comparator, estimated from prior resolved labels only.
        naive: list[float] = []
        for r in all_records:
            horizon = 1 if suffix == "y2" else 2
            prior = [
                e.target_starter for e in examples
                if e.horizon == horizon and e.source_season >= DEV_START and e.target_season < r["source_season"]
            ]
            naive.append(statistics.mean(prior) if prior else 0.5)
        elite_records = [r for r in all_records if r["elite"]]
        state[key] = {
            "brier": brier(probs, actual),
            "naive_base_rate_brier": brier(naive, actual),
            "brier_gain_vs_base_rate": rel_gain(brier(naive, actual), brier(probs, actual)),
            "auc": auc(probs, actual),
            "ece_10bin": ece(probs, actual),
            "observed_starter_rate": statistics.mean(actual) if actual else math.nan,
            "mean_predicted_probability": statistics.mean(probs) if probs else math.nan,
            "elite_brier": brier(
                [r[f"prob_{suffix}"] for r in elite_records],
                [r[f"starter_{suffix}"] for r in elite_records],
            ),
            "elite_observed_rate": statistics.mean([r[f"starter_{suffix}"] for r in elite_records]) if elite_records else math.nan,
            "elite_mean_probability": statistics.mean([r[f"prob_{suffix}"] for r in elite_records]) if elite_records else math.nan,
        }

    fold_wins = [f for f in fold_results if f["challenger_cumulative_mae"] < f["carry_cumulative_mae"]]
    worst_fold = min((f["relative_improvement"] for f in fold_results), default=math.nan)
    upward_state = statistics.mean(r["prob_y3"] > r["prob_y2"] + 0.05 for r in all_records) if all_records else math.nan
    out_of_bounds = sum(
        1 for r in all_records
        if not (0.0 <= r["prob_y2"] <= 1.0 and 0.0 <= r["prob_y3"] <= 1.0)
        or r["challenger_y2"] < 0.0 or r["challenger_y3"] < 0.0
        or r["challenger_y2"] > r["current_points"] + 1e-9
        or r["challenger_y3"] > r["current_points"] + 1e-9
    )

    gates = {
        "all_qb_y2_mae": rel_gain(overall["carry"]["y2_mae"], overall["challenger"]["y2_mae"]) >= Y2_MAE_GAIN,
        "all_qb_y3_mae": rel_gain(overall["carry"]["y3_mae"], overall["challenger"]["y3_mae"]) >= Y3_MAE_GAIN,
        "all_qb_cumulative_mae": rel_gain(overall["carry"]["cumulative_mae"], overall["challenger"]["cumulative_mae"]) >= CUMULATIVE_MAE_GAIN,
        "elite_qb_cumulative_mae": rel_gain(elite["carry"]["cumulative_mae"], elite["challenger"]["cumulative_mae"]) >= ELITE_CUMULATIVE_GAIN,
        "chronological_fold_stability": (len(fold_wins) / len(fold_results) if fold_results else 0.0) >= FOLD_WIN_RATE,
        "worst_fold_guardrail": worst_fold >= -MAX_FOLD_HARM if math.isfinite(worst_fold) else False,
        "rank_safety": overall["challenger"]["cumulative_spearman"] >= overall["carry"]["cumulative_spearman"] - MAX_RANK_HARM,
        "state_brier_y2": state["y2"]["brier_gain_vs_base_rate"] >= BRIER_GAIN_VS_BASE_RATE,
        "state_brier_y3": state["y3"]["brier_gain_vs_base_rate"] >= BRIER_GAIN_VS_BASE_RATE,
        "state_auc_y2": state["y2"]["auc"] >= MIN_AUC,
        "state_auc_y3": state["y3"]["auc"] >= MIN_AUC,
        "state_calibration_y2": state["y2"]["ece_10bin"] <= MAX_ECE,
        "state_calibration_y3": state["y3"]["ece_10bin"] <= MAX_ECE,
        "trajectory_safety": out_of_bounds == 0 and upward_state <= MAX_UPWARD_STATE_RATE,
        "point_in_time_contract": True,
        "operational_simplicity": True,
    }

    return {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "overall": overall,
        "elite": elite,
        "state": state,
        "folds": fold_results,
        "fold_win_rate": len(fold_wins) / len(fold_results) if fold_results else 0.0,
        "worst_fold_relative_improvement": worst_fold,
        "trajectory": {
            "out_of_bounds_or_production_explosions": out_of_bounds,
            "p_y3_gt_p_y2_plus_0_05_rate": upward_state,
        },
        "coefficient_snapshots": coefficient_snapshots,
        "inference_seconds_per_fold": inference_times,
        "records": all_records,
    }


def write_prediction_csv(records: list[dict], path: Path) -> None:
    if not records:
        return
    fields = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--career-panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache = args.output_dir / "cache"

    t0 = time.perf_counter()
    rows = study.build_features(args.career_panel, cache, args.output_dir)
    source_seasons = sorted({r.season for r in rows})
    stats = study.load_season_stats(list(range(min(source_seasons), max(source_seasons) + 3)), cache)
    examples = build_examples(rows, stats)
    build_seconds = time.perf_counter() - t0

    result = evaluate(rows, examples)
    final_train = [e for e in examples if e.source_season >= DEV_START and e.target_season <= 2016]
    t1 = time.perf_counter()
    final_model = fit_logistic(final_train)
    fit_seconds = time.perf_counter() - t1
    artifact = {
        "model": "pooled binary logistic regression",
        "target": f"MEANINGFUL_STARTER = pass_attempts >= {int(MEANINGFUL_STARTER_ATTEMPTS)} in target season",
        "features": FEATURES,
        "means": final_model.means.tolist(),
        "scales": final_model.scales.tolist(),
        "beta": final_model.beta.tolist(),
        "training_contract": "development artifact uses labels resolved through 2016; each holdout fold refits using only target seasons strictly before the test source season",
    }
    artifact_path = args.output_dir / "qb_career_state_model.json"
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")

    result["definition"] = {
        "state": f"binary meaningful starter: target-season pass attempts >= {int(MEANINGFUL_STARTER_ATTEMPTS)}",
        "conditional_production": "source-season fantasy points carried forward unchanged if meaningful role; expected production = predicted role probability × source fantasy points",
        "features": FEATURES,
        "model_form": "single pooled maximum-likelihood logistic regression with horizon indicator; numerical Hessian stabilizer 1e-8 only",
        "elite_evaluation": "top quartile of source-season QB fantasy production within each source season; evaluation only, never a model input",
        "holdout": HOLDOUT_SEASONS,
    }
    result["operations"] = {
        "derived_rows": len(rows),
        "qb_examples": len(examples),
        "feature_build_seconds": build_seconds,
        "final_fit_seconds": fit_seconds,
        "model_artifact_bytes": artifact_path.stat().st_size,
        "mean_inference_ms_per_holdout_fold": statistics.mean(result["inference_seconds_per_fold"]) * 1000.0 if result["inference_seconds_per_fold"] else math.nan,
        "production_storage_if_promoted": "one compact coefficient/scaler artifact; no online historical table scan",
        "cache_impact": "none for research; if promoted, model/version becomes part of Forecast provenance and existing Forecast cache fingerprint",
    }
    result["provenance"] = {
        "career_panel": "existing governed PR #131 historical career-transition panel",
        "state_and_role_inputs": "nflverse annual player regular-season stats (offline research ingestion)",
        "draft_metadata": "nflverse players release via the existing career-persistence feature layer",
        "market_inputs": "none",
        "contract_inputs": "none",
    }

    records = result.pop("records")
    (args.output_dir / "qb_career_state_results.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_prediction_csv(records, args.output_dir / "qb_career_state_holdout_predictions.csv")

    lines = [
        "# QB Career-State Challenger Result",
        "",
        f"**Decision:** {'USE QB CAREER-STATE MODEL IN V1' if result['status'] == 'PASS' else 'KEEP CURRENT CONSERVATIVE QB V1 TREATMENT'}",
        "",
        f"Target: {result['definition']['state']}.",
        f"Model: {result['definition']['model_form']}.",
        "",
        "## Holdout metrics",
        "",
        f"- Carry Y2/Y3/cumulative MAE: {result['overall']['carry']['y2_mae']:.3f} / {result['overall']['carry']['y3_mae']:.3f} / {result['overall']['carry']['cumulative_mae']:.3f}.",
        f"- Challenger Y2/Y3/cumulative MAE: {result['overall']['challenger']['y2_mae']:.3f} / {result['overall']['challenger']['y3_mae']:.3f} / {result['overall']['challenger']['cumulative_mae']:.3f}.",
        f"- Governed bounded Y2/Y3/cumulative MAE: {result['overall']['bounded']['y2_mae']:.3f} / {result['overall']['bounded']['y3_mae']:.3f} / {result['overall']['bounded']['cumulative_mae']:.3f}.",
        f"- Elite carry/challenger cumulative MAE: {result['elite']['carry']['cumulative_mae']:.3f} / {result['elite']['challenger']['cumulative_mae']:.3f}.",
        f"- Fold win rate vs carry: {result['fold_win_rate']:.3f}; worst-fold relative improvement: {result['worst_fold_relative_improvement']:.3%}.",
        f"- State Brier Y2/Y3: {result['state']['y2']['brier']:.4f} / {result['state']['y3']['brier']:.4f}.",
        f"- State AUC Y2/Y3: {result['state']['y2']['auc']:.3f} / {result['state']['y3']['auc']:.3f}.",
        f"- State ECE Y2/Y3: {result['state']['y2']['ece_10bin']:.3f} / {result['state']['y3']['ece_10bin']:.3f}.",
        f"- Challenger cumulative Spearman: {result['overall']['challenger']['cumulative_spearman']:.3f}; carry: {result['overall']['carry']['cumulative_spearman']:.3f}.",
        "",
        "## Frozen gates",
        "",
    ]
    lines.extend(f"- {'PASS' if passed else 'FAIL'} — {name}" for name, passed in result["gates"].items())
    lines.extend(["", "## Fold results", ""])
    lines.extend(
        f"- {f['source_season']}: n={f['n']}; carry {f['carry_cumulative_mae']:.3f}; challenger {f['challenger_cumulative_mae']:.3f}; change {f['relative_improvement']:.2%}."
        for f in result["folds"]
    )
    (args.output_dir / "qb_career_state_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "gates", "overall", "elite", "state", "folds", "trajectory", "operations")}, indent=2))


if __name__ == "__main__":
    main()

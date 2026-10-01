from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import statistics
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np

from fsffl.team_utility.simulation import (
    NUMPY_BATCH_SIZE_DEFAULT,
    NUMPY_PCG64_BATCHED_GAUSS_V1,
    PYTHON_RANDOM_GAUSS_V1,
    RegularSeasonSimulationInput,
    simulate_regular_season,
)
from scripts.benchmark_simulation_performance import _request


PROBABILITY_METRICS = (
    "playoff_probability",
    "first_place_probability",
    "championship_probability",
)
SCORE_QUANTILES = (0.01, 0.05, 0.50, 0.95, 0.99)
HISTOGRAM_BIN_COUNT = 256


def _run(request: RegularSeasonSimulationInput, protocol: str, *, observe: bool):
    selected = request.model_copy(
        update={
            "rng_protocol": protocol,
            "rng_batch_size": ((request.rng_batch_size or NUMPY_BATCH_SIZE_DEFAULT) if protocol == NUMPY_PCG64_BATCHED_GAUSS_V1 else None),
        }
    )
    points = wins = ranks = champions = None
    if observe:
        team_count = len({
            item.team_id
            for item in (*selected.scoring, *selected.weekly_scoring)
        })
        points = np.empty((selected.simulation_count, team_count), dtype=np.float64)
        wins = np.empty_like(points)
        ranks = np.empty((selected.simulation_count, team_count), dtype=np.int16)
        champions = np.full(selected.simulation_count, -1, dtype=np.int16)
        sample_index = 0

        def capture(trial_wins, trial_points, standings, champion):
            nonlocal sample_index
            points[sample_index, :] = trial_points
            wins[sample_index, :] = trial_wins
            ranks[sample_index, np.asarray(standings, dtype=np.intp)] = np.arange(1, team_count + 1)
            if champion is not None:
                champions[sample_index] = champion
            sample_index += 1

        started = time.perf_counter()
        result = simulate_regular_season(selected, trial_observer=capture)
        if sample_index != selected.simulation_count:
            raise AssertionError(f"observer saw {sample_index} of {selected.simulation_count} trials")
    else:
        started = time.perf_counter()
        result = simulate_regular_season(selected)
    elapsed = time.perf_counter() - started

    summary = {
        "elapsed_seconds": elapsed,
        "simulation_count": result.simulation_count,
        "seed": result.seed,
        "rng_protocol": result.rng_protocol,
        "rng_runtime_version": result.rng_runtime_version,
        "rng_batch_size": result.rng_batch_size,
        "input_fingerprint": result.simulation_input_fingerprint,
        "outcomes": [item.model_dump(mode="json") for item in result.outcomes],
        "finish_distributions": [item.model_dump(mode="json") for item in result.finish_distributions],
    }
    if observe:
        team_ids = [row.team_id for row in result.outcomes]
        weekly_by_team = {team_id: [] for team_id in team_ids}
        for item in selected.weekly_scoring:
            weekly_by_team[item.team_id].append(item)
        for item in selected.scoring:
            if not weekly_by_team[item.team_id]:
                weekly_by_team[item.team_id] = [item] * len({row.week for row in selected.schedule})
        score_histograms = {}
        score_thresholds = {}
        score_observed = {}
        score_edges = {}
        for team_id in team_ids:
            weekly = weekly_by_team[team_id]
            model_mean = sum(item.mean_points for item in weekly)
            model_sd = sum(item.stddev_points**2 for item in weekly) ** 0.5
            # Fixed from the governed weekly input distributions, before either RNG is run.
            edges = np.linspace(0.0, max(model_mean + 8.0 * model_sd, 1.0), HISTOGRAM_BIN_COUNT + 1)
            score_edges[team_id] = edges
            score_thresholds[team_id] = {
                "mean_minus_3sd": max(0.0, model_mean - 3.0 * model_sd),
                "mean_minus_2sd": max(0.0, model_mean - 2.0 * model_sd),
                "mean_plus_2sd": model_mean + 2.0 * model_sd,
                "mean_plus_3sd": model_mean + 3.0 * model_sd,
            }
        # Build compact score evidence after the one run; no trial-level cube is persisted.
        for team_index, team_id in enumerate(team_ids):
            values = points[:, team_index]
            thresholds = score_thresholds[team_id]
            score_histograms[team_id] = np.histogram(values, bins=score_edges[team_id])[0].tolist()
            ordered = np.sort(values)
            score_observed[team_id] = {
                "mean": float(values.mean()),
                "standard_deviation": float(values.std(ddof=1)),
                "lower_1pct_tail_mean": float(ordered[:max(1, int(0.01 * len(ordered)))].mean()),
                "lower_5pct_tail_mean": float(ordered[:max(1, int(0.05 * len(ordered)))].mean()),
                "upper_95pct_tail_mean": float(ordered[int(0.95 * len(ordered)):].mean()),
                "upper_99pct_tail_mean": float(ordered[int(0.99 * len(ordered)):].mean()),
                "exceedance_probability": {
                    key: float(np.mean(values >= threshold))
                    for key, threshold in thresholds.items()
                },
            }
        traced_ranks = {
            team_id: [
                float(np.mean(ranks[:, team_index] == rank))
                for rank in range(1, team_count + 1)
            ]
            for team_index, team_id in enumerate(team_ids)
        }
        for team_index, finish in enumerate(result.finish_distributions):
            if traced_ranks[finish.team_id] != list(finish.rank_probabilities):
                raise AssertionError("per-trial standings trace disagrees with published finish distribution")
        outcome_by_team = {row.team_id: row for row in result.outcomes}
        for team_index, team_id in enumerate(team_ids):
            if abs(float(wins[:, team_index].mean()) - outcome_by_team[team_id].expected_wins) > 1e-10:
                raise AssertionError("per-trial wins trace disagrees with published expected wins")
            observed_champion_rate = float(np.mean(champions == team_index))
            published_champion_rate = outcome_by_team[team_id].championship_probability
            if published_champion_rate is None:
                if np.any(champions >= 0):
                    raise AssertionError("per-trial trace published a champion while championship probability is unavailable")
                continue
            if abs(observed_champion_rate - published_champion_rate) > 1e-10:
                raise AssertionError("per-trial champion trace disagrees with published championship probability")
        summary["traced_rank_probabilities"] = traced_ranks
        summary["team_score_quantiles"] = {
            team_id: {
                str(q): float(np.quantile(points[:, index], q))
                for q in SCORE_QUANTILES
            }
            for index, team_id in enumerate(team_ids)
        }
        summary["team_score_histograms"] = score_histograms
        summary["team_score_histogram_range"] = {
            team: [float(edges[0]), float(edges[-1]), len(edges) - 1]
            for team, edges in score_edges.items()
        }
        summary["input_derived_score_thresholds"] = score_thresholds
        summary["team_score_tail_and_moment_metrics"] = score_observed
        summary["team_points_standard_deviation"] = {
            team_id: float(points[:, index].std(ddof=1))
            for index, team_id in enumerate(team_ids)
        }
        summary["trial_wins_standard_deviation"] = {
            team_id: float(wins[:, index].std(ddof=1))
            for index, team_id in enumerate(team_ids)
        }
        championship_available = all(
            outcome.championship_probability is not None for outcome in result.outcomes
        )
        summary["champion_frequency_from_trials"] = (
            {
                team_id: float(np.mean(champions == index))
                for index, team_id in enumerate(team_ids)
            }
            if championship_available
            else {team_id: None for team_id in team_ids}
        )
        summary["win_percentile_quantiles"] = {
            team_id: {
                str(q): float(np.quantile(wins[:, index], q))
                for q in SCORE_QUANTILES
            }
            for index, team_id in enumerate(team_ids)
        }
    return result, summary


def _scalar_metrics(summary):
    values = {}
    simulation_count = summary["simulation_count"]
    for row in summary["outcomes"]:
        team = row["team_id"]
        for field in (
            "expected_wins",
            "wins_stddev",
            "playoff_probability",
            "first_place_probability",
            "championship_probability",
        ):
            if row[field] is not None:
                values[f"{team}.{field}"] = row[field]
        values[f"{team}.expected_wins_mcse"] = row["wins_stddev"] / simulation_count**0.5
        for field in PROBABILITY_METRICS:
            probability = row[field]
            if probability is not None:
                values[f"{team}.{field}_mcse"] = (
                    probability * (1 - probability) / simulation_count
                ) ** 0.5
    for row in summary["finish_distributions"]:
        team = row["team_id"]
        values[f"{team}.expected_finish"] = row["expected_finish"]
        for rank, probability in enumerate(row["rank_probabilities"], start=1):
            values[f"{team}.rank_{rank}_probability"] = probability
            values[f"{team}.rank_{rank}_mcse"] = (
                probability * (1 - probability) / simulation_count
            ) ** 0.5
    for team, quantiles in summary.get("team_score_quantiles", {}).items():
        for q, value in quantiles.items():
            values[f"{team}.team_score_q{q}"] = value
    for team, quantiles in summary.get("win_percentile_quantiles", {}).items():
        for q, value in quantiles.items():
            values[f"{team}.wins_q{q}"] = value
    for team, metrics in summary.get("team_score_tail_and_moment_metrics", {}).items():
        for field in (
            "mean",
            "standard_deviation",
            "lower_1pct_tail_mean",
            "lower_5pct_tail_mean",
            "upper_95pct_tail_mean",
            "upper_99pct_tail_mean",
        ):
            values[f"{team}.points_{field}"] = metrics[field]
        for threshold, value in metrics["exceedance_probability"].items():
            values[f"{team}.score_exceedance_{threshold}"] = value
    for group in (
        "team_points_standard_deviation",
        "trial_wins_standard_deviation",
        "champion_frequency_from_trials",
    ):
        for team, value in summary.get(group, {}).items():
            if value is not None:
                values[f"{team}.{group}"] = value
    return values


def _equivalence_report(python_summaries, numpy_summaries):
    python_rows = [_scalar_metrics(row) for row in python_summaries]
    numpy_rows = [_scalar_metrics(row) for row in numpy_summaries]
    key_sets = [set(row) for row in (*python_rows, *numpy_rows)]
    if any(keys != key_sets[0] for keys in key_sets[1:]):
        raise ValueError("RNG protocols do not expose the same available Simulation metrics")
    keys = sorted(key_sets[0])
    team_count = len(python_summaries[0]["outcomes"])
    rank_count = len(python_summaries[0]["finish_distributions"][0]["rank_probabilities"])
    comparison_count = max(1, len(keys) + 2 * team_count)
    critical = NormalDist().inv_cdf(1 - 0.05 / (2 * comparison_count))
    per_key = {}
    for key in keys:
        a = [row[key] for row in python_rows]
        b = [row[key] for row in numpy_rows]
        mean_a, mean_b = statistics.mean(a), statistics.mean(b)
        se = ((statistics.variance(a) / len(a)) + (statistics.variance(b) / len(b))) ** 0.5
        radius = critical * se
        difference = mean_b - mean_a
        if key.endswith(".expected_wins"):
            margin = 0.001
        elif any(key.endswith(f".{field}") for field in PROBABILITY_METRICS):
            margin = 0.002
        else:
            margin = None
        equivalent = None if margin is None else difference - radius >= -margin and difference + radius <= margin
        per_key[key] = {
            "python_mean": mean_a,
            "numpy_mean": mean_b,
            "difference_numpy_minus_python": difference,
            "simultaneous_ci95": [difference - radius, difference + radius],
            "predeclared_margin": margin,
            "equivalent": equivalent,
        }

    team_tv = {}
    for index, outcome in enumerate(python_summaries[0]["finish_distributions"]):
        team = outcome["team_id"]
        p = np.asarray([
            [row["finish_distributions"][index]["rank_probabilities"][rank] for row in python_summaries]
            for rank in range(len(outcome["rank_probabilities"]))
        ], dtype=np.float64)
        q = np.asarray([
            [row["finish_distributions"][index]["rank_probabilities"][rank] for row in numpy_summaries]
            for rank in range(len(outcome["rank_probabilities"]))
        ], dtype=np.float64)
        diff = q.mean(axis=1) - p.mean(axis=1)
        se = np.sqrt(q.var(axis=1, ddof=1) / q.shape[1] + p.var(axis=1, ddof=1) / p.shape[1])
        radius = critical * se
        tv = 0.5 * float(np.abs(diff).sum())
        conservative_upper = 0.5 * float((np.abs(diff) + radius).sum())
        team_tv[team] = {
            "total_variation_distance": tv,
            "simultaneous_conservative_upper": conservative_upper,
            "predeclared_margin": 0.005,
            "equivalent": conservative_upper <= 0.005,
        }

    team_score_cdf = {}
    for index, outcome in enumerate(python_summaries[0]["outcomes"]):
        team = outcome["team_id"]
        edges = np.linspace(0.0, max(
            python_summaries[0]["team_score_histogram_range"][team][1],
            numpy_summaries[0]["team_score_histogram_range"][team][1],
        ), HISTOGRAM_BIN_COUNT + 1)
        hist_python = np.sum(np.asarray([
            row["team_score_histograms"][team] for row in python_summaries
        ], dtype=np.int64), axis=0)
        hist_numpy = np.sum(np.asarray([
            row["team_score_histograms"][team] for row in numpy_summaries
        ], dtype=np.int64), axis=0)
        cdf_python = np.cumsum(hist_python) / hist_python.sum()
        cdf_numpy = np.cumsum(hist_numpy) / hist_numpy.sum()
        team_score_cdf[team] = {
            "pooled_histogram_ks_distance": float(np.max(np.abs(cdf_numpy - cdf_python))),
            "simultaneous_95pct_dkw_upper_bound": min(
                1.0,
                float(np.max(np.abs(cdf_numpy - cdf_python)))
                + 2.0 * (np.log(4.0 * team_count / 0.05) / (2.0 * hist_python.sum())) ** 0.5,
            ),
            "bins": HISTOGRAM_BIN_COUNT,
            "range": [float(edges[0]), float(edges[-1])],
            "samples_per_engine": int(hist_python.sum()),
            "tail_mass_beyond_upper_histogram_edge": {
                "python": float(1.0 - hist_python.sum() / sum(row["simulation_count"] for row in python_summaries)),
                "numpy": float(1.0 - hist_numpy.sum() / sum(row["simulation_count"] for row in numpy_summaries)),
            },
        }

    def mean_expected_wins(rows, team_id):
        return statistics.mean(
            next(outcome["expected_wins"] for outcome in row["outcomes"] if outcome["team_id"] == team_id)
            for row in rows
        )

    team_ids = [row["team_id"] for row in python_summaries[0]["outcomes"]]
    order_a = sorted(team_ids, key=lambda team_id: mean_expected_wins(python_summaries, team_id), reverse=True)
    order_b = sorted(team_ids, key=lambda team_id: mean_expected_wins(numpy_summaries, team_id), reverse=True)
    inversions = sum(
        order_a.index(left) < order_a.index(right) and order_b.index(left) > order_b.index(right)
        or order_a.index(left) > order_a.index(right) and order_b.index(left) < order_b.index(right)
        for i, left in enumerate(order_a) for right in order_a[i + 1:]
    )
    failures = [key for key, item in per_key.items() if item["equivalent"] is False]
    failures += [f"{team}.rank_distribution_tv" for team, item in team_tv.items() if not item["equivalent"]]
    return {
        "confidence_level": 0.95,
        "multiple_comparison_method": "Bonferroni-normal simultaneous intervals across scalar team/rank/tail summaries",
        "root_seeds_per_engine": len(python_rows),
        "simultaneous_comparison_count": comparison_count,
        "critical_value": critical,
        "team_metrics": per_key,
        "rank_distribution_total_variation": team_tv,
        "team_score_distribution": {
            "method": "pooled 256-bin empirical CDF over independent root-seed trial histograms; simultaneous two-sample DKW upper bound controls 95% family-wise error over teams; threshold metrics are derived from fixed weekly input distributions",
            "per_team": team_score_cdf,
        },
        "team_expected_wins_order_python": order_a,
        "team_expected_wins_order_numpy": order_b,
        "team_order_pairwise_inversions": inversions,
        "failed_predeclared_equivalence_checks": failures,
        "all_predeclared_checks_pass": not failures,
        "player_scope": "The kernel consumes weekly team scoring distributions and emits team/playoff outcomes; it does not generate player-level Monte Carlo outcomes. Upstream Forecast player distributions are identical inputs and are not transformed by RNG protocol selection.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--count", type=int, default=50_000)
    parser.add_argument("--output", type=Path, default=Path("output/simulation_rng_equivalence_study.json"))
    parser.add_argument("--resource-only", action="store_true")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--protocol", choices=(PYTHON_RANDOM_GAUSS_V1, NUMPY_PCG64_BATCHED_GAUSS_V1))
    args = parser.parse_args()

    template = _request(args.count)
    if args.batch_size is not None:
        template = template.model_copy(update={"rng_batch_size": args.batch_size})
    if args.resource_only:
        if not args.protocol:
            parser.error("--resource-only requires --protocol")
        result, summary = _run(template, args.protocol, observe=False)
        print(json.dumps({
            "elapsed_seconds": summary["elapsed_seconds"],
            "simulation_count": result.simulation_count,
            "rng_protocol": result.rng_protocol,
            "rng_runtime_version": result.rng_runtime_version,
            "rng_batch_size": result.rng_batch_size,
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "full_output_sha256": hashlib.sha256(
                json.dumps(result.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }, indent=2))
        return

    python_rows = []
    numpy_rows = []
    timing = {PYTHON_RANDOM_GAUSS_V1: [], NUMPY_PCG64_BATCHED_GAUSS_V1: []}
    for index in range(args.seeds):
        seed = 20261001 + index
        request = template.model_copy(update={"seed": seed})
        old_result, old_summary = _run(request, PYTHON_RANDOM_GAUSS_V1, observe=True)
        new_result, new_summary = _run(request, NUMPY_PCG64_BATCHED_GAUSS_V1, observe=True)
        python_rows.append(old_summary)
        numpy_rows.append(new_summary)
        timing[PYTHON_RANDOM_GAUSS_V1].append(old_summary["elapsed_seconds"])
        timing[NUMPY_PCG64_BATCHED_GAUSS_V1].append(new_summary["elapsed_seconds"])
        print(
            f"seed={seed} python={old_summary['elapsed_seconds']:.3f}s "
            f"numpy={new_summary['elapsed_seconds']:.3f}s",
            flush=True,
        )

    report = _equivalence_report(python_rows, numpy_rows)
    report["fixture"] = {"teams": 12, "weeks": 14, "games": len(template.schedule), "playoff_teams": 6}
    report["simulation_count_per_seed"] = args.count
    report["root_seeds"] = [20261001, 20261001 + args.seeds - 1]
    report["timing"] = {
        protocol: {
            "median_seconds": statistics.median(values),
            "mean_seconds": statistics.mean(values),
            "samples": values,
        }
        for protocol, values in timing.items()
    }
    report["runtime"] = {"python": platform.python_version(), "numpy": np.__version__}
    report["per_seed_summaries"] = {
        PYTHON_RANDOM_GAUSS_V1: python_rows,
        NUMPY_PCG64_BATCHED_GAUSS_V1: numpy_rows,
    }
    report["resource_scope"] = "Use two fresh --resource-only processes for peak RSS; study observer retains one seed's per-trial team scores at a time."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "all_predeclared_checks_pass": report["all_predeclared_checks_pass"],
        "failed_checks": report["failed_predeclared_equivalence_checks"],
        "numpy_speedup_median": report["timing"][PYTHON_RANDOM_GAUSS_V1]["median_seconds"] / report["timing"][NUMPY_PCG64_BATCHED_GAUSS_V1]["median_seconds"],
        "python_median_seconds": report["timing"][PYTHON_RANDOM_GAUSS_V1]["median_seconds"],
        "numpy_median_seconds": report["timing"][NUMPY_PCG64_BATCHED_GAUSS_V1]["median_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()

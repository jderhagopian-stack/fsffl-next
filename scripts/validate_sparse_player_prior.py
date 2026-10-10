from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path

from fsffl.forecast.sparse_player_prior import (
    CALIBRATION_VERSION,
    PRIOR_VERSION,
    HistoricalOutcome,
    HistoricalSparsePlayerPrior,
    PriorCalibrationCase,
    RollingConformalPriorCalibrator,
    SparsePlayerProfile,
    SparsePriorAuthorityError,
)


POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def _optional_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _player_rows(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            player_id = str(row.get("gsis_id") or row.get("player_id") or "").strip()
            if not player_id:
                continue
            position = str(row.get("position") or row.get("position_group") or "").strip().upper()
            if position not in POSITIONS:
                continue
            prior = result.get(player_id)
            if prior is not None:
                old_rookie = _optional_int(prior.get("rookie_season"))
                new_rookie = _optional_int(row.get("rookie_season"))
                if old_rookie != new_rookie or prior.get("position") != position:
                    raise ValueError(f"conflicting player identity rows for {player_id}")
                continue
            result[player_id] = {**row, "position": position}
    return result


def load_outcomes(raw_path: Path, players_path: Path) -> tuple[HistoricalOutcome, ...]:
    """Build actual next-season labels for returning players and NFL rookies.

    A returning player's missing next-season stat row is an observed zero only
    because the accepted historical season source is complete and the player was
    already in the NFL player-season panel. A rookie zero is included only when
    the accepted player directory explicitly identifies that player's rookie
    season. Arbitrary absent identities/seasons are never synthesized.
    """

    player_meta = _player_rows(players_path)
    stats: dict[tuple[str, int], dict[str, str]] = {}
    raw_rows: list[dict[str, str]] = []
    with raw_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            player_id = str(row.get("player_id") or row.get("gsis_id") or "").strip()
            position = str(row.get("position_group") or row.get("position") or "").strip().upper()
            season = _optional_int(row.get("season"))
            points = _optional_float(row.get("fantasy_points"))
            if not player_id or position not in POSITIONS or season is None or points is None:
                continue
            key = (player_id, season)
            if key in stats:
                raise ValueError(f"duplicate historical player-season row: {key}")
            normalized = {**row, "player_id": player_id, "position_group": position}
            stats[key] = normalized
            raw_rows.append(normalized)
    if not raw_rows:
        raise ValueError("accepted historical panel contains no QB/RB/WR/TE outcomes")

    max_target_season = max(int(row["season"]) for row in raw_rows)
    min_target_season = min(int(row["season"]) for row in raw_rows)
    outcomes: dict[tuple[str, int], HistoricalOutcome] = {}

    # Returning players are known NFL subjects from their prior season. Project
    # their next season using only facts carried by that prior row; all target
    # points are labels observed after that target season completes.
    for row in raw_rows:
        prior_season = int(row["season"])
        target_season = prior_season + 1
        if target_season > max_target_season:
            continue
        player_id = row["player_id"]
        target = stats.get((player_id, target_season))
        points = float(target["fantasy_points"]) if target is not None else 0.0
        age = _optional_float(row.get("age"))
        experience = _optional_int(row.get("years_of_experience"))
        if age is not None:
            age += 1.0
        if experience is not None:
            experience += 1
        position = str(row["position_group"])
        key = (player_id, target_season)
        outcomes[key] = HistoricalOutcome(
            player_id=f"nflverse:{player_id}",
            position=position,
            season=target_season,
            age_years=age,
            experience_years=experience,
            fantasy_points=points,
            scoring_coordinate="standard_non_ppr",
            observed_at=datetime(target_season + 1, 2, 1, tzinfo=UTC),
        )

    # Rookie cohorts include NFL-listed players even when their first season had
    # no stat row. This prevents the prior from being trained only on rookies who
    # immediately produced fantasy points.
    rookie_keys: set[tuple[str, int]] = set()
    for player_id, meta in player_meta.items():
        rookie_season = _optional_int(meta.get("rookie_season"))
        if (
            rookie_season is None
            or rookie_season < min_target_season
            or rookie_season > max_target_season
        ):
            continue
        key = (player_id, rookie_season)
        if key in outcomes or key in rookie_keys:
            continue
        rookie_keys.add(key)
        target = stats.get(key)
        points = float(target["fantasy_points"]) if target is not None else 0.0
        age = _optional_float(target.get("age")) if target is not None else None
        if age is None:
            birth = str(meta.get("birth_date") or "").strip()
            try:
                birth_date = datetime.fromisoformat(birth).date()
                age = (datetime(rookie_season, 9, 1).date() - birth_date).days / 365.2425
            except ValueError:
                age = None
        outcomes[key] = HistoricalOutcome(
            player_id=f"nflverse:{player_id}",
            position=str(meta["position"]),
            season=rookie_season,
            age_years=age,
            experience_years=0,
            fantasy_points=points,
            scoring_coordinate="standard_non_ppr",
            observed_at=datetime(rookie_season + 1, 2, 1, tzinfo=UTC),
        )
    return tuple(sorted(outcomes.values(), key=lambda row: (row.season, row.position, row.player_id)))


def _wilson(successes: int, count: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if count == 0:
        return 0.0, 0.0
    observed = successes / count
    denominator = 1.0 + z * z / count
    center = (observed + z * z / (2 * count)) / denominator
    margin = z * math.sqrt(observed * (1 - observed) / count + z * z / (4 * count * count)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def validate_rolling_origin(
    outcomes: tuple[HistoricalOutcome, ...],
    *,
    history_window_seasons: int | None,
) -> dict[str, object]:
    by_season: dict[int, list[HistoricalOutcome]] = defaultdict(list)
    for row in outcomes:
        by_season[row.season].append(row)
    first_season = min(by_season)
    last_season = max(by_season)
    cases: list[PriorCalibrationCase] = []
    validated: dict[tuple[str, str], list[tuple[object, ...]]] = defaultdict(list)
    calibrated_count = 0
    authority_failures: dict[str, int] = defaultdict(int)

    for evaluation_season in range(first_season + 1, last_season + 1):
        as_of = datetime(evaluation_season, 9, 1, tzinfo=UTC)
        prior = HistoricalSparsePlayerPrior(
            outcomes,
            history_window_seasons=history_window_seasons,
        )
        calibrator = RollingConformalPriorCalibrator(cases) if cases else None
        for actual in by_season.get(evaluation_season, ()):
            for evidence_tier, age, experience in (
                ("known_age_experience", actual.age_years, actual.experience_years),
                ("sparse_position_only", None, None),
            ):
                profile = SparsePlayerProfile(
                    player_id=actual.player_id,
                    position=actual.position,
                    evaluation_season=evaluation_season,
                    as_of=as_of,
                    age_years=age,
                    experience_years=experience,
                )
                try:
                    base = prior.forecast(profile)
                except SparsePriorAuthorityError as exc:
                    authority_failures[exc.reason] += 1
                    continue
                if calibrator is not None:
                    try:
                        predicted = calibrator.calibrate(base, as_of=as_of)
                    except SparsePriorAuthorityError as exc:
                        authority_failures[exc.reason] += 1
                    else:
                        calibrated_count += 1
                        validated[(actual.position, evidence_tier)].append(
                            (
                                actual.fantasy_points,
                                base.p25 <= actual.fantasy_points <= base.p75,
                                predicted.p25 <= actual.fantasy_points <= predicted.p75,
                                base.p10 <= actual.fantasy_points <= base.p90,
                                predicted.p10 <= actual.fantasy_points <= predicted.p90,
                                *(actual.fantasy_points <= getattr(base, f"p{q}") for q in (10, 25, 50, 75, 90)),
                                *(actual.fantasy_points <= getattr(predicted, f"p{q}") for q in (10, 25, 50, 75, 90)),
                            )
                        )
                cases.append(
                    PriorCalibrationCase(
                        position=actual.position,
                        evidence_tier=base.evidence_tier,
                        evaluation_season=evaluation_season,
                        observed_at=actual.observed_at,
                        actual=actual.fantasy_points,
                        p10=base.p10,
                        p25=base.p25,
                        p75=base.p75,
                        p90=base.p90,
                    )
                )

    metrics: dict[str, object] = {}
    for (position, evidence_tier), rows in sorted(validated.items()):
        count = len(rows)
        intervals = {}
        for label, index, nominal in (
            ("base_50", 1, 0.50),
            ("calibrated_50", 2, 0.50),
            ("base_80", 3, 0.80),
            ("calibrated_80", 4, 0.80),
        ):
            success = sum(bool(row[index]) for row in rows)
            low, high = _wilson(success, count)
            intervals[label] = {
                "nominal": nominal,
                "covered": success,
                "count": count,
                "observed": success / count if count else None,
                "wilson_95": [low, high],
            }
        quantiles = {}
        for quantile_index, q in enumerate((10, 25, 50, 75, 90)):
            base_hit_index = 5 + quantile_index
            calibrated_hit_index = 10 + quantile_index
            base_hits = sum(bool(row[base_hit_index]) for row in rows)
            calibrated_hits = sum(bool(row[calibrated_hit_index]) for row in rows)
            quantiles[f"p{q}"] = {
                "nominal_cdf": q / 100,
                "base_observed_cdf": base_hits / count if count else None,
                "calibrated_observed_cdf": calibrated_hits / count if count else None,
                "count": count,
            }
        metrics[f"{position}|{evidence_tier}"] = {
            "position": position,
            "evidence_tier": evidence_tier,
            "count": count,
            "intervals": intervals,
            "quantiles": quantiles,
        }
    return {
        "schema_version": "fsffl-sparse-player-prior-rolling-calibration-v1",
        "prior_version": PRIOR_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "coordinate": "standard_non_ppr",
        "history_window_seasons": history_window_seasons,
        "evaluation_seasons": [first_season + 1, last_season],
        "historical_outcome_count": len(outcomes),
        "rolling_calibration_cases": len(cases),
        "calibrated_holdout_forecasts": calibrated_count,
        "authority_failures": dict(sorted(authority_failures.items())),
        "by_position": metrics,
        "limitations": [
            "Historical input is the accepted nflverse-derived player-season panel.",
            "Sparse position-only validation deliberately withholds player age and experience from the predictor.",
            "Prior calibration does not supply the P0 candidate feature packet or league scoring translation.",
            "A production Forecast is ready only when the exact State, canonical identity, scoring authority, and compatible calibration artifact are attached.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-player-seasons", required=True)
    parser.add_argument("--players", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--history-window-seasons", type=int, default=15)
    args = parser.parse_args()
    raw_path = Path(args.raw_player_seasons)
    players_path = Path(args.players)
    outcomes = load_outcomes(raw_path, players_path)
    report = validate_rolling_origin(
        outcomes,
        history_window_seasons=args.history_window_seasons,
    )
    report["input_sha256"] = {
        "raw_player_seasons": _file_sha256(raw_path),
        "players": _file_sha256(players_path),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "historical_outcome_count": report["historical_outcome_count"],
        "rolling_calibration_cases": report["rolling_calibration_cases"],
        "calibrated_holdout_forecasts": report["calibrated_holdout_forecasts"],
        "by_position": report["by_position"],
        "output": str(output),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

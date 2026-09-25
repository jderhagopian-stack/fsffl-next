from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsffl.forecast.k_dst_calibration import (
    DST_REDUCED_2024_FINGERPRINT,
    K_REDUCED_2024_FINGERPRINT,
    KDstCalibrationSample,
    WeeklyRealizedScore,
    evaluate_calibration_fingerprint_compatibility,
    evaluate_k_dst_season_error_holdout,
    fit_k_dst_season_error,
    fit_k_dst_weekly_volatility,
)
from fsffl.state.models import LeagueRules, LineupRequirement, RosterSlot, ScoringRule


def test_season_error_harness_enforces_two_source_gate() -> None:
    samples = (
        KDstCalibrationSample(
            subject_key="K:k1",
            season=2024,
            projected_points=140,
            realized_points=120,
            independent_source_count=1,
        ),
        KDstCalibrationSample(
            subject_key="K:k2",
            season=2024,
            projected_points=150,
            realized_points=160,
            independent_source_count=2,
        ),
    )

    result = fit_k_dst_season_error(samples)

    assert result.sample_size == 1
    assert result.seasons == (2024,)
    assert result.relative_rmse == pytest.approx(10 / 150)


def test_weekly_volatility_uses_realized_games_not_season_mean_division() -> None:
    scores = (
        WeeklyRealizedScore(subject_key="DST:DEN", season=2024, week=1, points=4),
        WeeklyRealizedScore(subject_key="DST:DEN", season=2024, week=2, points=10),
        WeeklyRealizedScore(subject_key="DST:DEN", season=2024, week=3, points=7),
        WeeklyRealizedScore(subject_key="DST:BUF", season=2024, week=1, points=8),
        WeeklyRealizedScore(subject_key="DST:BUF", season=2024, week=2, points=2),
    )

    result = fit_k_dst_weekly_volatility(scores)

    assert result.observation_count == 5
    assert result.subject_count == 2
    assert result.pooled_coefficient_of_variation > 0


def test_weekly_volatility_fails_closed_without_repeated_game_evidence() -> None:
    with pytest.raises(ValueError, match="two games"):
        fit_k_dst_weekly_volatility(
            (
                WeeklyRealizedScore(
                    subject_key="K:k1",
                    season=2024,
                    week=1,
                    points=10,
                ),
            )
        )


def _replay_fixture() -> dict[str, object]:
    path = Path(__file__).parent / "fixtures" / "k_dst_2024_reduced_fingerprint_replay.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_retained_replay_fixture_reproduces_research_k_dst_empirical_results() -> None:
    fixture = _replay_fixture()
    expected = fixture["expected"]

    k_samples = tuple(KDstCalibrationSample(**item) for item in fixture["k_season_samples"])
    dst_samples = tuple(KDstCalibrationSample(**item) for item in fixture["dst_season_samples"])
    k_season = fit_k_dst_season_error(k_samples)
    dst_season = fit_k_dst_season_error(dst_samples)

    def weekly(grouped: dict[str, list[list[float]]]) -> tuple[WeeklyRealizedScore, ...]:
        output: list[WeeklyRealizedScore] = []
        for subject_key, values in grouped.items():
            for week, points in values:
                output.append(
                    WeeklyRealizedScore(
                        subject_key=subject_key,
                        season=2024,
                        week=int(week),
                        points=float(points),
                    )
                )
        return tuple(output)

    k_weekly = fit_k_dst_weekly_volatility(weekly(fixture["k_weekly_points"]))
    dst_weekly = fit_k_dst_weekly_volatility(weekly(fixture["dst_weekly_points"]))

    assert k_season.sample_size == 34
    assert k_season.mean_projection == pytest.approx(expected["k_season"]["mean_projection"])
    assert k_season.relative_rmse == pytest.approx(0.38418847933549305)
    assert dst_season.sample_size == 30
    assert dst_season.mean_projection == pytest.approx(expected["dst_season"]["mean_projection"])
    assert dst_season.relative_rmse == pytest.approx(0.21402833115231343)
    assert k_weekly.observation_count == 542
    assert k_weekly.subject_count == 42
    assert k_weekly.pooled_coefficient_of_variation == pytest.approx(0.5223274618193781)
    assert dst_weekly.observation_count == 544
    assert dst_weekly.subject_count == 32
    assert dst_weekly.pooled_coefficient_of_variation == pytest.approx(0.6381941339011228)


def test_empirical_replay_has_deterministic_non_promoting_holdout_diagnostics() -> None:
    fixture = _replay_fixture()
    k_samples = tuple(KDstCalibrationSample(**item) for item in fixture["k_season_samples"])
    dst_samples = tuple(KDstCalibrationSample(**item) for item in fixture["dst_season_samples"])

    k_holdout = evaluate_k_dst_season_error_holdout(k_samples)
    dst_holdout = evaluate_k_dst_season_error_holdout(dst_samples)

    assert k_holdout.train_sample_size + k_holdout.holdout_sample_size == 34
    assert dst_holdout.train_sample_size + dst_holdout.holdout_sample_size == 30
    assert 0 <= k_holdout.holdout_within_one_train_floor_rate <= 1
    assert 0 <= dst_holdout.holdout_within_one_train_floor_rate <= 1
    assert k_holdout.train_relative_rmse > 0
    assert dst_holdout.train_relative_rmse > 0


def test_reduced_fingerprints_are_not_compatible_with_hodor_total_scoring() -> None:
    hodor = LeagueRules(
        team_count=12,
        roster_size=20,
        lineup=(
            LineupRequirement(slot=RosterSlot.K, count=1),
            LineupRequirement(slot=RosterSlot.DST, count=1),
        ),
        scoring=(
            ScoringRule(stat="fgm_0_19", points=3),
            ScoringRule(stat="fgm_20_29", points=3),
            ScoringRule(stat="fgm_30_39", points=3),
            ScoringRule(stat="fgm_40_49", points=4),
            ScoringRule(stat="fgm_50_59", points=5),
            ScoringRule(stat="fgm_60p", points=6),
            ScoringRule(stat="fgmiss", points=-1),
            ScoringRule(stat="xpm", points=1),
            ScoringRule(stat="xpmiss", points=-1),
            ScoringRule(stat="sack", points=1),
            ScoringRule(stat="int", points=2),
            ScoringRule(stat="ff", points=1),
            ScoringRule(stat="fum_rec", points=2),
            ScoringRule(stat="blk_kick", points=2),
            ScoringRule(stat="def_td", points=6),
            ScoringRule(stat="pts_allow_0", points=10),
        ),
    )

    k = evaluate_calibration_fingerprint_compatibility(K_REDUCED_2024_FINGERPRINT, hodor)
    dst = evaluate_calibration_fingerprint_compatibility(DST_REDUCED_2024_FINGERPRINT, hodor)

    assert k.compatible is False
    assert "fgm_60p" in k.missing_from_fingerprint
    assert dst.compatible is False
    assert "pts_allow_0" in dst.missing_from_fingerprint


def test_reduced_fingerprint_can_only_be_compatible_with_exact_same_family_scoring() -> None:
    k_rules = LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.K, count=1),),
        scoring=tuple(
            ScoringRule(stat=stat, points=points)
            for stat, points in K_REDUCED_2024_FINGERPRINT.rule_weights
        ),
    )
    dst_rules = LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.DST, count=1),),
        scoring=tuple(
            ScoringRule(stat=stat, points=points)
            for stat, points in DST_REDUCED_2024_FINGERPRINT.rule_weights
        ),
    )

    assert evaluate_calibration_fingerprint_compatibility(
        K_REDUCED_2024_FINGERPRINT, k_rules
    ).compatible
    assert evaluate_calibration_fingerprint_compatibility(
        DST_REDUCED_2024_FINGERPRINT, dst_rules
    ).compatible

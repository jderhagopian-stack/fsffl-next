"""Research-only tests for neutral current-competitive-strength estimator."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from fsffl.analytics.competitive_power_research import (
    CurrentTeamPrior,
    PregameTeamObservation,
    StrengthCalibration,
    estimate_competitive_strength,
)

AS_OF = datetime(2026, 11, 17, 22, tzinfo=timezone.utc)
FIRST_KICKOFF = datetime(2026, 11, 5, 23, tzinfo=timezone.utc)
FORECAST_AT = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
COMPLETED_AT = datetime(2026, 11, 10, 10, tzinfo=timezone.utc)


def _prior(tid, mean=110.0, starters=None):
    return CurrentTeamPrior(
        tid, mean, 28.0, 12.0, frozenset(starters or ("one", "two")),
        AS_OF - timedelta(minutes=3), "fixture-current"
    )


def _observation(tid, actual, expected=110.0, starters=None, week=10):
    return PregameTeamObservation(
        tid, week, expected, actual, 28.0, frozenset(starters or ("one", "two")),
        FORECAST_AT, FIRST_KICKOFF, COMPLETED_AT, "fixture-historical"
    )


def _rank(priors, observations):
    return estimate_competitive_strength(priors, observations, as_of=AS_OF, next_week=11)


def test_equal_priors_without_history_remain_tied_and_flag_no_evidence():
    rows = _rank((_prior("b"), _prior("a")), ())
    assert [r.team_id for r in rows] == ["a", "b"]
    assert all(r.neutral_allplay_win_rate == pytest.approx(.5) for r in rows)
    assert all(r.observed_weeks == 0 and r.effective_observations == 0 for r in rows)


def test_observed_outperformance_changes_strength_without_a_record_bonus():
    rows = _rank((_prior("a"), _prior("b")),
                 (_observation("a", 145), _observation("b", 110)))
    assert rows[0].team_id == "a"
    assert rows[0].posterior_correction_points > 0
    assert rows[1].posterior_correction_points < 0
    assert rows[0].posterior_correction_points < 35  # shrinkage


def test_shared_leaguewide_forecast_bias_is_not_individual_skill():
    rows = _rank((_prior("a"), _prior("b")),
                 (_observation("a", 133), _observation("b", 133)))
    assert all(row.posterior_correction_points == pytest.approx(0) for row in rows)


def test_complete_starter_turnover_ignores_stale_residual():
    rows = _rank((_prior("a", starters=("new",)), _prior("b")),
                 (_observation("a", 160, starters=("old",)), _observation("b", 110)))
    assert next(row for row in rows if row.team_id == "a").posterior_correction_points == 0


def test_outlier_in_one_week_is_shrunk_and_clipped():
    rows = _rank((_prior("a"), _prior("b")),
                 (_observation("a", 10000), _observation("b", 110)))
    delta = next(row for row in rows if row.team_id == "a").posterior_correction_points
    assert 0 < delta < 15


def test_future_and_leaky_evidence_fail_closed():
    with pytest.raises(ValueError, match="future"):
        _rank((_prior("a"), _prior("b")),
              (_observation("a", 120, week=11), _observation("b", 110, week=11)))
    with pytest.raises(ValueError, match="future"):
        estimate_competitive_strength((_prior("a"), _prior("b")), (),
            as_of=AS_OF - timedelta(hours=1), next_week=11)
    with pytest.raises(ValueError, match="predate"):
        PregameTeamObservation("a", 10, 100, 110, 20, frozenset(("one",)),
            FIRST_KICKOFF, FIRST_KICKOFF, COMPLETED_AT, "invalid")


def test_incomplete_week_and_mismatched_league_are_rejected():
    with pytest.raises(ValueError, match="cover every league"):
        _rank((_prior("a"), _prior("b")), (_observation("a", 130),))
    with pytest.raises(ValueError, match="outside current league"):
        _rank((_prior("a"), _prior("b")),
              (_observation("a", 130), _observation("foreign", 130)))


def test_duplicate_and_invalid_priors_fail():
    with pytest.raises(ValueError, match="duplicate"):
        _rank((_prior("a"), _prior("a")), ())
    with pytest.raises(ValueError, match="finite"):
        _prior("a", float("nan"))


def test_model_strength_is_not_record_or_championship_odds():
    rows = _rank((_prior("strong", 135), _prior("weak", 90)), ())
    assert rows[0].team_id == "strong"
    assert rows[0].neutral_allplay_win_rate > .5
    assert all(row.posterior_correction_sd == pytest.approx(12.0) for row in rows)


def test_same_week_allplay_is_one_observation_not_eleven_independent_results():
    rows = _rank((_prior("a"), _prior("b"), _prior("c")),
                 (_observation("a", 140), _observation("b", 105), _observation("c", 104)))
    assert all(row.observed_weeks == 1 for row in rows)
    assert all(row.effective_observations <= 1 for row in rows)


def test_older_evidence_has_less_influence_than_recent_evidence():
    new_obs = (_observation("a", 135), _observation("b", 110))
    old_obs = tuple(replace(row, week=5) for row in new_obs)
    newer = _rank((_prior("a"), _prior("b")), new_obs)
    older = _rank((_prior("a"), _prior("b")), old_obs)
    assert newer[0].posterior_correction_points > older[0].posterior_correction_points


def test_calibration_rejects_invalid_parameters_and_is_explicitly_configurable():
    with pytest.raises(ValueError, match="finite"):
        StrengthCalibration(half_life_weeks=float("inf"))
    result = estimate_competitive_strength((_prior("a"), _prior("b")),
        (), as_of=AS_OF, next_week=11,
        calibration=StrengthCalibration(half_life_weeks=2, residual_clip_sd=2))
    assert result[0].observed_weeks == 0
